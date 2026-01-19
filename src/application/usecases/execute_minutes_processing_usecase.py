"""議事録処理実行ユースケース

議事録一覧画面から発言抽出処理を実行するためのユースケース。
GCSまたはPDFから議事録テキストを取得し、MinutesProcessingServiceを使用して
発言を抽出してデータベースに保存します。
"""

from dataclasses import dataclass
from datetime import datetime

from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.dtos.minutes_processing_dto import MinutesProcessingResultDTO
from src.application.exceptions import ProcessingError
from src.application.usecases.update_statement_from_extraction_usecase import (
    UpdateStatementFromExtractionUseCase,
)
from src.common.logging import get_logger
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker
from src.domain.interfaces.minutes_divider_service import IMinutesDividerService
from src.domain.interfaces.role_name_mapping_service import IRoleNameMappingService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.services.interfaces.storage_service import IStorageService
from src.domain.services.interfaces.unit_of_work import IUnitOfWork
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.domain.value_objects.speaker_speech import SpeakerSpeech


logger = get_logger(__name__)


@dataclass
class ExecuteMinutesProcessingDTO:
    """議事録処理実行リクエストDTO"""

    meeting_id: int
    force_reprocess: bool = False


class ExecuteMinutesProcessingUseCase:
    """議事録処理実行ユースケース

    議事録一覧画面から発言抽出処理を実行するユースケース。
    GCSテキストまたはPDFから議事録を取得し、発言を抽出して保存します。
    """

    def __init__(
        self,
        speaker_domain_service: SpeakerDomainService,
        minutes_processing_service: IMinutesProcessingService,
        storage_service: IStorageService,
        unit_of_work: IUnitOfWork,
        update_statement_usecase: UpdateStatementFromExtractionUseCase,
        role_name_mapping_service: IRoleNameMappingService | None = None,
        minutes_divider_service: IMinutesDividerService | None = None,
    ):
        """ユースケースを初期化する

        Args:
            speaker_domain_service: 発言者ドメインサービス
            minutes_processing_service: 議事録処理サービス
            storage_service: ストレージサービス
            unit_of_work: Unit of Work for transaction management
            update_statement_usecase: Statement更新UseCase（抽出ログ統合）
            role_name_mapping_service: 役職-人名マッピング抽出サービス（オプション）
            minutes_divider_service: 議事録分割サービス（境界検出用、オプション）
        """
        self.speaker_service = speaker_domain_service
        self.minutes_processing_service = minutes_processing_service
        self.storage_service = storage_service
        self.uow = unit_of_work
        self.update_statement_usecase = update_statement_usecase
        self.role_name_mapping_service = role_name_mapping_service
        self.minutes_divider_service = minutes_divider_service

    async def execute(
        self, request: ExecuteMinutesProcessingDTO
    ) -> MinutesProcessingResultDTO:
        """議事録処理を実行する

        Args:
            request: 処理リクエストDTO

        Returns:
            MinutesProcessingResultDTO: 処理結果

        Raises:
            ValueError: 会議が見つからない、処理可能なソースがない場合
            APIKeyError: APIキーが設定されていない場合
            ProcessingError: 処理中にエラーが発生した場合
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            # 会議情報を取得
            meeting = await self.uow.meeting_repository.get_by_id(request.meeting_id)
            if not meeting:
                raise ValueError(f"Meeting {request.meeting_id} not found")

            # 既存の議事録をチェック
            if meeting.id is None:
                raise ValueError("Meeting must have an ID")

            existing_minutes = await self.uow.minutes_repository.get_by_meeting(
                meeting.id
            )

            # 既存のConversationsをチェック・削除
            if existing_minutes and existing_minutes.id:
                conversations = await self.uow.conversation_repository.get_by_minutes(
                    existing_minutes.id
                )
                if conversations:
                    if not request.force_reprocess:
                        raise ValueError(
                            f"Meeting {meeting.id} already has conversations"
                        )
                    else:
                        # 強制再処理の場合は既存conversationsを削除
                        logger.info(
                            f"Deleting {len(conversations)} existing conversations "
                            f"for force reprocessing"
                        )
                        for conv in conversations:
                            if conv.id:
                                await self.uow.conversation_repository.delete(conv.id)
                        # Flush to ensure deletions are applied
                        await self.uow.flush()
                        logger.info("Existing conversations deleted")

            # 議事録テキストを取得
            extracted_text = await self._fetch_minutes_text(meeting)

            # 役職-人名マッピングを抽出
            role_name_mappings = await self._extract_role_name_mappings(extracted_text)

            # Minutes レコードを作成または取得
            if not existing_minutes:
                minutes = Minutes(
                    meeting_id=meeting.id,
                    url=meeting.url,
                    role_name_mappings=role_name_mappings,
                )
                minutes = await self.uow.minutes_repository.create(minutes)
                # Flush to make foreign key available for conversations
                await self.uow.flush()
                logger.info(f"Minutes created and flushed: id={minutes.id}")
            else:
                minutes = existing_minutes
                # 既存のMinutesの場合もマッピングを更新
                if role_name_mappings and minutes.id:
                    await self.uow.minutes_repository.update_role_name_mappings(
                        minutes.id, role_name_mappings
                    )
                    logger.info(f"Updated role_name_mappings for minutes {minutes.id}")

            # 議事録を処理（役職-人名マッピングを渡す: Issue #946）
            results = await self._process_minutes(
                extracted_text, meeting.id, role_name_mappings
            )

            # Conversationsを保存
            if minutes.id is None:
                raise ValueError("Minutes must have an ID")

            saved_conversations = await self._save_conversations(results, minutes.id)

            # Speakersを抽出・作成
            unique_speakers = await self._extract_and_create_speakers(
                saved_conversations
            )

            # トランザクションをコミット（単一コミット）
            await self.uow.commit()
            logger.info("Transaction committed successfully")

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            return MinutesProcessingResultDTO(
                minutes_id=minutes.id if minutes.id is not None else 0,
                meeting_id=meeting.id if meeting.id is not None else 0,
                total_conversations=len(saved_conversations),
                unique_speakers=unique_speakers,
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
                role_name_mappings=role_name_mappings,
            )

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Minutes processing failed: {e}", exc_info=True)
            # エラー時はロールバック
            await self.uow.rollback()
            logger.info("Transaction rolled back")
            raise

    async def _fetch_minutes_text(self, meeting: Meeting) -> str:
        """議事録テキストを取得する

        優先順位:
        1. GCSテキストURI
        2. GCS PDF URI

        Args:
            meeting: 会議エンティティ

        Returns:
            str: 議事録テキスト

        Raises:
            ValueError: 処理可能なソースが見つからない場合
        """
        if meeting.gcs_text_uri:
            # GCSからテキストを取得
            try:
                data = await self.storage_service.download_file(meeting.gcs_text_uri)
                if data:
                    text = data.decode("utf-8")
                    logger.info(
                        f"Downloaded text from GCS ({len(text)} characters)",
                        meeting_id=meeting.id,
                    )
                    return text
            except Exception as e:
                logger.warning(f"Failed to download from GCS: {e}")

        # PDFからのテキスト抽出（See: Issue #981）
        if meeting.gcs_pdf_uri:
            raise ValueError(
                f"PDF processing not yet implemented for meeting {meeting.id}"
            )

        raise ValueError(f"No valid source found for meeting {meeting.id}")

    async def _process_minutes(
        self,
        text: str,
        meeting_id: int,
        role_name_mappings: dict[str, str] | None = None,
    ) -> list[SpeakerSpeech]:
        """議事録を処理して発言を抽出する

        Args:
            text: 議事録テキスト
            meeting_id: 会議ID
            role_name_mappings: 役職-人名マッピング辞書（例: {"議長": "伊藤条一"}）
                発言者名が役職のみの場合に実名に変換（Issue #946）

        Returns:
            list[SpeakerSpeech]: 抽出された発言リスト（ドメイン値オブジェクト）
        """
        if not text:
            raise ProcessingError("No text provided for processing", {"text_length": 0})

        logger.info(f"Processing minutes (text length: {len(text)})")

        # 注入された議事録処理サービスを使用（マッピングを渡す: Issue #946）
        results = await self.minutes_processing_service.process_minutes(
            text, role_name_mappings=role_name_mappings
        )

        logger.info(f"Extracted {len(results)} conversations")
        return results

    async def _save_conversations(
        self, results: list[SpeakerSpeech], minutes_id: int
    ) -> list[Conversation]:
        """発言をデータベースに保存する（抽出ログ統合版）

        Issue #865: Statement処理パイプラインへの抽出ログ統合
        - Conversationを作成後、UseCaseで抽出ログを記録

        Args:
            results: 抽出された発言データ（ドメイン値オブジェクト）
            minutes_id: 議事録ID

        Returns:
            list[Conversation]: 保存された発言エンティティリスト
        """
        conversations: list[Conversation] = []
        for idx, result in enumerate(results):
            conv = Conversation(
                minutes_id=minutes_id,
                speaker_name=result.speaker,
                comment=result.speech_content,
                sequence_number=idx + 1,
            )
            conversations.append(conv)

        # バルク作成
        saved = await self.uow.conversation_repository.bulk_create(conversations)
        logger.info(
            f"Created {len(saved)} conversations in database", minutes_id=minutes_id
        )

        # 各Conversationに対して話者マッチングと抽出ログを記録
        # Issue #865: Statement処理パイプラインへの抽出ログ統合
        for idx, (conv, result) in enumerate(zip(saved, results, strict=True)):
            if conv.id is None:
                logger.warning(f"Conversation {idx} has no ID, skipping extraction log")
                continue

            try:
                # 話者マッチング: speaker_nameからSpeakerを検索してspeaker_idを設定
                speaker_id = None
                if result.speaker:
                    # 名前から政党情報を抽出
                    clean_name, party_info = (
                        self.speaker_service.extract_party_from_name(result.speaker)
                    )
                    # Speakerを検索
                    existing_speaker = (
                        await self.uow.speaker_repository.get_by_name_party_position(
                            clean_name, party_info, None
                        )
                    )
                    if existing_speaker and existing_speaker.id:
                        speaker_id = existing_speaker.id
                        logger.debug(
                            f"Matched speaker: {result.speaker} "
                            f"-> Speaker ID {speaker_id}",
                            conversation_id=conv.id,
                        )

                # 抽出結果を作成
                extraction_result = ConversationExtractionResult(
                    comment=result.speech_content,
                    speaker_name=result.speaker,
                    speaker_id=speaker_id,  # マッチしたspeaker_idを設定
                    sequence_number=idx + 1,
                    minutes_id=minutes_id,
                )

                # UseCaseで更新（抽出ログ自動記録）
                await self.update_statement_usecase.execute(
                    entity_id=conv.id,
                    extraction_result=extraction_result,
                    pipeline_version="minutes-divider-v1",
                )
                logger.debug(
                    f"Extraction log saved for conversation {conv.id}",
                    conversation_id=conv.id,
                    speaker_id=speaker_id,
                )

            except Exception as e:
                # 抽出ログ記録エラーは警告レベル（処理は継続）
                logger.warning(
                    f"Failed to save extraction log for conversation {conv.id}: {e}",
                    conversation_id=conv.id,
                    error=str(e),
                )

        logger.info(
            f"Saved {len(saved)} conversations with extraction logs",
            minutes_id=minutes_id,
        )
        return saved

    async def _extract_and_create_speakers(
        self, conversations: list[Conversation]
    ) -> int:
        """発言から一意な発言者を抽出し、発言者レコードを作成する

        Args:
            conversations: 発言エンティティのリスト

        Returns:
            int: 作成された発言者数
        """
        speaker_names: set[tuple[str, str | None]] = set()

        for conv in conversations:
            if conv.speaker_name:
                # 名前から政党情報を抽出
                clean_name, party_info = self.speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        # 発言者レコードを作成
        created_count = 0
        for name, party_info in speaker_names:
            # 既存の発言者をチェック
            existing = await self.uow.speaker_repository.get_by_name_party_position(
                name, party_info, None
            )

            if not existing:
                # 新規発言者を作成
                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # 政党があれば政治家と仮定
                )
                await self.uow.speaker_repository.create(speaker)
                created_count += 1

        logger.info(f"Created {created_count} new speakers")
        return created_count

    async def _extract_role_name_mappings(
        self, minutes_text: str
    ) -> dict[str, str] | None:
        """議事録テキストから役職-人名マッピングを抽出する

        Args:
            minutes_text: 議事録テキスト

        Returns:
            dict[str, str] | None: 役職-人名マッピング、抽出できない場合はNone
        """
        if not self.role_name_mapping_service:
            logger.debug(
                "Role name mapping service not configured, skipping extraction"
            )
            return None

        if not minutes_text:
            return None

        try:
            # 境界検出で出席者部分を取得
            attendee_text = minutes_text
            if self.minutes_divider_service:
                boundary = await self.minutes_divider_service.detect_attendee_boundary(
                    minutes_text
                )
                if boundary.boundary_found and boundary.boundary_text:
                    attendee_text, _ = (
                        self.minutes_divider_service.split_minutes_by_boundary(
                            minutes_text, boundary
                        )
                    )
                    logger.info(
                        f"Attendee section extracted: {len(attendee_text)} chars"
                    )

            # 役職-人名マッピングを抽出
            result = await self.role_name_mapping_service.extract_role_name_mapping(
                attendee_text
            )

            if result.mappings:
                mappings_dict = result.to_dict()
                logger.info(
                    f"Extracted {len(mappings_dict)} role-name mappings "
                    f"with confidence {result.confidence}"
                )
                # マッピング内容を詳細ログで出力（Issue #946）
                for role, name in mappings_dict.items():
                    logger.info(f"  役職マッピング: {role} → {name}")
                return mappings_dict

            logger.debug("No role-name mappings found in minutes")
            return None

        except Exception as e:
            logger.warning(f"Failed to extract role-name mappings: {e}")
            return None
