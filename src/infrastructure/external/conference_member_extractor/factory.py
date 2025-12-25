"""Member extractor factory

BAML実装のみを提供します（Pydantic実装は削除済み）。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging

from src.domain.interfaces.member_extractor_service import IMemberExtractorService

logger = logging.getLogger(__name__)


class MemberExtractorFactory:
    """Member extractor factory

    BAML実装のMemberExtractorを提供します。
    """

    @staticmethod
    def create() -> IMemberExtractorService:
        """BAML MemberExtractorを作成

        Returns:
            IMemberExtractorService: BAML実装
        """
        logger.info("Creating BAML member extractor")
        # ruff: noqa: E501
        from src.infrastructure.external.conference_member_extractor.baml_extractor import (
            BAMLMemberExtractor,
        )

        return BAMLMemberExtractor()
