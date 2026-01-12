"""Presenter for politician management."""

import asyncio

from typing import Any
from uuid import UUID

import pandas as pd

from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
from src.application.usecases.manage_politicians_usecase import (
    CreatePoliticianInputDto,
    DeletePoliticianInputDto,
    ManagePoliticiansUseCase,
    MergePoliticiansInputDto,
    PoliticianListInputDto,
    UpdatePoliticianInputDto,
)
from src.common.logging import get_logger
from src.domain.entities import PoliticalParty, Politician
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_operation_log_repository_impl import (
    PoliticianOperationLogRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl,
)
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class PoliticianPresenter(BasePresenter[list[Politician]]):
    """Presenter for politician management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        # Initialize repositories and use case
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
        self.party_repo = RepositoryAdapter(PoliticalPartyRepositoryImpl)
        self.operation_log_repo = RepositoryAdapter(
            PoliticianOperationLogRepositoryImpl
        )
        self.speaker_repo = RepositoryAdapter(SpeakerRepositoryImpl)
        # Type: ignore - RepositoryAdapter duck-types as repository protocol
        self.use_case = ManagePoliticiansUseCase(
            politician_repository=self.politician_repo,  # type: ignore[arg-type]
            operation_log_repository=self.operation_log_repo,  # type: ignore[arg-type]
            speaker_repository=self.speaker_repo,  # type: ignore[arg-type]
        )
        self.session = SessionManager()
        self.logger = get_logger(__name__)
        self._container = container or Container()

    def get_current_user_id(self) -> UUID | None:
        """現在ログインしているユーザーのIDを取得する."""
        user_info = google_sign_in.get_user_info()
        if not user_info:
            return None

        try:
            auth_usecase = AuthenticateUserUseCase(
                user_repository=self._container.repositories.user_repository()
            )
            email = user_info.get("email", "")
            name = user_info.get("name")
            user = asyncio.run(auth_usecase.execute(email=email, name=name))
            return user.user_id
        except Exception:
            return None

    def load_data(self) -> list[Politician]:
        """Load all politicians."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[Politician]:
        """Load all politicians (async implementation)."""
        try:
            result = await self.use_case.list_politicians(PoliticianListInputDto())
            return result.politicians
        except Exception as e:
            self.logger.error(f"Failed to load politicians: {e}")
            return []

    def load_politicians_with_filters(
        self, party_id: int | None = None, search_name: str | None = None
    ) -> list[Politician]:
        """Load politicians with filters."""
        return self._run_async(
            self._load_politicians_with_filters_async(party_id, search_name)
        )

    async def _load_politicians_with_filters_async(
        self, party_id: int | None = None, search_name: str | None = None
    ) -> list[Politician]:
        """Load politicians with filters (async implementation)."""
        try:
            result = await self.use_case.list_politicians(
                PoliticianListInputDto(party_id=party_id, search_name=search_name)
            )
            return result.politicians
        except Exception as e:
            self.logger.error(f"Failed to load politicians with filters: {e}")
            return []

    def get_all_parties(self) -> list[PoliticalParty]:
        """Get all political parties."""
        return self._run_async(self._get_all_parties_async())

    async def _get_all_parties_async(self) -> list[PoliticalParty]:
        """Get all political parties (async implementation)."""
        try:
            return await self.party_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get parties: {e}")
            return []

    def create(
        self,
        name: str,
        prefecture: str,
        party_id: int | None,
        district: str,
        profile_url: str | None = None,
        user_id: UUID | None = None,
    ) -> tuple[bool, int | None, str | None]:
        """Create a new politician."""
        return self._run_async(
            self._create_async(
                name, prefecture, party_id, district, profile_url, user_id
            )
        )

    async def _create_async(
        self,
        name: str,
        prefecture: str,
        party_id: int | None,
        district: str,
        profile_url: str | None = None,
        user_id: UUID | None = None,
    ) -> tuple[bool, int | None, str | None]:
        """Create a new politician (async implementation)."""
        try:
            result = await self.use_case.create_politician(
                CreatePoliticianInputDto(
                    name=name,
                    prefecture=prefecture,
                    district=district,
                    party_id=party_id,
                    profile_url=profile_url,
                    user_id=user_id,
                )
            )
            if result.success and result.politician_id:
                return True, result.politician_id, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to create politician: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def update(
        self,
        id: int,
        name: str,
        prefecture: str,
        party_id: int | None,
        district: str,
        profile_url: str | None = None,
        user_id: UUID | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing politician."""
        return self._run_async(
            self._update_async(
                id, name, prefecture, party_id, district, profile_url, user_id
            )
        )

    async def _update_async(
        self,
        id: int,
        name: str,
        prefecture: str,
        party_id: int | None,
        district: str,
        profile_url: str | None = None,
        user_id: UUID | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing politician (async implementation)."""
        try:
            result = await self.use_case.update_politician(
                UpdatePoliticianInputDto(
                    id=id,
                    name=name,
                    prefecture=prefecture,
                    district=district,
                    party_id=party_id,
                    profile_url=profile_url,
                    user_id=user_id,
                )
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to update politician: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(
        self, id: int, user_id: UUID | None = None, force: bool = False
    ) -> tuple[bool, str | None, bool, int, list[str] | None]:
        """Delete a politician.

        Args:
            id: 政治家ID
            user_id: 操作ユーザーID
            force: 警告を無視して削除を実行（speakerとの紐づきを解除）

        Returns:
            (success, error_message, has_linked_speakers, linked_count, speaker_names)
        """
        return self._run_async(self._delete_async(id, user_id, force))

    async def _delete_async(
        self, id: int, user_id: UUID | None = None, force: bool = False
    ) -> tuple[bool, str | None, bool, int, list[str] | None]:
        """Delete a politician (async implementation)."""
        try:
            result = await self.use_case.delete_politician(
                DeletePoliticianInputDto(id=id, user_id=user_id, force=force)
            )
            return (
                result.success,
                result.error_message,
                result.has_linked_speakers,
                result.linked_speaker_count,
                result.linked_speaker_names,
            )
        except Exception as e:
            error_msg = f"Failed to delete politician: {e}"
            self.logger.error(error_msg)
            return False, error_msg, False, 0, None

    def merge(self, source_id: int, target_id: int) -> tuple[bool, str | None]:
        """Merge two politicians."""
        return self._run_async(self._merge_async(source_id, target_id))

    async def _merge_async(
        self, source_id: int, target_id: int
    ) -> tuple[bool, str | None]:
        """Merge two politicians (async implementation)."""
        try:
            result = await self.use_case.merge_politicians(
                MergePoliticiansInputDto(source_id=source_id, target_id=target_id)
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to merge politicians: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def to_dataframe(
        self, politicians: list[Politician], parties: list[PoliticalParty]
    ) -> pd.DataFrame | None:
        """Convert politicians to DataFrame."""
        if not politicians:
            return None

        party_map = {p.id: p.name for p in parties}

        df_data = []
        for politician in politicians:
            df_data.append(
                {
                    "ID": politician.id,
                    "名前": politician.name,
                    "都道府県": politician.prefecture or "",
                    "政党": party_map.get(politician.political_party_id, "無所属")
                    if politician.political_party_id
                    else "無所属",
                    "選挙区": politician.district or "",
                    "プロフィールURL": politician.profile_page_url or "",
                }
            )
        return pd.DataFrame(df_data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "list":
            return self.load_politicians_with_filters(
                kwargs.get("party_id"), kwargs.get("search_name")
            )
        elif action == "create":
            return self.create(
                kwargs.get("name", ""),
                kwargs.get("prefecture", ""),
                kwargs.get("party_id"),
                kwargs.get("district", ""),
                kwargs.get("profile_url"),
            )
        elif action == "update":
            return self.update(
                kwargs.get("id", 0),
                kwargs.get("name", ""),
                kwargs.get("prefecture", ""),
                kwargs.get("party_id"),
                kwargs.get("district", ""),
                kwargs.get("profile_url"),
            )
        elif action == "delete":
            return self.delete(kwargs.get("id", 0))
        elif action == "merge":
            return self.merge(kwargs.get("source_id", 0), kwargs.get("target_id", 0))
        else:
            raise ValueError(f"Unknown action: {action}")
