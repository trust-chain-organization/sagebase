"""Application DTOs package."""

from src.application.dtos.conference_dto import (
    AffiliationDTO,
    ConferenceDTO,
    ConferenceMemberMatchingDTO,
    CreateAffiliationDTO,
    ExtractedConferenceMemberDTO,
)
from src.application.dtos.extraction_log_dto import (
    DailyCountDTO,
    ExtractionLogDetailDTO,
    ExtractionLogFilterDTO,
    ExtractionStatisticsDTO,
    PaginatedExtractionLogsDTO,
)
from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.dtos.extraction_result.parliamentary_group_membership_extraction_result import (  # noqa: E501
    ParliamentaryGroupMembershipExtractionResult,
)
from src.application.dtos.extraction_result.politician_extraction_result import (
    PoliticianExtractionResult,
)
from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
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
    # Extraction Result DTOs
    "ConversationExtractionResult",
    "ParliamentaryGroupMembershipExtractionResult",
    "PoliticianExtractionResult",
    "SpeakerExtractionResult",
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
    # Extraction Log DTOs
    "DailyCountDTO",
    "ExtractionLogDetailDTO",
    "ExtractionLogFilterDTO",
    "ExtractionStatisticsDTO",
    "PaginatedExtractionLogsDTO",
]
