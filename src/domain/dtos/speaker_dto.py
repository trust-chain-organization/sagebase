"""Speaker DTOs for domain layer repository contracts."""

from dataclasses import dataclass

from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


@dataclass
class SpeakerWithConversationCountDTO:
    """DTO for speaker with conversation count.

    This DTO is used in repository contracts and belongs to the domain layer.
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
    """DTO for speaker with linked politician information.

    This DTO is used when retrieving speakers along with their matched politician
    data. It maintains Clean Architecture by avoiding dynamic attribute assignment
    on domain entities.
    """

    speaker: Speaker
    politician: Politician | None
