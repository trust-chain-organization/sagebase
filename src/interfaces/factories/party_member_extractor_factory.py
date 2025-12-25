"""政党メンバー抽出器ファクトリー

BAML実装のPartyMemberExtractorを提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging

from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)
from src.domain.services.interfaces.llm_service import ILLMService

logger = logging.getLogger(__name__)


class PartyMemberExtractorFactory:
    """政党メンバー抽出器ファクトリー

    BAML実装を提供します。
    """

    @staticmethod
    def create(llm_service: ILLMService | None = None) -> IPartyMemberExtractorService:
        """BAML party member extractorを作成

        Args:
            llm_service: LLMService instance (optional, not used by BAML implementation)

        Returns:
            IPartyMemberExtractorService: BAML実装
        """
        logger.info("Creating BAML party member extractor")
        # ruff: noqa: E501
        from src.infrastructure.external.party_member_extractor.baml_extractor import (
            BAMLPartyMemberExtractor,
        )

        return BAMLPartyMemberExtractor()
