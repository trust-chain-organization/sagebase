"""Tests for DataCoverageRepositoryImpl."""

from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.persistence.data_coverage_repository_impl import (
    DataCoverageRepositoryImpl,
)


@pytest_asyncio.fixture
async def async_session() -> AsyncGenerator[AsyncSession]:
    """Create an async session for testing."""
    # Use SQLite in-memory database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        # Create test tables
        await conn.execute(
            text("""
            CREATE TABLE governing_bodies (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE conferences (
                id INTEGER PRIMARY KEY,
                name TEXT,
                governing_body_id INTEGER
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE meetings (
                id INTEGER PRIMARY KEY,
                name TEXT,
                date DATE,
                conference_id INTEGER
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE minutes (
                id INTEGER PRIMARY KEY,
                meeting_id INTEGER,
                content TEXT
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY,
                minutes_id INTEGER,
                speaker_id INTEGER,
                speaker_name TEXT,
                comment TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                chapter_number INTEGER,
                sub_chapter_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE speakers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                created_at TIMESTAMP
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE politicians (
                id INTEGER PRIMARY KEY,
                name TEXT,
                political_party_id INTEGER,
                created_at TIMESTAMP
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE political_parties (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        )

    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def repository(async_session: AsyncSession) -> DataCoverageRepositoryImpl:
    """Create repository instance for testing.

    Args:
        async_session: Async database session fixture

    Returns:
        DataCoverageRepositoryImpl instance
    """
    return DataCoverageRepositoryImpl(async_session)


@pytest_asyncio.fixture
async def sample_governing_body(async_session: AsyncSession) -> int:
    """Create a sample governing body and return its ID.

    Args:
        async_session: Async database session

    Returns:
        int: ID of created governing body
    """
    result = await async_session.execute(
        text("""
            INSERT INTO governing_bodies (name, type)
            VALUES ('Test Gov', '都道府県')
            RETURNING id
        """)
    )
    await async_session.commit()
    gov_id = result.scalar()
    assert gov_id is not None, "Failed to create governing body"
    return gov_id


@pytest_asyncio.fixture
async def sample_conference(
    async_session: AsyncSession, sample_governing_body: int
) -> int:
    """Create a sample conference and return its ID.

    Args:
        async_session: Async database session
        sample_governing_body: ID of governing body

    Returns:
        int: ID of created conference
    """
    result = await async_session.execute(
        text("""
            INSERT INTO conferences (name, governing_body_id)
            VALUES ('Test Conference', :gov_id)
            RETURNING id
        """),
        {"gov_id": sample_governing_body},
    )
    await async_session.commit()
    conf_id = result.scalar()
    assert conf_id is not None, "Failed to create conference"
    return conf_id


@pytest_asyncio.fixture
async def sample_meeting(async_session: AsyncSession, sample_conference: int) -> int:
    """Create a sample meeting and return its ID.

    Args:
        async_session: Async database session
        sample_conference: ID of conference

    Returns:
        int: ID of created meeting
    """
    result = await async_session.execute(
        text("""
            INSERT INTO meetings (name, conference_id, date)
            VALUES ('Test Meeting', :conf_id, CURRENT_DATE)
            RETURNING id
        """),
        {"conf_id": sample_conference},
    )
    await async_session.commit()
    meeting_id = result.scalar()
    assert meeting_id is not None, "Failed to create meeting"
    return meeting_id


@pytest.mark.asyncio
async def test_get_governing_body_stats_empty(
    repository: DataCoverageRepositoryImpl,
) -> None:
    """Test get_governing_body_stats with empty database."""
    stats = await repository.get_governing_body_stats()

    assert stats["total"] == 0
    assert stats["with_conferences"] == 0
    assert stats["with_meetings"] == 0
    assert stats["coverage_percentage"] == 0.0


@pytest.mark.asyncio
async def test_get_governing_body_stats_with_data(
    repository: DataCoverageRepositoryImpl,
    async_session: AsyncSession,
) -> None:
    """Test get_governing_body_stats with test data."""
    # Insert test data
    await async_session.execute(
        text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES
                (1, 'Test Prefecture', '都道府県'),
                (2, 'Test Municipality', '市町村'),
                (3, 'Test City', '市町村')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conferences (id, name, governing_body_id)
            VALUES
                (1, 'Test Conference 1', 1),
                (2, 'Test Conference 2', 2)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO meetings (id, name, conference_id, date)
            VALUES
                (1, 'Test Meeting', 1, CURRENT_DATE)
        """)
    )

    await async_session.commit()

    # Execute test
    stats = await repository.get_governing_body_stats()

    assert stats["total"] == 3
    assert stats["with_conferences"] == 2
    assert stats["with_meetings"] == 1
    assert 0 < stats["coverage_percentage"] <= 100


