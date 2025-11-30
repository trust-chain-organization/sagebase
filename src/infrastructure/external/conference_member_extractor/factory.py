"""Member extractor factory

フィーチャーフラグに基づいて適切なMemberExtractor実装を提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。
"""

import logging
import os

from src.domain.interfaces.member_extractor_service import IMemberExtractorService

logger = logging.getLogger(__name__)


class MemberExtractorFactory:
    """Member extractor factory

    フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
    A/Bテストモードでは、両方の実装を使用する特別な実装を返します。
    """

    @staticmethod
    def create() -> IMemberExtractorService:
        """フィーチャーフラグに基づいてextractorを作成

        Returns:
            IMemberExtractorService: 適切な実装

        Environment Variables:
            USE_BAML_MEMBER_EXTRACTION: "true"でBAML実装を使用
            ENABLE_MEMBER_EXTRACTION_AB_TEST: "true"でA/Bテスト実装を使用
        """
        use_baml = os.getenv("USE_BAML_MEMBER_EXTRACTION", "false").lower() == "true"
        enable_ab_test = (
            os.getenv("ENABLE_MEMBER_EXTRACTION_AB_TEST", "false").lower() == "true"
        )

        if enable_ab_test:
            logger.info("Creating A/B test member extractor")
            # ruff: noqa: E501
            from src.infrastructure.external.conference_member_extractor.ab_test_extractor import (
                ABTestMemberExtractor,
            )

            return ABTestMemberExtractor()

        if use_baml:
            logger.info("Creating BAML member extractor")
            # ruff: noqa: E501
            from src.infrastructure.external.conference_member_extractor.baml_extractor import (
                BAMLMemberExtractor,
            )

            return BAMLMemberExtractor()

        logger.info("Creating Pydantic member extractor")
        # ruff: noqa: E501
        from src.infrastructure.external.conference_member_extractor.pydantic_extractor import (
            PydanticMemberExtractor,
        )

        return PydanticMemberExtractor()
