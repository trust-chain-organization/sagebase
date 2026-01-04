"""Presenter for parliamentary group management."""

from datetime import date
from typing import Any

import pandas as pd

from src.application.usecases.manage_parliamentary_groups_usecase import (
    CreateParliamentaryGroupInputDto,
    DeleteParliamentaryGroupInputDto,
    ExtractMembersInputDto,
    ManageParliamentaryGroupsUseCase,
    ParliamentaryGroupListInputDto,
    UpdateParliamentaryGroupInputDto,
)
from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
    UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
)
from src.common.logging import get_logger
from src.domain.entities import Conference, ParliamentaryGroup
from src.infrastructure.di.container import Container
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ParliamentaryGroupPresenter(BasePresenter[list[ParliamentaryGroup]]):
    """Presenter for parliamentary group management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        # Initialize repositories and use case
        self.parliamentary_group_repo = RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl
        )
        self.conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
        self.membership_repo = RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl
        )
        self.extracted_member_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )
        self.llm_service = GeminiLLMService()

        # Initialize member extractor using Factory
        self.member_extractor = ParliamentaryGroupMemberExtractorFactory.create()

        # 抽出ログ記録用のUseCaseを作成
        self.extraction_log_repo = RepositoryAdapter(ExtractionLogRepositoryImpl)
        session_adapter = AsyncSessionAdapter(self.extracted_member_repo._session)

        self.update_usecase = (
            UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase(
                extracted_parliamentary_group_member_repo=self.extracted_member_repo,  # type: ignore[arg-type]
                extraction_log_repo=self.extraction_log_repo,  # type: ignore[arg-type]
                session_adapter=session_adapter,
            )
        )

        # Initialize use case with required dependencies
        # Type: ignore - RepositoryAdapter duck-types as repository protocol
        self.use_case = ManageParliamentaryGroupsUseCase(
            parliamentary_group_repository=self.parliamentary_group_repo,  # type: ignore[arg-type]
            member_extractor=self.member_extractor,  # Injected extractor
            extracted_member_repository=self.extracted_member_repo,  # type: ignore[arg-type]
            update_usecase=self.update_usecase,  # 抽出ログ記録用UseCase
        )
        self.session = SessionManager()
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(__name__)

    def _get_or_create_form_state(self) -> dict[str, Any]:
        """Get or create form state in session."""
        default_state = {
            "editing_mode": None,
            "editing_id": None,
            "conference_filter": "すべて",
            "created_parliamentary_groups": [],
        }
        return self.session.get_or_create(
            "parliamentary_group_form_state", default_state
        )

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("parliamentary_group_form_state", self.form_state)

    def load_data(self) -> list[ParliamentaryGroup]:
        """Load all parliamentary groups."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[ParliamentaryGroup]:
        """Load all parliamentary groups (async implementation)."""
        try:
            result = await self.use_case.list_parliamentary_groups(
                ParliamentaryGroupListInputDto()
            )
            return result.parliamentary_groups
        except Exception as e:
            self.logger.error(f"Failed to load parliamentary groups: {e}")
            return []

    def load_parliamentary_groups_with_filters(
        self, conference_id: int | None = None, active_only: bool = False
    ) -> list[ParliamentaryGroup]:
        """Load parliamentary groups with filters."""
        return self._run_async(
            self._load_parliamentary_groups_with_filters_async(
                conference_id, active_only
            )
        )

    async def _load_parliamentary_groups_with_filters_async(
        self, conference_id: int | None = None, active_only: bool = False
    ) -> list[ParliamentaryGroup]:
        """Load parliamentary groups with filters (async implementation)."""
        try:
            result = await self.use_case.list_parliamentary_groups(
                ParliamentaryGroupListInputDto(
                    conference_id=conference_id, active_only=active_only
                )
            )
            return result.parliamentary_groups
        except Exception as e:
            self.logger.error(f"Failed to load parliamentary groups with filters: {e}")
            return []

    def get_all_conferences(self) -> list[Conference]:
        """Get all conferences."""
        return self._run_async(self._get_all_conferences_async())

    async def _get_all_conferences_async(self) -> list[Conference]:
        """Get all conferences (async implementation)."""
        try:
            return await self.conference_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get conferences: {e}")
            return []

    def create(
        self,
        name: str,
        conference_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> tuple[bool, ParliamentaryGroup | None, str | None]:
        """Create a new parliamentary group."""
        return self._run_async(
            self._create_async(name, conference_id, url, description, is_active)
        )

    async def _create_async(
        self,
        name: str,
        conference_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> tuple[bool, ParliamentaryGroup | None, str | None]:
        """Create a new parliamentary group (async implementation)."""
        try:
            result = await self.use_case.create_parliamentary_group(
                CreateParliamentaryGroupInputDto(
                    name=name,
                    conference_id=conference_id,
                    url=url,
                    description=description,
                    is_active=is_active,
                )
            )
            if result.success:
                return True, result.parliamentary_group, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to create parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def update(
        self,
        id: int,
        name: str,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> tuple[bool, str | None]:
        """Update an existing parliamentary group."""
        return self._run_async(
            self._update_async(id, name, url, description, is_active)
        )

    async def _update_async(
        self,
        id: int,
        name: str,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> tuple[bool, str | None]:
        """Update an existing parliamentary group (async implementation)."""
        try:
            result = await self.use_case.update_parliamentary_group(
                UpdateParliamentaryGroupInputDto(
                    id=id,
                    name=name,
                    url=url,
                    description=description,
                    is_active=is_active,
                )
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to update parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """Delete a parliamentary group."""
        return self._run_async(self._delete_async(id))

    async def _delete_async(self, id: int) -> tuple[bool, str | None]:
        """Delete a parliamentary group (async implementation)."""
        try:
            result = await self.use_case.delete_parliamentary_group(
                DeleteParliamentaryGroupInputDto(id=id)
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to delete parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def extract_members(
        self,
        parliamentary_group_id: int,
        url: str,
        confidence_threshold: float = 0.7,
        start_date: date | None = None,
        dry_run: bool = True,
    ) -> tuple[bool, Any, str | None]:
        """Extract members from parliamentary group URL."""
        return self._run_async(
            self._extract_members_async(
                parliamentary_group_id, url, confidence_threshold, start_date, dry_run
            )
        )

    async def _extract_members_async(
        self,
        parliamentary_group_id: int,
        url: str,
        confidence_threshold: float = 0.7,
        start_date: date | None = None,
        dry_run: bool = True,
    ) -> tuple[bool, Any, str | None]:
        """Extract members from parliamentary group URL (async implementation)."""
        try:
            result = await self.use_case.extract_members(
                ExtractMembersInputDto(
                    parliamentary_group_id=parliamentary_group_id,
                    url=url,
                    confidence_threshold=confidence_threshold,
                    start_date=start_date,
                    dry_run=dry_run,
                )
            )
            if result.success:
                return True, result, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to extract members: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for parliamentary groups."""
        return self._run_async(self._generate_seed_file_async())

    async def _generate_seed_file_async(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for parliamentary groups (async implementation)."""
        try:
            result = await self.use_case.generate_seed_file()
            if result.success:
                return True, result.seed_content, result.file_path
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to generate seed file: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def to_dataframe(
        self,
        parliamentary_groups: list[ParliamentaryGroup],
        conferences: list[Conference],
    ) -> pd.DataFrame | None:
        """Convert parliamentary groups to DataFrame."""
        if not parliamentary_groups:
            return None

        df_data = []
        for group in parliamentary_groups:
            # Find conference name
            conf = next((c for c in conferences if c.id == group.conference_id), None)
            conf_name = f"{conf.name}" if conf else "不明"

            df_data.append(
                {
                    "ID": group.id,
                    "議員団名": group.name,
                    "会議体": conf_name,
                    "URL": group.url or "未設定",
                    "説明": group.description or "",
                    "状態": "活動中" if group.is_active else "非活動",
                    "作成日": group.created_at,
                }
            )
        return pd.DataFrame(df_data)

    def get_member_counts(
        self, parliamentary_groups: list[ParliamentaryGroup]
    ) -> pd.DataFrame | None:
        """Get member counts for parliamentary groups."""
        if not parliamentary_groups:
            return None

        member_counts = []
        for group in parliamentary_groups:
            # Get current members for this group
            if group.id:
                try:
                    current_members = self.membership_repo.get_current_members(group.id)
                    member_count = len(current_members)
                except Exception as e:
                    self.logger.error(
                        f"Failed to get member count for group {group.id}: {e}"
                    )
                    member_count = 0
            else:
                member_count = 0

            member_counts.append(
                {
                    "議員団名": group.name,
                    "現在のメンバー数": member_count,
                }
            )
        return pd.DataFrame(member_counts)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "list":
            return self.load_parliamentary_groups_with_filters(
                kwargs.get("conference_id"), kwargs.get("active_only", False)
            )
        elif action == "create":
            return self.create(
                kwargs.get("name", ""),
                kwargs.get("conference_id", 0),
                kwargs.get("url"),
                kwargs.get("description"),
                kwargs.get("is_active", True),
            )
        elif action == "update":
            return self.update(
                kwargs.get("id", 0),
                kwargs.get("name", ""),
                kwargs.get("url"),
                kwargs.get("description"),
                kwargs.get("is_active", True),
            )
        elif action == "delete":
            return self.delete(kwargs.get("id", 0))
        elif action == "extract_members":
            return self.extract_members(
                kwargs.get("parliamentary_group_id", 0),
                kwargs.get("url", ""),
                kwargs.get("confidence_threshold", 0.7),
                kwargs.get("start_date"),
                kwargs.get("dry_run", True),
            )
        elif action == "generate_seed":
            return self.generate_seed_file()
        else:
            raise ValueError(f"Unknown action: {action}")

    def add_created_group(
        self, group: ParliamentaryGroup, conference_name: str
    ) -> None:
        """Add a created group to the session state."""
        created_group = {
            "id": group.id,
            "name": group.name,
            "conference_id": group.conference_id,
            "conference_name": conference_name,
            "url": group.url or "",
            "description": group.description or "",
            "is_active": group.is_active,
            "created_at": group.created_at,
        }
        self.form_state["created_parliamentary_groups"].append(created_group)
        self._save_form_state()

    def remove_created_group(self, index: int) -> None:
        """Remove a created group from the session state."""
        if 0 <= index < len(self.form_state["created_parliamentary_groups"]):
            self.form_state["created_parliamentary_groups"].pop(index)
            self._save_form_state()

    def get_created_groups(self) -> list[dict[str, Any]]:
        """Get created groups from the session state."""
        return self.form_state.get("created_parliamentary_groups", [])

    def get_extracted_members(self, parliamentary_group_id: int) -> list[Any]:
        """Get extracted members for a parliamentary group from database."""
        try:
            # RepositoryAdapter handles async to sync conversion
            members = self.extracted_member_repo.get_by_parliamentary_group(
                parliamentary_group_id
            )
            return members
        except Exception as e:
            self.logger.error(f"Failed to get extracted members: {e}")
            return []

    def get_extraction_summary(self, parliamentary_group_id: int) -> dict[str, int]:
        """Get extraction summary for a parliamentary group."""
        try:
            # RepositoryAdapter handles async to sync conversion
            summary = self.extracted_member_repo.get_extraction_summary(
                parliamentary_group_id
            )
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get extraction summary: {e}")
            return {
                "total": 0,
                "pending": 0,
                "matched": 0,
                "no_match": 0,
                "needs_review": 0,
            }
