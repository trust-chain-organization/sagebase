"""Tests for ProposalSubmitterRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType
from src.infrastructure.persistence.proposal_submitter_repository_impl import (
    ProposalSubmitterRepositoryImpl,
)


class TestProposalSubmitterRepositoryImpl:
    """Test cases for ProposalSubmitterRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.add_all = MagicMock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ProposalSubmitterRepositoryImpl:
        """Create proposal submitter repository."""
        return ProposalSubmitterRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_submitter_dict(self) -> dict[str, Any]:
        """Sample proposal submitter data as dict."""
        return {
            "id": 1,
            "proposal_id": 10,
            "submitter_type": "politician",
            "politician_id": 100,
            "parliamentary_group_id": None,
            "raw_name": "山田太郎",
            "is_representative": True,
            "display_order": 0,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_submitter_entity(self) -> ProposalSubmitter:
        """Sample proposal submitter entity."""
        return ProposalSubmitter(
            id=1,
            proposal_id=10,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=100,
            raw_name="山田太郎",
            is_representative=True,
            display_order=0,
        )

    def _create_mock_row(self, data: dict[str, Any]) -> MagicMock:
        """Create a mock database row."""
        mock_row = MagicMock()
        mock_row._mapping = data
        mock_row._asdict = MagicMock(return_value=data)
        return mock_row

    @pytest.mark.asyncio
    async def test_get_by_proposal(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal returns list of submitters."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal(proposal_id=10)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].proposal_id == 10
        assert result[0].submitter_type == SubmitterType.POLITICIAN
        assert result[0].politician_id == 100
        assert result[0].raw_name == "山田太郎"
        assert result[0].is_representative is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_empty(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal returns empty list when no submitters found."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal(proposal_id=999)

        assert len(result) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_politician(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test get_by_politician returns list of submitters."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician(politician_id=100)

        assert len(result) == 1
        assert result[0].politician_id == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_parliamentary_group returns list of submitters."""
        group_submitter_dict = {
            "id": 2,
            "proposal_id": 20,
            "submitter_type": "parliamentary_group",
            "politician_id": None,
            "parliamentary_group_id": 50,
            "raw_name": "自民党議員団",
            "is_representative": False,
            "display_order": 0,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = self._create_mock_row(group_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_parliamentary_group(parliamentary_group_id=50)

        assert len(result) == 1
        assert result[0].parliamentary_group_id == 50
        assert result[0].submitter_type == SubmitterType.PARLIAMENTARY_GROUP
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test bulk_create creates multiple submitters."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        submitters = [
            ProposalSubmitter(
                proposal_id=10,
                submitter_type=SubmitterType.POLITICIAN,
                politician_id=100,
                raw_name="山田太郎",
                is_representative=True,
            ),
        ]

        result = await repository.bulk_create(submitters)

        assert len(result) == 1
        assert result[0].id == 1
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create with empty list returns empty list."""
        result = await repository.bulk_create([])

        assert len(result) == 0
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_by_proposal(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete_by_proposal deletes submitters and returns count."""
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_proposal(proposal_id=10)

        assert result == 3
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_proposal_none_deleted(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete_by_proposal returns 0 when no submitters found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete_by_proposal(proposal_id=999)

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_by_id(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id returns submitter when found."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(entity_id=1)

        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(entity_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test create creates a new submitter."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        submitter = ProposalSubmitter(
            proposal_id=10,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=100,
            raw_name="山田太郎",
            is_representative=True,
        )

        result = await repository.create(submitter)

        assert result.id == 1
        assert result.proposal_id == 10
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test update updates an existing submitter."""
        updated_dict = sample_submitter_dict.copy()
        updated_dict["raw_name"] = "山田次郎"

        mock_row = self._create_mock_row(updated_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        submitter = ProposalSubmitter(
            id=1,
            proposal_id=10,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=100,
            raw_name="山田次郎",
            is_representative=True,
        )

        result = await repository.update(submitter)

        assert result.raw_name == "山田次郎"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id_raises_error(
        self,
        repository: ProposalSubmitterRepositoryImpl,
    ) -> None:
        """Test update raises ValueError when entity has no ID."""
        submitter = ProposalSubmitter(
            proposal_id=10,
            submitter_type=SubmitterType.POLITICIAN,
        )

        with pytest.raises(ValueError, match="Entity must have an ID to update"):
            await repository.update(submitter)

    @pytest.mark.asyncio
    async def test_delete(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete deletes a submitter."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete(entity_id=1)

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete returns False when submitter not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(entity_id=999)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test get_all returns all submitters."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit_and_offset(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        mock_session: MagicMock,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit and offset."""
        mock_row = self._create_mock_row(sample_submitter_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    def test_dict_to_entity(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        sample_submitter_dict: dict[str, Any],
    ) -> None:
        """Test _dict_to_entity converts dict to entity correctly."""
        entity = repository._dict_to_entity(sample_submitter_dict)

        assert entity.id == 1
        assert entity.proposal_id == 10
        assert entity.submitter_type == SubmitterType.POLITICIAN
        assert entity.politician_id == 100
        assert entity.raw_name == "山田太郎"
        assert entity.is_representative is True
        assert entity.display_order == 0

    def test_to_entity(
        self,
        repository: ProposalSubmitterRepositoryImpl,
    ) -> None:
        """Test _to_entity converts model to entity."""
        from src.infrastructure.persistence.proposal_submitter_repository_impl import (
            ProposalSubmitterModel,
        )

        model = ProposalSubmitterModel(
            id=1,
            proposal_id=10,
            submitter_type="politician",
            politician_id=100,
            raw_name="山田太郎",
            is_representative=True,
            display_order=0,
        )

        entity = repository._to_entity(model)

        assert entity.id == 1
        assert entity.submitter_type == SubmitterType.POLITICIAN

    def test_to_model(
        self,
        repository: ProposalSubmitterRepositoryImpl,
        sample_submitter_entity: ProposalSubmitter,
    ) -> None:
        """Test _to_model converts entity to model."""
        model = repository._to_model(sample_submitter_entity)

        assert model.id == 1
        assert model.proposal_id == 10
        assert model.submitter_type == "politician"
        assert model.politician_id == 100
