"""Domain type definitions for type safety."""

from .common import EntityId, OptionalDate, OptionalInt, OptionalStr, Timestamp
from .dto import (
    ConferenceDTO,
    ConversationDTO,
    ExtractedConferenceMemberDTO,
    GoverningBodyDTO,
    MeetingDTO,
    MinutesDTO,
    ParliamentaryGroupDTO,
    PoliticianDTO,
    SpeakerDTO,
)
from .llm import (
    LLMConferenceMemberExtractContext,
    LLMExtractResult,
    LLMMatchResult,
    LLMPoliticianMatchContext,
    LLMSpeakerMatchContext,
)


__all__ = [
    # Common types
    "EntityId",
    "Timestamp",
    "OptionalStr",
    "OptionalInt",
    "OptionalDate",
    # DTOs
    "PoliticianDTO",
    "SpeakerDTO",
    "MeetingDTO",
    "ConversationDTO",
    "MinutesDTO",
    "ConferenceDTO",
    "GoverningBodyDTO",
    "ParliamentaryGroupDTO",
    "ExtractedConferenceMemberDTO",
    # LLM types
    "LLMMatchResult",
    "LLMExtractResult",
    "LLMSpeakerMatchContext",
    "LLMPoliticianMatchContext",
    "LLMConferenceMemberExtractContext",
]
