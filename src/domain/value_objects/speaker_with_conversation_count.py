"""発言者と発言回数を表すValue Object"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerWithConversationCount:
    """発言者と発言回数のValue Object

    リポジトリからの戻り値として使用され、発言者情報と
    その発言者に紐づく会話の数を保持します。

    frozen=Trueによりイミュータブルとなり、Value Objectの
    等価性とハッシュ可能性が自動的に保証されます。
    """

    id: int
    name: str
    type: str | None
    political_party_name: str | None
    position: str | None
    is_politician: bool
    conversation_count: int