@pytest.mark.asyncio
async def test_get_meeting_stats_empty(
    repository: DataCoverageRepositoryImpl,
) -> None:
    """Test get_meeting_stats with empty database."""
    stats = await repository.get_meeting_stats()

    assert stats["total_meetings"] == 0
    assert stats["with_minutes"] == 0
    assert stats["with_conversations"] == 0
    assert stats["average_conversations_per_meeting"] == 0.0
    assert stats["meetings_by_conference"] == {}


@pytest.mark.asyncio
async def test_get_meeting_stats_with_data(
    repository: DataCoverageRepositoryImpl,
    async_session: AsyncSession,
) -> None:
    """Test get_meeting_stats with test data."""
    # Insert test data
    await async_session.execute(
        text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'Test Gov', '都道府県')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conferences (id, name, governing_body_id)
            VALUES (1, 'Test Conference', 1)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO meetings (id, name, conference_id, date)
            VALUES
                (1, 'Meeting 1', 1, CURRENT_DATE),
                (2, 'Meeting 2', 1, CURRENT_DATE)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO minutes (id, meeting_id, content)
            VALUES (1, 1, 'Test content')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conversations (
                id, minutes_id, speaker_name, comment, sequence_number
            )
            VALUES
                (1, 1, 'Speaker 1', 'Content 1', 1),
                (2, 1, 'Speaker 2', 'Content 2', 2)
        """)
    )

    await async_session.commit()

    # Execute test
    stats = await repository.get_meeting_stats()

    assert stats["total_meetings"] == 2
    assert stats["with_minutes"] == 1
    assert stats["with_conversations"] == 1
    assert stats["average_conversations_per_meeting"] == 1.0
    assert "Test Conference" in stats["meetings_by_conference"]
    assert stats["meetings_by_conference"]["Test Conference"] == 2


@pytest.mark.asyncio
async def test_get_meeting_stats_conference_without_meetings(
    repository: DataCoverageRepositoryImpl,
    async_session: AsyncSession,
) -> None:
    """Test get_meeting_stats with conferences that have no meetings."""
    # Arrange: Create governing body and conference without meetings
    await async_session.execute(
        text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'Test Gov', '都道府県')
        """)
    )
    await async_session.execute(
        text("""
            INSERT INTO conferences (id, name, governing_body_id)
            VALUES (1, 'Empty Conference', 1)
        """)
    )
    await async_session.commit()

    # Act
    stats = await repository.get_meeting_stats()

    # Assert
    assert stats["total_meetings"] == 0
    assert stats["with_minutes"] == 0
    assert stats["with_conversations"] == 0
    assert stats["average_conversations_per_meeting"] == 0.0
    # Conference should appear with 0 meetings
    assert "Empty Conference" in stats["meetings_by_conference"]
    assert stats["meetings_by_conference"]["Empty Conference"] == 0


