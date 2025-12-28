"""Tests for PoliticianAffiliationRepositoryImpl."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.infrastructure.persistence.politician_affiliation_repository_impl import (
    PoliticianAffiliationModel,
    PoliticianAffiliationRepositoryImpl,
)


class TestPoliticianAffiliationRepositoryImpl:
    """Test cases for PoliticianAffiliationRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self, mock_session: MagicMock
    ) -> PoliticianAffiliationRepositoryImpl:
        """Create politician affiliation repository."""
        return PoliticianAffiliationRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_affiliation_entity(self) -> PoliticianAffiliation:
        """Sample politician affiliation entity."""
        return PoliticianAffiliation(
            id=1,
            politician_id=100,
            conference_id=10,
            start_date=date(2024, 1, 1),
            end_date=None,
            role="議員",
        )

    @pytest.mark.asyncio
    async def test_get_by_politician_and_conference_found(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_politician_and_conference when affiliation is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.politician_id = 100
        mock_row.conference_id = 10
        mock_row.role = "議員"
        mock_row.start_date = date(2024, 1, 1)
        mock_row.end_date = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician_and_conference(100, 10)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].politician_id == 100
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_politician_and_conference_not_found(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_politician_and_conference when not found."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician_and_conference(999, 10)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_conference returns affiliations."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.politician_id = 100
        mock_row.conference_id = 10
        mock_row.role = "議員"
        mock_row.start_date = date(2024, 1, 1)
        mock_row.end_date = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference(10)

        assert len(result) == 1
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_politician(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_politician returns affiliations."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.politician_id = 100
        mock_row.conference_id = 10
        mock_row.role = 5

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_politician(100)

        assert len(result) == 1
        assert result[0].politician_id == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_create_new(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
        sample_affiliation_entity: PoliticianAffiliation,
    ) -> None:
        """Test upsert creates new affiliation."""
        # Mock check for existing affiliation (returns None)
        mock_result1 = MagicMock()
        mock_result1.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result1

        # Mock the create method
        created_entity = PoliticianAffiliation(
            id=1,
            politician_id=100,
            conference_id=10,
            start_date=date(2024, 1, 1),
            end_date=None,
            role="議員",
        )
        repository.create = AsyncMock(return_value=created_entity)

        result = await repository.upsert(
            politician_id=100,
            conference_id=10,
            start_date=date(2024, 1, 1),
            end_date=None,
            role="議員",
        )

        assert result.id == 1
        assert result.politician_id == 100
        repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_affiliation_success(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test end_affiliation successfully ends affiliation."""
        # Mock update query
        mock_update_result = MagicMock()
        mock_session.execute.return_value = mock_update_result

        # Mock get_by_id
        updated_entity = PoliticianAffiliation(
            id=1,
            politician_id=100,
            conference_id=10,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            role="議員",
        )
        repository.get_by_id = AsyncMock(return_value=updated_entity)

        result = await repository.end_affiliation(1, date(2024, 12, 31))

        assert result is not None
        assert result.end_date == date(2024, 12, 31)
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
        repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_end_affiliation_not_found(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test end_affiliation returns None when not found."""
        # Mock update query
        mock_update_result = MagicMock()
        mock_session.execute.return_value = mock_update_result

        # Mock get_by_id (returns None)
        repository.get_by_id = AsyncMock(return_value=None)

        result = await repository.end_affiliation(999, date(2024, 12, 31))

        assert result is None
        mock_session.commit.assert_called_once()
        repository.get_by_id.assert_called_once_with(999)

    def test_to_entity(self, repository: PoliticianAffiliationRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = PoliticianAffiliationModel(
            id=1,
            politician_id=100,
            conference_id=10,
            role="議員",
            start_date=date(2024, 1, 1),
            end_date=None,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, PoliticianAffiliation)
        assert entity.id == 1
        assert entity.politician_id == 100

    def test_to_model(
        self,
        repository: PoliticianAffiliationRepositoryImpl,
        sample_affiliation_entity: PoliticianAffiliation,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_affiliation_entity)

        assert isinstance(model, PoliticianAffiliationModel)
        assert model.politician_id == 100
        assert model.conference_id == 10
