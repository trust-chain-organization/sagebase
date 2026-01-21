"""Tests for ProposalParliamentaryGroupJudgeRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (  # noqa: E501
    ProposalParliamentaryGroupJudgeModel,
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)


class TestProposalParliamentaryGroupJudgeRepositoryImpl:
    """Test cases for ProposalParliamentaryGroupJudgeRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self, mock_session: MagicMock
    ) -> ProposalParliamentaryGroupJudgeRepositoryImpl:
        """Create repository instance."""
        return ProposalParliamentaryGroupJudgeRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_judge_dict(self) -> dict[str, Any]:
        """Sample parliamentary group judge data as dict."""
        return {
            "id": 1,
            "proposal_id": 10,
            "parliamentary_group_id": 20,
            "judgment": "賛成",
            "member_count": 5,
            "note": "全会一致",
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_judge_entity(self) -> ProposalParliamentaryGroupJudge:
        """Sample parliamentary group judge entity."""
        return ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
            member_count=5,
            note="全会一致",
        )

    @pytest.mark.asyncio
    async def test_get_by_proposal(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal returns list of judges."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal(10)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].proposal_id == 10
        assert result[0].parliamentary_group_id == 20
        assert result[0].judgment == "賛成"
        assert result[0].member_count == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_empty(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal returns empty list when no judges found."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_parliamentary_group returns list of judges."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_parliamentary_group(20)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].parliamentary_group_id == 20
        assert result[0].proposal_id == 10
        assert result[0].judgment == "賛成"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_empty(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_parliamentary_group returns empty list when no judges found."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_parliamentary_group(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_and_group_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal_and_group when judge is found."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal_and_group(10, 20)

        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.parliamentary_group_id == 20
        assert result.judgment == "賛成"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_and_group_not_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal_and_group when judge is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal_and_group(999, 999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create multiple judges."""
        result_dicts = [
            {
                "id": 1,
                "proposal_id": 10,
                "parliamentary_group_id": 20,
                "judgment": "賛成",
                "member_count": 5,
                "note": None,
                "created_at": None,
                "updated_at": None,
            },
            {
                "id": 2,
                "proposal_id": 10,
                "parliamentary_group_id": 21,
                "judgment": "反対",
                "member_count": 3,
                "note": "一部反対",
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

        judges = [
            ProposalParliamentaryGroupJudge(
                proposal_id=10,
                parliamentary_group_id=20,
                judgment="賛成",
                member_count=5,
            ),
            ProposalParliamentaryGroupJudge(
                proposal_id=10,
                parliamentary_group_id=21,
                judgment="反対",
                member_count=3,
                note="一部反対",
            ),
        ]

        result = await repository.bulk_create(judges)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].judgment == "賛成"
        assert result[1].id == 2
        assert result[1].judgment == "反対"
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create with empty list."""
        result = await repository.bulk_create([])

        assert result == []
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test create parliamentary group judge."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        entity = ProposalParliamentaryGroupJudge(
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
            member_count=5,
            note="全会一致",
        )

        result = await repository.create(entity)

        assert result.id == 1
        assert result.proposal_id == 10
        assert result.parliamentary_group_id == 20
        assert result.judgment == "賛成"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update parliamentary group judge."""
        updated_dict = {
            "id": 1,
            "proposal_id": 10,
            "parliamentary_group_id": 20,
            "judgment": "反対",
            "member_count": 4,
            "note": "変更後",
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = updated_dict
        mock_row._asdict = MagicMock(return_value=updated_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        entity = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="反対",
            member_count=4,
            note="変更後",
        )

        result = await repository.update(entity)

        assert result.id == 1
        assert result.judgment == "反対"
        assert result.member_count == 4
        assert result.note == "変更後"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id_raises_error(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update without ID raises ValueError."""
        entity = ProposalParliamentaryGroupJudge(
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
        )

        with pytest.raises(ValueError, match="Entity must have an ID to update"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete parliamentary group judge successfully."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete(1)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete parliamentary group judge not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when judge is found."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.parliamentary_group_id == 20
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when judge is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_all returns list of judges."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        assert result[0].id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit and offset."""
        mock_row = MagicMock()
        mock_row._mapping = sample_judge_dict
        mock_row._asdict = MagicMock(return_value=sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling_get_by_proposal(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in get_by_proposal."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal(10)
        assert "Failed to get judges by proposal" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_handling_get_by_parliamentary_group(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in get_by_parliamentary_group."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_parliamentary_group(20)
        assert "Failed to get judges by parliamentary group" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_handling_get_by_proposal_and_group(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in get_by_proposal_and_group."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal_and_group(10, 20)
        assert "Failed to get judge by proposal and group" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_handling_bulk_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in bulk_create."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        judges = [
            ProposalParliamentaryGroupJudge(
                proposal_id=10,
                parliamentary_group_id=20,
                judgment="賛成",
            )
        ]

        with pytest.raises(DatabaseError) as exc_info:
            await repository.bulk_create(judges)
        assert "Failed to bulk create parliamentary group judges" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in create."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        entity = ProposalParliamentaryGroupJudge(
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
        )

        with pytest.raises(DatabaseError) as exc_info:
            await repository.create(entity)
        assert "Failed to create parliamentary group judge" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling_delete(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in delete."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.delete(1)
        assert "Failed to delete parliamentary group judge" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    def test_to_entity(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _to_entity conversion."""
        model = ProposalParliamentaryGroupJudgeModel(
            id=1,
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
            member_count=5,
            note="テスト",
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.proposal_id == 10
        assert entity.parliamentary_group_id == 20
        assert entity.judgment == "賛成"
        assert entity.member_count == 5
        assert entity.note == "テスト"

    def test_to_model(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _to_model conversion."""
        entity = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
            member_count=5,
            note="テスト",
        )

        model = repository._to_model(entity)

        assert model.id == 1
        assert model.proposal_id == 10
        assert model.parliamentary_group_id == 20
        assert model.judgment == "賛成"
        assert model.member_count == 5
        assert model.note == "テスト"

    def test_update_model(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _update_model."""
        model = ProposalParliamentaryGroupJudgeModel(
            id=1,
            proposal_id=10,
            parliamentary_group_id=20,
            judgment="賛成",
            member_count=5,
            note="元の備考",
        )
        entity = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=11,
            parliamentary_group_id=21,
            judgment="反対",
            member_count=3,
            note="新しい備考",
        )

        repository._update_model(model, entity)

        assert model.proposal_id == 11
        assert model.parliamentary_group_id == 21
        assert model.judgment == "反対"
        assert model.member_count == 3
        assert model.note == "新しい備考"

    def test_dict_to_entity(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _dict_to_entity conversion."""
        data = {
            "id": 1,
            "proposal_id": 10,
            "parliamentary_group_id": 20,
            "judgment": "賛成",
            "member_count": 5,
            "note": "テスト",
        }

        entity = repository._dict_to_entity(data)

        assert entity.id == 1
        assert entity.proposal_id == 10
        assert entity.parliamentary_group_id == 20
        assert entity.judgment == "賛成"
        assert entity.member_count == 5
        assert entity.note == "テスト"

    def test_dict_to_entity_minimal(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _dict_to_entity with minimal data."""
        data = {
            "proposal_id": 10,
            "parliamentary_group_id": 20,
            "judgment": "賛成",
        }

        entity = repository._dict_to_entity(data)

        assert entity.id is None
        assert entity.proposal_id == 10
        assert entity.parliamentary_group_id == 20
        assert entity.judgment == "賛成"
        assert entity.member_count is None
        assert entity.note is None
