"""議員団メンバー抽出DTO

議員団メンバー抽出のためのデータ転送オブジェクト。
レイヤー間でメンバー情報をやり取りする際に使用されます。
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExtractedParliamentaryGroupMemberDTO:
    """抽出された議員団メンバー情報のDTO

    HTMLからLLMによって抽出されたメンバー情報を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。
    """

    name: str
    role: str | None = None
    party_name: str | None = None
    district: str | None = None
    additional_info: str | None = None


@dataclass
class ParliamentaryGroupMemberExtractionResultDTO:
    """議員団メンバー抽出結果のDTO

    議員団URLからのメンバー抽出結果を表現します。
    インフラストラクチャ層からアプリケーション層への
    データ転送に使用されます。
    """

    parliamentary_group_id: int
    url: str
    extracted_members: list[ExtractedParliamentaryGroupMemberDTO]
    extraction_date: datetime | None = None
    error: str | None = None


@dataclass
class ParliamentaryGroupMemberAgentResultDTO:
    """議員団メンバー抽出エージェントの結果DTO

    LangGraphエージェントによる議員団メンバー抽出の結果を表現します。
    会議体メンバー抽出エージェントと同様の構造を持ちます。

    Note:
        ParliamentaryGroupMemberExtractionResultDTOはURL経由の抽出結果用、
        このDTOはLangGraphエージェント経由の抽出結果用です。

    Attributes:
        members: 抽出されたメンバーのリスト
        success: 抽出成功フラグ
        validation_errors: 検証エラーのリスト
        error_message: エラーメッセージ（エラー時のみ）
    """

    members: list[ExtractedParliamentaryGroupMemberDTO]
    success: bool
    validation_errors: list[str]
    error_message: str | None = None
