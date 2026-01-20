"""Main page for conference management.

会議体管理のメインページとタブ構成を定義します。
"""

from typing import cast

import streamlit as st

from .tabs.edit_delete_tab import render_edit_delete_form
from .tabs.extracted_members_tab import render_extracted_members
from .tabs.list_tab import render_conferences_list
from .tabs.new_tab import render_new_conference_form
from .tabs.seed_generator_tab import render_seed_generator

from src.application.usecases.manage_conferences_usecase import (
    ManageConferencesUseCase,
)
from src.domain.repositories import ConferenceRepository, GoverningBodyRepository
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)


def render_conferences_page() -> None:
    """Render conferences management page.

    会議体管理のメインページをレンダリングします。
    5つのタブ（会議体一覧、新規登録、編集・削除、SEED生成、抽出結果確認）を提供します。
    """
    st.title("会議体管理")

    # Initialize repositories
    conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
    governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    extracted_member_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)

    # Initialize use case and presenter
    # Type: ignore - RepositoryAdapter duck-types as repository protocol
    use_case = ManageConferencesUseCase(
        conference_repo,  # type: ignore[arg-type]
        meeting_repo,  # type: ignore[arg-type]
    )
    presenter = ConferencePresenter(use_case)

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["会議体一覧", "新規登録", "編集・削除", "SEED生成", "抽出結果確認"]
    )

    with tab1:
        render_conferences_list(
            presenter, cast(GoverningBodyRepository, governing_body_repo)
        )

    with tab2:
        render_new_conference_form(
            presenter, cast(GoverningBodyRepository, governing_body_repo)
        )

    with tab3:
        render_edit_delete_form(
            presenter,
            cast(ConferenceRepository, conference_repo),
            cast(GoverningBodyRepository, governing_body_repo),
        )

    with tab4:
        render_seed_generator(presenter)

    with tab5:
        render_extracted_members(extracted_member_repo, conference_repo)
