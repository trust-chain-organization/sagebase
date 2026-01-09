"""会議体メンバー抽出用のLangGraphエージェント

LangGraph（ワークフロー層）+ BAML（LLM通信層）の二層構造で
会議体メンバー抽出を実現します。

Issue #903: [LangGraph+BAML] 会議体メンバー抽出のエージェント化
"""

import logging

from typing import TYPE_CHECKING

from src.domain.dtos.conference_member_dto import (
    ConferenceMemberExtractionResult,
    ExtractedMemberDTO,
)
from src.domain.interfaces.conference_member_extraction_agent import (
    IConferenceMemberExtractionAgent,
)


if TYPE_CHECKING:
    from src.domain.interfaces.member_extractor_service import IMemberExtractorService

# ruff: noqa: E501  # 長いインポートパスは許容
from src.infrastructure.external.langgraph_tools.conference_member_extraction_tools import (  # noqa: E501
    create_conference_member_extraction_tools,
)


logger = logging.getLogger(__name__)


class ConferenceMemberExtractionAgent(IConferenceMemberExtractionAgent):
    """会議体メンバー抽出エージェント

    IConferenceMemberExtractionAgentインターフェースの実装。
    LangGraphツールを順番に呼び出して、会議体メンバーの高精度な抽出を実現します。

    処理フロー:
    1. extract_members_from_html: HTMLからメンバーを抽出（BAML使用）
    2. validate_extracted_members: 抽出結果を検証
    3. deduplicate_members: 重複メンバーを除去

    Attributes:
        member_extractor: メンバー抽出サービス（依存性注入用）
        tools: メンバー抽出用のツールリスト
    """

    def __init__(
        self,
        member_extractor: "IMemberExtractorService | None" = None,
    ):
        """エージェントを初期化

        Args:
            member_extractor: メンバー抽出サービス（省略時はファクトリから取得）
                テスト時にモックを注入可能
        """
        self.member_extractor = member_extractor
        self.tools = create_conference_member_extraction_tools(
            member_extractor=self.member_extractor
        )
        # ツールを名前でアクセスできるように辞書化
        self._tools_by_name = {tool.name: tool for tool in self.tools}
        logger.info(
            f"ConferenceMemberExtractionAgent initialized with {len(self.tools)} tools"
        )

    async def extract_members(
        self,
        html_content: str,
        conference_name: str,
    ) -> ConferenceMemberExtractionResult:
        """会議体メンバーを抽出

        Args:
            html_content: 解析対象のHTMLコンテンツ
            conference_name: 会議体名（抽出精度向上に使用）

        Returns:
            抽出結果を含む辞書:
            - members: 抽出されたメンバーのリスト（ExtractedMemberDTO）
            - success: 抽出成功フラグ
            - validation_errors: 検証エラーのリスト
            - error_message: エラーメッセージ（エラー時のみ）
        """
        logger.info(
            f"Starting member extraction for '{conference_name}' "
            f"(HTML size: {len(html_content)} chars)"
        )

        validation_errors: list[str] = []

        try:
            # Step 1: HTMLからメンバーを抽出（BAML使用）
            extract_tool = self._tools_by_name["extract_members_from_html"]
            extract_result = await extract_tool.ainvoke(
                {"html_content": html_content, "conference_name": conference_name}
            )

            if not extract_result.get("success"):
                error_msg = extract_result.get("error", "抽出に失敗しました")
                logger.warning(f"Extraction failed: {error_msg}")
                return ConferenceMemberExtractionResult(
                    members=[],
                    success=False,
                    validation_errors=[],
                    error_message=error_msg,
                )

            raw_members = extract_result.get("members", [])
            logger.info(f"Step 1 completed: {len(raw_members)} members extracted")

            if not raw_members:
                return ConferenceMemberExtractionResult(
                    members=[],
                    success=False,
                    validation_errors=[],
                    error_message="メンバーが抽出されませんでした",
                )

            # Step 2: 抽出結果を検証
            validate_tool = self._tools_by_name["validate_extracted_members"]
            validate_result = await validate_tool.ainvoke({"members": raw_members})

            valid_members = validate_result.get("valid_members", [])
            validation_errors = validate_result.get("validation_errors", [])
            logger.info(
                f"Step 2 completed: {len(valid_members)} valid, "
                f"{validate_result.get('invalid_count', 0)} invalid"
            )

            if not valid_members:
                # 検証で全て除外された場合は元のメンバーを使用
                logger.warning(
                    "All members were invalidated, using raw members instead"
                )
                valid_members = raw_members

            # Step 3: 重複を除去
            dedupe_tool = self._tools_by_name["deduplicate_members"]
            dedupe_result = await dedupe_tool.ainvoke({"members": valid_members})

            final_members = dedupe_result.get("unique_members", [])
            logger.info(
                f"Step 3 completed: {len(final_members)} unique members "
                f"({dedupe_result.get('original_count', 0) - len(final_members)} "
                f"duplicates removed)"
            )

            # 辞書形式からExtractedMemberDTOに変換
            members_dto = [
                ExtractedMemberDTO(
                    name=m.get("name", ""),
                    role=m.get("role"),
                    party_name=m.get("party_name"),
                    additional_info=m.get("additional_info"),
                )
                for m in final_members
                if m.get("name")
            ]

            logger.info(
                f"Member extraction completed: {len(members_dto)} members "
                f"from '{conference_name}'"
            )

            return ConferenceMemberExtractionResult(
                members=members_dto,
                success=len(members_dto) > 0,
                validation_errors=validation_errors,
                error_message=None,
            )

        except Exception as e:
            logger.error(
                f"Error during member extraction: {str(e)}",
                exc_info=True,
            )
            return ConferenceMemberExtractionResult(
                members=[],
                success=False,
                validation_errors=validation_errors,
                error_message=f"メンバー抽出中にエラーが発生しました: {str(e)}",
            )
