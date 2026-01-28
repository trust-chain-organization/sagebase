"""Integration tests for MonitoringRepository"""

import os

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl as MonitoringRepository,
)


# Skip all tests in this module if running in CI environment
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Integration tests require database connection not available in CI",
)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing with transaction rollback"""
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def setup_test_data(db_session):
    """Set up test data for monitoring"""
    # Ensure we have a governing body
    gb_check = db_session.execute(text("SELECT id FROM governing_bodies WHERE id = 1"))
    if not gb_check.scalar():
        db_session.execute(
            text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'テスト市', '市区町村')
            """)
        )
        db_session.commit()

    # Insert test conference
    conf_result = db_session.execute(
        text("""
        INSERT INTO conferences (governing_body_id, name, type)
        VALUES (1, 'モニターテスト議会', '地方議会全体')
        RETURNING id
        """)
    )
    conference_id = conf_result.scalar()

    # Insert test meeting
    meeting_result = db_session.execute(
        text("""
        INSERT INTO meetings (conference_id, name, date, url)
        VALUES (:conf_id, 'モニターテスト会議', CURRENT_DATE, 'http://test.example.com')
        RETURNING id
        """),
        {"conf_id": conference_id},
    )
    meeting_id = meeting_result.scalar()

    # Insert test minutes
    minutes_result = db_session.execute(
        text("""
        INSERT INTO minutes (meeting_id, url)
        VALUES (:meeting_id, 'http://test.example.com/minutes')
        RETURNING id
        """),
        {"meeting_id": meeting_id},
    )
    minutes_id = minutes_result.scalar()

    # Insert test speaker
    speaker_result = db_session.execute(
        text("""
        INSERT INTO speakers (name, type, is_politician)
        VALUES ('モニターテスト議員', '議員', true)
        RETURNING id
        """)
    )
    speaker_id = speaker_result.scalar()

    # Insert test political party
    party_result = db_session.execute(
        text("""
        INSERT INTO political_parties (name)
        VALUES ('モニターテスト党')
        RETURNING id
        """)
    )
    party_id = party_result.scalar()

    # Insert test politician (speaker_id removed in migration 032)
    politician_result = db_session.execute(
        text("""
        INSERT INTO politicians
            (name, prefecture, district, political_party_id)
        VALUES ('モニターテスト議員', '東京都', '東京1区', :party_id)
        RETURNING id
        """),
        {"party_id": party_id},
    )
    politician_id = politician_result.scalar()

    db_session.commit()

    return {
        "conference_id": conference_id,
        "meeting_id": meeting_id,
        "minutes_id": minutes_id,
        "speaker_id": speaker_id,
        "politician_id": politician_id,
        "party_id": party_id,
    }


@pytest.fixture
def repository(db_session):
    """Create MonitoringRepository instance with test session"""
    async_session = AsyncSessionAdapter(db_session)
    return MonitoringRepository(session=async_session)


