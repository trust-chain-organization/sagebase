"""議員団メンバー抽出用のLangGraphエージェント

LangGraph（ワークフロー層）+ BAML（LLM通信層）の二層構造で
議員団メンバー抽出を実現します。

Issue #905: [LangGraph+BAML] 議員団メンバー抽出のエージェント化
"""

import logging

from typing import TYPE_CHECKING

from src.application.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
    ParliamentaryGroupMemberAgentResultDTO,
)
from src.domain.interfaces.parliamentary_group_member_extraction_agent import (
    IParliamentaryGroupMemberExtractionAgent,
)


if TYPE_CHECKING:
    from src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor import (  # noqa: E501
        BAMLParliamentaryGroupMemberExtractor,
    )

from src.infrastructure.external.langgraph_tools.parliamentary_group_member_extraction_tools import (  # noqa: E501
    create_parliamentary_group_member_extraction_tools,
)


logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberExtractionAgent(IParliamentaryGroupMemberExtractionAgent):
    """議員団メンバー抽出エージェント

    IParliamentaryGroupMemberExtractionAgentインターフェースの実装。
    LangGraphツールを順番に呼び出して、議員団メンバーの高精度な抽出を実現します。

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
        member_extractor: "BAMLParliamentaryGroupMemberExtractor | None" = None,
    ):
        """エージェントを初期化

        Args:
            member_extractor: メンバー抽出サービス（省略時はファクトリから取得）
                テスト時にモックを注入可能
        """
        self.member_extractor = member_extractor
        self.tools = create_parliamentary_group_member_extraction_tools(
            member_extractor=self.member_extractor
        )
        self._tools_by_name = {tool.name: tool for tool in self.tools}
        logger.info(
            f"ParliamentaryGroupMemberExtractionAgent initialized "
            f"with {len(self.tools)} tools"
        )

    async def extract_members(
        self,
        html_content: str,
        parliamentary_group_name: str,
    ) -> ParliamentaryGroupMemberAgentResultDTO:
        """議員団メンバーを抽出

        Args:
            html_content: 解析対象のHTMLコンテンツ
            parliamentary_group_name: 議員団名（抽出精度向上に使用）

        Returns:
            抽出結果を含むParliamentaryGroupMemberAgentResultDTO:
            - members: 抽出されたメンバーのリスト
              （ExtractedParliamentaryGroupMemberDTO）
            - success: 抽出成功フラグ
            - validation_errors: 検証エラーのリスト
            - error_message: エラーメッセージ（エラー時のみ）
        """
        logger.info(
            f"Starting member extraction for '{parliamentary_group_name}' "
            f"(HTML size: {len(html_content)} chars)"
        )

        validation_errors: list[str] = []

        try:
            # Step 1: HTMLからメンバーを抽出（BAML使用）
            extract_tool = self._tools_by_name["extract_members_from_html"]
            extract_result = await extract_tool.ainvoke(
                {
                    "html_content": html_content,
                    "parliamentary_group_name": parliamentary_group_name,
                }
            )

            if not extract_result.get("success"):
                error_msg = extract_result.get("error", "抽出に失敗しました")
                logger.warning(f"Extraction failed: {error_msg}")
                return ParliamentaryGroupMemberAgentResultDTO(
                    members=[],
                    success=False,
                    validation_errors=[],
                    error_message=error_msg,
                )

            raw_members = extract_result.get("members", [])
            logger.info(f"Step 1 completed: {len(raw_members)} members extracted")

            if not raw_members:
                return ParliamentaryGroupMemberAgentResultDTO(
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

            # 辞書形式からExtractedParliamentaryGroupMemberDTOに変換
            members_dto = [
                ExtractedParliamentaryGroupMemberDTO(
                    name=m.get("name", ""),
                    role=m.get("role"),
                    party_name=m.get("party_name"),
                    district=m.get("district"),
                    additional_info=m.get("additional_info"),
                )
                for m in final_members
                if m.get("name")
            ]

            logger.info(
                f"Member extraction completed: {len(members_dto)} members "
                f"from '{parliamentary_group_name}'"
            )

            return ParliamentaryGroupMemberAgentResultDTO(
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
            return ParliamentaryGroupMemberAgentResultDTO(
                members=[],
                success=False,
                validation_errors=validation_errors,
                error_message=f"メンバー抽出中にエラーが発生しました: {str(e)}",
            )
