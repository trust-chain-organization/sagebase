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
            "content": "令和6年度予算案の承認について",
            "status": "審議中",
            "detail_url": "https://example.com/proposal/001",
            "status_url": "https://example.com/proposal/status/001",
            "submission_date": "2024-01-15",
            "submitter": "財務委員会",
            "proposal_number": "議案第1号",
            "meeting_id": 100,
            "summary": "令和6年度の一般会計予算を承認する議案",
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_proposal_entity(self) -> Proposal:
        """Sample proposal entity."""
        return Proposal(
            id=1,
            content="令和6年度予算案の承認について",
            status="審議中",
            url="https://example.com/proposal/001",
            submission_date="2024-01-15",
            submitter="財務委員会",
            proposal_number="議案第1号",
            meeting_id=100,
            summary="令和6年度の一般会計予算を承認する議案",
        )

    @pytest.mark.asyncio
    async def test_get_by_status(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_status returns list of proposals."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_status("審議中")

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].content == "令和6年度予算案の承認について"
        assert result[0].status == "審議中"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_status_database_error(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_status with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute and assert
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_status("審議中")

        assert "Failed to get proposals by status" in str(exc_info.value)

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
        assert result.content == "令和6年度予算案の承認について"
        assert result.status == "審議中"
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
            content="令和6年度予算案の承認について",
            status="審議中",
        )

        # Execute
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.content == "令和6年度予算案の承認について"
        assert result.status == "審議中"
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
            "content": "令和6年度予算案の承認について（修正版）",
            "status": "可決",
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
            content="令和6年度予算案の承認について（修正版）",
            status="可決",
        )

        # Execute
        result = await repository.update(entity)

        # Assert
        assert result.id == 1
        assert result.content == "令和6年度予算案の承認について（修正版）"
        assert result.status == "可決"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update proposal without ID raises error."""
        entity = Proposal(content="Test", status="審議中")

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
            content="Test content",
            status="審議中",
            detail_url="https://test.detail.url",
            status_url="https://test.status.url",
            submission_date="2024-01-15",
            submitter="テスト提出者",
            proposal_number="テスト番号",
            meeting_id=42,
            summary="テスト概要",
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.content == "Test content"
        assert entity.status == "審議中"
        assert entity.detail_url == "https://test.detail.url"
        assert entity.status_url == "https://test.status.url"
        assert entity.submission_date == "2024-01-15"
        assert entity.submitter == "テスト提出者"
        assert entity.proposal_number == "テスト番号"
        assert entity.meeting_id == 42
        assert entity.summary == "テスト概要"

    def test_to_model(self, repository: ProposalRepositoryImpl) -> None:
        """Test _to_model conversion."""
        entity = Proposal(
            id=1,
            content="Test content",
            status="審議中",
            detail_url="https://test.detail.url",
            status_url="https://test.status.url",
            submission_date="2024-01-15",
            submitter="テスト提出者",
            proposal_number="テスト番号",
            meeting_id=42,
            summary="テスト概要",
        )

        model = repository._to_model(entity)

        assert model.id == 1
        assert model.content == "Test content"
        assert model.status == "審議中"
        assert model.detail_url == "https://test.detail.url"
        assert model.status_url == "https://test.status.url"
        assert model.submission_date == "2024-01-15"
        assert model.submitter == "テスト提出者"
        assert model.proposal_number == "テスト番号"
        assert model.meeting_id == 42
        assert model.summary == "テスト概要"

    def test_update_model(self, repository: ProposalRepositoryImpl) -> None:
        """Test _update_model."""
        model = ProposalModel(
            id=1,
            content="Old content",
            status="審議中",
            detail_url="https://old.detail.url",
            status_url="https://old.status.url",
            submission_date="2023-01-01",
            submitter="旧提出者",
            proposal_number="旧番号",
            meeting_id=1,
            summary="旧概要",
        )
        entity = Proposal(
            id=1,
            content="New content",
            status="可決",
            detail_url="https://new.detail.url",
            status_url="https://new.status.url",
            submission_date="2024-01-01",
            submitter="新提出者",
            proposal_number="新番号",
            meeting_id=2,
            summary="新概要",
        )

        repository._update_model(model, entity)

        assert model.content == "New content"
        assert model.status == "可決"
        assert model.detail_url == "https://new.detail.url"
        assert model.status_url == "https://new.status.url"
        assert model.submission_date == "2024-01-01"
        assert model.submitter == "新提出者"
        assert model.proposal_number == "新番号"
        assert model.meeting_id == 2
        assert model.summary == "新概要"

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
        assert result[0].proposal_number == "議案第1号"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_number_found(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal_number when proposal is found."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_proposal_number("議案第1号")

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.proposal_number == "議案第1号"
        assert result.content == "令和6年度予算案の承認について"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_number_not_found(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_proposal_number when proposal is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_proposal_number("議案第999号")

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_submission_date_range(
        self,
        repository: ProposalRepositoryImpl,
        mock_session: MagicMock,
        sample_proposal_dict: dict[str, Any],
    ) -> None:
        """Test get_by_submission_date_range returns list of proposals."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_proposal_dict
        mock_row._asdict = MagicMock(return_value=sample_proposal_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_submission_date_range(
            "2024-01-01", "2024-12-31"
        )

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].submission_date == "2024-01-15"
        assert result[0].submitter == "財務委員会"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_method_database_errors(
        self, repository: ProposalRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test database error handling in new methods."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Test get_by_meeting_id
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_meeting_id(100)
        assert "Failed to get proposals by meeting ID" in str(exc_info.value)

        # Reset side effect
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Test get_by_proposal_number
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal_number("議案第1号")
        assert "Failed to get proposal by proposal number" in str(exc_info.value)

        # Reset side effect
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Test get_by_submission_date_range
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_submission_date_range("2024-01-01", "2024-12-31")
        assert "Failed to get proposals by submission date range" in str(exc_info.value)
