"""Tests for ConversationRepositoryImpl."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.domain.entities.conversation import Conversation
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationModel,
    ConversationRepositoryImpl,
)
from src.minutes_divide_processor.models import SpeakerAndSpeechContent


@pytest.fixture
def mock_async_session():
    """Create mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_sync_session():
    """Create mock sync session."""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def conversation_repo_async(mock_async_session):
    """Create ConversationRepositoryImpl with async session."""
    return ConversationRepositoryImpl(
        session=mock_async_session, model_class=ConversationModel
    )


@pytest.fixture
def conversation_repo_sync(mock_sync_session):
    """Create ConversationRepositoryImpl with sync session."""
    repo = ConversationRepositoryImpl(
        session=mock_sync_session, model_class=ConversationModel
    )
    return repo


@pytest.mark.asyncio
async def test_get_by_minutes_async(conversation_repo_async, mock_async_session):
    """Test get_by_minutes with async session."""
    # Setup mock data
    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.comment = "Test comment"
    mock_row.sequence_number = 1
    mock_row.minutes_id = 100
    mock_row.speaker_id = 10
    mock_row.speaker_name = "Test Speaker"
    mock_row.chapter_number = 1
    mock_row.sub_chapter_number = 1

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_async_session.execute.return_value = mock_result

    # Execute
    conversations = await conversation_repo_async.get_by_minutes(100)

    # Verify
    assert len(conversations) == 1
    assert conversations[0].id == 1
    assert conversations[0].comment == "Test comment"
    assert conversations[0].minutes_id == 100
    mock_async_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_speaker_async(conversation_repo_async, mock_async_session):
    """Test get_by_speaker with async session."""
    # Setup mock data
    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.comment = "Speaker comment"
    mock_row.sequence_number = 1
    mock_row.minutes_id = 100
    mock_row.speaker_id = 20
    mock_row.speaker_name = "Speaker Name"
    mock_row.chapter_number = 1
    mock_row.sub_chapter_number = None

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_async_session.execute.return_value = mock_result

    # Execute
    conversations = await conversation_repo_async.get_by_speaker(20, limit=10)

    # Verify
    assert len(conversations) == 1
    assert conversations[0].speaker_id == 20
    mock_async_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_unlinked_async(conversation_repo_async, mock_async_session):
    """Test get_unlinked with async session."""
    # Setup mock data
    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.comment = "Unlinked comment"
    mock_row.sequence_number = 1
    mock_row.minutes_id = 100
    mock_row.speaker_id = None
    mock_row.speaker_name = "Unknown Speaker"
    mock_row.chapter_number = 1
    mock_row.sub_chapter_number = None

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_async_session.execute.return_value = mock_result

    # Execute
    conversations = await conversation_repo_async.get_unlinked(limit=5)

    # Verify
    assert len(conversations) == 1
    assert conversations[0].speaker_id is None
    mock_async_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_create_async(conversation_repo_async, mock_async_session):
    """Test bulk_create with async session (ORM version with flush)."""
    # Setup
    conversations = [
        Conversation(
            comment="Comment 1",
            sequence_number=1,
            minutes_id=100,
            speaker_name="Speaker 1",
        ),
        Conversation(
            comment="Comment 2",
            sequence_number=2,
            minutes_id=100,
            speaker_name="Speaker 2",
        ),
    ]

    # Mock add_all to track added models
    added_models = []

    def mock_add_all(models):
        added_models.extend(models)

    mock_async_session.add_all.side_effect = mock_add_all

    # Mock flush to assign IDs to models
    async def mock_flush():
        for i, model in enumerate(added_models, start=1):
            model.id = i

    mock_async_session.flush.side_effect = mock_flush

    # Mock refresh to simulate database refresh (no-op in test)
    async def mock_refresh(model):
        pass

    mock_async_session.refresh.side_effect = mock_refresh

    # Execute
    created = await conversation_repo_async.bulk_create(conversations)

    # Verify
    assert len(created) == 2
    assert created[0].id == 1
    assert created[1].id == 2
    mock_async_session.add_all.assert_called_once()
    mock_async_session.flush.assert_called_once()
    # Note: commit() should NOT be called - UseCase manages transaction
    mock_async_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_save_speaker_and_speech_content_list_async(
    conversation_repo_async, mock_async_session
):
    """Test save_speaker_and_speech_content_list with async session."""
    # Setup
    speech_list = [
        SpeakerAndSpeechContent(
            speaker="Speaker 1",
            speech_content="Content 1",
            speech_order=1,
            chapter_number=1,
            sub_chapter_number=1,
        ),
    ]

    # Mock _find_speaker_id to return None (no matching speaker)
    # Mock bulk_create to return conversations with IDs
    with patch.object(conversation_repo_async, "_find_speaker_id", return_value=None):
        with patch.object(conversation_repo_async, "bulk_create") as mock_bulk_create:
            # Create mock conversations with IDs
            from src.domain.entities.conversation import Conversation

            mock_conversation = Conversation(
                id=1,
                minutes_id=100,
                speaker_id=None,
                speaker_name="Speaker 1",
                comment="Content 1",
                sequence_number=1,
                chapter_number=1,
                sub_chapter_number=1,
            )
            mock_bulk_create.return_value = [mock_conversation]

            # Execute
            saved_ids = (
                await conversation_repo_async.save_speaker_and_speech_content_list(
                    speech_list, minutes_id=100
                )
            )

            # Verify
            assert saved_ids == [1]
            # Note: commit/close are NOT called - following Unit of Work pattern
            mock_bulk_create.assert_called_once()
            # Verify the created conversation entities have correct attributes
            created_conversations = mock_bulk_create.call_args[0][0]
            assert len(created_conversations) == 1
            assert created_conversations[0].speaker_name == "Speaker 1"
            assert created_conversations[0].comment == "Content 1"
            assert created_conversations[0].sequence_number == 1


