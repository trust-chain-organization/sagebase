import logging

from src.application.dtos.convert_extracted_politician_dto import (
    ConvertedPoliticianDTO,
    ConvertExtractedPoliticianInputDTO,
    ConvertExtractedPoliticianOutputDTO,
)
from src.domain.entities.politician import Politician
from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)
from src.domain.entities.speaker import Speaker
from src.domain.repositories.extracted_politician_repository import (
    ExtractedPoliticianRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository


logger = logging.getLogger(__name__)


class ConvertExtractedPoliticianUseCase:
    """抽出済み政治家を正式な政治家データに変換するユースケース

    extracted_politiciansテーブルのapproved状態のレコードを
    politicians/speakersテーブルに変換します。

    Attributes:
        extracted_politician_repo: 抽出済み政治家リポジトリ
        politician_repo: 政治家リポジトリ
        speaker_repo: スピーカーリポジトリ

    Example:
        >>> use_case = ConvertExtractedPoliticianUseCase(
        ...     extracted_politician_repo, politician_repo, speaker_repo
        ... )
        >>> # 全approvedレコードを変換
        >>> result = await use_case.execute(
        ...     ConvertExtractedPoliticianInputDTO()
        ... )
        >>> print(f"変換成功: {result.converted_count}件")

        >>> # 特定政党のレコードのみ変換（ドライラン）
        >>> result = await use_case.execute(
        ...     ConvertExtractedPoliticianInputDTO(party_id=5, dry_run=True)
        ... )
    """

    def __init__(
        self,
        extracted_politician_repository: ExtractedPoliticianRepository,
        politician_repository: PoliticianRepository,
        speaker_repository: SpeakerRepository,
    ):
        """変換ユースケースを初期化する

        Args:
            extracted_politician_repository: 抽出済み政治家リポジトリの実装
            politician_repository: 政治家リポジトリの実装
            speaker_repository: スピーカーリポジトリの実装
        """
        self.extracted_politician_repo = extracted_politician_repository
        self.politician_repo = politician_repository
        self.speaker_repo = speaker_repository

    async def execute(
        self,
        request: ConvertExtractedPoliticianInputDTO,
    ) -> ConvertExtractedPoliticianOutputDTO:
        """抽出済み政治家の変換を実行する

        処理の流れ：
        1. approved状態のextracted_politiciansを取得
        2. 各レコードについて：
           - 対応するSpeakerを作成または取得
           - 対応するPoliticianを作成または更新
           - extracted_politicianのstatusをconvertedに更新
        3. 結果をまとめて返却

        Args:
            request: 変換リクエストDTO
                - party_id: 特定政党のみ対象とする場合のID（オプション）
                - batch_size: バッチサイズ（デフォルト100）
                - dry_run: 実行せずに結果を確認するか

        Returns:
            ConvertExtractedPoliticianOutputDTO:
            - total_processed: 処理対象件数
            - converted_count: 変換成功件数
            - skipped_count: スキップ件数
            - error_count: エラー件数
            - converted_politicians: 変換された政治家情報
            - skipped_names: スキップされた政治家名
            - error_messages: エラーメッセージ

        Raises:
            ValueError: 無効なパラメータが指定された場合
        """
        # Get approved extracted politicians
        approved_politicians = await self.extracted_politician_repo.get_by_status(
            "approved"
        )

        # Filter by party if specified
        if request.party_id:
            approved_politicians = [
                p for p in approved_politicians if p.party_id == request.party_id
            ]

        # Apply batch size limit
        if len(approved_politicians) > request.batch_size:
            approved_politicians = approved_politicians[: request.batch_size]

        total_processed = len(approved_politicians)
        converted_politicians: list[ConvertedPoliticianDTO] = []
        skipped_names: list[str] = []
        error_messages: list[str] = []

        logger.info(f"Processing {total_processed} approved extracted politicians")

        for extracted in approved_politicians:
            try:
                if request.dry_run:
                    # Dry run - just check without actual conversion
                    # Check for existing politician
                    existing = await self.politician_repo.get_by_name_and_party(
                        extracted.name, extracted.party_id
                    )
                    if existing:
                        logger.info(
                            f"[DRY RUN] Would update existing politician: "
                            f"{extracted.name}"
                        )
                    else:
                        logger.info(
                            f"[DRY RUN] Would create new politician: {extracted.name}"
                        )

                    # Mock converted politician for dry run
                    converted_politicians.append(
                        ConvertedPoliticianDTO(
                            politician_id=existing.id
                            if existing and existing.id
                            else 0,
                            name=extracted.name,
                            party_id=extracted.party_id,
                            district=extracted.district,
                            profile_url=extracted.profile_url,
                        )
                    )
                else:
                    # Actual conversion
                    politician = await self._convert_to_politician(extracted)
                    if politician:
                        converted_politicians.append(
                            ConvertedPoliticianDTO(
                                politician_id=politician.id if politician.id else 0,
                                name=politician.name,
                                party_id=politician.political_party_id,
                                district=politician.district,
                                profile_url=politician.profile_page_url,
                            )
                        )

                        # Update extracted politician status to converted
                        await self.extracted_politician_repo.update_status(
                            extracted.id if extracted.id else 0,
                            "converted",
                        )
                        logger.info(
                            f"Successfully converted politician: {politician.name}"
                        )
                    else:
                        skipped_names.append(extracted.name)
                        logger.warning(f"Skipped politician: {extracted.name}")

            except Exception as e:
                error_messages.append(f"Error converting {extracted.name}: {str(e)}")
                logger.error(f"Error converting {extracted.name}: {e}")

        # Calculate final counts
        converted_count = len(converted_politicians)
        skipped_count = len(skipped_names)
        error_count = len(error_messages)

        logger.info(
            f"Conversion complete - Converted: {converted_count}, "
            f"Skipped: {skipped_count}, Errors: {error_count}"
        )

        return ConvertExtractedPoliticianOutputDTO(
            total_processed=total_processed,
            converted_count=converted_count,
            skipped_count=skipped_count,
            error_count=error_count,
            converted_politicians=converted_politicians,
            skipped_names=skipped_names,
            error_messages=error_messages,
        )

    async def _convert_to_politician(
        self, extracted: PoliticianPartyExtractedPolitician
    ) -> Politician | None:
        """抽出済み政治家を正式な政治家に変換する

        Args:
            extracted: ExtractedPoliticianエンティティ

        Returns:
            変換されたPoliticianエンティティ、変換できない場合はNone

        Raises:
            Exception: スピーカー作成に失敗した場合
        """
        try:
            # Note: We no longer create speaker here as it's
            # decoupled from politician creation

            # Check for existing politician
            existing_politician = await self.politician_repo.get_by_name_and_party(
                extracted.name, extracted.party_id
            )

            if existing_politician:
                # Update existing politician
                existing_politician.district = (
                    extracted.district or existing_politician.district
                )
                existing_politician.profile_page_url = (
                    extracted.profile_url or existing_politician.profile_page_url
                )
                politician = await self.politician_repo.update(existing_politician)
                logger.info(f"Updated existing politician: {politician.name}")
            else:
                # Create new politician
                politician = Politician(
                    name=extracted.name,
                    political_party_id=extracted.party_id,
                    district=extracted.district,
                    profile_page_url=extracted.profile_url,
                )
                politician = await self.politician_repo.create(politician)
                logger.info(f"Created new politician: {politician.name}")

                # Create or update speaker and link to politician
                speaker = await self._get_or_create_speaker(extracted)
                if speaker and politician.id:
                    speaker.politician_id = politician.id
                    await self.speaker_repo.update(speaker)
                    logger.info(
                        f"Linked speaker {speaker.name} to politician {politician.name}"
                    )

            return politician

        except Exception as e:
            logger.error(f"Error converting {extracted.name}: {e}")
            raise  # Re-raise exception to be caught by caller

    async def _get_or_create_speaker(
        self, extracted: PoliticianPartyExtractedPolitician
    ) -> Speaker | None:
        """抽出済み政治家に対応するスピーカーを取得または作成する

        Args:
            extracted: ExtractedPoliticianエンティティ

        Returns:
            作成または取得されたSpeakerエンティティ
        """
        try:
            # Check for existing speaker
            existing_speaker = await self.speaker_repo.find_by_name(extracted.name)

            if existing_speaker:
                # Update speaker as politician if not already
                if not existing_speaker.is_politician:
                    existing_speaker.is_politician = True
                    existing_speaker = await self.speaker_repo.update(existing_speaker)
                return existing_speaker

            # Create new speaker
            speaker = Speaker(
                name=extracted.name,
                type="議員",
                political_party_name=None,  # Will be set from party_id relation
                position=None,  # Position info managed via politician_affiliations
                is_politician=True,
            )
            created_speaker = await self.speaker_repo.create(speaker)
            logger.info(f"Created new speaker: {created_speaker.name}")
            return created_speaker

        except Exception as e:
            logger.error(f"Error creating speaker for {extracted.name}: {e}")
            return None
