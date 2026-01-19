"""政治家マッチングエージェントDTO

政治家マッチングエージェントのためのデータ転送オブジェクト。
LangGraphエージェントの結果をレイヤー間で転送する際に使用されます。
"""

from typing import TypedDict


class PoliticianMatchingAgentResult(TypedDict):
    """政治家マッチングエージェント結果のDTO

    LangGraphエージェントによる政治家マッチングの結果を表現します。
    マッチング結果、信頼度、判定理由、エラー情報を含みます。
    """

    matched: bool
    politician_id: int | None
    politician_name: str | None
    political_party_name: str | None
    confidence: float
    reason: str
    error_message: str | None
