"""発言抽出用のLangGraph ReActエージェント実装

このモジュールは、議事録からの発言境界検出を行うReActエージェントを提供します。
親グラフのサブグラフとして動作し、ツールを使用した試行錯誤により
高精度な境界検出を実現します。
"""

from typing import Annotated

import structlog

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict

from src.infrastructure.external.langgraph_tools.speech_extraction_tools import (
    create_speech_extraction_tools,
)


logger = structlog.get_logger(__name__)

# 定数定義
CONFIDENCE_THRESHOLD = 0.7  # 境界検出の最小信頼度閾値
MAX_REACT_STEPS = 10  # ReActエージェントの最大実行ステップ数


class VerifiedBoundary(TypedDict):
    """検証済み境界の型定義"""

    position: int  # 境界位置（文字インデックス）
    boundary_type: str  # 境界の種類（speech_start, separator_line等）
    confidence: float  # 信頼度（0.0-1.0）


class BoundaryExtractionResult(TypedDict):
    """境界抽出結果の型定義"""

    verified_boundaries: list[VerifiedBoundary]  # 検証済み境界のリスト
    error_message: str | None  # エラーメッセージ（エラー時のみ）


class SpeechExtractionAgentState(TypedDict):
    """発言抽出Agent固有の状態定義

    LangGraphのサブグラフとして動作するために必要な状態を定義します。
    ReActエージェントの要件として `messages` と `remaining_steps` が必須です。
    """

    minutes_text: str  # 議事録テキスト全体
    boundary_candidates: list[int]  # 境界候補位置のリスト（文字インデックス）
    verified_boundaries: list[VerifiedBoundary]  # 検証済み境界情報のリスト
    current_position: int  # 現在の検証位置
    messages: Annotated[list[BaseMessage], add_messages]  # エージェントメッセージ履歴
    remaining_steps: int  # ReActエージェントの残りステップ数
    error_message: str | None  # エラーメッセージ


class SpeechExtractionAgent:
    """発言抽出用のReActエージェント

    LangGraphのサブグラフとして動作し、ツールを使用した試行錯誤により
    議事録からの発言境界を高精度で検出します。

    Attributes:
        llm: 使用するLangChainチャットモデル
        tools: 境界検出用のツールリスト
        agent: コンパイル済みのReActエージェント
    """

    def __init__(self, llm: BaseChatModel):
        """エージェントを初期化

        Args:
            llm: LangChainのチャットモデル（例: ChatAnthropic）
        """
        self.llm = llm
        self.tools = create_speech_extraction_tools()
        self.agent = self._create_workflow()
        logger.info(
            "SpeechExtractionAgent initialized",
            tool_count=len(self.tools),
        )

    def _create_workflow(self):
        """ReActグラフを構築

        Issue #795で実装されたツールを使用して、
        ReAct型エージェントグラフを作成します。

        Returns:
            コンパイル済みのReActエージェント（サブグラフとして使用可能）
        """
        system_prompt = f"""あなたは議事録からの発言抽出を専門とするエージェントです。

あなたの役割:
1. 議事録テキストから発言者と発言内容の境界を検出する
2. 提供されたツールを使用して境界候補を検証する
3. 高精度な境界検出のために試行錯誤を行う

利用可能なツール:
- validate_boundary_candidate: 境界候補の妥当性を検証
- analyze_context: 境界周辺のコンテキストを分析
- verify_boundary: 最終的な境界検証を実行

境界検出のパターン:
- 区切り線（---、===など）
- 発言開始マーカー（○、◆など）
- 時刻表記（午前10時、10:00など）
- 出席者リストの終了

信頼度{CONFIDENCE_THRESHOLD}以上の境界のみを採用してください。
"""

        logger.info("Creating ReAct workflow for speech extraction")

        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_schema=SpeechExtractionAgentState,
            prompt=system_prompt,
        )

    def compile(self):
        """サブグラフとして使用可能な形にコンパイル

        親グラフの add_node() に直接渡すことができる
        コンパイル済みエージェントを返します。

        Returns:
            コンパイル済みエージェント
        """
        logger.debug("Compiling SpeechExtractionAgent as subgraph")
        return self.agent

    async def extract_boundaries(self, minutes_text: str) -> BoundaryExtractionResult:
        """発言境界を抽出

        Args:
            minutes_text: 議事録テキスト

        Returns:
            抽出結果を含む辞書:
            - verified_boundaries: 検証済み境界のリスト
            - error_message: エラーメッセージ（エラー時のみ）
        """
        logger.info(
            "Starting boundary extraction",
            text_length=len(minutes_text),
        )

        initial_state: SpeechExtractionAgentState = {
            "minutes_text": minutes_text,
            "boundary_candidates": [],
            "verified_boundaries": [],
            "current_position": 0,
            "messages": [],
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        try:
            result = await self.agent.ainvoke(initial_state)

            boundary_count = len(result.get("verified_boundaries", []))
            logger.info(
                "Boundary extraction completed",
                boundary_count=boundary_count,
                has_error=result.get("error_message") is not None,
            )

            return BoundaryExtractionResult(
                verified_boundaries=result.get("verified_boundaries", []),
                error_message=result.get("error_message"),
            )

        except Exception as e:
            logger.error(
                "Error during boundary extraction",
                error=str(e),
                exc_info=True,
            )
            return BoundaryExtractionResult(
                verified_boundaries=[],
                error_message=f"境界抽出中にエラーが発生しました: {str(e)}",
            )
