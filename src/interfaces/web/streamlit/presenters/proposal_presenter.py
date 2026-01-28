"""Presenter for proposal management in Streamlit.

This module provides the presenter layer for proposal management,
handling UI state and coordinating with use cases.
"""

from __future__ import annotations

import asyncio

from typing import Any, cast
from uuid import UUID

import pandas as pd

from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeDTO,
)
from src.application.dtos.submitter_candidates_dto import SubmitterCandidatesDTO
from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
from src.application.usecases.extract_proposal_judges_usecase import (
    CreateProposalJudgesInputDTO,
    CreateProposalJudgesOutputDTO,
    ExtractProposalJudgesInputDTO,
    ExtractProposalJudgesOutputDTO,
    ExtractProposalJudgesUseCase,
    MatchProposalJudgesInputDTO,
    MatchProposalJudgesOutputDTO,
)
from src.application.usecases.manage_parliamentary_group_judges_usecase import (
    CreateJudgeOutputDTO,
    DeleteJudgeOutputDTO,
    ManageParliamentaryGroupJudgesUseCase,
    UpdateJudgeOutputDTO,
)
from src.application.usecases.manage_proposal_submitter_usecase import (
    ClearSubmitterOutputDTO,
    ManageProposalSubmitterUseCase,
    SetSubmitterOutputDTO,
    UpdateSubmittersOutputDTO,
)
from src.application.usecases.manage_proposals_usecase import (
    CreateProposalInputDto,
    CreateProposalOutputDto,
    DeleteProposalInputDto,
    DeleteProposalOutputDto,
    ManageProposalsUseCase,
    ProposalListInputDto,
    ProposalListOutputDto,
    UpdateProposalInputDto,
    UpdateProposalOutputDto,
)
from src.application.usecases.scrape_proposal_usecase import (
    ScrapeProposalInputDTO,
    ScrapeProposalOutputDTO,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_affiliation_repository_impl import (
    PoliticianAffiliationRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_operation_log_repository_impl import (
    ProposalOperationLogRepositoryImpl,
)
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (  # noqa: E501
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.proposal_submitter_repository_impl import (
    ProposalSubmitterRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.dto.base import FormStateDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ProposalPresenter(CRUDPresenter[list[Proposal]]):
    """Presenter for proposal management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.proposal_repository = RepositoryAdapter(ProposalRepositoryImpl)
        self.extracted_judge_repository = RepositoryAdapter(
            ExtractedProposalJudgeRepositoryImpl
        )
        self.judge_repository = RepositoryAdapter(ProposalJudgeRepositoryImpl)
        self.parliamentary_group_judge_repository = RepositoryAdapter(
            ProposalParliamentaryGroupJudgeRepositoryImpl
        )
        self.parliamentary_group_repository = RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl
        )
        self.politician_repository = RepositoryAdapter(PoliticianRepositoryImpl)
        self.meeting_repository = RepositoryAdapter(MeetingRepositoryImpl)
        self.conference_repository = RepositoryAdapter(ConferenceRepositoryImpl)
        self.operation_log_repository = RepositoryAdapter(
            ProposalOperationLogRepositoryImpl
        )
        self.submitter_repository = RepositoryAdapter(ProposalSubmitterRepositoryImpl)
        self.politician_affiliation_repository = RepositoryAdapter(
            PoliticianAffiliationRepositoryImpl
        )

        # Initialize use cases
        self.manage_usecase = ManageProposalsUseCase(
            repository=self.proposal_repository,  # type: ignore[arg-type]
            operation_log_repository=self.operation_log_repository,  # type: ignore[arg-type]
        )
        self.manage_parliamentary_group_judges_usecase = (
            ManageParliamentaryGroupJudgesUseCase(
                judge_repository=self.parliamentary_group_judge_repository,  # type: ignore[arg-type]
                parliamentary_group_repository=self.parliamentary_group_repository,  # type: ignore[arg-type]
                politician_repository=self.politician_repository,  # type: ignore[arg-type]
            )
        )
        self.manage_submitter_usecase = ManageProposalSubmitterUseCase(
            proposal_repository=self.proposal_repository,  # type: ignore[arg-type]
            proposal_submitter_repository=self.submitter_repository,  # type: ignore[arg-type]
            meeting_repository=self.meeting_repository,  # type: ignore[arg-type]
            politician_affiliation_repository=self.politician_affiliation_repository,  # type: ignore[arg-type]
            parliamentary_group_repository=self.parliamentary_group_repository,  # type: ignore[arg-type]
            politician_repository=self.politician_repository,  # type: ignore[arg-type]
        )

        # Session management
        self.session = SessionManager(namespace="proposal")
        self.form_state = self._get_or_create_form_state()

    def _get_or_create_form_state(self) -> FormStateDTO:
        """Get or create form state from session."""
        state_dict = self.session.get("form_state", {})
        if not state_dict:
            state = FormStateDTO()
            self.session.set("form_state", state.__dict__)
            return state
        return FormStateDTO(**state_dict)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("form_state", self.form_state.__dict__)

    def get_current_user_id(self) -> UUID | None:
        """現在ログインしているユーザーのIDを取得する."""
        user_info = google_sign_in.get_user_info()
        if not user_info:
            return None

        try:
            auth_usecase = AuthenticateUserUseCase(
                user_repository=self.container.repositories.user_repository()
            )
            email = user_info.get("email", "")
            name = user_info.get("name")
            user = asyncio.run(auth_usecase.execute(email=email, name=name))
            return user.user_id
        except Exception:
            return None

    def load_data(self) -> list[Proposal]:
        """Load proposals data."""
        result = self.load_data_filtered("all")
        return result.proposals

    def load_data_filtered(
        self,
        filter_type: str = "all",
        meeting_id: int | None = None,
        conference_id: int | None = None,
    ) -> ProposalListOutputDto:
        """Load proposals with filter."""
        return self._run_async(
            self._load_data_filtered_async(filter_type, meeting_id, conference_id)
        )

    async def _load_data_filtered_async(
        self,
        filter_type: str = "all",
        meeting_id: int | None = None,
        conference_id: int | None = None,
    ) -> ProposalListOutputDto:
        """Load proposals with filter (async implementation)."""
        try:
            input_dto = ProposalListInputDto(
                filter_type=filter_type,
                meeting_id=meeting_id,
                conference_id=conference_id,
            )
            return await self.manage_usecase.list_proposals(input_dto)
        except Exception as e:
            self.logger.error(f"Error loading proposals: {e}", exc_info=True)
            raise

    def create(self, **kwargs: Any) -> CreateProposalOutputDto:
        """Create a new proposal."""
        return self._run_async(self._create_async(**kwargs))

    async def _create_async(self, **kwargs: Any) -> CreateProposalOutputDto:
        """Create a new proposal (async implementation)."""
        input_dto = CreateProposalInputDto(
            title=kwargs["title"],
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            votes_url=kwargs.get("votes_url"),
            meeting_id=kwargs.get("meeting_id"),
            conference_id=kwargs.get("conference_id"),
            user_id=kwargs.get("user_id"),
        )
        return await self.manage_usecase.create_proposal(input_dto)

    def update(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal."""
        return self._run_async(self._update_async(**kwargs))

    async def _update_async(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal (async implementation)."""
        input_dto = UpdateProposalInputDto(
            proposal_id=kwargs["proposal_id"],
            title=kwargs.get("title"),
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            votes_url=kwargs.get("votes_url"),
            meeting_id=kwargs.get("meeting_id"),
            conference_id=kwargs.get("conference_id"),
            user_id=kwargs.get("user_id"),
        )
        return await self.manage_usecase.update_proposal(input_dto)

    def delete(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal."""
        return self._run_async(self._delete_async(**kwargs))

    async def _delete_async(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal (async implementation)."""
        input_dto = DeleteProposalInputDto(
            proposal_id=kwargs["proposal_id"],
            user_id=kwargs.get("user_id"),
        )
        return await self.manage_usecase.delete_proposal(input_dto)

    def scrape_proposal(
        self, url: str, meeting_id: int | None = None
    ) -> ScrapeProposalOutputDTO:
        """Scrape proposal from URL."""
        return self._run_async(self._scrape_proposal_async(url, meeting_id))

    async def _scrape_proposal_async(
        self, url: str, meeting_id: int | None = None
    ) -> ScrapeProposalOutputDTO:
        """Scrape proposal from URL (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        scrape_usecase = self.container.use_cases.scrape_proposal_usecase()
        input_dto = ScrapeProposalInputDTO(url=url, meeting_id=meeting_id)
        return await scrape_usecase.scrape_and_save(input_dto)

    def extract_judges(
        self, url: str, proposal_id: int | None = None, force: bool = False
    ) -> ExtractProposalJudgesOutputDTO:
        """Extract judges from proposal status URL."""
        return self._run_async(self._extract_judges_async(url, proposal_id, force))

    async def _extract_judges_async(
        self, url: str, proposal_id: int | None = None, force: bool = False
    ) -> ExtractProposalJudgesOutputDTO:
        """Extract judges from proposal status URL (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = ExtractProposalJudgesInputDTO(
            url=url, proposal_id=proposal_id, force=force
        )
        return await extract_usecase.extract_judges(input_dto)

    def match_judges(
        self, proposal_id: int | None = None
    ) -> MatchProposalJudgesOutputDTO:
        """Match extracted judges with politicians."""
        return self._run_async(self._match_judges_async(proposal_id))

    async def _match_judges_async(
        self, proposal_id: int | None = None
    ) -> MatchProposalJudgesOutputDTO:
        """Match extracted judges with politicians (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = MatchProposalJudgesInputDTO(proposal_id=proposal_id)
        return await extract_usecase.match_judges(input_dto)

    def create_judges_from_matched(
        self, proposal_id: int | None = None
    ) -> CreateProposalJudgesOutputDTO:
        """Create proposal judges from matched extracted judges."""
        return self._run_async(self._create_judges_from_matched_async(proposal_id))

    async def _create_judges_from_matched_async(
        self, proposal_id: int | None = None
    ) -> CreateProposalJudgesOutputDTO:
        """Create proposal judges from matched extracted judges (async)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = CreateProposalJudgesInputDTO(proposal_id=proposal_id)
        return await extract_usecase.create_judges(input_dto)

    def load_extracted_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Load extracted judges."""
        return self._run_async(self._load_extracted_judges_async(proposal_id))

    async def _load_extracted_judges_async(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Load extracted judges (async implementation)."""
        if proposal_id:
            return await self.extracted_judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        else:
            return await self.extracted_judge_repository.get_all()  # type: ignore[attr-defined]

    def load_proposal_judges(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Load final proposal judges."""
        return self._run_async(self._load_proposal_judges_async(proposal_id))

    async def _load_proposal_judges_async(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Load final proposal judges (async implementation)."""
        if proposal_id:
            return await self.judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        else:
            return await self.judge_repository.get_all()  # type: ignore[attr-defined]

    def load_politicians(self) -> list[Politician]:
        """Load all politicians for selection."""
        return self._run_async(self._load_politicians_async())

    async def _load_politicians_async(self) -> list[Politician]:
        """Load all politicians (async implementation)."""
        return await self.politician_repository.get_all()  # type: ignore[attr-defined]

    def load_meetings(self) -> list[dict[str, Any]]:
        """Load all meetings for selection."""
        return self._run_async(self._load_meetings_async())

    async def _load_meetings_async(self) -> list[dict[str, Any]]:
        """Load all meetings (async implementation)."""
        meetings = await self.meeting_repository.get_all()  # type: ignore[attr-defined]
        return [
            {"id": m.id, "name": m.name or f"会議ID: {m.id}", "date": m.date}
            for m in meetings
        ]

    def load_conferences(self) -> list[dict[str, Any]]:
        """Load all conferences for selection."""
        return self._run_async(self._load_conferences_async())

    async def _load_conferences_async(self) -> list[dict[str, Any]]:
        """Load all conferences (async implementation)."""
        conferences = await self.conference_repository.get_all()  # type: ignore[attr-defined]
        return [{"id": c.id, "name": c.name} for c in conferences]

    def to_dataframe(self, proposals: list[Proposal]) -> pd.DataFrame:
        """Convert proposals to DataFrame for display."""
        if not proposals:
            return pd.DataFrame(
                {
                    "ID": [],
                    "タイトル": [],
                    "会議ID": [],
                    "会議体ID": [],
                }
            )

        data = []
        for proposal in proposals:
            data.append(
                {
                    "ID": proposal.id,
                    "タイトル": (
                        proposal.title[:50] + "..."
                        if len(proposal.title) > 50
                        else proposal.title
                    ),
                    "会議ID": proposal.meeting_id or "未設定",
                    "会議体ID": proposal.conference_id or "未設定",
                }
            )

        return pd.DataFrame(data)

    def extracted_judges_to_dataframe(
        self, judges: list[ExtractedProposalJudge]
    ) -> pd.DataFrame:
        """Convert extracted judges to DataFrame for display."""
        if not judges:
            return pd.DataFrame(
                {
                    "ID": [],
                    "政治家名": [],
                    "議員団名": [],
                    "賛否": [],
                    "信頼度": [],
                    "ステータス": [],
                }
            )

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "政治家名": judge.extracted_politician_name or "未設定",
                    "議員団名": judge.extracted_parliamentary_group_name or "未設定",
                    "賛否": judge.extracted_judgment or "未設定",
                    "信頼度": (
                        f"{judge.matching_confidence:.2f}"
                        if judge.matching_confidence
                        else "未実施"
                    ),
                    "ステータス": judge.matching_status or "pending",
                }
            )

        return pd.DataFrame(data)

    def proposal_judges_to_dataframe(self, judges: list[ProposalJudge]) -> pd.DataFrame:
        """Convert proposal judges to DataFrame for display."""
        if not judges:
            return pd.DataFrame({"ID": [], "政治家ID": [], "賛否": []})

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "政治家ID": judge.politician_id or "未設定",
                    "賛否": judge.approve or "未設定",
                }
            )

        return pd.DataFrame(data)

    def set_editing_mode(self, proposal_id: int) -> None:
        """Set form to editing mode."""
        self.form_state.set_editing(proposal_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, proposal_id: int) -> bool:
        """Check if editing."""
        return self.form_state.is_editing and self.form_state.current_id == proposal_id

    def read(self, **kwargs: Any) -> Proposal | None:
        """Read a single proposal by ID.

        Args:
            **kwargs: Must include proposal_id

        Returns:
            Proposal entity or None if not found
        """
        proposal_id = kwargs.get("proposal_id")
        if not proposal_id:
            raise ValueError("proposal_id is required")

        return self._run_async(
            self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        )

    def list(self, **kwargs: Any) -> list[Proposal]:
        """List all proposals.

        Args:
            **kwargs: Can include filter_type, meeting_id, conference_id

        Returns:
            List of proposals
        """
        filter_type = kwargs.get("filter_type", "all")
        meeting_id = kwargs.get("meeting_id")
        conference_id = kwargs.get("conference_id")
        result = self.load_data_filtered(filter_type, meeting_id, conference_id)
        return result.proposals

    # ========== Submitter Methods ==========

    def load_submitters(self, proposal_id: int) -> list[ProposalSubmitter]:
        """Load submitters for a proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalSubmitter entities
        """
        return self._run_async(self._load_submitters_async(proposal_id))

    async def _load_submitters_async(self, proposal_id: int) -> list[ProposalSubmitter]:
        """Load submitters for a proposal (async implementation)."""
        return await self.submitter_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]

    def update_submitters(
        self,
        proposal_id: int,
        politician_ids: list[int] | None = None,
        conference_ids: list[int] | None = None,
        parliamentary_group_id: int | None = None,
        other_submitter: tuple[SubmitterType, str] | None = None,
    ) -> UpdateSubmittersOutputDTO:
        """Update submitters for a proposal.

        This method deletes existing submitters and creates new ones.
        Uses ManageProposalSubmitterUseCase for business logic.

        Args:
            proposal_id: ID of the proposal
            politician_ids: List of politician IDs to set as submitters
            conference_ids: List of conference IDs to set as submitters
            parliamentary_group_id: Parliamentary group ID (single)
            other_submitter: Tuple of (SubmitterType, raw_name) for other types

        Returns:
            UpdateSubmittersOutputDTO with operation result
        """
        return self._run_async(
            self._update_submitters_async(
                proposal_id,
                politician_ids,
                conference_ids,
                parliamentary_group_id,
                other_submitter,
            )
        )

    async def _update_submitters_async(
        self,
        proposal_id: int,
        politician_ids: list[int] | None = None,
        conference_ids: list[int] | None = None,
        parliamentary_group_id: int | None = None,
        other_submitter: tuple[SubmitterType, str] | None = None,
    ) -> UpdateSubmittersOutputDTO:
        """Update submitters for a proposal (async implementation).

        Delegates to ManageProposalSubmitterUseCase.
        """
        return await self.manage_submitter_usecase.update_submitters(
            proposal_id=proposal_id,
            politician_ids=politician_ids,
            conference_ids=conference_ids,
            parliamentary_group_id=parliamentary_group_id,
            other_submitter=other_submitter,
        )

    # ========== Parliamentary Group Judge Methods (Issue #1007) ==========

    def load_parliamentary_group_judges(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudgeDTO]:
        """会派賛否一覧を取得する.

        Args:
            proposal_id: 議案ID

        Returns:
            会派賛否DTOのリスト
        """
        return cast(
            list[ProposalParliamentaryGroupJudgeDTO],
            self._run_async(self._load_parliamentary_group_judges_async(proposal_id)),
        )

    async def _load_parliamentary_group_judges_async(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudgeDTO]:
        """会派賛否一覧を取得する（非同期実装）."""
        result = await self.manage_parliamentary_group_judges_usecase.list_by_proposal(
            proposal_id
        )
        return cast(list[ProposalParliamentaryGroupJudgeDTO], result.judges)

    def create_parliamentary_group_judge(
        self,
        proposal_id: int,
        judgment: str,
        judge_type: str = "parliamentary_group",
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派/政治家賛否を新規登録する.

        Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。

        Args:
            proposal_id: 議案ID
            judgment: 賛否（賛成/反対/棄権/欠席）
            judge_type: 賛否種別（parliamentary_group/politician）
            parliamentary_group_ids: 会派IDのリスト（会派単位の場合）
            politician_ids: 政治家IDのリスト（政治家単位の場合）
            member_count: 人数（会派単位の場合）
            note: 備考

        Returns:
            作成結果DTO
        """
        return self._run_async(
            self._create_parliamentary_group_judge_async(
                proposal_id,
                judgment,
                judge_type,
                parliamentary_group_ids,
                politician_ids,
                member_count,
                note,
            )
        )

    async def _create_parliamentary_group_judge_async(
        self,
        proposal_id: int,
        judgment: str,
        judge_type: str = "parliamentary_group",
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
        member_count: int | None = None,
        note: str | None = None,
    ) -> CreateJudgeOutputDTO:
        """会派/政治家賛否を新規登録する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.create(
            proposal_id=proposal_id,
            judgment=judgment,
            judge_type=judge_type,
            parliamentary_group_ids=parliamentary_group_ids,
            politician_ids=politician_ids,
            member_count=member_count,
            note=note,
        )

    def update_parliamentary_group_judge(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する.

        Args:
            judge_id: 会派賛否ID
            judgment: 賛否（賛成/反対/棄権/欠席）
            member_count: 人数
            note: 備考
            parliamentary_group_ids: 紐付ける会派IDのリスト（Noneの場合は変更しない）
            politician_ids: 紐付ける政治家IDのリスト（Noneの場合は変更しない）

        Returns:
            更新結果DTO
        """
        return self._run_async(
            self._update_parliamentary_group_judge_async(
                judge_id,
                judgment,
                member_count,
                note,
                parliamentary_group_ids,
                politician_ids,
            )
        )

    async def _update_parliamentary_group_judge_async(
        self,
        judge_id: int,
        judgment: str | None = None,
        member_count: int | None = None,
        note: str | None = None,
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
    ) -> UpdateJudgeOutputDTO:
        """会派賛否を更新する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.update(
            judge_id=judge_id,
            judgment=judgment,
            member_count=member_count,
            note=note,
            parliamentary_group_ids=parliamentary_group_ids,
            politician_ids=politician_ids,
        )

    def delete_parliamentary_group_judge(self, judge_id: int) -> DeleteJudgeOutputDTO:
        """会派賛否を削除する.

        Args:
            judge_id: 会派賛否ID

        Returns:
            削除結果DTO
        """
        return self._run_async(self._delete_parliamentary_group_judge_async(judge_id))

    async def _delete_parliamentary_group_judge_async(
        self, judge_id: int
    ) -> DeleteJudgeOutputDTO:
        """会派賛否を削除する（非同期実装）."""
        return await self.manage_parliamentary_group_judges_usecase.delete(judge_id)

    def load_parliamentary_groups_for_proposal(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ParliamentaryGroup]:
        """議案に関連する会派一覧を取得する.

        議案 → 会議 → 会議体 → 会派の流れで取得します。

        Args:
            proposal_id: 議案ID

        Returns:
            会派エンティティのリスト
        """
        return cast(
            list[ParliamentaryGroup],
            self._run_async(
                self._load_parliamentary_groups_for_proposal_async(proposal_id)
            ),
        )

    async def _load_parliamentary_groups_for_proposal_async(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[ParliamentaryGroup]:
        """議案に関連する会派一覧を取得する（非同期実装）."""
        # 議案を取得
        proposal = await self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        if not proposal:
            return []

        # conference_idを取得（直接設定されている場合はそれを使用）
        conference_id: int | None = None
        if proposal.conference_id:
            conference_id = proposal.conference_id
        elif proposal.meeting_id:
            # 会議から会議体IDを取得
            meeting = await self.meeting_repository.get_by_id(proposal.meeting_id)  # type: ignore[attr-defined]
            if meeting:
                conference_id = meeting.conference_id

        if not conference_id:
            return []

        # 会議体IDから会派一覧を取得
        groups = await self.parliamentary_group_repository.get_by_conference_id(  # type: ignore[attr-defined]
            conference_id, active_only=True
        )
        return cast(list[ParliamentaryGroup], groups)

    def load_politicians_for_proposal(self, proposal_id: int) -> list[Politician]:
        """議案に関連する政治家一覧を取得する.

        議案 → 会議 → 会議体 → 政治家の流れで取得します。

        Args:
            proposal_id: 議案ID

        Returns:
            政治家エンティティのリスト
        """
        return cast(
            list[Politician],
            self._run_async(self._load_politicians_for_proposal_async(proposal_id)),
        )

    async def _load_politicians_for_proposal_async(  # type: ignore[return]
        self, proposal_id: int
    ) -> list[Politician]:
        """議案に紐付け可能な政治家一覧を取得する（非同期実装）.

        Args:
            proposal_id: 議案ID（将来的な絞り込み用、現在は未使用）

        Returns:
            全政治家のリスト
        """
        _ = proposal_id  # 将来的な絞り込み用に引数は残す
        politicians = await self.politician_repository.get_all()  # type: ignore[attr-defined]
        return cast(list[Politician], politicians)

    def parliamentary_group_judges_to_dataframe(
        self, judges: list[ProposalParliamentaryGroupJudgeDTO]
    ) -> pd.DataFrame:
        """会派/政治家賛否DTOリストをDataFrameに変換する.

        Many-to-Many構造対応: 複数の会派名・政治家名をカンマ区切りで表示。
        """
        if not judges:
            return pd.DataFrame(
                {
                    "ID": [],
                    "種別": [],
                    "会派/政治家": [],
                    "賛否": [],
                    "人数": [],
                    "備考": [],
                    "登録日時": [],
                }
            )

        data = []
        for judge in judges:
            if judge.judge_type == "parliamentary_group":
                judge_type_display = "会派"
                # 複数の会派名をカンマ区切りで結合
                if judge.parliamentary_group_names:
                    name_display = ", ".join(judge.parliamentary_group_names)
                else:
                    name_display = "（不明）"
            else:
                judge_type_display = "政治家"
                # 複数の政治家名をカンマ区切りで結合
                if judge.politician_names:
                    name_display = ", ".join(judge.politician_names)
                else:
                    name_display = "（不明）"

            created_at_str = "-"
            if judge.created_at:
                created_at_str = judge.created_at.strftime("%Y-%m-%d %H:%M")

            data.append(
                {
                    "ID": judge.id,
                    "種別": judge_type_display,
                    "会派/政治家": name_display,
                    "賛否": judge.judgment,
                    "人数": judge.member_count if judge.member_count else "-",
                    "備考": judge.note if judge.note else "-",
                    "登録日時": created_at_str,
                }
            )

        return pd.DataFrame(data)

    # ========== Submitter Management Methods (Issue #1023) ==========

    def set_submitter(
        self,
        proposal_id: int,
        submitter: str,
        submitter_type: SubmitterType,
        submitter_politician_id: int | None = None,
        submitter_parliamentary_group_id: int | None = None,
    ) -> SetSubmitterOutputDTO:
        """議案の提出者情報を設定する.

        Args:
            proposal_id: 議案ID
            submitter: 生の提出者文字列
            submitter_type: 提出者種別
            submitter_politician_id: 議員提出の場合のPolitician ID
            submitter_parliamentary_group_id: 会派提出の場合のParliamentaryGroup ID

        Returns:
            設定結果DTO
        """
        return self._run_async(
            self._set_submitter_async(
                proposal_id,
                submitter,
                submitter_type,
                submitter_politician_id,
                submitter_parliamentary_group_id,
            )
        )

    async def _set_submitter_async(
        self,
        proposal_id: int,
        submitter: str,
        submitter_type: SubmitterType,
        submitter_politician_id: int | None = None,
        submitter_parliamentary_group_id: int | None = None,
    ) -> SetSubmitterOutputDTO:
        """議案の提出者情報を設定する（非同期実装）."""
        return await self.manage_submitter_usecase.set_submitter(
            proposal_id=proposal_id,
            submitter=submitter,
            submitter_type=submitter_type,
            submitter_politician_id=submitter_politician_id,
            submitter_parliamentary_group_id=submitter_parliamentary_group_id,
        )

    def clear_submitter(self, proposal_id: int) -> ClearSubmitterOutputDTO:
        """議案の提出者情報をクリアする.

        Args:
            proposal_id: 議案ID

        Returns:
            クリア結果DTO
        """
        return self._run_async(self._clear_submitter_async(proposal_id))

    async def _clear_submitter_async(self, proposal_id: int) -> ClearSubmitterOutputDTO:
        """議案の提出者情報をクリアする（非同期実装）."""
        return await self.manage_submitter_usecase.clear_submitter(proposal_id)

    def get_submitter_candidates(self, conference_id: int) -> SubmitterCandidatesDTO:
        """会議体に所属する議員/会派の候補一覧を取得する.

        Args:
            conference_id: 会議体ID

        Returns:
            提出者候補一覧DTO
        """
        return self._run_async(self._get_submitter_candidates_async(conference_id))

    async def _get_submitter_candidates_async(
        self, conference_id: int
    ) -> SubmitterCandidatesDTO:
        """会議体に所属する議員/会派の候補一覧を取得する（非同期実装）."""
        return await self.manage_submitter_usecase.get_submitter_candidates(
            conference_id
        )

    def get_conference_id_for_proposal(self, proposal_id: int) -> int | None:
        """議案に関連する会議体IDを取得する.

        Args:
            proposal_id: 議案ID

        Returns:
            会議体ID（取得できない場合はNone）
        """
        return self._run_async(self._get_conference_id_for_proposal_async(proposal_id))

    async def _get_conference_id_for_proposal_async(
        self, proposal_id: int
    ) -> int | None:
        """議案に関連する会議体IDを取得する（非同期実装）."""
        proposal = await self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        if not proposal:
            return None

        if proposal.conference_id:
            return proposal.conference_id

        if proposal.meeting_id:
            meeting = await self.meeting_repository.get_by_id(proposal.meeting_id)  # type: ignore[attr-defined]
            if meeting:
                return meeting.conference_id

        return None
