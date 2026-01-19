"""発言者関連DTO"""

from dataclasses import dataclass

from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


@dataclass
class SpeakerWithConversationCountDTO:
    """発言者と発言回数のDTO

    リポジトリコントラクトで使用されます。
    """

    id: int
    name: str
    type: str | None
    political_party_name: str | None
    position: str | None
    is_politician: bool
    conversation_count: int


@dataclass
class SpeakerWithPoliticianDTO:
    """発言者と紐付け政治家情報のDTO

    発言者をマッチした政治家データと一緒に取得する際に使用します。
    ドメインエンティティへの動的属性追加を避けることで
    Clean Architectureを維持します。
    """

    speaker: Speaker
    politician: Politician | None


@dataclass
class CreateSpeakerDTO:
    """DTO for creating a speaker."""

    name: str
    type: str | None = None
    political_party_name: str | None = None
    position: str | None = None
    is_politician: bool = False


@dataclass
class UpdateSpeakerDTO:
    """DTO for updating a speaker."""

    id: int
    name: str | None = None
    type: str | None = None
    political_party_name: str | None = None
    position: str | None = None
    is_politician: bool | None = None


@dataclass
class SpeakerDTO:
    """DTO for speaker data."""

    id: int
    name: str
    type: str | None
    political_party_name: str | None
    position: str | None
    is_politician: bool
    linked_politician_id: int | None = None
    linked_politician_name: str | None = None


@dataclass
class SpeakerMatchingDTO:
    """DTO for speaker matching results."""

    speaker_id: int
    speaker_name: str
    matched_politician_id: int | None
    matched_politician_name: str | None
    confidence_score: float
    matching_method: str  # "rule-based", "llm", "manual", "existing", "none"
    matching_reason: str = (
        ""  # Reason for the matching decision  # "rule-based", "llm", "manual"
    )


__all__ = [
    "CreateSpeakerDTO",
    "UpdateSpeakerDTO",
    "SpeakerDTO",
    "SpeakerMatchingDTO",
    "SpeakerWithConversationCountDTO",
    "SpeakerWithPoliticianDTO",
]