@pytest.mark.asyncio
async def test_get_speaker_matching_stats_empty(
    repository: DataCoverageRepositoryImpl,
) -> None:
    """Test get_speaker_matching_stats with empty database."""
    stats = await repository.get_speaker_matching_stats()

    assert stats["total_speakers"] == 0
    assert stats["matched_speakers"] == 0
    assert stats["unmatched_speakers"] == 0
    assert stats["matching_rate"] == 0.0
    assert stats["total_conversations"] == 0
    assert stats["linked_conversations"] == 0
    assert stats["linkage_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_speaker_matching_stats_with_data(
    repository: DataCoverageRepositoryImpl,
    async_session: AsyncSession,
) -> None:
    """Test get_speaker_matching_stats with test data."""
    # Insert test data
    await async_session.execute(
        text("""
            INSERT INTO speakers (id, name, type, created_at)
            VALUES
                (1, 'Politician 1', 'politician', CURRENT_TIMESTAMP),
                (2, 'Unknown Speaker', 'unknown', CURRENT_TIMESTAMP),
                (3, 'Politician 2', '政治家', CURRENT_TIMESTAMP)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'Test Gov', '都道府県')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conferences (id, name, governing_body_id)
            VALUES (1, 'Test Conference', 1)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO meetings (id, name, conference_id, date)
            VALUES (1, 'Meeting 1', 1, CURRENT_DATE)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO minutes (id, meeting_id, content)
            VALUES (1, 1, 'Test minutes content')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conversations (
                id, minutes_id, speaker_name, comment, sequence_number, speaker_id
            )
            VALUES
                (1, 1, 'Politician 1', 'Content 1', 1, 1),
                (2, 1, 'Unknown', 'Content 2', 2, NULL)
        """)
    )

    await async_session.commit()

    # Execute test
    stats = await repository.get_speaker_matching_stats()

    assert stats["total_speakers"] == 3
    assert stats["matched_speakers"] == 2
    assert stats["unmatched_speakers"] == 1
    assert 0 < stats["matching_rate"] <= 100
    assert stats["total_conversations"] == 2
    assert stats["linked_conversations"] == 1
    assert 0 < stats["linkage_rate"] <= 100


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="SQLite doesn't support generate_series and INTERVAL. "
    "This functionality should be tested with PostgreSQL integration tests."
)
async def test_get_activity_trend_empty(
    repository: DataCoverageRepositoryImpl,
) -> None:
    """Test get_activity_trend with empty database."""
    trend = await repository.get_activity_trend(period="7d")

    assert len(trend) == 8  # 7 days + today
    assert all(activity["meetings_count"] == 0 for activity in trend)
    assert all(activity["conversations_count"] == 0 for activity in trend)
    assert all(activity["speakers_count"] == 0 for activity in trend)
    assert all(activity["politicians_count"] == 0 for activity in trend)


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="SQLite doesn't support generate_series and INTERVAL. "
    "This functionality should be tested with PostgreSQL integration tests."
)
async def test_get_activity_trend_with_data(
    repository: DataCoverageRepositoryImpl,
    async_session: AsyncSession,
) -> None:
    """Test get_activity_trend with test data."""
    # Insert test data with specific dates
    today = datetime.now().date()

    await async_session.execute(
        text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'Test Gov', '都道府県')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conferences (id, name, governing_body_id)
            VALUES (1, 'Test Conference', 1)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO meetings (id, name, conference_id, date)
            VALUES (1, 'Meeting Today', 1, CURRENT_DATE)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO conversations (id, meeting_id, speaker_name, content, sequence)
            VALUES (1, 1, 'Speaker', 'Content', 1)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO speakers (id, name, type, created_at)
            VALUES (1, 'Speaker', 'unknown', CURRENT_TIMESTAMP)
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO political_parties (id, name)
            VALUES (1, 'Test Party')
        """)
    )

    await async_session.execute(
        text("""
            INSERT INTO politicians (id, name, political_party_id, created_at)
            VALUES (1, 'Politician', 1, CURRENT_TIMESTAMP)
        """)
    )

    await async_session.commit()

    # Execute test
    trend = await repository.get_activity_trend(period="7d")

    assert len(trend) == 8  # 7 days + today
    # Check that today has data
    today_str = today.isoformat()
    today_data = [a for a in trend if a["date"] == today_str]
    assert len(today_data) == 1
    assert today_data[0]["meetings_count"] == 1
    assert today_data[0]["conversations_count"] == 1
    assert today_data[0]["speakers_count"] == 1
    assert today_data[0]["politicians_count"] == 1


@pytest.mark.asyncio
async def test_get_activity_trend_invalid_period(
    repository: DataCoverageRepositoryImpl,
) -> None:
    """Test get_activity_trend with invalid period."""
    with pytest.raises(ValueError, match="Period must end with 'd'"):
        await repository.get_activity_trend(period="30")

    with pytest.raises(ValueError, match="Period must be a number"):
        await repository.get_activity_trend(period="abcd")

    with pytest.raises(ValueError, match="Period must be between 1 and 365 days"):
        await repository.get_activity_trend(period="0d")

    with pytest.raises(ValueError, match="Period must be between 1 and 365 days"):
        await repository.get_activity_trend(period="400d")
