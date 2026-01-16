"""Presenter for meeting management in Streamlit.

This module provides the presenter layer for meeting management,
handling UI state and coordinating with repositories.
"""

import builtins

from typing import Any

import pandas as pd

from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
    ExecuteMinutesProcessingUseCase,
)
from src.application.usecases.execute_scrape_meeting_usecase import (
    ExecuteScrapeMeetingDTO,
    ExecuteScrapeMeetingUseCase,
)
from src.application.usecases.execute_speaker_extraction_usecase import (
    ExecuteSpeakerExtractionDTO,
    ExecuteSpeakerExtractionUseCase,
)
from src.application.usecases.update_statement_from_extraction_usecase import (
    UpdateStatementFromExtractionUseCase,
)
from src.common.logging import get_logger
from src.domain.entities.meeting import Meeting
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.services.interfaces.storage_service import IStorageService
from src.domain.services.interfaces.unit_of_work import IUnitOfWork
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.di.container import Container
from src.infrastructure.external.gcs_storage_service import GCSStorageService
from src.infrastructure.external.minutes_processing_service import (
    MinutesProcessAgentService,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.minutes_repository_impl import MinutesRepositoryImpl
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl
from src.infrastructure.persistence.unit_of_work_impl import UnitOfWorkImpl
from src.interfaces.web.streamlit.dto.base import FormStateDTO, WebResponseDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager
from src.seed_generator import SeedGenerator


class MeetingPresenter(CRUDPresenter[list[Meeting]]):
    """Presenter for meeting management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
        self.governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
        self.conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
        self.session = SessionManager(namespace="meeting")
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(self.__class__.__name__)

    def _get_or_create_form_state(self) -> FormStateDTO:
        """Get or create form state from session.

        Returns:
            Form state DTO
        """
        state_dict = self.session.get("form_state", {})
        if not state_dict:
            state = FormStateDTO()
            self.session.set("form_state", state.__dict__)
            return state
        return FormStateDTO(**state_dict)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("form_state", self.form_state.__dict__)

    def load_data(self) -> list[Meeting]:
        """Load all meetings.

        Returns:
            List of meetings
        """
        return self.meeting_repo.get_all()

    def load_meetings_with_filters(
        self, governing_body_id: int | None = None, conference_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Load meetings with optional filters.

        Args:
            governing_body_id: Optional governing body filter
            conference_id: Optional conference filter

        Returns:
            List of meeting dictionaries with additional info
        """
        from src.infrastructure.persistence.conversation_repository_impl import (
            ConversationRepositoryImpl,
        )
        from src.infrastructure.persistence.minutes_repository_impl import (
            MinutesRepositoryImpl,
        )
        from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

        # Get all meetings
        meetings = self.meeting_repo.get_all()

        # Convert to dictionaries with additional info
        result = []
        for meeting in meetings:
            # Get conference and governing body info
            conference = self.conference_repo.get_by_id(meeting.conference_id)
            if conference:
                governing_body = self.governing_body_repo.get_by_id(
                    conference.governing_body_id
                )

                # Apply filters
                if (
                    governing_body_id
                    and conference.governing_body_id != governing_body_id
                ):
                    continue
                if conference_id and meeting.conference_id != conference_id:
                    continue

                # Get conversation and speaker counts
                conversation_count = 0
                speaker_count = 0
                try:
                    minutes_repo = RepositoryAdapter(MinutesRepositoryImpl)
                    minutes = minutes_repo.get_by_meeting(meeting.id)
                    if minutes and minutes.id:
                        conversation_repo = RepositoryAdapter(
                            ConversationRepositoryImpl
                        )
                        conversations = conversation_repo.get_by_minutes(minutes.id)
                        conversation_count = len(conversations)
                        # Count unique speakers
                        speaker_ids = {
                            c.speaker_id for c in conversations if c.speaker_id
                        }
                        speaker_count = len(speaker_ids)
                except Exception as e:
                    self.logger.debug(
                        f"Failed to get counts for meeting {meeting.id}: {e}"
                    )

                result.append(
                    {
                        "id": meeting.id,
                        "conference_id": meeting.conference_id,
                        "date": meeting.date,
                        "url": meeting.url,
                        "gcs_pdf_uri": meeting.gcs_pdf_uri,
                        "gcs_text_uri": meeting.gcs_text_uri,
                        "conference_name": conference.name,
                        "governing_body_name": governing_body.name
                        if governing_body
                        else "",
                        "governing_body_type": governing_body.type
                        if governing_body
                        else "",
                        "conversation_count": conversation_count,
                        "speaker_count": speaker_count,
                    }
                )

        return result

    def get_governing_bodies(self) -> list[dict[str, Any]]:
        """Get all governing bodies.

        Returns:
            List of governing body dictionaries
        """
        bodies = self.governing_body_repo.get_all()
        return [
            {
                "id": body.id,
                "name": body.name,
                "type": body.type,
                "display_name": f"{body.name} ({body.type})",
            }
            for body in bodies
        ]

    def get_conferences_by_governing_body(
        self, governing_body_id: int
    ) -> list[dict[str, Any]]:
        """Get conferences for a specific governing body.

        Args:
            governing_body_id: Governing body ID

        Returns:
            List of conference dictionaries
        """
        conferences = self.conference_repo.get_by_governing_body(governing_body_id)
        return [
            {
                "id": conf.id,
                "name": conf.name,
                "governing_body_id": conf.governing_body_id,
            }
            for conf in conferences
        ]

    def create(self, **kwargs: Any) -> WebResponseDTO[Meeting]:
        """Create a new meeting.

        Args:
            **kwargs: Meeting data (conference_id, date, url)

        Returns:
            Response with created meeting
        """
        try:
            # Validate required fields
            required = ["conference_id", "date", "url"]
            is_valid, error_msg = self.validate_input(kwargs, required)
            if not is_valid:
                return WebResponseDTO.error_response(error_msg)

            # Create meeting entity
            meeting = Meeting(
                id=0,  # Will be assigned by repository
                conference_id=kwargs["conference_id"],
                date=kwargs["date"],
                url=kwargs["url"],
            )

            # Save to repository
            created_meeting = self.meeting_repo.create(meeting)

            return WebResponseDTO.success_response(
                created_meeting, "会議を登録しました"
            )

        except Exception as e:
            self.logger.error(f"Error creating meeting: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"会議の登録に失敗しました: {str(e)}")

    def read(self, **kwargs: Any) -> Meeting | None:
        """Read a single meeting.

        Args:
            **kwargs: Must include meeting_id

        Returns:
            Meeting entity or None
        """
        meeting_id = kwargs.get("meeting_id")
        if not meeting_id:
            raise ValueError("meeting_id is required")

        return self.meeting_repo.get_by_id(meeting_id)

    def update(self, **kwargs: Any) -> WebResponseDTO[Meeting]:
        """Update a meeting.

        Args:
            **kwargs: Meeting data including meeting_id

        Returns:
            Response with updated meeting
        """
        try:
            meeting_id = kwargs.get("meeting_id")
            if not meeting_id:
                return WebResponseDTO.error_response("meeting_id is required")

            # Get existing meeting
            meeting = self.meeting_repo.get_by_id(meeting_id)
            if not meeting:
                return WebResponseDTO.error_response(
                    f"会議ID {meeting_id} が見つかりません"
                )

            # Update fields
            if "conference_id" in kwargs:
                meeting.conference_id = kwargs["conference_id"]
            if "date" in kwargs:
                meeting.date = kwargs["date"]
            if "url" in kwargs:
                meeting.url = kwargs["url"]

            # Save to repository
            updated_meeting = self.meeting_repo.update(meeting)

            return WebResponseDTO.success_response(
                updated_meeting, "会議を更新しました"
            )

        except Exception as e:
            self.logger.error(f"Error updating meeting: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"会議の更新に失敗しました: {str(e)}")

    def delete(self, **kwargs: Any) -> WebResponseDTO[bool]:
        """Delete a meeting.

        Args:
            **kwargs: Must include meeting_id

        Returns:
            Response with success status
        """
        try:
            meeting_id = kwargs.get("meeting_id")
            if not meeting_id:
                return WebResponseDTO.error_response("meeting_id is required")

            success = self.meeting_repo.delete(meeting_id)

            if success:
                return WebResponseDTO.success_response(True, "会議を削除しました")
            else:
                return WebResponseDTO.error_response("会議の削除に失敗しました")

        except Exception as e:
            self.logger.error(f"Error deleting meeting: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"会議の削除に失敗しました: {str(e)}")

    def list(self, **kwargs: Any) -> list[Meeting]:
        """List meetings with optional filters.

        Args:
            **kwargs: Can include governing_body_id, conference_id

        Returns:
            List of meetings
        """
        governing_body_id = kwargs.get("governing_body_id")
        conference_id = kwargs.get("conference_id")

        meetings = self.load_meetings_with_filters(governing_body_id, conference_id)

        # Convert back to Meeting entities for consistency
        return [
            Meeting(
                id=m["id"],
                conference_id=m["conference_id"],
                date=m["date"],
                url=m["url"],
                gcs_pdf_uri=m.get("gcs_pdf_uri"),
                gcs_text_uri=m.get("gcs_text_uri"),
            )
            for m in meetings
        ]

    def to_dataframe(self, meetings: builtins.list[dict[str, Any]]) -> pd.DataFrame:
        """Convert meetings to DataFrame for display.

        Args:
            meetings: List of meeting dictionaries

        Returns:
            DataFrame for display
        """
        if not meetings:
            return pd.DataFrame(
                {
                    "ID": [],
                    "開催日": [],
                    "開催主体・会議体": [],
                    "URL": [],
                    "GCS": [],
                    "発言数": [],
                    "発言者数": [],
                }
            )

        df = pd.DataFrame(meetings)

        # Format date
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False)
        df["開催日"] = df["date"].dt.strftime("%Y年%m月%d日")

        # Format governing body and conference
        df["開催主体・会議体"] = df.apply(
            lambda row: f"{row['governing_body_name']} - {row['conference_name']}",
            axis=1,
        )

        # Check GCS status
        df["GCS"] = df.apply(
            lambda row: "✓"
            if row.get("gcs_pdf_uri") or row.get("gcs_text_uri")
            else "",
            axis=1,
        )

        # Format conversation and speaker counts
        df["発言数"] = df["conversation_count"].fillna(0).astype(int)
        df["発言者数"] = df["speaker_count"].fillna(0).astype(int)

        # Select columns for display
        return df[
            ["id", "開催日", "開催主体・会議体", "url", "GCS", "発言数", "発言者数"]
        ].rename(columns={"id": "ID", "url": "URL"})

    def generate_seed_file(self) -> WebResponseDTO[str]:
        """Generate seed file for meetings.

        Returns:
            Response with seed file content
        """
        try:
            generator = SeedGenerator()
            content = generator.generate_meetings_seed()

            return WebResponseDTO.success_response(
                content, "SEEDファイルを生成しました"
            )

        except Exception as e:
            self.logger.error(f"Error generating seed file: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"SEEDファイル生成に失敗しました: {str(e)}"
            )

    def set_editing_mode(self, meeting_id: int) -> None:
        """Set form to editing mode for a specific meeting.

        Args:
            meeting_id: ID of the meeting to edit
        """
        self.form_state.set_editing(meeting_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, meeting_id: int | None = None) -> bool:
        """Check if in editing mode.

        Args:
            meeting_id: Optional specific meeting ID to check

        Returns:
            True if in editing mode
        """
        if meeting_id:
            return (
                self.form_state.is_editing and self.form_state.current_id == meeting_id
            )
        return self.form_state.is_editing

    async def scrape_meeting(
        self, meeting_id: int, force_rescrape: bool = False
    ) -> WebResponseDTO[dict[str, Any]]:
        """Execute scraping for a meeting.

        Args:
            meeting_id: Meeting ID to scrape
            force_rescrape: Whether to force re-scraping

        Returns:
            Response with scraping result
        """
        try:
            # Initialize use case
            scrape_usecase = ExecuteScrapeMeetingUseCase(
                meeting_repository=self.meeting_repo,  # type: ignore[arg-type]
                enable_gcs=True,
            )

            # Execute scraping
            request = ExecuteScrapeMeetingDTO(
                meeting_id=meeting_id,
                force_rescrape=force_rescrape,
                upload_to_gcs=True,
            )
            result = await scrape_usecase.execute(request)

            return WebResponseDTO.success_response(
                {
                    "title": result.title,
                    "speakers_count": result.speakers_count,
                    "content_length": result.content_length,
                    "gcs_text_uri": result.gcs_text_uri,
                    "processing_time": result.processing_time_seconds,
                },
                f"会議 {meeting_id} のスクレイピングが完了しました",
            )

        except Exception as e:
            self.logger.error(
                f"Error scraping meeting {meeting_id}: {e}", exc_info=True
            )
            return WebResponseDTO.error_response(
                f"スクレイピングに失敗しました: {str(e)}"
            )

    async def extract_minutes(
        self, meeting_id: int, force_reprocess: bool = False
    ) -> WebResponseDTO[dict[str, Any]]:
        """Execute minutes processing (conversation extraction) for a meeting.

        Args:
            meeting_id: Meeting ID to process
            force_reprocess: Whether to force re-processing

        Returns:
            Response with processing result
        """
        # Import exceptions at method level for proper scope
        from src.application.exceptions import AuthenticationFailedException
        from src.infrastructure.exceptions import AuthenticationError

        try:
            # Get services from DI container
            import os

            from src.infrastructure.external.llm_service import GeminiLLMService

            # Initialize services
            bucket_name = os.getenv("GCS_BUCKET_NAME", "sagebase-bucket")

            # Initialize GCS Storage Service with proper error handling
            try:
                storage_service: IStorageService = GCSStorageService(
                    bucket_name=bucket_name
                )
            except AuthenticationError as e:
                # Convert Infrastructure exception to Application exception
                raise AuthenticationFailedException(
                    service=e.details.get("service", "Storage"),
                    reason=e.details.get("reason", str(e)),
                    solution=e.details.get("solution"),
                ) from e

            llm_service = GeminiLLMService()  # Use concrete implementation
            minutes_processing_service: IMinutesProcessingService = (
                MinutesProcessAgentService(llm_service=llm_service)
            )
            speaker_domain_service = SpeakerDomainService()

            # Initialize role name mapping services
            from src.infrastructure.external.minutes_divider.baml_minutes_divider import (  # noqa: E501
                BAMLMinutesDivider,
            )
            from src.infrastructure.external.role_name_mapping.baml_role_name_mapping_service import (  # noqa: E501
                BAMLRoleNameMappingService,
            )

            role_name_mapping_service = BAMLRoleNameMappingService()
            minutes_divider_service = BAMLMinutesDivider()

            # Initialize Unit of Work
            from src.infrastructure.config.async_database import get_async_session
            from src.infrastructure.persistence.sqlalchemy_session_adapter import (
                SQLAlchemySessionAdapter,
            )

            async with get_async_session() as session:
                # Wrap AsyncSession with adapter to satisfy ISessionAdapter interface
                session_adapter = SQLAlchemySessionAdapter(session)
                uow: IUnitOfWork = UnitOfWorkImpl(session=session_adapter)

                # Initialize update statement usecase
                from src.infrastructure.persistence.extraction_log_repository_impl import (  # noqa: E501
                    ExtractionLogRepositoryImpl,
                )

                conversation_repo = ConversationRepositoryImpl(session=session_adapter)
                extraction_log_repo = ExtractionLogRepositoryImpl(
                    session=session_adapter
                )
                update_statement_usecase = UpdateStatementFromExtractionUseCase(
                    conversation_repo=conversation_repo,
                    extraction_log_repo=extraction_log_repo,
                    session_adapter=session_adapter,
                )

                # Initialize use case
                minutes_usecase = ExecuteMinutesProcessingUseCase(
                    speaker_domain_service=speaker_domain_service,
                    minutes_processing_service=minutes_processing_service,
                    storage_service=storage_service,
                    unit_of_work=uow,
                    update_statement_usecase=update_statement_usecase,
                    role_name_mapping_service=role_name_mapping_service,
                    minutes_divider_service=minutes_divider_service,
                )

                # Execute processing
                request = ExecuteMinutesProcessingDTO(
                    meeting_id=meeting_id, force_reprocess=force_reprocess
                )
                result = await minutes_usecase.execute(request)

                return WebResponseDTO.success_response(
                    {
                        "minutes_id": result.minutes_id,
                        "total_conversations": result.total_conversations,
                        "unique_speakers": result.unique_speakers,
                        "processing_time": result.processing_time_seconds,
                        "role_name_mappings": result.role_name_mappings,
                    },
                    f"会議 {meeting_id} の発言抽出が完了しました",
                )

        except AuthenticationFailedException as e:
            # Application層の認証エラーをキャッチ
            self.logger.error(
                f"Authentication failed for meeting {meeting_id}: {e}",
                exc_info=True,
            )
            return WebResponseDTO.error_response(str(e))

        except Exception as e:
            # その他のエラー
            self.logger.error(
                f"Error extracting minutes for meeting {meeting_id}: {e}",
                exc_info=True,
            )
            return WebResponseDTO.error_response(f"発言抽出に失敗しました: {str(e)}")

    async def extract_speakers(
        self, meeting_id: int, force_reprocess: bool = False
    ) -> WebResponseDTO[dict[str, Any]]:
        """Execute speaker extraction for a meeting.

        Args:
            meeting_id: Meeting ID to process
            force_reprocess: Whether to force re-processing

        Returns:
            Response with extraction result
        """
        try:
            # Initialize shared repository adapter for transaction
            adapter = RepositoryAdapter(MinutesRepositoryImpl)

            # Execute within transaction to ensure all changes are committed
            async with adapter.transaction():
                # Create repositories sharing the same session
                minutes_repo = RepositoryAdapter(MinutesRepositoryImpl)
                minutes_repo._shared_session = adapter._shared_session  # type: ignore[attr-defined]

                conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)
                conversation_repo._shared_session = adapter._shared_session  # type: ignore[attr-defined]

                speaker_repo = RepositoryAdapter(SpeakerRepositoryImpl)
                speaker_repo._shared_session = adapter._shared_session  # type: ignore[attr-defined]

                speaker_domain_service = SpeakerDomainService()

                # Initialize use case
                speaker_usecase = ExecuteSpeakerExtractionUseCase(
                    minutes_repository=minutes_repo,  # type: ignore[arg-type]
                    conversation_repository=conversation_repo,  # type: ignore[arg-type]
                    speaker_repository=speaker_repo,  # type: ignore[arg-type]
                    speaker_domain_service=speaker_domain_service,
                )

                # Execute extraction
                request = ExecuteSpeakerExtractionDTO(
                    meeting_id=meeting_id, force_reprocess=force_reprocess
                )
                result = await speaker_usecase.execute(request)

                return WebResponseDTO.success_response(
                    {
                        "total_conversations": result.total_conversations,
                        "unique_speakers": result.unique_speakers,
                        "new_speakers": result.new_speakers,
                        "existing_speakers": result.existing_speakers,
                        "processing_time": result.processing_time_seconds,
                    },
                    f"会議 {meeting_id} の発言者抽出が完了しました",
                )

        except Exception as e:
            self.logger.error(
                f"Error extracting speakers for meeting {meeting_id}: {e}",
                exc_info=True,
            )
            return WebResponseDTO.error_response(f"発言者抽出に失敗しました: {str(e)}")

    async def check_meeting_status(self, meeting_id: int) -> dict[str, bool]:
        """Check processing status for a meeting.

        Args:
            meeting_id: Meeting ID to check

        Returns:
            Dictionary with status flags:
                - is_scraped: Whether meeting has been scraped
                - has_conversations: Whether conversations have been extracted
                - has_speakers_linked: Whether speakers have been linked
        """
        try:
            # Get meeting
            meeting = await self.meeting_repo.get_by_id(meeting_id)
            if not meeting:
                return {
                    "is_scraped": False,
                    "has_conversations": False,
                    "has_speakers_linked": False,
                }

            # Check if scraped (has GCS URIs)
            is_scraped = bool(meeting.gcs_text_uri or meeting.gcs_pdf_uri)

            # Check if conversations exist
            minutes_repo = RepositoryAdapter(MinutesRepositoryImpl)
            minutes = await minutes_repo.get_by_meeting(meeting_id)
            has_conversations = False
            has_speakers_linked = False

            if minutes and minutes.id:
                conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)
                conversations = await conversation_repo.get_by_minutes(minutes.id)
                has_conversations = len(conversations) > 0

                # Check if any conversation has speaker_id linked
                if conversations:
                    has_speakers_linked = any(
                        conv.speaker_id is not None for conv in conversations
                    )

            return {
                "is_scraped": is_scraped,
                "has_conversations": has_conversations,
                "has_speakers_linked": has_speakers_linked,
            }

        except Exception as e:
            self.logger.error(
                f"Error checking status for meeting {meeting_id}: {e}", exc_info=True
            )
            return {
                "is_scraped": False,
                "has_conversations": False,
                "has_speakers_linked": False,
            }
