"""会議体メンバー抽出DTO

会議体メンバー抽出のためのデータ転送オブジェクト。
レイヤー間でメンバー情報をやり取りする際に使用されます。
"""

from typing import TypedDict

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


class ConferenceMemberExtractionResult(TypedDict):
    """会議体メンバー抽出結果のDTO

    LangGraphエージェントによるメンバー抽出の結果を表現します。
    抽出されたメンバーリスト、成功フラグ、検証エラー、
    エラーメッセージを含みます。
    """

    members: list[ExtractedMemberDTO]
    success: bool
    validation_errors: list[str]
    error_message: str | None
