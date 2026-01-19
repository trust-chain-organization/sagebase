"""政治家マッチングAgent実装

このモジュールは、LangGraphのReActエージェントを使用して、
発言者と政治家の高精度なマッチングを実現します。

Issue #904 で実装。
"""

import json
import logging

from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from src.application.dtos.politician_matching_dto import PoliticianMatchingAgentResult
from src.domain.interfaces.politician_matching_agent import IPoliticianMatchingAgent
from src.domain.repositories.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
    create_politician_matching_tools,
)


logger = logging.getLogger(__name__)

# 最大ReActステップ数
MAX_REACT_STEPS = 10

# 信頼度閾値
CONFIDENCE_THRESHOLD = 0.7


class PoliticianMatchCandidate(TypedDict):
    """マッチング候補の型定義"""

    politician_id: int
    politician_name: str
    party_name: str | None
    score: float
    match_type: str


class PoliticianMatchingAgentState(TypedDict):
    """政治家マッチングAgent固有の状態定義

    LangGraphのサブグラフとして動作するために必要な状態を定義します。
    ReActエージェントの要件として `messages` と `remaining_steps` が必須です。
    """

    # 入力データ
    speaker_name: str  # 発言者名（マッチング対象）
    speaker_type: str | None  # 発言者の種別
    speaker_party: str | None  # 発言者の所属政党

    # 処理中のデータ
    candidates: list[PoliticianMatchCandidate]  # マッチング候補リスト
    best_match: dict[str, Any] | None  # 現在の最良マッチ

    # ReAct必須フィールド
    messages: Annotated[list[BaseMessage], add_messages]  # エージェントメッセージ履歴
    remaining_steps: int  # ReActエージェントの残りステップ数

    # エラーハンドリング
    error_message: str | None  # エラーメッセージ