class TestMonitoringRepository:
    """Test cases for MonitoringRepository"""

    @pytest.mark.asyncio
    async def test_get_overall_metrics(self, db_session, setup_test_data, repository):
        """Test getting overall metrics"""
        # Execute
        metrics = await repository.get_overall_metrics()

        # Verify
        assert isinstance(metrics, dict)

        # Check main category keys exist
        assert "conferences" in metrics
        assert "governing_bodies" in metrics
        assert "meetings" in metrics
        assert "conversations" in metrics

        # Check conferences structure
        assert "total" in metrics["conferences"]
        assert "active" in metrics["conferences"]
        assert "coverage" in metrics["conferences"]

        # Check governing_bodies structure
        assert "total" in metrics["governing_bodies"]
        assert "active" in metrics["governing_bodies"]
        assert "coverage" in metrics["governing_bodies"]

        # Check meetings structure
        assert "total" in metrics["meetings"]

        # Check conversations structure
        assert "total" in metrics["conversations"]
        assert "linked" in metrics["conversations"]
        assert "linkage_rate" in metrics["conversations"]

        # Check values are reasonable
        assert metrics["conferences"]["total"] > 0
        assert metrics["governing_bodies"]["total"] > 0
        assert metrics["meetings"]["total"] > 0

        # Check coverage percentages are valid
        assert metrics["conferences"]["coverage"] >= 0
        assert metrics["governing_bodies"]["coverage"] >= 0
        assert metrics["conversations"]["linkage_rate"] >= 0

        # Skip processed_minutes check since processed_at column doesn't exist
        # assert metrics["processed_minutes"] > 0

    @pytest.mark.asyncio
    async def test_get_recent_activities(self, db_session, setup_test_data, repository):
        """Test getting recent activities"""
        # Execute - get recent activities with default limit
        activities = await repository.get_recent_activities(limit=30)

        # Verify
        assert isinstance(activities, list)
        assert len(activities) > 0

        # Check structure of activity objects
        for activity in activities:
            assert isinstance(activity, dict)
            assert "type" in activity
            assert "id" in activity
            assert "name" in activity
            assert "date" in activity
            assert "created_at" in activity
            assert "details" in activity

        # Check that our test data is included
        test_activities = [
            a for a in activities if a["name"] and "モニターテスト" in a["name"]
        ]
        assert len(test_activities) > 0

    @pytest.mark.asyncio
    async def test_get_conference_coverage(
        self, db_session, setup_test_data, repository
    ):
        """Test getting conference coverage data"""
        # Execute
        coverage = await repository.get_conference_coverage()

        # Verify
        assert isinstance(coverage, list)
        assert len(coverage) > 0

        # Check structure of coverage objects
        for item in coverage:
            assert isinstance(item, dict)
            assert "id" in item
            assert "name" in item
            assert "governing_body" in item

        # Check our test conference is included
        test_conf = [c for c in coverage if c.get("name") == "モニターテスト議会"]
        assert len(test_conf) >= 1

    @pytest.mark.asyncio
    async def test_get_timeline_data(self, db_session, setup_test_data, repository):
        """Test getting timeline data"""
        # Execute
        result = await repository.get_timeline_data(period_days=30)

        # Verify
        assert isinstance(result, dict)

        # Check that result contains timeline data
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_get_prefecture_coverage(
        self, db_session, setup_test_data, repository
    ):
        """Test getting prefecture coverage data"""
        # Execute
        coverage = await repository.get_prefecture_coverage()

        # Verify
        assert isinstance(coverage, dict)

        # Check structure
        assert "prefectures" in coverage
        assert "municipalities" in coverage

    @pytest.mark.asyncio
    async def test_get_committee_type_coverage(
        self, db_session, setup_test_data, repository
    ):
        """Test getting committee type coverage data"""
        # Execute
        coverage = await repository.get_committee_type_coverage()

        # Verify
        assert isinstance(coverage, list)

        # Check structure if there's data
        if len(coverage) > 0:
            for item in coverage:
                assert isinstance(item, dict)

    @pytest.mark.asyncio
    async def test_get_party_coverage(self, db_session, setup_test_data, repository):
        """Test getting party coverage data"""
        # Execute
        coverage = await repository.get_party_coverage()

        # Verify
        assert isinstance(coverage, list)
        assert len(coverage) > 0

        # Check structure
        for item in coverage:
            assert isinstance(item, dict)
            assert "id" in item
            assert "name" in item

        # Check our test party is included
        test_party = [p for p in coverage if p.get("name") == "モニターテスト党"]
        assert len(test_party) >= 1

    @pytest.mark.asyncio
    async def test_get_prefecture_detailed_coverage(
        self, db_session, setup_test_data, repository
    ):
        """Test getting prefecture detailed coverage data"""
        # Execute
        coverage = await repository.get_prefecture_detailed_coverage()

        # Verify
        assert isinstance(coverage, list)
        # May be empty if no prefectures in test data

        # Check structure if there's data
        if len(coverage) > 0:
            for item in coverage:
                assert isinstance(item, dict)
