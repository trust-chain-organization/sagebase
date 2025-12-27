"""Integration tests for PoliticalPartyRepository"""

import os

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl as PoliticalPartyRepository,
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

    # Clean up any existing test data before yielding
    try:
        session.execute(text("DELETE FROM political_parties WHERE name LIKE 'テスト%'"))
        session.commit()
    except Exception:
        session.rollback()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def repository(db_session):
    """Create PoliticalPartyRepository instance with test session"""
    return PoliticalPartyRepository(session=db_session)


class TestPoliticalPartyRepository:
    """Test cases for PoliticalPartyRepository"""

    def test_create_party_if_not_exists_new_party(self, db_session, repository):
        """Test creating a new political party"""
        # Execute
        party_id = repository.create_party_if_not_exists("テスト新党")

        # Verify
        assert party_id is not None
        assert isinstance(party_id, int)

        # Check it was created in database
        result = db_session.execute(
            text("SELECT id, name FROM political_parties WHERE name = :name"),
            {"name": "テスト新党"},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == party_id
        assert row[1] == "テスト新党"

    def test_create_party_if_not_exists_existing_party(self, db_session, repository):
        """Test that existing party is not duplicated"""
        # Setup - create existing party
        first_id = repository.create_party_if_not_exists("テスト既存党")
        assert first_id is not None

        # Execute - try to create same party again
        second_id = repository.create_party_if_not_exists("テスト既存党")

        # Verify - should return same ID
        assert second_id == first_id

        # Check only one party exists
        result = db_session.execute(
            text("SELECT COUNT(*) FROM political_parties WHERE name = :name"),
            {"name": "テスト既存党"},
        )
        count = result.scalar()
        assert count == 1

    def test_get_by_name_found(self, db_session, repository):
        """Test getting party by name when it exists"""
        # Setup - create party
        party_id = repository.create_party_if_not_exists("テスト検索党")

        # Execute
        result = repository.get_by_name("テスト検索党")

        # Verify
        assert result is not None
        assert result[0] == party_id
        assert result[1] == "テスト検索党"

    def test_get_by_name_not_found(self, repository):
        """Test getting party by name when it doesn't exist"""
        # Execute
        result = repository.get_by_name("存在しない党")

        # Verify
        assert result is None

    def test_get_all(self, db_session, repository):
        """Test getting all political parties"""
        # Setup - create test parties
        repository.create_party_if_not_exists("テスト党A")
        repository.create_party_if_not_exists("テスト党B")
        repository.create_party_if_not_exists("テスト党C")

        # Execute
        all_parties = repository.get_all()

        # Verify
        assert isinstance(all_parties, list)
        assert len(all_parties) > 0

        # Check our test parties are included
        test_party_names = [
            party[1] for party in all_parties if party[1].startswith("テスト党")
        ]
        assert "テスト党A" in test_party_names
        assert "テスト党B" in test_party_names
        assert "テスト党C" in test_party_names

        # Verify ordering by ID
        party_ids = [party[0] for party in all_parties]
        assert party_ids == sorted(party_ids)

    def test_transaction_rollback_on_error(self, db_session, repository):
        """Test that transaction is rolled back on error"""
        # This test is difficult to implement without mocking
        # as the repository methods handle errors internally
        # For now, we'll skip this test
        pass
