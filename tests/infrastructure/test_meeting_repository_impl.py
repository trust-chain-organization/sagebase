"""Tests for MeetingRepositoryImpl

Test suite covering initialization and conversion methods for the Meeting repository.

NOTE: CRUD operations, queries, and GCS operations are not included in this unit test
suite due to the repository's use of raw SQL instead of ORM methods. These operations
require integration tests with a real database to test properly. See Issue #684 for
future integration test implementation.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.meeting import Meeting
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl


@pytest.fixture
def mock_async_session():
    """Create mock async session for testing"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def async_repository(mock_async_session):
    """Create repository with async session"""
    return MeetingRepositoryImpl(session=mock_async_session)


@pytest.fixture
def sample_meeting():
    """Create sample meeting entity for testing"""
    return Meeting(
        id=1,
        conference_id=100,
        date=date(2024, 1, 15),
        url="https://example.com/meeting/1",
        name="Sample Meeting",
        gcs_pdf_uri="gs://bucket/meeting1.pdf",
        gcs_text_uri="gs://bucket/meeting1.txt",
        attendees_mapping={"speaker1": "politician1"},
    )


@pytest.fixture
def sample_meeting_dict():
    """Create sample meeting as dict for testing"""
    return {
        "id": 1,
        "conference_id": 100,
        "date": date(2024, 1, 15),
        "url": "https://example.com/meeting/1",
        "name": "Sample Meeting",
        "gcs_pdf_uri": "gs://bucket/meeting1.pdf",
        "gcs_text_uri": "gs://bucket/meeting1.txt",
        "attendees_mapping": {"speaker1": "politician1"},
    }


class TestMeetingRepositoryImplInitialization:
    """Test repository initialization with different session types"""

    def test_sync_session_initialization(self):
        """Test that sync session is properly initialized"""
        sync_session = MagicMock()
        repo = MeetingRepositoryImpl(session=sync_session)

        assert repo.sync_session == sync_session
        assert repo.async_session is None
        assert repo.session_adapter is None

    @pytest.mark.asyncio
    async def test_async_session_initialization(self):
        """Test that async session is properly initialized"""
        async_session = AsyncMock(spec=AsyncSession)
        repo = MeetingRepositoryImpl(session=async_session)

        assert repo.async_session == async_session
        assert repo.sync_session is None


class TestMeetingRepositoryImplConversions:
    """Test conversion methods"""

    def test_to_entity_complete_data(self, async_repository, sample_meeting_dict):
        """Test converting model to entity with complete data"""
        mock_model = MagicMock()
        for key, value in sample_meeting_dict.items():
            setattr(mock_model, key, value)

        entity = async_repository._to_entity(mock_model)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 100
        assert entity.name == "Sample Meeting"

    def test_to_entity_minimal_data(self, async_repository):
        """Test converting model to entity with minimal data"""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.conference_id = 100
        mock_model.date = None
        mock_model.url = None
        mock_model.name = None
        mock_model.gcs_pdf_uri = None
        mock_model.gcs_text_uri = None
        mock_model.attendees_mapping = None

        entity = async_repository._to_entity(mock_model)

        assert entity.id == 1
        assert entity.conference_id == 100
        assert entity.date is None

    def test_to_model_complete_data(self, async_repository, sample_meeting):
        """Test converting entity to model with complete data"""
        model = async_repository._to_model(sample_meeting)

        assert model.id == 1
        assert model.conference_id == 100
        assert model.name == "Sample Meeting"

    def test_to_model_minimal_data(self, async_repository):
        """Test converting entity to model with minimal data"""
        minimal_meeting = Meeting(conference_id=100)

        model = async_repository._to_model(minimal_meeting)

        assert model.conference_id == 100

    def test_update_model_all_fields(self, async_repository, sample_meeting):
        """Test updating all model fields from entity"""
        mock_model = MagicMock()

        async_repository._update_model(mock_model, sample_meeting)

        assert mock_model.conference_id == 100
        assert mock_model.name == "Sample Meeting"

    def test_update_model_partial_fields(self, async_repository):
        """Test updating model with partial entity data"""
        mock_model = MagicMock()
        mock_model.name = "Old Name"

        partial_meeting = Meeting(conference_id=100, name="New Name")

        async_repository._update_model(mock_model, partial_meeting)

        assert mock_model.conference_id == 100

    def test_dict_to_entity_success(self, async_repository, sample_meeting_dict):
        """Test converting dict to entity"""
        entity = async_repository._dict_to_entity(sample_meeting_dict)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 100

    def test_pydantic_to_entity_success(self, async_repository):
        """Test converting Pydantic model to entity"""
        mock_pydantic = MagicMock()
        mock_pydantic.model_dump = MagicMock(
            return_value={
                "id": 1,
                "conference_id": 100,
                "name": "Pydantic Meeting",
            }
        )

        entity = async_repository._pydantic_to_entity(mock_pydantic)

        assert isinstance(entity, Meeting)
