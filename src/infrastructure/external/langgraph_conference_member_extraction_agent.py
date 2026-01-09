"""会議体メンバー抽出用のLangGraphエージェント

LangGraph（ワークフロー層）+ BAML（LLM通信層）の二層構造で
会議体メンバー抽出を実現するReActエージェント。

Issue #903: [LangGraph+BAML] 会議体メンバー抽出のエージェント化
"""

import json
import logging

from typing import TYPE_CHECKING, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

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

# エージェントの最大ステップ数
MAX_REACT_STEPS = 10


class ConferenceMemberExtractionAgentState(TypedDict, total=False):
    """会議体メンバー抽出エージェントの状態

    ReActエージェントが使用する状態を定義します。
    """

    # 入力データ
    html_content: str
    conference_name: str

    # 処理中のデータ
    raw_members: list[dict[str, Any]]
    validated_members: list[dict[str, Any]]
    final_members: list[dict[str, Any]]

    # 検証結果
    validation_errors: list[str]

    # ReActエージェント用
    messages: list[BaseMessage]
    remaining_steps: int

    # エラー情報
    error_message: str | None


class ConferenceMemberExtractionAgent(IConferenceMemberExtractionAgent):
    """会議体メンバー抽出用のReActエージェント

    IConferenceMemberExtractionAgentインターフェースの実装。
    LangGraphのサブグラフとして動作し、ツールを使用した試行錯誤により
    会議体メンバーの高精度な抽出を実現します。

    Attributes:
        llm: 使用するLangChainチャットモデル
        member_extractor: メンバー抽出サービス（依存性注入用）
        tools: メンバー抽出用のツールリスト
        agent: コンパイル済みのReActエージェント
    """

    def __init__(
        self,
        llm: BaseChatModel,
        member_extractor: "IMemberExtractorService | None" = None,
    ):
        """エージェントを初期化

        Args:
            llm: LangChainのチャットモデル（例: ChatGoogleGenerativeAI）
            member_extractor: メンバー抽出サービス（省略時はファクトリから取得）
                テスト時にモックを注入可能
        """
        self.llm = llm
        self.member_extractor = member_extractor
        self.tools = create_conference_member_extraction_tools(
            member_extractor=self.member_extractor
        )
        self.agent = self._create_workflow()
        logger.info(
            f"ConferenceMemberExtractionAgent initialized with {len(self.tools)} tools"
        )

    def _create_workflow(self):
        """ReActグラフを構築

        会議体メンバー抽出用のReAct型エージェントグラフを作成します。

        Returns:
            コンパイル済みのReActエージェント（サブグラフとして使用可能）
        """
        system_prompt = """あなたは会議体メンバー情報の抽出を専門とするエージェントです。

あなたの役割:
1. HTMLコンテンツから会議体メンバー情報を抽出する
2. 抽出結果を検証し、不正なデータを除外する
3. 重複メンバーを検出して統合する

利用可能なツール:
- extract_members_from_html: HTMLからメンバー情報を抽出
- validate_extracted_members: 抽出結果の妥当性を検証
- deduplicate_members: 重複メンバーを除去

推奨される手順:
1. extract_members_from_htmlでHTMLからメンバーを抽出
2. validate_extracted_membersで抽出結果を検証
3. deduplicate_membersで重複を除去
4. 最終結果を確認し、必要に応じて再抽出

品質基準:
- 名前は姓名のフルネームである必要がある
- 敬称（議員、氏、様など）は除外する
- 役職は議長、副議長、委員長、委員などの標準的な表記に統一
- 指定された会議体のメンバーのみを抽出（他の委員会のメンバーは除外）
"""

        logger.info("Creating ReAct workflow for conference member extraction")

        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_schema=ConferenceMemberExtractionAgentState,
            prompt=system_prompt,
        )

    def compile(self):
        """サブグラフとして使用可能な形にコンパイル

        親グラフの add_node() に直接渡すことができる
        コンパイル済みエージェントを返します。

        Returns:
            コンパイル済みエージェント
        """
        logger.debug("Compiling ConferenceMemberExtractionAgent as subgraph")
        return self.agent

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

        # タスク指示メッセージを作成
        task_description = (
            f"以下のHTMLから'{conference_name}'の会議体メンバー情報を抽出してください。\n\n"
            f"手順:\n"
            f"1. extract_members_from_htmlツールでメンバーを抽出\n"
            f"2. validate_extracted_membersツールで検証\n"
            f"3. deduplicate_membersツールで重複を除去\n\n"
            f"会議体名: {conference_name}\n"
            f"HTMLコンテンツのサイズ: {len(html_content)}文字"
        )

        initial_state: ConferenceMemberExtractionAgentState = {
            "html_content": html_content,
            "conference_name": conference_name,
            "raw_members": [],
            "validated_members": [],
            "final_members": [],
            "validation_errors": [],
            "messages": [HumanMessage(content=task_description)],
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        try:
            result = await self.agent.ainvoke(initial_state)

            # 結果からメンバーリストを抽出
            final_members = result.get("final_members", [])
            validation_errors = result.get("validation_errors", [])

            # 最終メンバーがない場合、raw_membersを使用
            if not final_members:
                final_members = result.get("validated_members", [])
            if not final_members:
                final_members = result.get("raw_members", [])

            # メッセージから抽出結果を取得する（ツール呼び出し結果から）
            if not final_members:
                final_members = self._extract_members_from_messages(
                    result.get("messages", [])
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
                validation_errors=[],
                error_message=f"メンバー抽出中にエラーが発生しました: {str(e)}",
            )

    def _extract_members_from_messages(
        self, messages: list[Any]
    ) -> list[dict[str, Any]]:
        """メッセージ履歴からメンバーリストを抽出

        ReActエージェントのツール呼び出し結果からメンバーリストを取得します。

        Args:
            messages: ReActエージェントのメッセージ履歴

        Returns:
            抽出されたメンバーリスト
        """
        members: list[dict[str, Any]] = []

        for message in reversed(messages):
            # ToolMessageからコンテンツを取得
            if hasattr(message, "content") and isinstance(message.content, str):
                try:
                    content = json.loads(message.content)
                    # deduplicate_membersの結果を優先
                    if "unique_members" in content and content.get("unique_members"):
                        return content["unique_members"]
                    # validate_extracted_membersの結果
                    if "valid_members" in content and content.get("valid_members"):
                        return content["valid_members"]
                    # extract_members_from_htmlの結果
                    if "members" in content and content.get("members"):
                        members = content["members"]
                except (json.JSONDecodeError, TypeError):
                    continue

        return members
