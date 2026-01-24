"""
Dependency providers for dependency injection containers.

This module defines the providers for repositories, services, and use cases.
"""

from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.application.usecases.backfill_role_name_mappings_usecase import (
    BackfillRoleNameMappingsUseCase,
)
from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingUseCase,
)
from src.application.usecases.execute_speaker_extraction_usecase import (
    ExecuteSpeakerExtractionUseCase,
)
from src.application.usecases.extract_proposal_judges_usecase import (
    ExtractProposalJudgesUseCase,
)
from src.application.usecases.link_speaker_to_politician_usecase import (
    LinkSpeakerToPoliticianUseCase,
)
from src.application.usecases.manage_conference_members_usecase import (
    ManageConferenceMembersUseCase,
)
from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.application.usecases.process_minutes_usecase import ProcessMinutesUseCase
from src.application.usecases.update_extracted_conference_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedConferenceMemberFromExtractionUseCase,
)
from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
)
from src.application.usecases.update_speaker_from_extraction_usecase import (
    UpdateSpeakerFromExtractionUseCase,
)
from src.application.usecases.update_statement_from_extraction_usecase import (
    UpdateStatementFromExtractionUseCase,
)
from src.application.usecases.view_data_coverage_usecase import (
    ViewActivityTrendUseCase,
    ViewGoverningBodyCoverageUseCase,
    ViewMeetingCoverageUseCase,
    ViewSpeakerMatchingStatsUseCase,
)
from src.domain.interfaces.minutes_divider_service import IMinutesDividerService
from src.domain.interfaces.role_name_mapping_service import IRoleNameMappingService
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.services.interfaces.storage_service import IStorageService
from src.domain.services.politician_domain_service import PoliticianDomainService
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.external.gcs_storage_service import GCSStorageService
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.minutes_divider.baml_minutes_divider import (
    BAMLMinutesDivider,
)
from src.infrastructure.external.minutes_processing_service import (
    MinutesProcessAgentService,
)
from src.infrastructure.external.politician_matching import (
    BAMLPoliticianMatchingService,
)
from src.infrastructure.external.role_name_mapping.baml_role_name_mapping_service import (
    BAMLRoleNameMappingService,
)
from src.infrastructure.external.web_scraper_service import (
    IWebScraperService,
    PlaywrightScraperService,
)
from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.data_coverage_repository_impl import (
    DataCoverageRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.llm_processing_history_repository_impl import (
    LLMProcessingHistoryRepositoryImpl,
)
from src.infrastructure.persistence.llm_service_adapter import LLMServiceAdapter
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.minutes_repository_impl import MinutesRepositoryImpl
from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_affiliation_repository_impl import (
    PoliticianAffiliationRepositoryImpl,
)
from src.infrastructure.persistence.politician_operation_log_repository_impl import (
    PoliticianOperationLogRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.prompt_version_repository_impl import (
    PromptVersionRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_operation_log_repository_impl import (
    ProposalOperationLogRepositoryImpl,
)
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.proposal_submitter_repository_impl import (
    ProposalSubmitterRepositoryImpl,
)
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl
from src.infrastructure.persistence.unit_of_work_impl import UnitOfWorkImpl
from src.infrastructure.persistence.user_repository_impl import UserRepositoryImpl


def _create_conference_member_extraction_agent():
    """会議体メンバー抽出エージェントを作成するヘルパー関数

    遅延インポートを使用して循環参照を回避します。
    Issue #903: LangGraph+BAML統合
    """
    from src.infrastructure.external.conference_member_extractor.factory import (
        MemberExtractorFactory,
    )

    return MemberExtractorFactory.create_agent()


def _create_politician_matching_agent(
    politician_repo: "PoliticianRepositoryImpl",
    affiliation_repo: "PoliticianAffiliationRepositoryImpl",
):
    """政治家マッチングエージェントを作成するヘルパー関数

    遅延インポートを使用して循環参照を回避します。
    Issue #904: LangGraph+BAML統合（政治家マッチング）

    Args:
        politician_repo: PoliticianRepository（必須）
        affiliation_repo: PoliticianAffiliationRepository（必須）
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    from src.infrastructure.external.langgraph_politician_matching_agent import (
        PoliticianMatchingAgent,
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.0,
    )
    return PoliticianMatchingAgent(
        llm=llm,
        politician_repo=politician_repo,
        affiliation_repo=affiliation_repo,
    )


# Mock SQLAlchemy model classes for repositories that don't have them yet
class MockSpeakerModel:
    """Mock SQLAlchemy model for Speaker entity."""

    __tablename__ = "speakers"
    id = None
    name = None


class MockPoliticianModel:
    """Mock SQLAlchemy model for Politician entity."""

    __tablename__ = "politicians"
    id = None
    name = None


class MockMeetingModel:
    """Mock SQLAlchemy model for Meeting entity."""

    __tablename__ = "meetings"
    id = None


class MockConversationModel:
    """Mock SQLAlchemy model for Conversation entity."""

    __tablename__ = "conversations"
    id = None


class MockMinutesModel:
    """Mock SQLAlchemy model for Minutes entity."""

    __tablename__ = "minutes"
    id = None


class MockService:
    """Mock service for testing."""

    def __init__(self, service_type: str):
        self.service_type = service_type


class MockDomainService:
    """Mock domain service for testing."""

    def __init__(self, domain_type: str):
        self.domain_type = domain_type


class MockRepository:
    """Mock repository for testing."""

    def __init__(self, repository_type: str):
        self.repository_type = repository_type


def create_engine_with_config(database_url: str | None):
    """Create SQLAlchemy engine with appropriate configuration for database type."""
    # Handle None database_url with a default
    if database_url is None:
        import logging
        import os

        logger = logging.getLogger(__name__)
        # Use debug level as this is expected behavior during initial container setup
        logger.debug("database_url is None, using default value based on environment")

        # Check if running in Docker
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
            database_url = (
                "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db"
            )
        else:
            database_url = "postgresql://sagebase_user:sagebase_password@localhost:5432/sagebase_db"

    engine_kwargs = {
        "url": database_url,
        "pool_pre_ping": True,
    }

    # Only add pool parameters for non-SQLite databases
    if not database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
            }
        )

    return create_engine(**engine_kwargs)


class DatabaseContainer(containers.DeclarativeContainer):
    """Container for database-related dependencies."""

    config = providers.Configuration()

    engine = providers.Singleton(
        create_engine_with_config,
        database_url=config.database_url,
    )

    session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    session = providers.Factory(
        lambda factory: factory(),
        factory=session_factory,
    )

    async_session = providers.Factory(
        AsyncSessionAdapter,
        sync_session=session,
    )


class RepositoryContainer(containers.DeclarativeContainer):
    """Container for repository implementations."""

    database = providers.DependenciesContainer()

    speaker_repository = providers.Factory(
        SpeakerRepositoryImpl,
        session=database.async_session,
    )

    politician_repository = providers.Factory(
        PoliticianRepositoryImpl,
        session=database.async_session,
    )

    meeting_repository = providers.Factory(
        MeetingRepositoryImpl,
        session=database.async_session,
    )

    conversation_repository = providers.Factory(
        ConversationRepositoryImpl,
        session=database.async_session,
    )

    extraction_log_repository = providers.Factory(
        ExtractionLogRepositoryImpl,
        session=database.async_session,
    )

    minutes_repository = providers.Factory(
        MinutesRepositoryImpl,
        session=database.async_session,
    )

    conference_repository = providers.Factory(
        ConferenceRepositoryImpl,
        session=database.async_session,
    )

    governing_body_repository = providers.Factory(
        GoverningBodyRepositoryImpl,
        session=database.async_session,
    )

    political_party_repository = providers.Factory(
        PoliticalPartyRepositoryImpl,
        session=database.async_session,
    )

    politician_affiliation_repository = providers.Factory(
        PoliticianAffiliationRepositoryImpl,
        session=database.async_session,
    )

    extracted_conference_member_repository = providers.Factory(
        ExtractedConferenceMemberRepositoryImpl,
        session=database.async_session,
    )

    extracted_parliamentary_group_member_repository = providers.Factory(
        ExtractedParliamentaryGroupMemberRepositoryImpl,
        session=database.async_session,
    )

    extracted_proposal_judge_repository = providers.Factory(
        ExtractedProposalJudgeRepositoryImpl,
        session=database.async_session,
    )

    parliamentary_group_repository = providers.Factory(
        ParliamentaryGroupRepositoryImpl,
        session=database.async_session,
    )

    parliamentary_group_membership_repository = providers.Factory(
        ParliamentaryGroupMembershipRepositoryImpl,
        session=database.async_session,
    )

    monitoring_repository = providers.Factory(
        MonitoringRepositoryImpl,
        session=database.async_session,
    )

    llm_processing_history_repository = providers.Factory(
        LLMProcessingHistoryRepositoryImpl,
        session=database.async_session,
    )

    prompt_version_repository = providers.Factory(
        PromptVersionRepositoryImpl,
        session=database.async_session,
    )

    proposal_repository = providers.Factory(
        ProposalRepositoryImpl,
        session=database.async_session,
    )

    proposal_judge_repository = providers.Factory(
        ProposalJudgeRepositoryImpl,
        session=database.async_session,
    )

    proposal_parliamentary_group_judge_repository = providers.Factory(
        ProposalParliamentaryGroupJudgeRepositoryImpl,
        session=database.async_session,
    )

    proposal_submitter_repository = providers.Factory(
        ProposalSubmitterRepositoryImpl,
        session=database.async_session,
    )

    data_coverage_repository = providers.Factory(
        DataCoverageRepositoryImpl,
        session=database.async_session,
    )

    user_repository = providers.Factory(
        UserRepositoryImpl,
        session=database.async_session,
    )

    politician_operation_log_repository = providers.Factory(
        PoliticianOperationLogRepositoryImpl,
        session=database.async_session,
    )

    proposal_operation_log_repository = providers.Factory(
        ProposalOperationLogRepositoryImpl,
        session=database.async_session,
    )


class ServiceContainer(containers.DeclarativeContainer):
    """Container for external service implementations."""

    config = providers.Configuration()

    # Create async LLM service
    async_llm_service: providers.Provider[ILLMService] = providers.Factory(
        GeminiLLMService,
        api_key=config.google_api_key,
        model_name=config.llm_model,
        temperature=config.llm_temperature,
    )

    # Wrap with adapter for synchronous use cases
    llm_service = providers.Factory(
        LLMServiceAdapter,
        llm_service=async_llm_service,
    )

    storage_service: providers.Provider[IStorageService] = providers.Singleton(
        GCSStorageService,
        bucket_name=config.gcs_bucket_name,
    )

    web_scraper_service: providers.Provider[IWebScraperService] = providers.Factory(
        PlaywrightScraperService,
        headless=True,
    )

    minutes_processing_service: providers.Provider[IMinutesProcessingService] = (
        providers.Factory(
            MinutesProcessAgentService,
            llm_service=llm_service,
        )
    )

    # Domain services
    politician_domain_service = providers.Factory(PoliticianDomainService)
    speaker_domain_service = providers.Factory(SpeakerDomainService)

    # Mock services for testing (these may not have real implementations yet)
    minutes_domain_service = providers.Factory(lambda: MockDomainService("minutes"))

    pdf_processor_service = providers.Factory(lambda: MockService("pdf_processor"))

    text_extractor_service = providers.Factory(lambda: MockService("text_extractor"))

    # Conference member extraction agent (Issue #903)
    # LangGraph + BAMLの二層構造を持つエージェント
    conference_member_extraction_agent = providers.Factory(
        lambda: _create_conference_member_extraction_agent()
    )

    # Role name mapping service (Issue #944)
    role_name_mapping_service: providers.Provider[IRoleNameMappingService] = (
        providers.Factory(BAMLRoleNameMappingService)
    )

    # Minutes divider service (境界検出用)
    minutes_divider_service: providers.Provider[IMinutesDividerService] = (
        providers.Factory(BAMLMinutesDivider)
    )


class UseCaseContainer(containers.DeclarativeContainer):
    """Container for use case implementations."""

    repositories = providers.DependenciesContainer()
    services = providers.DependenciesContainer()
    database = providers.DependenciesContainer()

    process_minutes_usecase = providers.Factory(
        ProcessMinutesUseCase,
        meeting_repository=repositories.meeting_repository,
        minutes_repository=repositories.minutes_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_repository=repositories.speaker_repository,
        minutes_domain_service=services.minutes_domain_service,
        speaker_domain_service=services.speaker_domain_service,
        pdf_processor=services.pdf_processor_service,
        text_extractor=services.text_extractor_service,
    )

    # Update Speaker from Extraction UseCase (Issue #865)
    update_speaker_usecase = providers.Factory(
        UpdateSpeakerFromExtractionUseCase,
        speaker_repo=repositories.speaker_repository,
        extraction_log_repo=repositories.extraction_log_repository,
        session_adapter=database.async_session,
    )

    # Update Extracted Conference Member from Extraction UseCase (Issue #867)
    update_extracted_conference_member_usecase = providers.Factory(
        UpdateExtractedConferenceMemberFromExtractionUseCase,
        extracted_conference_member_repo=repositories.extracted_conference_member_repository,
        extraction_log_repo=repositories.extraction_log_repository,
        session_adapter=database.async_session,
    )

    # Update Extracted Parliamentary Group Member from Extraction UseCase (Issue #867)
    update_extracted_parliamentary_group_member_usecase = providers.Factory(
        UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
        extracted_parliamentary_group_member_repo=repositories.extracted_parliamentary_group_member_repository,
        extraction_log_repo=repositories.extraction_log_repository,
        session_adapter=database.async_session,
    )

    # BAML Politician Matching Service (Issue #885)
    baml_politician_matching_service = providers.Factory(
        BAMLPoliticianMatchingService,
        llm_service=services.async_llm_service,
        politician_repository=repositories.politician_repository,
    )

    match_speakers_usecase = providers.Factory(
        MatchSpeakersUseCase,
        speaker_repository=repositories.speaker_repository,
        politician_repository=repositories.politician_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_domain_service=services.speaker_domain_service,
        llm_service=services.async_llm_service,  # Use async service directly
        update_speaker_usecase=update_speaker_usecase,
        baml_matching_service=baml_politician_matching_service,  # Issue #885
    )

    # Link Speaker to Politician UseCase (PR #957)
    # 発言者と政治家の手動紐付け用ユースケース
    link_speaker_to_politician_usecase = providers.Factory(
        LinkSpeakerToPoliticianUseCase,
        speaker_repository=repositories.speaker_repository,
    )

    manage_conference_members_usecase = providers.Factory(
        ManageConferenceMembersUseCase,
        conference_repository=repositories.conference_repository,
        extracted_member_repository=repositories.extracted_conference_member_repository,
        politician_repository=repositories.politician_repository,
        politician_affiliation_repository=repositories.politician_affiliation_repository,
        web_scraper_service=services.web_scraper_service,
        llm_service=services.llm_service,
    )

    speaker_extraction_usecase = providers.Factory(
        ExecuteSpeakerExtractionUseCase,
        minutes_repository=repositories.minutes_repository,
        conversation_repository=repositories.conversation_repository,
        speaker_repository=repositories.speaker_repository,
        speaker_domain_service=services.speaker_domain_service,
    )

    # Unit of Work for transaction management
    unit_of_work = providers.Factory(
        UnitOfWorkImpl,
        session=database.async_session,
    )

    # Update Statement from Extraction UseCase (Issue #865)
    update_statement_usecase = providers.Factory(
        UpdateStatementFromExtractionUseCase,
        conversation_repo=repositories.conversation_repository,
        extraction_log_repo=repositories.extraction_log_repository,
        session_adapter=database.async_session,
    )

    minutes_processing_usecase = providers.Factory(
        ExecuteMinutesProcessingUseCase,
        speaker_domain_service=services.speaker_domain_service,
        minutes_processing_service=services.minutes_processing_service,
        storage_service=services.storage_service,
        unit_of_work=unit_of_work,
        update_statement_usecase=update_statement_usecase,
        role_name_mapping_service=services.role_name_mapping_service,
        minutes_divider_service=services.minutes_divider_service,
    )

    extract_proposal_judges_usecase = providers.Factory(
        ExtractProposalJudgesUseCase,
        proposal_repository=repositories.proposal_repository,
        politician_repository=repositories.politician_repository,
        extracted_proposal_judge_repository=repositories.extracted_proposal_judge_repository,
        proposal_judge_repository=repositories.proposal_judge_repository,
        web_scraper_service=services.web_scraper_service,
        llm_service=services.llm_service,
    )

    # Data coverage use cases
    view_governing_body_coverage_usecase = providers.Factory(
        ViewGoverningBodyCoverageUseCase,
        data_coverage_repo=repositories.data_coverage_repository,
    )

    view_meeting_coverage_usecase = providers.Factory(
        ViewMeetingCoverageUseCase,
        data_coverage_repo=repositories.data_coverage_repository,
    )

    view_speaker_matching_stats_usecase = providers.Factory(
        ViewSpeakerMatchingStatsUseCase,
        data_coverage_repo=repositories.data_coverage_repository,
    )

    view_activity_trend_usecase = providers.Factory(
        ViewActivityTrendUseCase,
        data_coverage_repo=repositories.data_coverage_repository,
    )

    # Politician matching agent (Issue #904)
    # LangGraph + BAMLの二層構造を持つエージェント
    # リポジトリを注入してService Locatorパターンを回避
    politician_matching_agent = providers.Factory(
        _create_politician_matching_agent,
        politician_repo=repositories.politician_repository,
        affiliation_repo=repositories.politician_affiliation_repository,
    )

    # Backfill role name mappings usecase (Issue #947)
    backfill_role_name_mappings_usecase = providers.Factory(
        BackfillRoleNameMappingsUseCase,
        unit_of_work=unit_of_work,
        storage_service=services.storage_service,
        role_name_mapping_service=services.role_name_mapping_service,
        minutes_divider_service=services.minutes_divider_service,
    )
