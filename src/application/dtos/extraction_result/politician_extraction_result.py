"""政治家の抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PoliticianExtractionResult:
    """政治家のAI抽出結果を表すDTO。

    Attributes:
        name: 政治家名
        furigana: ふりがな
        political_party_id: 所属政党ID
        district: 選挙区
        profile_page_url: プロフィールページURL
        party_position: 党内役職
    """

    name: str
    furigana: str | None = None
    political_party_id: int | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現
        """
        return asdict(self)
