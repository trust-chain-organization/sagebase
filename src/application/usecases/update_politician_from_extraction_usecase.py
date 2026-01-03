"""政治家エンティティをAI抽出結果から更新するUseCase。"""

import logging

from typing import Any

from src.application.dtos.extraction_result.politician_extraction_result import (
    PoliticianExtractionResult,
)
from src.application.usecases.base.update_entity_from_extraction_usecase import (
    UpdateEntityFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType
from src.domain.entities.politician import Politician
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.session_adapter import ISessionAdapter


logger = logging.getLogger(__name__)


class UpdatePoliticianFromExtractionUseCase(
    UpdateEntityFromExtractionUseCase[Politician, PoliticianExtractionResult]
):
    """政治家エンティティをAI抽出結果から更新するUseCase。

    人間による手動修正を保護しつつ、AI抽出結果で政治家エンティティを更新する。

    Attributes:
        _politician_repo: 政治家リポジトリ
        _extraction_log_repo: 抽出ログリポジトリ
        _session: セッションアダプター
    """

    def __init__(
        self,
        politician_repo: PoliticianRepository,
        extraction_log_repo: ExtractionLogRepository,
        session_adapter: ISessionAdapter,
    ) -> None:
        """UseCaseを初期化する。

        Args:
            politician_repo: 政治家リポジトリ
            extraction_log_repo: 抽出ログリポジトリ
            session_adapter: セッションアダプター
        """
        super().__init__(extraction_log_repo, session_adapter)
        self._politician_repo = politician_repo

    def _get_entity_type(self) -> EntityType:
        """エンティティタイプを返す。

        Returns:
            EntityType.POLITICIAN
        """
        return EntityType.POLITICIAN

    async def _get_entity(self, entity_id: int) -> Politician | None:
        """政治家エンティティを取得する。

        Args:
            entity_id: 政治家ID

        Returns:
            政治家エンティティ、存在しない場合はNone
        """
        return await self._politician_repo.get_by_id(entity_id)

    async def _save_entity(self, entity: Politician) -> None:
        """政治家エンティティを保存する。

        Args:
            entity: 保存する政治家エンティティ
        """
        await self._politician_repo.update(entity)

    def _to_extracted_data(self, result: PoliticianExtractionResult) -> dict[str, Any]:  # type: ignore[override]
        """抽出結果をdictに変換する。

        Args:
            result: 政治家抽出結果

        Returns:
            抽出データのdict表現
        """
        return result.to_dict()

    async def _apply_extraction(
        self, entity: Politician, result: PoliticianExtractionResult, log_id: int
    ) -> None:
        """抽出結果を政治家エンティティに適用する。

        スクレイピング処理（nameが設定されている場合）のみエンティティを更新。
        マッチング処理の場合は、抽出ログの記録のみ行い、エンティティは更新しない。

        Args:
            entity: 更新対象の政治家エンティティ
            result: 抽出結果
            log_id: 抽出ログID
        """
        # スクレイピング処理の場合のみエンティティを更新
        if result.name is not None:
            # 抽出結果を各フィールドに反映
            entity.name = result.name
            if result.furigana is not None:
                entity.furigana = result.furigana
            if result.political_party_id is not None:
                entity.political_party_id = result.political_party_id
            if result.district is not None:
                entity.district = result.district
            if result.profile_page_url is not None:
                entity.profile_page_url = result.profile_page_url
            if result.party_position is not None:
                entity.party_position = result.party_position

            # 抽出ログIDを更新
            entity.update_from_extraction_log(log_id)

            logger.debug(
                f"Applied scraping extraction to Politician id={entity.id}, "
                f"log_id={log_id}"
            )
        else:
            # マッチング処理の場合は抽出ログのみ記録（エンティティは更新しない）
            logger.debug(
                f"Matching extraction logged for Politician id={entity.id}, "
                f"log_id={log_id}"
            )

    def _get_confidence_score(self, result: PoliticianExtractionResult) -> float | None:  # type: ignore[override]
        """信頼度スコアを取得する。

        スクレイピング処理またはマッチング処理の信頼度スコアを返す。

        Args:
            result: 抽出結果

        Returns:
            信頼度スコア（0.0〜1.0）、または取得できない場合はNone
        """
        if result.confidence_score is not None:
            return result.confidence_score
        if result.match_confidence is not None:
            return result.match_confidence
        return None

    def _get_metadata(self, result: PoliticianExtractionResult) -> dict[str, Any]:  # type: ignore[override]
        """抽出メタデータを取得する。

        Args:
            result: 抽出結果

        Returns:
            抽出メタデータのdict
        """
        metadata = {}
        if result.matched_from_speaker_id is not None:
            metadata["matched_from_speaker_id"] = result.matched_from_speaker_id
        if result.match_reason is not None:
            metadata["match_reason"] = result.match_reason
        return metadata
