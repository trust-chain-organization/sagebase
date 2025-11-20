"""Tests for SpeakerRepositoryImpl."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.speaker import Speaker
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl


class MockColumn:
    """Mock SQLAlchemy column descriptor."""

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        """Mock equality comparison for SQLAlchemy filters."""
        return f"{self.name} == {other}"

    def ilike(self, pattern):
        """Mock ilike for pattern matching."""
        return f"{self.name} ILIKE {pattern}"


class MockSpeakerModel:
    """Mock speaker model for testing."""

    # Add __tablename__ to make it look like a SQLAlchemy model
    __tablename__ = "speakers"

    # Mock SQLAlchemy columns
    name = MockColumn("name")
    type = MockColumn("type")
    political_party_name = MockColumn("political_party_name")
    position = MockColumn("position")
    is_politician = MockColumn("is_politician")
    politician_id = MockColumn("politician_id")
    matched_by_user_id = MockColumn("matched_by_user_id")

    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        type: str | None = None,
        political_party_name: str | None = None,
        position: str | None = None,
        is_politician: bool = False,
        politician_id: int | None = None,
        matched_by_user_id: str | None = None,
    ):
        self.id = id
        self.name = name
        self.type = type
        self.political_party_name = political_party_name
        self.position = position
        self.is_politician = is_politician
        self.politician_id = politician_id
        self.matched_by_user_id = matched_by_user_id


class TestSpeakerRepositoryImpl:
    """Test cases for SpeakerRepositoryImpl."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = MagicMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create speaker repository."""
        # Create repository and inject MockSpeakerModel as the model class
        repo = SpeakerRepositoryImpl(mock_session)
        repo.model_class = MockSpeakerModel
        return repo

    @pytest.mark.asyncio
    async def test_get_by_name_party_position_found(self, repository, mock_session):
        """Test get_by_name_party_position when speaker is found."""
        # Setup - Create a mock row that looks like a database result
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 1,
            "name": "山田太郎",
            "type": "議員",
            "political_party_name": "自民党",
            "position": "議長",
            "is_politician": True,
        }
        # Set up attribute access
        for key, value in mock_row._mapping.items():
            setattr(mock_row, key, value)

        # Create a mock result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row

        # Create async mock for execute
        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_by_name_party_position(
            name="山田太郎",
            political_party_name="自民党",
            position="議長",
        )

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.name == "山田太郎"
        assert result.political_party_name == "自民党"
        assert result.position == "議長"
        assert result.is_politician is True

    @pytest.mark.asyncio
    async def test_get_by_name_party_position_not_found(self, repository, mock_session):
        """Test get_by_name_party_position when speaker is not found."""
        # Create a mock result with no data
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_by_name_party_position(name="存在しない人")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_party_position_partial_match(
        self, repository, mock_session
    ):
        """Test get_by_name_party_position with only name."""
        # Setup
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 1,
            "name": "山田太郎",
            "type": "議員",
            "political_party_name": None,
            "position": None,
            "is_politician": True,
        }
        for key, value in mock_row._mapping.items():
            setattr(mock_row, key, value)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_by_name_party_position(name="山田太郎")

        # Verify
        assert result is not None
        assert result.name == "山田太郎"
        assert result.political_party_name is None
        assert result.position is None

    @pytest.mark.asyncio
    async def test_get_politicians(self, repository, mock_session):
        """Test get_politicians method."""
        # Setup
        mock_rows = [
            MagicMock(),
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "id": 1,
            "name": "山田太郎",
            "type": "議員",
            "political_party_name": "自民党",
            "position": None,
            "is_politician": True,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_rows[1]._mapping = {
            "id": 2,
            "name": "鈴木花子",
            "type": "議員",
            "political_party_name": "民主党",
            "position": None,
            "is_politician": True,
        }
        for key, value in mock_rows[1]._mapping.items():
            setattr(mock_rows[1], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_politicians()

        # Verify
        assert len(result) == 2
        assert all(speaker.is_politician for speaker in result)
        assert result[0].name == "山田太郎"
        assert result[1].name == "鈴木花子"

    @pytest.mark.asyncio
    async def test_search_by_name(self, repository, mock_session):
        """Test search_by_name method."""
        # Setup
        mock_rows = [
            MagicMock(),
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "id": 1,
            "name": "山田太郎",
            "type": "議員",
            "political_party_name": None,
            "position": None,
            "is_politician": False,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_rows[1]._mapping = {
            "id": 2,
            "name": "山田花子",
            "type": "議員",
            "political_party_name": None,
            "position": None,
            "is_politician": False,
        }
        for key, value in mock_rows[1]._mapping.items():
            setattr(mock_rows[1], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.search_by_name("山田")

        # Verify
        assert len(result) == 2
        assert all("山田" in speaker.name for speaker in result)

    @pytest.mark.asyncio
    async def test_upsert_create_new(self, repository, mock_session):
        """Test upsert when creating new speaker."""
        # Setup
        new_speaker = Speaker(
            name="新規議員",
            type="議員",
            political_party_name="新党",
            is_politician=True,
        )

        # Mock get_by_name_party_position to return None
        with patch.object(repository, "get_by_name_party_position", return_value=None):
            # Mock create to return the new speaker with ID
            created_speaker = Speaker(
                id=10,
                name="新規議員",
                type="議員",
                political_party_name="新党",
                is_politician=True,
            )
            with patch.object(repository, "create", return_value=created_speaker):
                # Execute
                result = await repository.upsert(new_speaker)

                # Verify
                assert result.id == 10
                assert result.name == "新規議員"
                assert result.political_party_name == "新党"

    @pytest.mark.asyncio
    async def test_upsert_update_existing(self, repository, mock_session):
        """Test upsert when updating existing speaker."""
        # Setup
        speaker = Speaker(
            name="山田太郎",
            type="議員",
            political_party_name="自民党",
            position="新役職",  # New position
            is_politician=True,
        )

        # Mock get_by_name_party_position to return existing speaker
        existing_speaker = Speaker(
            id=1,
            name="山田太郎",
            type="議員",
            political_party_name="自民党",
            position="旧役職",
            is_politician=True,
        )

        with patch.object(
            repository, "get_by_name_party_position", return_value=existing_speaker
        ):
            # Mock update to return updated speaker
            updated_speaker = Speaker(
                id=1,
                name="山田太郎",
                type="議員",
                political_party_name="自民党",
                position="新役職",
                is_politician=True,
            )
            with patch.object(repository, "update", return_value=updated_speaker):
                # Execute
                result = await repository.upsert(speaker)

                # Verify
                assert result.id == 1
                assert result.name == "山田太郎"
                assert result.position == "新役職"

    @pytest.mark.asyncio
    async def test_to_entity_conversion(self, repository):
        """Test model to entity conversion."""
        # Setup
        model = MockSpeakerModel(
            id=1,
            name="山田太郎",
            type="議員",
            political_party_name="自民党",
            position="議長",
            is_politician=True,
        )

        # Execute
        entity = repository._to_entity(model)

        # Verify
        assert isinstance(entity, Speaker)
        assert entity.id == 1
        assert entity.name == "山田太郎"
        assert entity.type == "議員"
        assert entity.political_party_name == "自民党"
        assert entity.position == "議長"
        assert entity.is_politician is True

    @pytest.mark.asyncio
    async def test_to_model_conversion(self, repository):
        """Test entity to model conversion."""
        # Setup
        entity = Speaker(
            id=1,
            name="山田太郎",
            type="議員",
            political_party_name="自民党",
            position="議長",
            is_politician=True,
        )

        # Execute
        model = repository._to_model(entity)

        # Verify
        assert isinstance(model, MockSpeakerModel)
        assert model.name == "山田太郎"
        assert model.type == "議員"
        assert model.political_party_name == "自民党"
        assert model.position == "議長"
        assert model.is_politician is True
        # Note: ID is not set in _to_model

    @pytest.mark.asyncio
    async def test_update_model(self, repository):
        """Test update model from entity."""
        # Setup
        model = MockSpeakerModel(
            id=1,
            name="旧名前",
            type="旧タイプ",
            political_party_name="旧党",
            position="旧役職",
            is_politician=False,
        )
        entity = Speaker(
            id=1,
            name="新名前",
            type="新タイプ",
            political_party_name="新党",
            position="新役職",
            is_politician=True,
        )

        # Execute
        repository._update_model(model, entity)

        # Verify
        assert model.name == "新名前"
        assert model.type == "新タイプ"
        assert model.political_party_name == "新党"
        assert model.position == "新役職"
        assert model.is_politician is True
