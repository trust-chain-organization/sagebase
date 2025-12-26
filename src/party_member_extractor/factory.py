"""Party member extractor factory

BAML実装のPartyMemberExtractorを提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging

from typing import Any


logger = logging.getLogger(__name__)


class PartyMemberExtractorFactory:
    """Party member extractor factory

    BAML実装を提供します。
    """

    @staticmethod
    def create(
        llm_service: Any | None = None,
        party_id: int | None = None,
        proc_logger: Any = None,
    ) -> Any:
        """BAML party member extractorを作成

        Args:
            llm_service: LLMService instance (optional)
            party_id: ID of the party being processed (for history tracking)
            proc_logger: ProcessingLogger instance (optional)

        Returns:
            BAMLPartyMemberExtractor: BAML実装のPartyMemberExtractor
        """
        logger.info("Creating BAML party member extractor")
        # ruff: noqa: E501
        from src.party_member_extractor.baml_llm_extractor import (
            BAMLPartyMemberExtractor,
        )

        return BAMLPartyMemberExtractor(llm_service, party_id, proc_logger)
