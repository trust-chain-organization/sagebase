"""発言者名寄せAgent実装

このモジュールは、LangGraphのReActエージェントを使用して、
発言者と政治家の高精度なマッチングを実現します。

Issue #799 (PBI-006) で実装。
"""

import logging

from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from src.infrastructure.external.langgraph_tools.speaker_matching_tools import (
    create_speaker_matching_tools,
)


logger = logging.getLogger(__name__)

# 最大ReActステップ数
MAX_REACT_STEPS = 10

# 確信度閾値
CONFIDENCE_THRESHOLD = 0.8


class MatchCandidate(TypedDict):
    """マッチング候補の型定義"""

    politician_id: int
    politician_name: str
    party: str | None
    score: float
    match_type: str
    is_affiliated: bool


class ConfidenceJudgement(TypedDict):
    """確信度判定結果の型定義"""

    confidence: float
    confidence_level: str  # "high", "medium", "low"
    should_match: bool
    reason: str
    contributing_factors: list[dict[str, Any]]
    recommendation: str


class SpeakerMatchingAgentState(TypedDict):
    """名寄せAgent固有の状態定義

    LangGraphのサブグラフとして動作するために必要な状態を定義します。
    ReActエージェントの要件として `messages` と `remaining_steps` が必須です。
    """

    # 入力データ
    speaker_name: str  # 発言者名（マッチング対象）
    meeting_date: str | None  # 会議開催日（YYYY-MM-DD形式、オプション）
    conference_id: int | None  # 会議体ID（オプション）

    # 処理中のデータ
    candidates: list[MatchCandidate]  # マッチング候補リスト
    current_candidate_index: int  # 現在評価中の候補インデックス
    best_match: MatchCandidate | None  # 現在の最良マッチ
    best_confidence: ConfidenceJudgement | None  # 最良マッチの確信度

    # ReAct必須フィールド
    messages: Annotated[list[BaseMessage], add_messages]  # エージェントメッセージ履歴
    remaining_steps: int  # ReActエージェントの残りステップ数

    # エラーハンドリング
    error_message: str | None  # エラーメッセージ


class SpeakerMatchingResult(TypedDict):
    """マッチング結果の型定義"""

    matched: bool  # マッチングが成功したかどうか
    politician_id: int | None  # マッチした政治家のID
    politician_name: str | None  # マッチした政治家の名前
    confidence: float  # 確信度（0.0-1.0）
    reason: str  # マッチング判定の理由
    error_message: str | None  # エラーメッセージ（エラー時のみ）


