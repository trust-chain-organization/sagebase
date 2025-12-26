"""Tests for ConferenceRepositoryImpl."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.conference import Conference
from src.infrastructure.exceptions import (
    DatabaseError,
    RecordNotFoundError,
    UpdateError,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceModel,
    ConferenceRepositoryImpl,
)


class TestConferenceRepositoryImpl:
    """Test cases for ConferenceRepositoryImpl."""

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
    def repository(self, mock_session: MagicMock) -> ConferenceRepositoryImpl:
        """Create conference repository."""
        return ConferenceRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_conference_dict(self) -> dict[str, Any]:
        """Sample conference data as dict."""
        return {
            "id": 1,
            "name": "本会議",
            "type": "plenary",
            "governing_body_id": 10,
            "members_introduction_url": "https://example.com/members",
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_conference_entity(self) -> Conference:
        """Sample conference entity."""
        return Conference(
            id=1,
            name="本会議",
            type="plenary",
            governing_body_id=10,
            members_introduction_url="https://example.com/members",
        )

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_found(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_by_name_and_governing_body when conference is found."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_name_and_governing_body("本会議", 10)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.name == "本会議"
        assert result.type == "plenary"
        assert result.governing_body_id == 10
        assert result.members_introduction_url == "https://example.com/members"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_not_found(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_name_and_governing_body when conference is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_name_and_governing_body("本会議", 10)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_governing_body_database_error(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_name_and_governing_body with database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute and assert
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_name_and_governing_body("本会議", 10)

        assert "Failed to get conference by name and governing body" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_by_governing_body(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_by_governing_body returns list of conferences."""
        # Setup mock result with multiple conferences
        mock_row1 = MagicMock()
        mock_row1._mapping = sample_conference_dict
        mock_row1._asdict = MagicMock(return_value=sample_conference_dict)
        mock_row2_dict = {
            **sample_conference_dict,
            "id": 2,
            "name": "予算委員会",
        }
        mock_row2 = MagicMock()
        mock_row2._mapping = mock_row2_dict
        mock_row2._asdict = MagicMock(return_value=mock_row2_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_governing_body(10)

        # Assert
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "本会議"
        assert result[1].id == 2
        assert result[1].name == "予算委員会"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_governing_body_empty(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_governing_body returns empty list when no conferences."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_governing_body(10)

        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_members_url(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_with_members_url returns conferences with members URL."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_with_members_url()

        # Assert
        assert len(result) == 1
        assert result[0].members_introduction_url == "https://example.com/members"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_members_url_success(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_members_url successfully updates URL."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.update_members_url(
            1, "https://example.com/new-members"
        )

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_members_url_not_found(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_members_url raises error when conference not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Execute and assert
        with pytest.raises(RecordNotFoundError) as exc_info:
            await repository.update_members_url(1, "https://example.com/new-members")

        assert "Conference" in str(exc_info.value)
        assert "1" in str(exc_info.value)
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_members_url_database_error(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_members_url handles database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute and assert
        with pytest.raises(UpdateError) as exc_info:
            await repository.update_members_url(1, "https://example.com/new-members")

        assert "Failed to update members URL for conference ID 1" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_members_url_clear(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_members_url can clear URL by setting to None."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.update_members_url(1, None)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit and offset."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(limit=10, offset=5)

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        # Check that execute was called with limit and offset params
        call_args = mock_session.execute.call_args
        assert "LIMIT :limit OFFSET :offset" in call_args[0][0].text
        assert call_args[0][1]["limit"] == 10
        assert call_args[0][1]["offset"] == 5

    @pytest.mark.asyncio
    async def test_get_all_without_limit(
        self,
        repository: ConferenceRepositoryImpl,
        mock_session: MagicMock,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test get_all without limit."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row._mapping = sample_conference_dict
        mock_row._asdict = MagicMock(return_value=sample_conference_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all()

        # Assert
        assert len(result) == 1
        # Check that execute was called without limit/offset params
        call_args = mock_session.execute.call_args
        assert "LIMIT" not in call_args[0][0].text
        assert call_args[0][1] == {}

    @pytest.mark.asyncio
    async def test_get_all_database_error(
        self, repository: ConferenceRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_all handles database error."""
        # Setup mock to raise exception
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        # Execute and assert
        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_all()

        assert "Failed to get all conferences" in str(exc_info.value)

    def test_to_entity(self, repository: ConferenceRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        # Create model
        model = ConferenceModel(
            id=1,
            name="本会議",
            type="plenary",
            governing_body_id=10,
            members_introduction_url="https://example.com/members",
        )

        # Convert
        entity = repository._to_entity(model)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.id == 1
        assert entity.name == "本会議"
        assert entity.type == "plenary"
        assert entity.governing_body_id == 10
        assert entity.members_introduction_url == "https://example.com/members"

    def test_to_model(
        self, repository: ConferenceRepositoryImpl, sample_conference_entity: Conference
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        # Convert
        model = repository._to_model(sample_conference_entity)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(model, ConferenceModel)
        assert model.id == 1
        assert model.name == "本会議"
        assert model.type == "plenary"
        assert model.governing_body_id == 10
        assert model.members_introduction_url == "https://example.com/members"

    def test_update_model(
        self, repository: ConferenceRepositoryImpl, sample_conference_entity: Conference
    ) -> None:
        """Test _update_model updates model fields from entity."""
        # Create model with different values
        model = ConferenceModel(
            id=1,
            name="旧会議",
            type="old_type",
            governing_body_id=5,
            members_introduction_url=None,
        )

        # Update model
        repository._update_model(model, sample_conference_entity)  # type: ignore[reportPrivateUsage]

        # Assert
        assert model.name == "本会議"
        assert model.type == "plenary"
        assert model.governing_body_id == 10
        assert model.members_introduction_url == "https://example.com/members"

    def test_dict_to_entity(
        self,
        repository: ConferenceRepositoryImpl,
        sample_conference_dict: dict[str, Any],
    ) -> None:
        """Test _dict_to_entity converts dictionary to entity correctly."""
        # Convert
        entity = repository._dict_to_entity(sample_conference_dict)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.id == 1
        assert entity.name == "本会議"
        assert entity.type == "plenary"
        assert entity.governing_body_id == 10
        assert entity.members_introduction_url == "https://example.com/members"

    def test_dict_to_entity_with_missing_optional_fields(
        self, repository: ConferenceRepositoryImpl
    ) -> None:
        """Test _dict_to_entity handles missing optional fields."""
        # Dictionary with only required fields
        data: dict[str, Any] = {
            "name": "本会議",
            "governing_body_id": 10,
        }

        # Convert
        entity = repository._dict_to_entity(data)  # type: ignore[reportPrivateUsage]

        # Assert
        assert isinstance(entity, Conference)
        assert entity.id is None
        assert entity.name == "本会議"
        assert entity.type is None
        assert entity.governing_body_id == 10
        assert entity.members_introduction_url is None
