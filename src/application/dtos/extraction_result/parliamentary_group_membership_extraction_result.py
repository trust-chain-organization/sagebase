"""議員団メンバーシップの抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


@dataclass
class ParliamentaryGroupMembershipExtractionResult:
    """議員団メンバーシップのAI抽出結果を表すDTO。

    Attributes:
        politician_id: 政治家ID
        parliamentary_group_id: 議員団ID
        start_date: 開始日
        end_date: 終了日
        role: 役職
    """

    politician_id: int
    parliamentary_group_id: int
    start_date: date
    end_date: date | None = None
    role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現（dateはISO形式文字列に変換）
        """
        data = asdict(self)
        # dateオブジェクトをISO形式文字列に変換
        if self.start_date is not None:
            data["start_date"] = self.start_date.isoformat()
        if self.end_date is not None:
            data["end_date"] = self.end_date.isoformat()
        return data
