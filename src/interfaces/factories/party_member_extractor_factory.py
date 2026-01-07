"""政党メンバー抽出器ファクトリー

BAML実装のPartyMemberExtractorを提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)
from src.domain.services.interfaces.llm_service import ILLMService


if TYPE_CHECKING:
    from src.application.usecases.update_politician_from_extraction_usecase import (
        UpdatePoliticianFromExtractionUseCase,
    )
    from src.domain.repositories.politician_repository import PoliticianRepository


logger = logging.getLogger(__name__)


class PartyMemberExtractorFactory:
    """政党メンバー抽出器ファクトリー

    BAML実装を提供します。
    """

    @staticmethod
    def create(
        llm_service: ILLMService | None = None,
        politician_repository: PoliticianRepository | None = None,
        update_politician_usecase: UpdatePoliticianFromExtractionUseCase | None = None,
    ) -> IPartyMemberExtractorService:
        """BAML party member extractorを作成

        Args:
            llm_service: LLMService instance (optional, not used by BAML implementation)
            politician_repository: 政治家リポジトリ（抽出ログ記録時に使用）
            update_politician_usecase: 政治家更新UseCase（抽出ログ記録用）

        Returns:
            IPartyMemberExtractorService: BAML実装
        """
        logger.info("Creating BAML party member extractor")
        # ruff: noqa: E501
        from src.infrastructure.external.party_member_extractor.baml_extractor import (
            BAMLPartyMemberExtractor,
        )

        return BAMLPartyMemberExtractor(
            politician_repository=politician_repository,
            update_politician_usecase=update_politician_usecase,
        )
