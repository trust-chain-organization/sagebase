"""Parliamentary group member extraction DTOs

議員団メンバー抽出のためのデータ転送オブジェクト。
レイヤー間でメンバー情報をやり取りする際に使用されます。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ExtractedParliamentaryGroupMemberDTO(BaseModel):
    """抽出された議員団メンバー情報のDTO

    HTMLからLLMによって抽出されたメンバー情報を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。
    """

    name: str = Field(..., description="議員名")
    role: str | None = Field(None, description="役職（団長、幹事長など）")
    party_name: str | None = Field(None, description="所属政党名")
    district: str | None = Field(None, description="選挙区")
    additional_info: str | None = Field(None, description="その他の情報")


class ParliamentaryGroupMemberExtractionResultDTO(BaseModel):
    """議員団メンバー抽出結果のDTO

    議員団URLからのメンバー抽出結果を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。
    """

    parliamentary_group_id: int = Field(..., description="議員団ID")
    url: str = Field(..., description="抽出元URL")
    extracted_members: list[ExtractedParliamentaryGroupMemberDTO] = Field(
        ..., description="抽出されたメンバーリスト"
    )
    extraction_date: datetime | None = Field(None, description="抽出日時")
    error: str | None = Field(None, description="エラーメッセージ")
