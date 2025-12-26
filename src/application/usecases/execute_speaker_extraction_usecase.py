"""発言者抽出実行ユースケース

このモジュールは、議事録一覧画面から発言者抽出処理を実行するユースケースを提供します。
既存のConversationsから発言者を抽出し、Speakerレコードを作成します。
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.conversation import Conversation
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.speaker_domain_service import SpeakerDomainService


logger = logging.getLogger(__name__)


@dataclass
class ExecuteSpeakerExtractionDTO:
    """発言者抽出実行リクエストDTO"""

    meeting_id: int
    force_reprocess: bool = False


@dataclass
class SpeakerExtractionResultDTO:
    """発言者抽出結果DTO"""

    meeting_id: int
    total_conversations: int
    unique_speakers: int
    new_speakers: int
    existing_speakers: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


class ExecuteSpeakerExtractionUseCase:
    """発言者抽出実行ユースケース

    既存のConversationsから発言者を抽出し、Speakerレコードを作成します。
    """

    def __init__(
        self,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        speaker_domain_service: SpeakerDomainService,
    ):
        """ユースケースを初期化する

        Args:
            minutes_repository: 議事録リポジトリ
            conversation_repository: 発言リポジトリ
            speaker_repository: 発言者リポジトリ
            speaker_domain_service: 発言者ドメインサービス
        """
        self.minutes_repo = minutes_repository
        self.conversation_repo = conversation_repository
        self.speaker_repo = speaker_repository
        self.speaker_service = speaker_domain_service

    async def execute(
        self, request: ExecuteSpeakerExtractionDTO
    ) -> SpeakerExtractionResultDTO:
        """発言者抽出処理を実行する

        Args:
            request: 処理リクエストDTO

        Returns:
            SpeakerExtractionResultDTO: 処理結果

        Raises:
            ValueError: Conversationsが存在しない、既にSpeakersが存在する場合
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            # 議事録を取得
            minutes = await self.minutes_repo.get_by_meeting(request.meeting_id)
            if not minutes or not minutes.id:
                raise ValueError(f"No minutes found for meeting {request.meeting_id}")

            # Conversationsを取得
            conversations = await self.conversation_repo.get_by_minutes(minutes.id)
            if not conversations:
                raise ValueError(
                    f"No conversations found for meeting {request.meeting_id}"
                )

            logger.info(
                f"Found {len(conversations)} conversations "
                f"for meeting {request.meeting_id}"
            )

            # 既存のSpeaker linkをチェック・クリア
            conversations_with_speakers = [
                c for c in conversations if c.speaker_id is not None
            ]
            if conversations_with_speakers:
                if not request.force_reprocess:
                    raise ValueError(
                        f"Meeting {request.meeting_id} already has "
                        f"{len(conversations_with_speakers)} "
                        f"conversations with speakers linked"
                    )
                else:
                    # 強制再処理の場合は既存のspeaker linkをクリア
                    logger.info(
                        f"Clearing speaker links for "
                        f"{len(conversations_with_speakers)} conversations "
                        f"for force reprocessing"
                    )
                    for conv in conversations_with_speakers:
                        conv.speaker_id = None
                        if conv.id:
                            await self.conversation_repo.update(conv)
                    logger.info("Speaker links cleared")

            # 発言者を抽出・作成
            extraction_result = await self._extract_and_create_speakers(conversations)

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            return SpeakerExtractionResultDTO(
                meeting_id=request.meeting_id,
                total_conversations=len(conversations),
                unique_speakers=extraction_result["unique_speakers"],
                new_speakers=extraction_result["new_speakers"],
                existing_speakers=extraction_result["existing_speakers"],
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Speaker extraction failed: {e}", exc_info=True)
            raise

    async def _extract_and_create_speakers(
        self, conversations: list[Conversation]
    ) -> dict[str, int]:
        """発言から一意な発言者を抽出し、発言者レコードを作成し、conversationsにリンクする

        Args:
            conversations: 発言エンティティのリスト

        Returns:
            dict: 抽出結果の統計情報
                - unique_speakers: ユニークな発言者数
                - new_speakers: 新規作成された発言者数
                - existing_speakers: 既存の発言者数
        """
        speaker_names: set[tuple[str, str | None]] = set()

        # 全conversationsから発言者名を抽出
        for conv in conversations:
            if conv.speaker_name:
                # 名前から政党情報を抽出
                clean_name, party_info = self.speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        logger.info(f"Found {len(speaker_names)} unique speaker names")

        # 発言者レコードを作成し、conversationsにリンク
        new_speakers = 0
        existing_speakers = 0
        linked_conversations = 0

        for name, party_info in speaker_names:
            # 既存の発言者をチェック
            existing = await self.speaker_repo.get_by_name_party_position(
                name, party_info, None
            )

            if not existing:
                # 新規発言者を作成
                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # 政党があれば政治家と仮定
                )
                created_speaker = await self.speaker_repo.create(speaker)
                new_speakers += 1
                logger.debug(f"Created new speaker: {name}")
                speaker_to_link = created_speaker
            else:
                existing_speakers += 1
                logger.debug(f"Speaker already exists: {name}")
                speaker_to_link = existing

            # この発言者に対応するすべてのconversationsをリンク
            if speaker_to_link and speaker_to_link.id:
                for conv in conversations:
                    if conv.speaker_name:
                        clean_conv_name, conv_party = (
                            self.speaker_service.extract_party_from_name(
                                conv.speaker_name
                            )
                        )
                        if clean_conv_name == name and conv_party == party_info:
                            conv.speaker_id = speaker_to_link.id
                            if conv.id:
                                logger.debug(
                                    f"Updating conversation {conv.id} "
                                    f"with speaker_id={speaker_to_link.id}"
                                )
                                await self.conversation_repo.update(conv)
                                linked_conversations += 1
                                logger.debug(
                                    f"Updated conversation {conv.id}, "
                                    f"speaker_id is now {conv.speaker_id}"
                                )

        logger.info(
            f"Speaker extraction complete - "
            f"New: {new_speakers}, Existing: {existing_speakers}, "
            f"Linked conversations: {linked_conversations}"
        )

        return {
            "unique_speakers": len(speaker_names),
            "new_speakers": new_speakers,
            "existing_speakers": existing_speakers,
        }
