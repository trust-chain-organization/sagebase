"""議員団メンバー抽出器のファクトリー

BAML実装およびLangGraphエージェントを提供します。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。

Issue #905: LangGraphエージェント作成機能を追加
"""

import logging

from typing import TYPE_CHECKING

from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)


if TYPE_CHECKING:
    from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (  # noqa: E501
        ParliamentaryGroupMemberExtractionAgent,
    )


logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberExtractorFactory:
    """議員団メンバー抽出器のファクトリー

    BAML実装のMemberExtractorおよびLangGraphエージェントを提供します。
    """

    @staticmethod
    def create() -> IParliamentaryGroupMemberExtractorService:
        """BAML parliamentary group member extractorを作成

        既存のStreamlit UIなどとの後方互換性を維持するためのメソッドです。

        Returns:
            IParliamentaryGroupMemberExtractorService: BAML実装
        """
        logger.info("Creating BAML parliamentary group member extractor")
        from src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor import (  # noqa: E501
            BAMLParliamentaryGroupMemberExtractor,
        )

        return BAMLParliamentaryGroupMemberExtractor()

    @staticmethod
    def create_agent() -> "ParliamentaryGroupMemberExtractionAgent":
        """LangGraph議員団メンバー抽出エージェントを作成

        LangGraph（ワークフロー層）+ BAML（LLM通信層）の二層構造を持つ
        エージェントを作成します。

        処理フロー:
        1. extract_members_from_html: HTMLからメンバーを抽出（BAML使用）
        2. validate_extracted_members: 抽出結果を検証
        3. deduplicate_members: 重複メンバーを除去

        Returns:
            ParliamentaryGroupMemberExtractionAgent: LangGraphエージェント
        """
        logger.info("Creating LangGraph parliamentary group member extraction agent")

        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (  # noqa: E501
            ParliamentaryGroupMemberExtractionAgent,
        )

        return ParliamentaryGroupMemberExtractionAgent()
