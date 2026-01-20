"""Tests for MeetingRepositoryImpl."""

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy import Column, Date, Integer, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import registry

from src.domain.entities.meeting import Meeting
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)


# Create a simple SQLAlchemy model for testing
mapper_registry = registry()


@mapper_registry.mapped
class MeetingModel:
    """Test Meeting model."""

    __table__ = Table(
        "meetings",
        mapper_registry.metadata,
        Column("id", Integer, primary_key=True),
        Column("conference_id", Integer),
        Column("name", String),
        Column("date", Date),
        Column("url", String),
        Column("gcs_pdf_uri", String),
        Column("gcs_text_uri", String),
        Column("attendees_mapping", JSONB),
        Column("summary", String),
        Column("uploaded_file_name", String),
    )


class TestMeetingRepositoryImpl:
    """Test cases for MeetingRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> MeetingRepositoryImpl:
        """Create meeting repository."""
        return MeetingRepositoryImpl(mock_session, model_class=MeetingModel)

    @pytest.fixture
    def sample_meeting_dict(self) -> dict[str, Any]:
        """Sample meeting data as dict."""
        return {
            "id": 1,
            "conference_id": 10,
            "date": date(2024, 1, 15),
            "url": "https://example.com/meeting",
            "name": "本会議",
            "gcs_pdf_uri": "gs://bucket/meeting.pdf",
            "gcs_text_uri": "gs://bucket/meeting.txt",
            "attendees_mapping": None,
            "created_at": None,
            "updated_at": None,
        }

    @pytest.fixture
    def sample_meeting_entity(self) -> Meeting:
        """Sample meeting entity."""
        return Meeting(
            id=1,
            conference_id=10,
            date=date(2024, 1, 15),
            url="https://example.com/meeting",
            name="本会議",
            gcs_pdf_uri="gs://bucket/meeting.pdf",
            gcs_text_uri="gs://bucket/meeting.txt",
        )

    @pytest.mark.asyncio
    async def test_get_by_conference_and_date_found(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_dict: dict[str, Any],
    ) -> None:
        """Test get_by_conference_and_date when meeting is found."""
        mock_row = MagicMock()
        mock_row._mapping = sample_meeting_dict
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference_and_date(10, date(2024, 1, 15))

        assert result is not None
        assert result.id == 1
        assert result.conference_id == 10
        assert result.date == date(2024, 1, 15)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference_and_date_not_found(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_conference_and_date when meeting is not found."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference_and_date(10, date(2024, 1, 15))

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_dict: dict[str, Any],
    ) -> None:
        """Test get_by_conference returns list of meetings."""
        mock_row = MagicMock()
        mock_row._mapping = sample_meeting_dict
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference(10)

        assert len(result) == 1
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference_with_limit(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_conference with limit."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference(10, limit=5)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_unprocessed(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_unprocessed returns meetings without minutes."""
        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.conference_id = 10
        mock_meeting.date = date(2024, 1, 15)
        mock_meeting.url = "https://example.com/meeting"
        mock_meeting.name = "本会議"
        mock_meeting.gcs_pdf_uri = None
        mock_meeting.gcs_text_uri = None
        mock_meeting.attendees_mapping = None

        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[mock_meeting]))
        )
        mock_session.execute.return_value = mock_result

        result = await repository.get_unprocessed()

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_gcs_uris_success(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_gcs_uris successfully updates URIs."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.update_gcs_uris(
            1, pdf_uri="gs://bucket/new.pdf", text_uri="gs://bucket/new.txt"
        )

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_gcs_uris_no_update(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_gcs_uris returns False when no URIs provided."""
        result = await repository.update_gcs_uris(1)

        assert result is False
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_gcs_uris_pdf_only(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_gcs_uris with only PDF URI."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.update_gcs_uris(1, pdf_uri="gs://bucket/new.pdf")

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_meeting_gcs_uris(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_meeting_gcs_uris is alias for update_gcs_uris."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.update_meeting_gcs_uris(
            1, pdf_uri="gs://bucket/new.pdf"
        )

        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_meetings_with_filters(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_meetings_with_filters returns filtered meetings."""
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 1,
            "conference_id": 10,
            "date": date(2024, 1, 15),
            "url": "https://example.com/meeting",
            "name": "本会議",
            "gcs_pdf_uri": None,
            "gcs_text_uri": None,
            "created_at": None,
            "updated_at": None,
            "conference_name": "東京都議会",
            "governing_body_name": "東京都",
            "governing_body_type": "都道府県",
        }

        mock_result1 = MagicMock()
        mock_result1.__iter__ = MagicMock(return_value=iter([mock_row]))

        mock_result2 = MagicMock()
        mock_result2.scalar = MagicMock(return_value=1)

        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        meetings, total = await repository.get_meetings_with_filters(
            conference_id=10, limit=10, offset=0
        )

        assert len(meetings) == 1
        assert total == 1
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_meeting_by_id_with_info_found(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_meeting_by_id_with_info when meeting is found."""
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 1,
            "conference_id": 10,
            "date": date(2024, 1, 15),
            "conference_name": "東京都議会",
            "governing_body_name": "東京都",
            "governing_body_type": "都道府県",
        }
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_meeting_by_id_with_info(1)

        assert result is not None
        assert result["id"] == 1
        assert result["conference_name"] == "東京都議会"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_meeting_by_id_with_info_not_found(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_meeting_by_id_with_info when meeting is not found."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_meeting_by_id_with_info(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_entity: Meeting,
        sample_meeting_dict: dict[str, Any],
    ) -> None:
        """Test create successfully creates a meeting."""
        mock_row = MagicMock()
        mock_row._mapping = sample_meeting_dict
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_meeting_entity)

        assert result.id == 1
        assert result.conference_id == 10
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_entity: Meeting,
    ) -> None:
        """Test create raises error when creation fails."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Failed to create meeting"):
            await repository.create(sample_meeting_entity)

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_entity: Meeting,
        sample_meeting_dict: dict[str, Any],
    ) -> None:
        """Test update successfully updates a meeting."""
        mock_row = MagicMock()
        mock_row._mapping = {**sample_meeting_dict, "name": "本会議（更新）"}
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        sample_meeting_entity.name = "本会議（更新）"
        result = await repository.update(sample_meeting_entity)

        assert result.name == "本会議（更新）"
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_failure(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_entity: Meeting,
    ) -> None:
        """Test update raises error when update fails."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        with pytest.raises(RuntimeError, match="Failed to update meeting"):
            await repository.update(sample_meeting_entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete successfully deletes a meeting."""
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_delete_result]
        )

        result = await repository.delete(1)

        assert result is True
        assert mock_session.execute.call_count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_minutes(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test delete returns False when meeting has minutes."""
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_count_result

        result = await repository.delete(1)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when meeting is found."""
        mock_row = MagicMock()
        mock_row._mapping = sample_meeting_dict
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_id when meeting is not found."""
        mock_result = MagicMock()
        mock_result.first = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
        sample_meeting_dict: dict[str, Any],
    ) -> None:
        """Test get_all returns all meetings."""
        mock_row = MagicMock()
        mock_row._mapping = sample_meeting_dict
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 1
        assert result[0].id == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_all with limit and offset."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count returns total number of meetings."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_zero(
        self, repository: MeetingRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test count returns 0 when no meetings."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    def test_to_entity(self, repository: MeetingRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""

        class MockModel:
            id = 1
            conference_id = 10
            date = date(2024, 1, 15)
            url = "https://example.com/meeting"
            name = "本会議"
            gcs_pdf_uri = "gs://bucket/meeting.pdf"
            gcs_text_uri = "gs://bucket/meeting.txt"
            attendees_mapping = None

        model = MockModel()
        entity = repository._to_entity(model)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 10
        assert entity.date == date(2024, 1, 15)

    def test_to_model(
        self, repository: MeetingRepositoryImpl, sample_meeting_entity: Meeting
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_meeting_entity)

        assert model.id == 1
        assert model.conference_id == 10
        assert model.date == date(2024, 1, 15)

    def test_update_model(
        self, repository: MeetingRepositoryImpl, sample_meeting_entity: Meeting
    ) -> None:
        """Test _update_model updates model fields from entity."""

        class MockModel:
            id = 1
            conference_id = 5
            date = date(2023, 1, 1)
            url = "https://old.com"
            name = "旧会議"
            gcs_pdf_uri = None
            gcs_text_uri = None
            attendees_mapping = None

        model = MockModel()
        repository._update_model(model, sample_meeting_entity)

        assert model.conference_id == 10
        assert model.date == date(2024, 1, 15)
        assert model.name == "本会議"
        assert model.gcs_pdf_uri == "gs://bucket/meeting.pdf"

    def test_dict_to_entity(
        self, repository: MeetingRepositoryImpl, sample_meeting_dict: dict[str, Any]
    ) -> None:
        """Test _dict_to_entity converts dictionary to entity correctly."""
        entity = repository._dict_to_entity(sample_meeting_dict)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 10
        assert entity.date == date(2024, 1, 15)

    def test_pydantic_to_entity(self, repository: MeetingRepositoryImpl) -> None:
        """Test _pydantic_to_entity converts Pydantic model to entity correctly."""

        class MockPydanticModel:
            id = 1
            conference_id = 10
            date = date(2024, 1, 15)
            url = "https://example.com/meeting"
            name = "本会議"
            gcs_pdf_uri = "gs://bucket/meeting.pdf"
            gcs_text_uri = "gs://bucket/meeting.txt"
            attendees_mapping = None

        model = MockPydanticModel()
        entity = repository._pydantic_to_entity(model)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 10

    def test_to_entity_with_none(self, repository: MeetingRepositoryImpl) -> None:
        """Test _to_entity raises ValueError when model is None."""
        with pytest.raises(ValueError, match="Cannot convert None to Meeting entity"):
            repository._to_entity(None)

    @pytest.mark.asyncio
    async def test_get_by_conference_empty(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_conference returns empty list when no meetings exist."""
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference(10)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete returns False when meeting not found."""
        # Mock count check (no related minutes)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        # Mock delete result (rowcount=0, not found)
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 0

        mock_session.execute.side_effect = [mock_count_result, mock_delete_result]

        result = await repository.delete(999)

        assert result is False
        assert mock_session.execute.call_count == 2
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_with_related_minutes(
        self,
        repository: MeetingRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete fails when meeting has related minutes."""
        # Mock count check (has related minutes)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_count_result

        result = await repository.delete(1)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()
