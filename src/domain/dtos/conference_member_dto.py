"""Conference member extraction DTOs

会議体メンバー抽出のためのデータ転送オブジェクト。
レイヤー間でメンバー情報をやり取りする際に使用されます。
"""

from pydantic import BaseModel, Field


class ExtractedMemberDTO(BaseModel):
    """抽出された会議体メンバー情報のDTO

    HTMLからLLMによって抽出されたメンバー情報を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。
    """

    name: str = Field(..., description="議員名")
    role: str | None = Field(None, description="役職（議長、副議長、委員長、委員など）")
    party_name: str | None = Field(None, description="所属政党名")
    additional_info: str | None = Field(None, description="その他の情報")
