"""議員団メンバー抽出器のファクトリー

フィーチャーフラグに基づいて、Pydantic実装またはBAML実装を提供します。
"""

import logging
import os

from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)

logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberExtractorFactory:
    """議員団メンバー抽出器のファクトリー

    フィーチャーフラグに基づいて、適切な実装を提供します。
    """

    @staticmethod
    def create() -> IParliamentaryGroupMemberExtractorService:
        """フィーチャーフラグに基づいてextractorを作成

        Returns:
            IParliamentaryGroupMemberExtractorService: 適切な実装

        Environment Variables:
            USE_BAML_PARLIAMENTARY_GROUP_EXTRACTOR: "true"でBAML実装を使用
        """
        use_baml = (
            os.getenv("USE_BAML_PARLIAMENTARY_GROUP_EXTRACTOR", "false").lower()
            == "true"
        )

        if use_baml:
            logger.info("Creating BAML parliamentary group member extractor")
            from src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor import (  # noqa: E501
                BAMLParliamentaryGroupMemberExtractor,
            )

            return BAMLParliamentaryGroupMemberExtractor()

        logger.info("Creating Pydantic parliamentary group member extractor")
        from src.infrastructure.external.parliamentary_group_member_extractor.pydantic_extractor import (  # noqa: E501
            PydanticParliamentaryGroupMemberExtractor,
        )

        return PydanticParliamentaryGroupMemberExtractor()
