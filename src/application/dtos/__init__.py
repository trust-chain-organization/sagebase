"""Application DTOs package."""

from src.application.dtos.conference_dto import (
    AffiliationDTO,
    ConferenceDTO,
    ConferenceMemberMatchingDTO,
    CreateAffiliationDTO,
    ExtractedConferenceMemberDTO,
)
from src.application.dtos.minutes_dto import (
    ExtractedSpeechDTO,
    MinutesDTO,
    MinutesProcessingResultDTO,
    ProcessMinutesDTO,
)
from src.application.dtos.politician_dto import (
    CreatePoliticianDTO,
    PoliticianDTO,
    PoliticianPartyExtractedPoliticianDTO,
    PoliticianPartyExtractedPoliticianOutputDTO,
    ScrapePoliticiansInputDTO,
    UpdatePoliticianDTO,
)
from src.application.dtos.speaker_dto import (
    CreateSpeakerDTO,
    SpeakerDTO,
    SpeakerMatchingDTO,
    UpdateSpeakerDTO,
)


__all__ = [
    # Conference DTOs
    "AffiliationDTO",
    "ConferenceDTO",
    "ConferenceMemberMatchingDTO",
    "CreateAffiliationDTO",
    "ExtractedConferenceMemberDTO",
    # Minutes DTOs
    "ExtractedSpeechDTO",
    "MinutesDTO",
    "MinutesProcessingResultDTO",
    "ProcessMinutesDTO",
    # Politician DTOs
    "CreatePoliticianDTO",
    "PoliticianDTO",
    "PoliticianPartyExtractedPoliticianDTO",
    "PoliticianPartyExtractedPoliticianOutputDTO",
    "ScrapePoliticiansInputDTO",
    "UpdatePoliticianDTO",
    # Speaker DTOs
    "CreateSpeakerDTO",
    "SpeakerDTO",
    "SpeakerMatchingDTO",
    "UpdateSpeakerDTO",
]
