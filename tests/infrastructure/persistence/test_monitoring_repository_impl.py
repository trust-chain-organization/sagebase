"""Tests for MonitoringRepositoryImpl."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl,
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
                type TEXT,
                organization_code TEXT,
                organization_type TEXT
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE conferences (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
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
                conference_id INTEGER,
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
        await conn.execute(
            text("""
            CREATE TABLE speakers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                political_party_name TEXT,
                created_at TIMESTAMP
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE conversations (
                id INTEGER PRIMARY KEY,
                meeting_id INTEGER,
                speaker_id INTEGER
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE politician_affiliations (
                id INTEGER PRIMARY KEY,
                politician_id INTEGER,
                conference_id INTEGER
            )
        """)
        )
        await conn.execute(
            text("""
            CREATE TABLE minutes (
                id INTEGER PRIMARY KEY,
                meeting_id INTEGER
            )
        """)
        )

    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_overall_metrics_empty(async_session: AsyncSession) -> None:
    """Test getting overall metrics with empty database."""
    repo = MonitoringRepositoryImpl(async_session)

    metrics = await repo.get_overall_metrics()

    assert metrics is not None
    assert "governing_bodies" in metrics
    assert metrics["governing_bodies"]["total"] == 0
    assert metrics["governing_bodies"]["active"] == 0
    assert metrics["governing_bodies"]["coverage"] == 0.0


@pytest.mark.asyncio
async def test_get_recent_activities_empty(async_session: AsyncSession) -> None:
    """Test getting recent activities with empty database."""
    repo = MonitoringRepositoryImpl(async_session)

    activities = await repo.get_recent_activities(limit=10)

    assert activities is not None
    assert isinstance(activities, list)
    assert len(activities) == 0


@pytest.mark.asyncio
async def test_get_conference_coverage_empty(async_session: AsyncSession) -> None:
    """Test getting conference coverage with empty database."""
    repo = MonitoringRepositoryImpl(async_session)

    coverage = await repo.get_conference_coverage()

    assert coverage is not None
    assert isinstance(coverage, list)
    assert len(coverage) == 0


@pytest.mark.asyncio
async def test_get_party_coverage_empty(async_session: AsyncSession) -> None:
    """Test getting party coverage with empty database."""
    repo = MonitoringRepositoryImpl(async_session)

    coverage = await repo.get_party_coverage()

    assert coverage is not None
    assert isinstance(coverage, list)
    assert len(coverage) == 0


@pytest.mark.asyncio
async def test_get_prefecture_coverage_empty(async_session: AsyncSession) -> None:
    """Test getting prefecture coverage with empty database."""
    repo = MonitoringRepositoryImpl(async_session)

    coverage = await repo.get_prefecture_coverage()

    assert coverage is not None
    assert isinstance(coverage, dict)
    assert "prefectures" in coverage
    assert "municipalities" in coverage
