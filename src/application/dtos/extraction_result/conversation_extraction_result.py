"""発言（会話）の抽出結果を表すDTO。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ConversationExtractionResult:
    """発言（会話）のAI抽出結果を表すDTO。

    Attributes:
        comment: 発言内容
        speaker_name: 発言者名
        speaker_id: 発言者ID
        sequence_number: 発言順序番号
        chapter_number: 章番号
        sub_chapter_number: 副章番号
        minutes_id: 議事録ID
    """

    comment: str
    sequence_number: int
    speaker_name: str | None = None
    speaker_id: int | None = None
    chapter_number: int | None = None
    sub_chapter_number: int | None = None
    minutes_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Returns:
            抽出データのdict表現
        """
        return asdict(self)
