"""議員団メンバー抽出器のファクトリー

BAML実装を提供します。
"""

import logging

from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)

logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberExtractorFactory:
    """議員団メンバー抽出器のファクトリー

    BAML実装を提供します。
    """

    @staticmethod
    def create() -> IParliamentaryGroupMemberExtractorService:
        """BAML parliamentary group member extractorを作成

        Returns:
            IParliamentaryGroupMemberExtractorService: BAML実装
        """
        logger.info("Creating BAML parliamentary group member extractor")
        from src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor import (  # noqa: E501
            BAMLParliamentaryGroupMemberExtractor,
        )

        return BAMLParliamentaryGroupMemberExtractor()
