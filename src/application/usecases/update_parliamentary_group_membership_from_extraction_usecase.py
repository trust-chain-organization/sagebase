"""議員団メンバーシップエンティティをAI抽出結果から更新するUseCase。"""

import logging

from typing import Any

from src.application.dtos.extraction_result.parliamentary_group_membership_extraction_result import (  # noqa: E501
    ParliamentaryGroupMembershipExtractionResult,
)
from src.application.usecases.base.update_entity_from_extraction_usecase import (
    UpdateEntityFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter


logger = logging.getLogger(__name__)


class UpdateParliamentaryGroupMembershipFromExtractionUseCase(
    UpdateEntityFromExtractionUseCase[
        ParliamentaryGroupMembership, ParliamentaryGroupMembershipExtractionResult
    ]
):
    """議員団メンバーシップエンティティをAI抽出結果から更新するUseCase。

    人間による手動修正を保護しつつ、AI抽出結果で議員団メンバーシップを更新する。

    Attributes:
        _membership_repo: 議員団メンバーシップリポジトリ
        _extraction_log_repo: 抽出ログリポジトリ
        _session: セッションアダプター
    """

    def __init__(
        self,
        membership_repo: ParliamentaryGroupMembershipRepository,
        extraction_log_repo: ExtractionLogRepository,
        session_adapter: ISessionAdapter,
    ) -> None:
        """UseCaseを初期化する。

        Args:
            membership_repo: 議員団メンバーシップリポジトリ
            extraction_log_repo: 抽出ログリポジトリ
            session_adapter: セッションアダプター
        """
        super().__init__(extraction_log_repo, session_adapter)
        self._membership_repo = membership_repo

    def _get_entity_type(self) -> EntityType:
        """エンティティタイプを返す。

        Returns:
            EntityType.PARLIAMENTARY_GROUP_MEMBER
        """
        return EntityType.PARLIAMENTARY_GROUP_MEMBER

    async def _get_entity(self, entity_id: int) -> ParliamentaryGroupMembership | None:
        """議員団メンバーシップエンティティを取得する。

        Args:
            entity_id: メンバーシップID

        Returns:
            議員団メンバーシップエンティティ、存在しない場合はNone
        """
        return await self._membership_repo.get_by_id(entity_id)

    async def _save_entity(self, entity: ParliamentaryGroupMembership) -> None:
        """議員団メンバーシップエンティティを保存する。

        Args:
            entity: 保存する議員団メンバーシップエンティティ
        """
        await self._membership_repo.update(entity)

    def _to_extracted_data(
        self, result: ParliamentaryGroupMembershipExtractionResult
    ) -> dict[str, Any]:  # type: ignore[override]
        """抽出結果をdictに変換する。

        Args:
            result: 議員団メンバーシップ抽出結果

        Returns:
            抽出データのdict表現
        """
        return result.to_dict()

    async def _apply_extraction(
        self,
        entity: ParliamentaryGroupMembership,
        result: ParliamentaryGroupMembershipExtractionResult,
        log_id: int,
    ) -> None:
        """抽出結果を議員団メンバーシップエンティティに適用する。

        Args:
            entity: 更新対象の議員団メンバーシップエンティティ
            result: 抽出結果
            log_id: 抽出ログID
        """
        # 抽出結果を各フィールドに反映
        entity.politician_id = result.politician_id
        entity.parliamentary_group_id = result.parliamentary_group_id
        entity.start_date = result.start_date
        entity.end_date = result.end_date
        if result.role is not None:
            entity.role = result.role

        # 抽出ログIDを更新
        entity.update_from_extraction_log(log_id)

        logger.debug(
            f"Applied extraction to ParliamentaryGroupMembership id={entity.id}, "
            f"log_id={log_id}"
        )
