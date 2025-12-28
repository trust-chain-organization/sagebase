"""Tests for MinutesRepositoryImpl."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.minutes import Minutes
from src.infrastructure.persistence.minutes_repository_impl import (
    MinutesModel,
    MinutesRepositoryImpl,
)


class TestMinutesRepositoryImpl:
    """Test cases for MinutesRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> MinutesRepositoryImpl:
        """Create minutes repository."""
        return MinutesRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_minutes_model(self) -> MinutesModel:
        """Sample minutes model."""
        return MinutesModel(
            id=1,
            meeting_id=10,
            url="https://example.com/minutes.pdf",
            processed_at=None,
        )

    @pytest.fixture
    def sample_minutes_entity(self) -> Minutes:
        """Sample minutes entity."""
        return Minutes(
            id=1,
            meeting_id=10,
            url="https://example.com/minutes.pdf",
            processed_at=None,
        )

    @pytest.mark.asyncio
    async def test_get_by_meeting_found(
        self,
        repository: MinutesRepositoryImpl,
        mock_session: MagicMock,
        sample_minutes_model: MinutesModel,
    ) -> None:
        """Test get_by_meeting when minutes is found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_minutes_model)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_meeting(10)

        assert result is not None
        assert result.id == 1
        assert result.meeting_id == 10
        assert result.url == "https://example.com/minutes.pdf"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_meeting_not_found(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_meeting when minutes is not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_meeting(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unprocessed(
        self,
        repository: MinutesRepositoryImpl,
        mock_session: MagicMock,
        sample_minutes_model: MinutesModel,
    ) -> None:
        """Test get_unprocessed returns unprocessed minutes."""
        sample_minutes_model2 = MinutesModel(
            id=2,
            meeting_id=20,
            url="https://example.com/minutes2.pdf",
            processed_at=None,
        )

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(
                all=MagicMock(
                    return_value=[sample_minutes_model, sample_minutes_model2]
                )
            )
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_unprocessed()

        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2
        assert result[0].processed_at is None
        assert result[1].processed_at is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unprocessed_with_limit(
        self,
        repository: MinutesRepositoryImpl,
        mock_session: MagicMock,
        sample_minutes_model: MinutesModel,
    ) -> None:
        """Test get_unprocessed with limit."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[sample_minutes_model]))
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_unprocessed(limit=1)

        assert len(result) == 1
        assert result[0].id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unprocessed_empty(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_unprocessed returns empty list when all processed."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_unprocessed()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_processed_success(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test mark_processed successfully marks minutes as processed."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.mark_processed(1)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_processed_not_found(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test mark_processed returns False when minutes not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.mark_processed(999)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count returns total number of minutes."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_zero(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count returns 0 when no minutes."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_processed(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count_processed returns number of processed minutes."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=50)
        mock_session.execute.return_value = mock_result

        result = await repository.count_processed()

        assert result == 50
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_processed_zero(
        self, repository: MinutesRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count_processed returns 0 when no processed minutes."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count_processed()

        assert result == 0

    def test_to_entity(
        self, repository: MinutesRepositoryImpl, sample_minutes_model: MinutesModel
    ) -> None:
        """Test _to_entity converts model to entity correctly."""
        entity = repository._to_entity(sample_minutes_model)

        assert isinstance(entity, Minutes)
        assert entity.id == 1
        assert entity.meeting_id == 10
        assert entity.url == "https://example.com/minutes.pdf"
        assert entity.processed_at is None

    def test_to_entity_with_processed_at(
        self, repository: MinutesRepositoryImpl
    ) -> None:
        """Test _to_entity with processed_at set."""
        processed_time = datetime(2024, 1, 15, 10, 30)
        model = MinutesModel(
            id=1,
            meeting_id=10,
            url="https://example.com/minutes.pdf",
            processed_at=processed_time,
        )

        entity = repository._to_entity(model)

        assert entity.processed_at == processed_time

    def test_to_model(
        self, repository: MinutesRepositoryImpl, sample_minutes_entity: Minutes
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_minutes_entity)

        assert isinstance(model, MinutesModel)
        assert model.id == 1
        assert model.meeting_id == 10
        assert model.url == "https://example.com/minutes.pdf"
        assert model.processed_at is None

    def test_to_model_without_id(self, repository: MinutesRepositoryImpl) -> None:
        """Test _to_model without id."""
        entity = Minutes(
            meeting_id=10,
            url="https://example.com/minutes.pdf",
        )

        model = repository._to_model(entity)

        assert isinstance(model, MinutesModel)
        assert not hasattr(model, "id") or model.id is None
        assert model.meeting_id == 10

    def test_update_model(
        self,
        repository: MinutesRepositoryImpl,
        sample_minutes_entity: Minutes,
        sample_minutes_model: MinutesModel,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        sample_minutes_model.meeting_id = 5
        sample_minutes_model.url = "https://old.com/minutes.pdf"

        repository._update_model(sample_minutes_model, sample_minutes_entity)

        assert sample_minutes_model.meeting_id == 10
        assert sample_minutes_model.url == "https://example.com/minutes.pdf"

    def test_update_model_with_processed_at(
        self, repository: MinutesRepositoryImpl, sample_minutes_model: MinutesModel
    ) -> None:
        """Test _update_model with processed_at."""
        processed_time = datetime(2024, 1, 15, 10, 30)
        entity = Minutes(
            id=1,
            meeting_id=10,
            url="https://example.com/minutes.pdf",
            processed_at=processed_time,
        )

        repository._update_model(sample_minutes_model, entity)

        assert sample_minutes_model.processed_at == processed_time
