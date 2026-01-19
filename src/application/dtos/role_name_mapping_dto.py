"""役職-人名マッピングDTO

役職-人名マッピング抽出のためのデータ転送オブジェクト。
議事録の出席者情報から抽出された役職と人名の対応を表現します。
"""

from pydantic import BaseModel, Field


class RoleNameMappingDTO(BaseModel):
    """役職-人名マッピングのDTO

    議事録の出席者情報から抽出された役職と人名の対応を表現します。
    """

    role: str = Field(..., description="役職名（例: 議長、副議長、知事）")
    name: str = Field(..., description="人名（例: 伊藤条一、梶谷大志）")
    member_number: str | None = Field(None, description="議員番号（あれば）")


class RoleNameMappingResultDTO(BaseModel):
    """役職-人名マッピング抽出結果のDTO

    議事録の出席者情報からの役職-人名マッピング抽出結果を表現します。
    マッピングリスト、出席者セクション検出フラグ、信頼度を含みます。
    """

    mappings: list[RoleNameMappingDTO] = Field(
        default_factory=list, description="役職と人名のマッピングリスト"
    )
    attendee_section_found: bool = Field(
        False, description="出席者セクションが見つかったか"
    )
    confidence: float = Field(0.0, description="抽出の信頼度（0.0-1.0）")

    def to_dict(self) -> dict[str, str]:
        """シンプルな辞書形式に変換（役職 -> 人名）

        Returns:
            dict[str, str]: 役職をキー、人名を値とする辞書

        Note:
            同一役職が複数存在する場合（例: 委員が複数名）、
            後に出現する人名で上書きされます。
            全ての人名を取得したい場合は、mappingsリストを直接参照してください。
        """
        return {m.role: m.name for m in self.mappings}
