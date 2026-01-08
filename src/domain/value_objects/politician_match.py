"""政治家マッチング結果のValue Object

このモジュールは、政治家マッチング処理の結果を表すValue Objectを定義します。
Domain層に配置されており、Infrastructure層の実装から利用されます。
"""

from pydantic import BaseModel, Field


class PoliticianMatch(BaseModel):
    """政治家マッチング結果のValue Object

    発言者と政治家のマッチング処理結果を保持します。
    ルールベースマッチングとLLM（BAML）マッチングの両方で使用されます。

    Attributes:
        matched: マッチングが成功したかどうか
        politician_id: マッチした政治家のID（マッチなしの場合None）
        politician_name: マッチした政治家の名前（マッチなしの場合None）
        political_party_name: マッチした政治家の所属政党（マッチなしの場合None）
        confidence: マッチングの信頼度（0.0〜1.0）
        reason: マッチング判定の理由
    """

    matched: bool = Field(description="マッチングが成功したかどうか")
    politician_id: int | None = Field(description="マッチした政治家のID", default=None)
    politician_name: str | None = Field(
        description="マッチした政治家の名前", default=None
    )
    political_party_name: str | None = Field(
        description="マッチした政治家の所属政党", default=None
    )
    confidence: float = Field(description="マッチングの信頼度 (0.0-1.0)", default=0.0)
    reason: str = Field(description="マッチング判定の理由", default="")