@pytest.mark.asyncio
async def test_get_conversations_count_async(
    conversation_repo_async, mock_async_session
):
    """Test get_conversations_count with async session."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar.return_value = 42
    mock_async_session.execute.return_value = mock_result

    # Execute
    count = await conversation_repo_async.get_conversations_count()

    # Verify
    assert count == 42
    mock_async_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_speaker_linking_stats_async(
    conversation_repo_async, mock_async_session
):
    """Test get_speaker_linking_stats with async session."""
    # Setup
    mock_results = [
        MagicMock(),  # Total count result
        MagicMock(),  # Linked count result
    ]
    mock_results[0].scalar.return_value = 100
    mock_results[1].scalar.return_value = 75

    mock_async_session.execute.side_effect = mock_results

    # Execute
    stats = await conversation_repo_async.get_speaker_linking_stats()

    # Verify
    assert stats["total_conversations"] == 100
    assert stats["linked_conversations"] == 75
    assert stats["unlinked_conversations"] == 25
    assert stats["linking_rate"] == 75.0
    assert mock_async_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_get_conversations_with_pagination_async(
    conversation_repo_async, mock_async_session
):
    """Test get_conversations_with_pagination with async session."""
    # Setup mock data
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 50

    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.speaker_name = "Test Speaker"
    mock_row.comment = "Test comment"
    mock_row.sequence_number = 1
    mock_row.chapter_number = 1
    mock_row.sub_chapter_number = None
    mock_row.speaker_id = 10
    mock_row.minutes_id = 100
    mock_row.meeting_title = "Test Meeting"
    mock_row.meeting_date = "2024-01-01"
    mock_row.linked_speaker_name = "Linked Speaker"

    mock_data_result = MagicMock()
    mock_data_result.fetchall.return_value = [mock_row]

    mock_async_session.execute.side_effect = [mock_count_result, mock_data_result]

    # Execute
    result = await conversation_repo_async.get_conversations_with_pagination(
        page=1, page_size=10, speaker_name="Test", meeting_id=100
    )

    # Verify
    assert result["total_count"] == 50
    assert result["total_pages"] == 5
    assert result["current_page"] == 1
    assert len(result["conversations"]) == 1
    assert result["conversations"][0]["speaker_name"] == "Test Speaker"
    assert mock_async_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_update_speaker_links_with_service(
    conversation_repo_async, mock_async_session
):
    """Test update_speaker_links with speaker matching service."""
    # Setup
    mock_service = MagicMock()
    mock_service.update_all_conversations.return_value = 10
    conversation_repo_async.speaker_matching_service = mock_service

    # Execute
    updated = await conversation_repo_async.update_speaker_links()

    # Verify
    assert updated == 10
    mock_service.update_all_conversations.assert_called_once()


@pytest.mark.asyncio
async def test_update_speaker_links_without_service(
    conversation_repo_async, mock_async_session
):
    """Test update_speaker_links without speaker matching service."""
    # Setup
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_async_session.execute.return_value = mock_result

    # Execute
    updated = await conversation_repo_async.update_speaker_links()

    # Verify
    assert updated == 5
    mock_async_session.execute.assert_called_once()
    mock_async_session.commit.assert_called_once()


def test_get_by_minutes_sync(conversation_repo_sync, mock_sync_session):
    """Test get_by_minutes with sync session."""
    # Setup mock data
    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.comment = "Sync comment"
    mock_row.sequence_number = 1
    mock_row.minutes_id = 100
    mock_row.speaker_id = 10
    mock_row.speaker_name = "Sync Speaker"
    mock_row.chapter_number = 1
    mock_row.sub_chapter_number = None

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]

    # Make execute return an awaitable (async coroutine)
    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_sync_session.execute = mock_execute

    # Execute
    loop = asyncio.new_event_loop()
    conversations = loop.run_until_complete(conversation_repo_sync.get_by_minutes(100))
    loop.close()

    # Verify
    assert len(conversations) == 1
    assert conversations[0].id == 1
    # Note: execute is now a plain async function, not a Mock,
    # so we can't assert call count


def test_bulk_create_sync(conversation_repo_sync, mock_sync_session):
    """Test bulk_create with sync session (no commit - UseCase manages transaction)."""
    # Setup
    conversations = [
        Conversation(
            comment="Sync Comment 1",
            sequence_number=1,
            minutes_id=100,
            speaker_name="Sync Speaker 1",
        ),
    ]

    # Mock the insert operation
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1

    # Make execute return an awaitable (async coroutine)
    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_sync_session.execute = mock_execute

    # Execute
    loop = asyncio.new_event_loop()
    created = loop.run_until_complete(conversation_repo_sync.bulk_create(conversations))
    loop.close()

    # Verify
    assert len(created) == 1
    assert created[0].id == 1
    # Note: execute is now a plain async function, not a Mock,
    # so we can't assert call count
    # Note: commit() should NOT be called - UseCase manages transaction
    mock_sync_session.commit.assert_not_called()


def test_empty_bulk_create():
    """Test bulk_create with empty list."""
    repo = ConversationRepositoryImpl(
        session=AsyncMock(), model_class=ConversationModel
    )

    loop = asyncio.new_event_loop()
    created = loop.run_until_complete(repo.bulk_create([]))
    loop.close()

    assert created == []


def test_model_conversion():
    """Test model to entity conversion."""
    repo = ConversationRepositoryImpl(
        session=AsyncMock(), model_class=ConversationModel
    )

    # Create a mock model
    model = ConversationModel(
        id=1,
        comment="Test",
        sequence_number=1,
        minutes_id=100,
        speaker_id=10,
        speaker_name="Speaker",
        chapter_number=1,
        sub_chapter_number=2,
    )

    # Convert to entity (using private method for testing)
    entity = repo._to_entity(model)  # type: ignore[attr-defined]

    assert entity.id == 1
    assert entity.comment == "Test"
    assert entity.sequence_number == 1
    assert entity.minutes_id == 100
    assert entity.speaker_id == 10
    assert entity.speaker_name == "Speaker"
    assert entity.chapter_number == 1
    assert entity.sub_chapter_number == 2


def test_entity_to_model_conversion():
    """Test entity to model conversion."""
    repo = ConversationRepositoryImpl(
        session=AsyncMock(), model_class=ConversationModel
    )

    # Create entity
    entity = Conversation(
        id=1,
        comment="Test",
        sequence_number=1,
        minutes_id=100,
        speaker_id=10,
        speaker_name="Speaker",
        chapter_number=1,
        sub_chapter_number=2,
    )

    # Convert to model (using private method for testing)
    model = repo._to_model(entity)  # type: ignore[attr-defined]

    assert model.comment == "Test"
    assert model.sequence_number == 1
    assert model.minutes_id == 100
    assert model.speaker_id == 10
    assert model.speaker_name == "Speaker"
    assert model.chapter_number == 1
    assert model.sub_chapter_number == 2
