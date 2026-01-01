"""発言者エンティティをAI抽出結果から更新するUseCase。"""

import logging

from typing import Any

from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)
from src.application.usecases.base.update_entity_from_extraction_usecase import (
    UpdateEntityFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType
from src.domain.entities.speaker import Speaker
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.domain.repositories.speaker_repository import SpeakerRepository


logger = logging.getLogger(__name__)


class UpdateSpeakerFromExtractionUseCase(
    UpdateEntityFromExtractionUseCase[Speaker, SpeakerExtractionResult]
):
    """発言者エンティティをAI抽出結果から更新するUseCase。

    人間による手動修正を保護しつつ、AI抽出結果で発言者エンティティを更新する。

    Attributes:
        _speaker_repo: 発言者リポジトリ
        _extraction_log_repo: 抽出ログリポジトリ
        _session: セッションアダプター
    """

    def __init__(
        self,
        speaker_repo: SpeakerRepository,
        extraction_log_repo: ExtractionLogRepository,
        session_adapter: ISessionAdapter,
    ) -> None:
        """UseCaseを初期化する。

        Args:
            speaker_repo: 発言者リポジトリ
            extraction_log_repo: 抽出ログリポジトリ
            session_adapter: セッションアダプター
        """
        super().__init__(extraction_log_repo, session_adapter)
        self._speaker_repo = speaker_repo

    def _get_entity_type(self) -> EntityType:
        """エンティティタイプを返す。

        Returns:
            EntityType.SPEAKER
        """
        return EntityType.SPEAKER

    async def _get_entity(self, entity_id: int) -> Speaker | None:
        """発言者エンティティを取得する。

        Args:
            entity_id: 発言者ID

        Returns:
            発言者エンティティ、存在しない場合はNone
        """
        return await self._speaker_repo.get_by_id(entity_id)

    async def _save_entity(self, entity: Speaker) -> None:
        """発言者エンティティを保存する。

        Args:
            entity: 保存する発言者エンティティ
        """
        await self._speaker_repo.update(entity)

    def _to_extracted_data(self, result: SpeakerExtractionResult) -> dict[str, Any]:  # type: ignore[override]
        """抽出結果をdictに変換する。

        Args:
            result: 発言者抽出結果

        Returns:
            抽出データのdict表現
        """
        return result.to_dict()

    async def _apply_extraction(
        self, entity: Speaker, result: SpeakerExtractionResult, log_id: int
    ) -> None:
        """抽出結果を発言者エンティティに適用する。

        Args:
            entity: 更新対象の発言者エンティティ
            result: 抽出結果
            log_id: 抽出ログID
        """
        # 抽出結果を各フィールドに反映
        entity.name = result.name
        if result.type is not None:
            entity.type = result.type
        if result.political_party_name is not None:
            entity.political_party_name = result.political_party_name
        if result.position is not None:
            entity.position = result.position
        entity.is_politician = result.is_politician
        if result.politician_id is not None:
            entity.politician_id = result.politician_id

        # 抽出ログIDを更新
        entity.update_from_extraction_log(log_id)

        logger.debug(f"Applied extraction to Speaker id={entity.id}, log_id={log_id}")
