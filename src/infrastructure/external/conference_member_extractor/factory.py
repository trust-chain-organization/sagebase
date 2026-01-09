"""Member extractor factory

BAML実装のみを提供します（Pydantic実装は削除済み）。
Clean Architectureの原則に従い、依存性の注入とファクトリーパターンを使用しています。

Issue #903: LangGraphエージェント作成機能を追加
"""

import logging

from typing import TYPE_CHECKING

from src.domain.interfaces.member_extractor_service import IMemberExtractorService


if TYPE_CHECKING:
    from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
        ConferenceMemberExtractionAgent,
    )


logger = logging.getLogger(__name__)


class MemberExtractorFactory:
    """Member extractor factory

    BAML実装のMemberExtractorおよびLangGraphエージェントを提供します。
    """

    @staticmethod
    def create() -> IMemberExtractorService:
        """BAML MemberExtractorを作成

        既存のStreamlit UIなどとの後方互換性を維持するためのメソッドです。

        Returns:
            IMemberExtractorService: BAML実装
        """
        logger.info("Creating BAML member extractor")
        # ruff: noqa: E501
        from src.infrastructure.external.conference_member_extractor.baml_extractor import (
            BAMLMemberExtractor,
        )

        return BAMLMemberExtractor()

    @staticmethod
    def create_agent() -> "ConferenceMemberExtractionAgent":
        """LangGraph会議体メンバー抽出エージェントを作成

        LangGraph（ワークフロー層）+ BAML（LLM通信層）の二層構造を持つ
        エージェントを作成します。

        処理フロー:
        1. extract_members_from_html: HTMLからメンバーを抽出（BAML使用）
        2. validate_extracted_members: 抽出結果を検証
        3. deduplicate_members: 重複メンバーを除去

        Returns:
            ConferenceMemberExtractionAgent: LangGraphエージェント
        """
        logger.info("Creating LangGraph conference member extraction agent")

        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        return ConferenceMemberExtractionAgent()
