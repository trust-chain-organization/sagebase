"""Tests for ProposalJudgeRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_judge import ProposalJudge
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeModel,
    ProposalJudgeRepositoryImpl,
)


class TestProposalJudgeRepositoryImpl:
    """Test cases for ProposalJudgeRepositoryImpl."""

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
    def repository(self, mock_session: MagicMock) -> ProposalJudgeRepositoryImpl:
        """Create proposal judge repository."""
        return ProposalJudgeRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_judge_dict(self) -> dict[str, Any]:
        """Sample proposal judge data as dict."""
        return {
            "id": 1,
            "proposal_id": 10,
            "politician_id": 20,
            "politician_party_id": 5,
            "approve": "賛成",
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_judge_entity(self) -> ProposalJudge:
        """Sample proposal judge entity."""
        return ProposalJudge(
            id=1,
            proposal_id=10,
            politician_id=20,
            politician_party_id=5,
            approve="賛成",
        )

    @pytest.mark.asyncio
    async def test_get_by_proposal(
        self,
        repository: ProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal returns list of judges."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_proposal(10)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].proposal_id == 10
        assert result[0].politician_id == 20
        assert result[0].approve == "賛成"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_politician(
        self,
        repository: ProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_politician returns list of judges."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_politician(20)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].politician_id == 20
        assert result[0].proposal_id == 10
        assert result[0].approve == "賛成"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_and_politician_found(
        self,
        repository: ProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal_and_politician when judge is found."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_proposal_and_politician(10, 20)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.politician_id == 20
        assert result.approve == "賛成"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_and_politician_not_found(
        self, repository: ProposalJudgeRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_proposal_and_politician when judge is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_proposal_and_politician(999, 999)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create multiple judges."""
        # Setup mock results for each insert
        result_dicts = [
            {
                "id": 1,
                "proposal_id": 10,
                "politician_id": 20,
                "politician_party_id": 5,
                "approve": "賛成",
                "created_at": None,
                "updated_at": None,
            },
            {
                "id": 2,
                "proposal_id": 10,
                "politician_id": 21,
                "politician_party_id": 5,
                "approve": "反対",
                "created_at": None,
                "updated_at": None,
            },
        ]

        mock_results = []
        for result_dict in result_dicts:
            mock_row = MagicMock()
            mock_row._mapping = result_dict
            mock_row._asdict = MagicMock(return_value=result_dict)
            mock_result = MagicMock()
            mock_result.fetchone = MagicMock(return_value=mock_row)
            mock_results.append(mock_result)

        mock_session.execute.side_effect = mock_results

        # Create entities
        judges = [
            ProposalJudge(
                proposal_id=10,
                politician_id=20,
                politician_party_id=5,
                approve="賛成",
            ),
            ProposalJudge(
                proposal_id=10,
                politician_id=21,
                politician_party_id=5,
                approve="反対",
            ),
        ]

        # Execute
        result = await repository.bulk_create(judges)

        # Assert
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].approve == "賛成"
        assert result[1].id == 2
        assert result[1].approve == "反対"
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(
        self, repository: ProposalJudgeRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test bulk_create with empty list."""
        result = await repository.bulk_create([])

        assert result == []
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test create proposal judge."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Create entity
        entity = ProposalJudge(
            proposal_id=10,
            politician_id=20,
            politician_party_id=5,
            approve="賛成",
        )

        # Execute
        result = await repository.create(entity)

        # Assert
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.politician_id == 20
        assert result.approve == "賛成"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update proposal judge."""
        # Setup mock result
        updated_dict = {
            "id": 1,
            "proposal_id": 10,
            "politician_id": 20,
            "politician_party_id": 6,
            "approve": "反対",
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
        entity = ProposalJudge(
            id=1,
            proposal_id=10,
            politician_id=20,
            politician_party_id=6,
            approve="反対",
        )

        # Execute
        result = await repository.update(entity)

        # Assert
        assert result.id == 1
        assert result.approve == "反対"
        assert result.politician_party_id == 6
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_success(
        self, repository: ProposalJudgeRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete proposal judge successfully."""
        # Mock delete result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.delete(1)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, repository: ProposalJudgeRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete proposal judge not found."""
        # Mock delete result
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.delete(999)

        # Assert
        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling(
        self, repository: ProposalJudgeRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test database error handling in various methods."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Test get_by_proposal
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal(10)
        assert "Failed to get judges by proposal" in str(exc_info.value)

        # Test get_by_politician
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_politician(20)
        assert "Failed to get judges by politician" in str(exc_info.value)

        # Test get_by_proposal_and_politician
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal_and_politician(10, 20)
        assert "Failed to get judge by proposal and politician" in str(exc_info.value)

    def test_to_entity(self, repository: ProposalJudgeRepositoryImpl) -> None:
        """Test _to_entity conversion."""
        model = ProposalJudgeModel(
            id=1,
            proposal_id=10,
            politician_id=20,
            politician_party_id=5,
            approve="賛成",
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.proposal_id == 10
        assert entity.politician_id == 20
        assert entity.politician_party_id == 5
        assert entity.approve == "賛成"

    def test_to_model(self, repository: ProposalJudgeRepositoryImpl) -> None:
        """Test _to_model conversion."""
        entity = ProposalJudge(
            id=1,
            proposal_id=10,
            politician_id=20,
            politician_party_id=5,
            approve="賛成",
        )

        model = repository._to_model(entity)

        assert model.id == 1
        assert model.proposal_id == 10
        assert model.politician_id == 20
        assert model.politician_party_id == 5
        assert model.approve == "賛成"

    def test_update_model(self, repository: ProposalJudgeRepositoryImpl) -> None:
        """Test _update_model."""
        model = ProposalJudgeModel(
            id=1,
            proposal_id=10,
            politician_id=20,
            politician_party_id=5,
            approve="賛成",
        )
        entity = ProposalJudge(
            id=1,
            proposal_id=11,
            politician_id=21,
            politician_party_id=6,
            approve="反対",
        )

        repository._update_model(model, entity)

        assert model.proposal_id == 11
        assert model.politician_id == 21
        assert model.politician_party_id == 6
        assert model.approve == "反対"