class PoliticianMatchingAgent(IPoliticianMatchingAgent):
    """政治家マッチング用のReActエージェント

    LangGraphのサブグラフとして動作し、ツールを使用した試行錯誤により
    発言者と政治家の高精度なマッチングを実現します。

    特徴:
        - ReActパターンによる反復的推論
        - ルールベースマッチング（高速パス）との統合
        - BAMLによるLLM通信の抽象化

    Attributes:
        llm: 使用するLangChainチャットモデル
        tools: 政治家マッチング用のツールリスト
        agent: コンパイル済みのReActエージェント
    """

    def __init__(
        self,
        llm: BaseChatModel,
        politician_repo: PoliticianRepository,
        affiliation_repo: PoliticianAffiliationRepository,
    ):
        """エージェントを初期化

        Args:
            llm: LangChainのチャットモデル
            politician_repo: PoliticianRepository（必須）
            affiliation_repo: PoliticianAffiliationRepository（必須）
        """
        self.llm = llm
        self.tools = create_politician_matching_tools(
            politician_repo=politician_repo,
            affiliation_repo=affiliation_repo,
        )
        self.agent = self._create_workflow()
        logger.info(f"PoliticianMatchingAgent initialized with {len(self.tools)} tools")

    def _create_workflow(self):
        """ReActグラフを構築

        ツールを使用して、ReAct型エージェントグラフを作成します。

        Returns:
            コンパイル済みのReActエージェント（サブグラフとして使用可能）
        """
        system_prompt = f"""あなたは政治家マッチング専門エージェントです。

あなたの役割:
1. 発言者名から最適な政治家候補を見つける
2. 提供されたツールを使用して候補を評価する
3. 高精度なマッチングのために試行錯誤を行う

利用可能なツール:
- search_politician_candidates: 発言者名から政治家候補を検索・スコアリング
- verify_politician_affiliation: 政治家の所属情報を検証
- match_politician_with_baml: BAMLを使用して政治家マッチングを実行

マッチングの判断基準:
- 名前の類似度（完全一致、部分一致、あいまい一致）
- 政党情報の一致
- 信頼度{CONFIDENCE_THRESHOLD}以上のマッチのみを採用

推奨される手順:
1. search_politician_candidatesで候補を取得
2. 上位候補に対してverify_politician_affiliationで所属を検証
3. 検証結果を踏まえてmatch_politician_with_bamlで最終判定
4. 信頼度が{CONFIDENCE_THRESHOLD}以上なら成功、それ未満なら失敗

重要な注意事項:
- 役職名のみ（例：「委員長」「議長」）は個人を特定できないためマッチ不可とする
- 同姓同名の場合は政党情報で判断する
- 確信が持てない場合はマッチなしとする
"""

        logger.info("Creating ReAct workflow for politician matching")

        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_schema=PoliticianMatchingAgentState,
            prompt=system_prompt,
        )

    def compile(self):
        """サブグラフとして使用可能な形にコンパイル

        親グラフの add_node() に直接渡すことができる
        コンパイル済みエージェントを返します。

        Returns:
            コンパイル済みエージェント
        """
        logger.debug("Compiling PoliticianMatchingAgent as subgraph")
        return self.agent

    async def match_politician(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
    ) -> PoliticianMatchingAgentResult:
        """発言者と政治家をマッチング

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別（例: "議員", "委員"など）
            speaker_party: 発言者の所属政党（もしあれば）

        Returns:
            PoliticianMatchingAgentResult:
                - matched: マッチング成功フラグ
                - politician_id: マッチした政治家のID
                - politician_name: マッチした政治家の名前
                - political_party_name: マッチした政治家の所属政党
                - confidence: マッチングの信頼度（0.0-1.0）
                - reason: マッチング判定の理由
                - error_message: エラーメッセージ（エラー時のみ）
        """
        logger.info(
            f"Starting politician matching for '{speaker_name}' "
            f"(type={speaker_type}, party={speaker_party})"
        )

        # タスク指示メッセージを作成
        task_description = (
            f"発言者'{speaker_name}'に最もマッチする政治家を見つけてください。"
        )
        if speaker_type:
            task_description += f"\n発言者種別: {speaker_type}"
        if speaker_party:
            task_description += f"\n所属政党: {speaker_party}"

        initial_state: PoliticianMatchingAgentState = {
            "speaker_name": speaker_name,
            "speaker_type": speaker_type,
            "speaker_party": speaker_party,
            "candidates": [],
            "best_match": None,
            "messages": [HumanMessage(content=task_description)],
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        try:
            result = await self.agent.ainvoke(initial_state)

            # 結果からマッチ情報を抽出
            best_match = result.get("best_match")

            # best_matchがある場合はその情報を使用
            if best_match and best_match.get("matched", False):
                confidence = best_match.get("confidence", 0.0)
                if confidence >= CONFIDENCE_THRESHOLD:
                    logger.info(
                        f"Politician matching completed successfully with "
                        f"confidence={confidence}"
                    )
                    return PoliticianMatchingAgentResult(
                        matched=True,
                        politician_id=best_match.get("politician_id"),
                        politician_name=best_match.get("politician_name"),
                        political_party_name=best_match.get("political_party_name"),
                        confidence=confidence,
                        reason=best_match.get("reason", ""),
                        error_message=None,
                    )

            # メッセージ履歴からツール呼び出し結果を解析
            match_result = self._extract_match_from_messages(result.get("messages", []))
            if match_result:
                return match_result

            # マッチなし
            logger.info("Politician matching completed with no match")
            return PoliticianMatchingAgentResult(
                matched=False,
                politician_id=None,
                politician_name=None,
                political_party_name=None,
                confidence=0.0,
                reason="マッチする政治家が見つかりませんでした",
                error_message=None,
            )

        except Exception as e:
            logger.error(
                f"Error during politician matching: {str(e)}",
                exc_info=True,
            )
            return PoliticianMatchingAgentResult(
                matched=False,
                politician_id=None,
                politician_name=None,
                political_party_name=None,
                confidence=0.0,
                reason="",
                error_message=f"マッチング中にエラーが発生しました: {str(e)}",
            )

    def _extract_match_from_messages(
        self, messages: list[BaseMessage]
    ) -> PoliticianMatchingAgentResult | None:
        """メッセージ履歴からマッチ結果を抽出

        ReActエージェントのツール呼び出し結果からマッチ情報を探します。

        Args:
            messages: エージェントのメッセージ履歴

        Returns:
            マッチ結果（見つからない場合はNone）
        """
        for message in reversed(messages):
            # ToolMessageからの結果を解析
            if hasattr(message, "content") and isinstance(message.content, str):
                try:
                    # JSON形式のツール結果を解析
                    content = message.content
                    if "matched" in content and "confidence" in content:
                        data = json.loads(content)
                        if (
                            data.get("matched", False)
                            and data.get("confidence", 0.0) >= CONFIDENCE_THRESHOLD
                        ):
                            return PoliticianMatchingAgentResult(
                                matched=True,
                                politician_id=data.get("politician_id"),
                                politician_name=data.get("politician_name"),
                                political_party_name=data.get("political_party_name"),
                                confidence=data.get("confidence", 0.0),
                                reason=data.get("reason", ""),
                                error_message=None,
                            )
                except (json.JSONDecodeError, TypeError):
                    continue

        return None
