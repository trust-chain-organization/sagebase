"""Domain type definitions for type safety."""

from .common import EntityId, OptionalDate, OptionalInt, OptionalStr, Timestamp
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
    # LLM types
    "LLMMatchResult",
    "LLMExtractResult",
    "LLMSpeakerMatchContext",
    "LLMPoliticianMatchContext",
    "LLMConferenceMemberExtractContext",
]
