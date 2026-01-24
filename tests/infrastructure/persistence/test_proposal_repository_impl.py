"""Tests for ProposalRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal import Proposal
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalModel,
    ProposalRepositoryImpl,
)


class TestProposalRepositoryImpl:
    """Test cases for ProposalRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        # Mock async methods
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ProposalRepositoryImpl:
        """Create proposal repository."""
        return ProposalRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_proposal_dict(self) -> dict[str, Any]:
        """Sample proposal data as dict."""
        return {
            "id": 1,
            "title": "令和6年度予算案の承認について",
            "detail_url": "https://example.com/proposal/001",
            "status_url": "https://example.com/proposal/status/001",
            "votes_url": "https://example.com/proposal/votes/001",
            "meeting_id": 100,
            "conference_id": 10,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_proposal_entity(self) -> Proposal:
        """Sample proposal entity."""
        return Proposal(
            id=1,
            title="令和6年度予算案の承認について",
            detail_url="https://example.com/proposal/001",
            status_url="https://example.com/proposal/status/001",
            votes_url="https://example.com/proposal/votes/001",
            meeting_id=100,
            conference_id=10,
        )

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when proposal is found."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(1)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.title == "令和6年度予算案の承認について"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_id when proposal is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test create proposal."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Create entity
        entity = Proposal(
            title="令和6年度予算案の承認について",
        )

        # Execute
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.title == "令和6年度予算案の承認について"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update proposal."""
        # Setup mock result
        updated_dict = {
            "id": 1,
            "title": "令和6年度予算案の承認について（修正版）",
            "detail_url": None,
            "status_url": None,
            "votes_url": None,
            "meeting_id": None,
            "conference_id": 10,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = updated_dict
        mock_row._asdict = MagicMock(return_value=updated_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Create entity with ID
        entity = Proposal(
            id=1,
            title="令和6年度予算案の承認について（修正版）",
            conference_id=10,
        )

        # Execute
        result = await repository.update(entity)

        # Assert
        assert result.id == 1
        assert result.title == "令和6年度予算案の承認について（修正版）"
        assert result.conference_id == 10
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update proposal without ID raises error."""
        entity = Proposal(title="Test")

        with pytest.raises(ValueError) as exc_info:
            await repository.update(entity)

        assert "Entity must have an ID to update" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_success(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete proposal successfully."""
        # Mock count check (no related judges)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        # Mock delete result
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute.side_effect = [mock_count_result, mock_delete_result]

        # Execute
        result = await repository.delete(1)

        # Assert
        assert result is True
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_related_records(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete proposal with related judges fails."""
        # Mock count check (has related judges)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_count_result

        # Execute
        result = await repository.delete(1)

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(limit=10, offset=0)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: ProposalRepositoryImpl) -> None:
        """Test _to_entity conversion."""
        model = ProposalModel(
            id=1,
            title="Test title",
            detail_url="https://test.detail.url",
            status_url="https://test.status.url",
            votes_url="https://test.votes.url",
            meeting_id=42,
            conference_id=10,
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.title == "Test title"
        assert entity.detail_url == "https://test.detail.url"
        assert entity.status_url == "https://test.status.url"
        assert entity.votes_url == "https://test.votes.url"
        assert entity.meeting_id == 42
        assert entity.conference_id == 10

    def test_to_model(self, repository: ProposalRepositoryImpl) -> None:
        """Test _to_model conversion."""
        entity = Proposal(
            id=1,
            title="Test title",
            detail_url="https://test.detail.url",
            status_url="https://test.status.url",
            votes_url="https://test.votes.url",
            meeting_id=42,
            conference_id=10,
        )

        model = repository._to_model(entity)

        assert model.id == 1
        assert model.title == "Test title"
        assert model.detail_url == "https://test.detail.url"
        assert model.status_url == "https://test.status.url"
        assert model.votes_url == "https://test.votes.url"
        assert model.meeting_id == 42
        assert model.conference_id == 10

    def test_update_model(self, repository: ProposalRepositoryImpl) -> None:
        """Test _update_model."""
        model = ProposalModel(
            id=1,
            title="Old title",
            detail_url="https://old.detail.url",
            status_url="https://old.status.url",
            votes_url="https://old.votes.url",
            meeting_id=1,
            conference_id=1,
        )
        entity = Proposal(
            id=1,
            title="New title",
            detail_url="https://new.detail.url",
            status_url="https://new.status.url",
            votes_url="https://new.votes.url",
            meeting_id=2,
            conference_id=2,
        )

        repository._update_model(model, entity)

        assert model.title == "New title"
        assert model.detail_url == "https://new.detail.url"
        assert model.status_url == "https://new.status.url"
        assert model.votes_url == "https://new.votes.url"
        assert model.meeting_id == 2
        assert model.conference_id == 2

    @pytest.mark.asyncio
    async def test_get_by_meeting_id(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_meeting_id returns list of proposals."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_meeting_id(100)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].meeting_id == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference_id(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_conference_id returns list of proposals."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_conference_id(10)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_errors(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test database error handling in methods."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Test get_by_meeting_id
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_meeting_id(100)
        assert "Failed to get proposals by meeting ID" in str(exc_info.value)

        # Reset side effect
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Test get_by_conference_id
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_conference_id(10)
        assert "Failed to get proposals by conference ID" in str(exc_info.value)
