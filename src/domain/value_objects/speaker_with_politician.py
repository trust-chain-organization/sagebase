"""発言者と政治家の組み合わせを表すValue Object"""

from dataclasses import dataclass

from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


@dataclass(frozen=True)
class SpeakerWithPolitician:
    """発言者と紐付け政治家情報のValue Object

    発言者をマッチした政治家データと一緒に取得する際に使用します。
    ドメインエンティティへの動的属性追加を避けることで
    Clean Architectureを維持します。
    """

    speaker: Speaker
    politician: Politician | None
