"""Application DTOs package."""

from src.application.dtos.base_dto import (
    ConferenceBaseDTO,
    ConversationBaseDTO,
    ExtractedConferenceMemberBaseDTO,
    GoverningBodyDTO,
    MeetingBaseDTO,
    MinutesBaseDTO,
    ParliamentaryGroupBaseDTO,
    PoliticianBaseDTO,
    SpeakerBaseDTO,
)
from src.application.dtos.conference_dto import (
    AffiliationDTO,
    ConferenceDTO,
    ConferenceMemberMatchingDTO,
    CreateAffiliationDTO,
    ExtractedConferenceMemberDTO,
)
from src.application.dtos.conference_member_extraction_dto import (
    ConferenceMemberExtractionResult,
    ExtractedMemberDTO,
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
from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)
from src.application.dtos.minutes_dto import (
    ExtractedSpeechDTO,
    MinutesDTO,
    MinutesProcessingResultDTO,
    ProcessMinutesDTO,
)
from src.application.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
    ParliamentaryGroupMemberAgentResultDTO,
    ParliamentaryGroupMemberExtractionResultDTO,
)
from src.application.dtos.parliamentary_group_membership_dto import (
    ParliamentaryGroupMembershipWithRelationsDTO,
)
from src.application.dtos.politician_dto import (
    CreatePoliticianDTO,
    CreatePoliticianInputDto,
    CreatePoliticianOutputDto,
    DeletePoliticianInputDto,
    DeletePoliticianOutputDto,
    MergePoliticiansInputDto,
    MergePoliticiansOutputDto,
    PoliticianDTO,
    PoliticianListInputDto,
    PoliticianListOutputDto,
    UpdatePoliticianDTO,
    UpdatePoliticianInputDto,
    UpdatePoliticianOutputDto,
)
from src.application.dtos.politician_matching_dto import (
    PoliticianMatchingAgentResult,
)
from src.application.dtos.role_name_mapping_dto import (
    RoleNameMappingDTO,
    RoleNameMappingResultDTO,
)
from src.application.dtos.speaker_dto import (
    CreateSpeakerDTO,
    SpeakerDTO,
    SpeakerMatchingDTO,
    SpeakerWithConversationCountDTO,
    UpdateSpeakerDTO,
)
from src.application.dtos.web_page_content_dto import WebPageContentDTO


__all__ = [
    # Base DTOs (for backward compatibility with domain types)
    "ConferenceBaseDTO",
    "ConversationBaseDTO",
    "ExtractedConferenceMemberBaseDTO",
    "GoverningBodyDTO",
    "MeetingBaseDTO",
    "MinutesBaseDTO",
    "ParliamentaryGroupBaseDTO",
    "PoliticianBaseDTO",
    "SpeakerBaseDTO",
    # Conference DTOs
    "AffiliationDTO",
    "ConferenceDTO",
    "ConferenceMemberMatchingDTO",
    "CreateAffiliationDTO",
    "ExtractedConferenceMemberDTO",
    # Conference Member Extraction DTOs
    "ConferenceMemberExtractionResult",
    "ExtractedMemberDTO",
    # Extraction Result DTOs
    "ConversationExtractionResult",
    "ParliamentaryGroupMembershipExtractionResult",
    "SpeakerExtractionResult",
    # Minutes DTOs
    "ExtractedSpeechDTO",
    "MinutesDTO",
    "MinutesProcessingResultDTO",
    "ProcessMinutesDTO",
    # Parliamentary Group Member DTOs
    "ExtractedParliamentaryGroupMemberDTO",
    "ParliamentaryGroupMemberAgentResultDTO",
    "ParliamentaryGroupMemberExtractionResultDTO",
    # Parliamentary Group Membership DTOs
    "ParliamentaryGroupMembershipWithRelationsDTO",
    # Politician DTOs
    "CreatePoliticianDTO",
    "CreatePoliticianInputDto",
    "CreatePoliticianOutputDto",
    "DeletePoliticianInputDto",
    "DeletePoliticianOutputDto",
    "MergePoliticiansInputDto",
    "MergePoliticiansOutputDto",
    "PoliticianDTO",
    "PoliticianListInputDto",
    "PoliticianListOutputDto",
    "UpdatePoliticianDTO",
    "UpdatePoliticianInputDto",
    "UpdatePoliticianOutputDto",
    # Politician Matching DTOs
    "PoliticianMatchingAgentResult",
    # Role Name Mapping DTOs
    "RoleNameMappingDTO",
    "RoleNameMappingResultDTO",
    # Speaker DTOs
    "CreateSpeakerDTO",
    "SpeakerDTO",
    "SpeakerMatchingDTO",
    "SpeakerWithConversationCountDTO",
    "UpdateSpeakerDTO",
    # Web Page Content DTOs
    "WebPageContentDTO",
    # Extraction Log DTOs
    "DailyCountDTO",
    "ExtractionLogDetailDTO",
    "ExtractionLogFilterDTO",
    "ExtractionStatisticsDTO",
    "PaginatedExtractionLogsDTO",
]