class SpeakerMatchingAgent:
    """発言者名寄せ用のReActエージェント

    LangGraphのサブグラフとして動作し、ツールを使用した試行錯誤により
    発言者と政治家の高精度なマッチングを実現します。

    Attributes:
        llm: 使用するLangChainチャットモデル
        tools: 名寄せ用のツールリスト
        agent: コンパイル済みのReActエージェント
    """

    def __init__(
        self,
        llm: BaseChatModel,
        speaker_repo: Any = None,
        politician_repo: Any = None,
        affiliation_repo: Any = None,
    ):
        """エージェントを初期化

        Args:
            llm: LangChainのチャットモデル（例: ChatGoogleGenerativeAI）
            speaker_repo: SpeakerRepository（オプション）
            politician_repo: PoliticianRepository（オプション）
            affiliation_repo: PoliticianAffiliationRepository（オプション）
        """
        self.llm = llm
        self.tools = create_speaker_matching_tools(
            speaker_repo=speaker_repo,
            politician_repo=politician_repo,
            affiliation_repo=affiliation_repo,
        )
        self.agent = self._create_workflow()
        logger.info(f"SpeakerMatchingAgent initialized with {len(self.tools)} tools")

    def _create_workflow(self):
        """ReActグラフを構築

        Issue #798で実装されたツールを使用して、
        ReAct型エージェントグラフを作成します。

        Returns:
            コンパイル済みのReActエージェント（サブグラフとして使用可能）
        """
        system_prompt = f"""あなたは発言者と政治家の名寄せを専門とするエージェントです。

あなたの役割:
1. 発言者名から最適な政治家候補を見つける
2. 提供されたツールを使用して候補を評価し、確信度を判定する
3. 高精度なマッチングのために試行錯誤を行う

利用可能なツール:
- evaluate_matching_candidates: 発言者名に対する政治家候補を評価
- search_additional_info: 政治家または発言者の追加情報を検索
- judge_confidence: マッチング候補の確信度を総合判定

マッチングの判断基準:
- 名前の類似度（完全一致、部分一致、類似）
- 所属情報の一致（会議体所属）
- 政党情報の一致
- 確信度{CONFIDENCE_THRESHOLD}以上のマッチのみを採用

推奨される手順:
1. evaluate_matching_candidatesで候補を取得
2. 上位候補に対してsearch_additional_infoで追加情報を収集
3. judge_confidenceで最終的な確信度を判定
4. should_match=Trueの候補があればマッチング成功、なければ失敗
"""

        logger.info("Creating ReAct workflow for speaker matching")

        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_schema=SpeakerMatchingAgentState,
            prompt=system_prompt,
        )

    def compile(self):
        """サブグラフとして使用可能な形にコンパイル

        親グラフの add_node() に直接渡すことができる
        コンパイル済みエージェントを返します。

        Returns:
            コンパイル済みエージェント
        """
        logger.debug("Compiling SpeakerMatchingAgent as subgraph")
        return self.agent

    async def match_speaker(
        self,
        speaker_name: str,
        meeting_date: str | None = None,
        conference_id: int | None = None,
    ) -> SpeakerMatchingResult:
        """発言者と政治家をマッチング

        Args:
            speaker_name: 発言者名
            meeting_date: 会議開催日（YYYY-MM-DD形式、オプション）
            conference_id: 会議体ID（オプション）

        Returns:
            マッチング結果を含む辞書:
            - matched: マッチング成功フラグ
            - politician_id: マッチした政治家ID
            - politician_name: マッチした政治家名
            - confidence: 確信度（0.0-1.0）
            - reason: マッチング判定理由
            - error_message: エラーメッセージ（エラー時のみ）
        """
        logger.info(
            f"Starting speaker matching for '{speaker_name}' "
            f"(meeting_date={meeting_date}, conference_id={conference_id})"
        )

        initial_state: SpeakerMatchingAgentState = {
            "speaker_name": speaker_name,
            "meeting_date": meeting_date,
            "conference_id": conference_id,
            "candidates": [],
            "current_candidate_index": 0,
            "best_match": None,
            "best_confidence": None,
            "messages": [],
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        try:
            result = await self.agent.ainvoke(initial_state)

            # 結果から最良マッチを抽出
            best_confidence = result.get("best_confidence")
            best_match = result.get("best_match")

            if best_confidence and best_confidence.get("should_match", False):
                logger.info(
                    f"Speaker matching completed successfully with "
                    f"confidence={best_confidence.get('confidence', 0.0)}"
                )
                return SpeakerMatchingResult(
                    matched=True,
                    politician_id=best_match.get("politician_id")
                    if best_match
                    else None,
                    politician_name=best_match.get("politician_name")
                    if best_match
                    else None,
                    confidence=best_confidence.get("confidence", 0.0),
                    reason=best_confidence.get("reason", ""),
                    error_message=None,
                )
            else:
                logger.info("Speaker matching completed with no match")
                return SpeakerMatchingResult(
                    matched=False,
                    politician_id=None,
                    politician_name=None,
                    confidence=0.0,
                    reason="確信度が閾値に達しませんでした",
                    error_message=None,
                )

        except Exception as e:
            logger.error(
                f"Error during speaker matching: {str(e)}",
                exc_info=True,
            )
            return SpeakerMatchingResult(
                matched=False,
                politician_id=None,
                politician_name=None,
                confidence=0.0,
                reason="",
                error_message=f"マッチング中にエラーが発生しました: {str(e)}",
            )
