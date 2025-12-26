"""Domain repository interfaces package."""

from src.domain.repositories.base import BaseRepository
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.governing_body_repository import GoverningBodyRepository
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.prompt_version_repository import PromptVersionRepository
from src.domain.repositories.speaker_repository import SpeakerRepository


__all__ = [
    "BaseRepository",
    "ConferenceRepository",
    "ConversationRepository",
    "GoverningBodyRepository",
    "LLMProcessingHistoryRepository",
    "MeetingRepository",
    "MinutesRepository",
    "ParliamentaryGroupRepository",
    "PoliticalPartyRepository",
    "PoliticianRepository",
    "PromptVersionRepository",
    "SpeakerRepository",
]
