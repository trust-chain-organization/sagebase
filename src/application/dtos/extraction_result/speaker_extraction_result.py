"""発言者の抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SpeakerExtractionResult:
    """発言者のAI抽出結果を表すDTO。

    Attributes:
        name: 発言者名
        type: 発言者タイプ（議員、参考人など）
        political_party_name: 所属政党名
        position: 役職
        is_politician: 政治家かどうか
        politician_id: 紐付けられた政治家ID
    """

    name: str
    type: str | None = None
    political_party_name: str | None = None
    position: str | None = None
    is_politician: bool = False
    politician_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現
        """
        return asdict(self)
