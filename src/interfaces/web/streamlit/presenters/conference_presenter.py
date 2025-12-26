"""Presenter for conference management."""

from dataclasses import dataclass

import pandas as pd

import streamlit as st
from src.application.usecases.manage_conferences_usecase import (
    ConferenceListInputDto,
    CreateConferenceInputDto,
    DeleteConferenceInputDto,
    ManageConferencesUseCase,
    UpdateConferenceInputDto,
)
from src.domain.entities import Conference
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


@dataclass
class ConferenceFormData:
    """Form data for conference."""

    name: str = ""
    governing_body_id: int | None = None
    type: str | None = None
    members_introduction_url: str | None = None


class ConferencePresenter:
    """Presenter for conference management."""

    def __init__(self, use_case: ManageConferencesUseCase):
        """Initialize the presenter."""
        self.use_case = use_case
        self.session = SessionManager()

    async def load_conferences(
        self,
        governing_body_id: int | None = None,
        with_members_url: bool | None = None,
    ) -> tuple[pd.DataFrame, int, int]:
        """Load conferences list."""
        input_dto = ConferenceListInputDto(
            governing_body_id=governing_body_id,
            with_members_url=with_members_url,
        )
        output_dto = await self.use_case.list_conferences(input_dto)

        # Convert to DataFrame
        if output_dto.conferences:
            df = self._conferences_to_dataframe(output_dto.conferences)
        else:
            df = pd.DataFrame()

        return df, output_dto.with_url_count, output_dto.without_url_count

    def _conferences_to_dataframe(self, conferences: list[Conference]) -> pd.DataFrame:
        """Convert conferences to DataFrame."""
        data = []
        for conf in conferences:
            data.append(
                {
                    "ID": conf.id,
                    "会議体名": conf.name,
                    "開催主体ID": conf.governing_body_id or "",
                    "種別": conf.type or "",
                    "議員紹介URL": conf.members_introduction_url or "",
                }
            )
        return pd.DataFrame(data)

    def get_form_data(self, prefix: str = "new") -> ConferenceFormData:
        """Get form data from session."""
        key = f"{prefix}_conference_form"
        if key not in st.session_state:
            st.session_state[key] = ConferenceFormData()
        return st.session_state[key]

    def update_form_data(
        self, form_data: ConferenceFormData, prefix: str = "new"
    ) -> None:
        """Update form data in session."""
        key = f"{prefix}_conference_form"
        st.session_state[key] = form_data

    def clear_form_data(self, prefix: str = "new") -> None:
        """Clear form data from session."""
        key = f"{prefix}_conference_form"
        if key in st.session_state:
            del st.session_state[key]

    async def create_conference(
        self, form_data: ConferenceFormData
    ) -> tuple[bool, str | None]:
        """Create new conference."""
        input_dto = CreateConferenceInputDto(
            name=form_data.name,
            governing_body_id=form_data.governing_body_id,
            type=form_data.type,
            members_introduction_url=form_data.members_introduction_url,
        )
        output_dto = await self.use_case.create_conference(input_dto)
        return output_dto.success, output_dto.error_message

    async def update_conference(
        self, conference_id: int, form_data: ConferenceFormData
    ) -> tuple[bool, str | None]:
        """Update conference."""
        input_dto = UpdateConferenceInputDto(
            id=conference_id,
            name=form_data.name,
            governing_body_id=form_data.governing_body_id,
            type=form_data.type,
            members_introduction_url=form_data.members_introduction_url,
        )
        output_dto = await self.use_case.update_conference(input_dto)
        return output_dto.success, output_dto.error_message

    async def delete_conference(self, conference_id: int) -> tuple[bool, str | None]:
        """Delete conference."""
        input_dto = DeleteConferenceInputDto(id=conference_id)
        output_dto = await self.use_case.delete_conference(input_dto)
        return output_dto.success, output_dto.error_message

    async def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file."""
        output_dto = await self.use_case.generate_seed_file()
        return output_dto.success, output_dto.file_path, output_dto.error_message

    def load_conference_for_edit(self, conference: Conference) -> ConferenceFormData:
        """Load conference data for editing."""
        return ConferenceFormData(
            name=conference.name,
            governing_body_id=conference.governing_body_id,
            type=conference.type,
            members_introduction_url=conference.members_introduction_url,
        )
