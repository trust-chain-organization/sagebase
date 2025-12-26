"""Integration tests for parliamentary group repositories

These tests verify that the parliamentary group and membership
repositories work correctly with the new Clean Architecture
implementation using entity-based patterns.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl as ParliamentaryGroupMembershipRepository,  # noqa: E501
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl as ParliamentaryGroupRepository,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing with transaction rollback"""
    engine = create_engine(DATABASE_URL)

    # Check if parliamentary_groups table exists
    with engine.connect() as temp_conn:
        result = temp_conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'parliamentary_groups'
            )
            """)
        )
        if not result.scalar():
            pytest.fail(
                "Parliamentary groups tables not found. "
                "Database migrations must be applied before running integration tests. "
                "Run: psql -f "
                "database/migrations/008_create_parliamentary_groups_tables.sql"
            )

    # Now create the actual test connection
    connection = engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    # Clean up any existing test data before yielding
    # Use TRUNCATE CASCADE to properly handle FK constraints and reset sequences
    try:
        session.execute(
            text("SET session_replication_role = replica;")
        )  # Disable FK checks
        session.execute(text("TRUNCATE TABLE parliamentary_group_memberships CASCADE"))
        session.execute(
            text("TRUNCATE TABLE parliamentary_groups RESTART IDENTITY CASCADE")
        )
        session.execute(text("DELETE FROM politician_affiliations WHERE id > 0"))
        session.execute(text("DELETE FROM politicians WHERE name LIKE 'テスト議員%'"))
        session.execute(text("DELETE FROM speakers WHERE name LIKE 'テスト議員%'"))
        session.execute(
            text("DELETE FROM political_parties WHERE name LIKE 'テスト党%'")
        )
        session.execute(text("DELETE FROM conferences WHERE name LIKE 'テスト%'"))
        session.execute(
            text("SET session_replication_role = DEFAULT;")
        )  # Re-enable FK checks
        session.commit()
    except Exception as e:
        # If cleanup fails, still continue with test
        print(f"Cleanup failed: {e}")
        session.rollback()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def setup_test_data(db_session):
    """Set up test data for parliamentary groups"""
    import uuid

    # Generate unique test identifier
    test_id = str(uuid.uuid4())[:8]

    # First check if governing body exists, if not create one
    gb_check = db_session.execute(text("SELECT id FROM governing_bodies WHERE id = 1"))
    if not gb_check.scalar():
        db_session.execute(
            text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'テスト市', '市区町村')
            """)
        )
        db_session.commit()

    # Insert test conference with unique name
    result = db_session.execute(
        text("""
        INSERT INTO conferences (governing_body_id, name, type)
        VALUES (1, :conference_name, '地方議会全体')
        RETURNING id
        """),
        {"conference_name": f"テスト市議会_{test_id}"},
    )
    conference_id = result.scalar()

    # Verify conference was created
    if not conference_id:
        pytest.fail("Failed to create test conference")

    # Insert test political parties with unique names
    party_result1 = db_session.execute(
        text("INSERT INTO political_parties (name) VALUES (:party_name) RETURNING id"),
        {"party_name": f"テスト党A_{test_id}"},
    )
    party_id1 = party_result1.scalar()

    party_result2 = db_session.execute(
        text("INSERT INTO political_parties (name) VALUES (:party_name) RETURNING id"),
        {"party_name": f"テスト党B_{test_id}"},
    )
    party_id2 = party_result2.scalar()

    # Insert test speakers first (required for politicians)
    db_session.execute(
        text(
            "INSERT INTO speakers (name, type, is_politician) "
            "VALUES (:speaker_name, '議員', true) RETURNING id"
        ),
        {"speaker_name": f"テスト議員1_{test_id}"},
    )

    db_session.execute(
        text(
            "INSERT INTO speakers (name, type, is_politician) "
            "VALUES (:speaker_name, '議員', true) RETURNING id"
        ),
        {"speaker_name": f"テスト議員2_{test_id}"},
    )

    db_session.execute(
        text(
            "INSERT INTO speakers (name, type, is_politician) "
            "VALUES (:speaker_name, '議員', true) RETURNING id"
        ),
        {"speaker_name": f"テスト議員3_{test_id}"},
    )

    # Insert test politicians (migration 032 removed speaker_id)
    politician_result1 = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id)
        VALUES (:politician_name, :party_id)
        RETURNING id
        """),
        {"politician_name": f"テスト議員1_{test_id}", "party_id": party_id1},
    )
    politician_id1 = politician_result1.scalar()

    politician_result2 = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id)
        VALUES (:politician_name, :party_id)
        RETURNING id
        """),
        {"politician_name": f"テスト議員2_{test_id}", "party_id": party_id2},
    )
    politician_id2 = politician_result2.scalar()

    politician_result3 = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id)
        VALUES (:politician_name, :party_id)
        RETURNING id
        """),
        {"politician_name": f"テスト議員3_{test_id}", "party_id": party_id1},
    )
    politician_id3 = politician_result3.scalar()

    # Note: Migration 032 removed the direct speaker-politician relationship
    # Speakers and politicians are now linked through conversations

    db_session.commit()

    return {
        "conference_id": conference_id,
        "party_ids": [party_id1, party_id2],
        "politician_ids": [politician_id1, politician_id2, politician_id3],
    }


@pytest.fixture
def group_repository(db_session):
    """Create ParliamentaryGroupRepository instance with test session"""
    async_session = AsyncSessionAdapter(db_session)
    return ParliamentaryGroupRepository(session=async_session)


@pytest.fixture
def membership_repository(db_session):
    """Create ParliamentaryGroupMembershipRepository instance with test session"""
    async_session = AsyncSessionAdapter(db_session)
    return ParliamentaryGroupMembershipRepository(session=async_session)


class TestParliamentaryGroupRepositoryIntegration:
    """Integration tests for ParliamentaryGroupRepository"""

    @pytest.mark.asyncio
    async def test_create_parliamentary_group(
        self, db_session, setup_test_data, group_repository
    ):
        """Test creating a parliamentary group"""
        # Create a parliamentary group entity
        group_entity = ParliamentaryGroup(
            name="テスト会派",
            conference_id=setup_test_data["conference_id"],
            url="http://test-group.example.com",
            description="テスト用の会派です",
            is_active=True,
        )

        # Create using repository
        created_group = await group_repository.create(group_entity)

        # Verify the created group
        assert created_group.name == "テスト会派"
        assert created_group.conference_id == setup_test_data["conference_id"]
        assert created_group.url == "http://test-group.example.com"
        assert created_group.description == "テスト用の会派です"
        assert created_group.is_active is True
        assert created_group.id is not None

    @pytest.mark.asyncio
    async def test_get_parliamentary_group_by_id(
        self, db_session, setup_test_data, group_repository
    ):
        """Test retrieving a parliamentary group by ID"""
        # Create a group
        group_entity = ParliamentaryGroup(
            name="取得テスト会派",
            conference_id=setup_test_data["conference_id"],
        )
        created_group = await group_repository.create(group_entity)

        # Retrieve by ID
        retrieved_group = await group_repository.get_by_id(created_group.id)

        assert retrieved_group is not None
        assert retrieved_group.id == created_group.id
        assert retrieved_group.name == "取得テスト会派"

        # Test non-existent ID
        non_existent = await group_repository.get_by_id(99999)
        assert non_existent is None

    @pytest.mark.asyncio
    async def test_get_parliamentary_groups_by_conference(
        self, db_session, setup_test_data, group_repository
    ):
        """Test retrieving parliamentary groups by conference"""
        conference_id = setup_test_data["conference_id"]

        # Create multiple groups
        await group_repository.create(
            ParliamentaryGroup(
                name="会派A", conference_id=conference_id, is_active=True
            )
        )
        await group_repository.create(
            ParliamentaryGroup(
                name="会派B", conference_id=conference_id, is_active=True
            )
        )
        await group_repository.create(
            ParliamentaryGroup(
                name="会派C(解散)", conference_id=conference_id, is_active=False
            )
        )

        # Get active groups only
        active_groups = await group_repository.get_by_conference_id(
            conference_id, active_only=True
        )
        assert len(active_groups) == 2
        assert all(g.is_active for g in active_groups)

        # Get all groups
        all_groups = await group_repository.get_by_conference_id(
            conference_id, active_only=False
        )
        assert len(all_groups) == 3
        assert any(not g.is_active for g in all_groups)

    @pytest.mark.asyncio
    async def test_get_by_name_and_conference(
        self, db_session, setup_test_data, group_repository
    ):
        """Test searching parliamentary groups by name and conference"""
        conference_id = setup_test_data["conference_id"]

        # Create test groups
        await group_repository.create(
            ParliamentaryGroup(name="自由民主党会派", conference_id=conference_id)
        )
        await group_repository.create(
            ParliamentaryGroup(name="立憲民主党会派", conference_id=conference_id)
        )
        await group_repository.create(
            ParliamentaryGroup(name="公明党会派", conference_id=conference_id)
        )

        # Search by name and conference
        result = await group_repository.get_by_name_and_conference(
            "立憲民主党会派", conference_id
        )
        assert result is not None
        assert result.name == "立憲民主党会派"

        # Search non-existent
        result = await group_repository.get_by_name_and_conference(
            "存在しない会派", conference_id
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_parliamentary_group(
        self, db_session, setup_test_data, group_repository
    ):
        """Test updating parliamentary group information"""
        # Create a group
        group = ParliamentaryGroup(
            name="更新前会派",
            conference_id=setup_test_data["conference_id"],
            description="更新前の説明",
        )
        created_group = await group_repository.create(group)

        # Update the group
        created_group.name = "更新後会派"
        created_group.description = "更新後の説明"
        created_group.url = "http://updated.example.com"

        updated_group = await group_repository.update(created_group)
        assert updated_group.name == "更新後会派"
        assert updated_group.description == "更新後の説明"
        assert updated_group.url == "http://updated.example.com"

        # Verify the update
        fetched_group = await group_repository.get_by_id(created_group.id)
        assert fetched_group.name == "更新後会派"
        assert fetched_group.description == "更新後の説明"
        assert fetched_group.url == "http://updated.example.com"

        # Test partial update (deactivate)
        fetched_group.is_active = False
        updated_again = await group_repository.update(fetched_group)
        assert updated_again.is_active is False
        assert updated_again.name == "更新後会派"  # Unchanged


@pytest.fixture
def setup_membership_group(db_session, setup_test_data, group_repository):
    """Create a parliamentary group for membership tests"""
    # Ensure we have a valid conference_id from setup_test_data
    conference_id = setup_test_data["conference_id"]
    if not conference_id:
        pytest.fail("No conference_id available from setup_test_data")

    # Create a group for membership tests (sync call since fixture isn't async)
    # We'll insert directly via SQL for the fixture
    result = db_session.execute(
        text("""
        INSERT INTO parliamentary_groups (name, conference_id)
        VALUES ('メンバーシップテスト会派', :conference_id)
        RETURNING id
        """),
        {"conference_id": conference_id},
    )
    group_id = result.scalar()
    db_session.commit()

    return {"id": group_id, "conference_id": conference_id}


class TestParliamentaryGroupMembershipRepositoryIntegration:
    """Integration tests for ParliamentaryGroupMembershipRepository"""

    @pytest.mark.asyncio
    async def test_add_membership(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test adding a membership"""
        membership = await membership_repository.add_membership(
            politician_id=setup_test_data["politician_ids"][0],
            parliamentary_group_id=setup_membership_group["id"],
            start_date=date(2024, 1, 1),
            role="会長",
        )

        assert membership.politician_id == setup_test_data["politician_ids"][0]
        assert membership.parliamentary_group_id == setup_membership_group["id"]
        assert membership.start_date == date(2024, 1, 1)
        assert membership.end_date is None
        assert membership.role == "会長"
        assert membership.id is not None

    @pytest.mark.asyncio
    async def test_get_current_members(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test getting current members of a group"""
        # Add current members
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
            role="会長",
        )
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date(2024, 1, 15),
        )

        # Add past member
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][2],
            setup_membership_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Get current members
        current_members = await membership_repository.get_current_members(
            setup_membership_group["id"]
        )

        assert len(current_members) == 2
        assert all(m["end_date"] is None for m in current_members)

        # Check roles
        leader = [m for m in current_members if m["role"] == "会長"]
        assert len(leader) == 1

    @pytest.mark.asyncio
    async def test_get_by_group(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test getting all memberships by group"""
        # Add members with history
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
        )
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Get all history
        all_history = await membership_repository.get_by_group(
            setup_membership_group["id"]
        )
        assert len(all_history) == 2

        # Get current only
        current_only = await membership_repository.get_active_by_group(
            setup_membership_group["id"]
        )
        assert len(current_only) == 1
        assert current_only[0].politician_id == setup_test_data["politician_ids"][0]

    @pytest.mark.asyncio
    async def test_get_by_politician(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test getting groups a politician belongs to"""
        # Create another group
        result = db_session.execute(
            text("""
            INSERT INTO parliamentary_groups (name, conference_id)
            VALUES ('別の会派', :conference_id)
            RETURNING id
            """),
            {"conference_id": setup_membership_group["conference_id"]},
        )
        another_group_id = result.scalar()
        db_session.commit()

        politician_id = setup_test_data["politician_ids"][0]

        # Add memberships
        await membership_repository.add_membership(
            politician_id,
            setup_membership_group["id"],
            date(2024, 1, 1),
        )
        await membership_repository.add_membership(
            politician_id,
            another_group_id,
            date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Get all groups for politician
        all_groups = await membership_repository.get_by_politician(politician_id)
        assert len(all_groups) == 2

    @pytest.mark.asyncio
    async def test_end_membership(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test ending a membership"""
        # Add membership
        politician_id = setup_test_data["politician_ids"][0]
        membership = await membership_repository.add_membership(
            politician_id,
            setup_membership_group["id"],
            date(2024, 1, 1),
        )

        # End membership
        ended = await membership_repository.end_membership(
            membership.id,
            date(2024, 6, 30),
        )
        assert ended is not None
        assert ended.end_date == date(2024, 6, 30)

        # Verify membership ended
        current_members = await membership_repository.get_current_members(
            setup_membership_group["id"]
        )
        assert len(current_members) == 0

        # Check history shows ended membership
        history = await membership_repository.get_by_group(setup_membership_group["id"])
        assert len(history) == 1
        assert history[0].end_date == date(2024, 6, 30)

    @pytest.mark.asyncio
    async def test_get_active_by_group_at_date(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test getting group members at a specific date"""
        # Add members with different periods
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 6, 30),
        )
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date(2023, 4, 1),
            end_date=date(2023, 12, 31),
        )
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][2],
            setup_membership_group["id"],
            date(2023, 7, 1),
        )

        # Check members at different dates
        members_jan = await membership_repository.get_active_by_group(
            setup_membership_group["id"], date(2023, 1, 15)
        )
        assert len(members_jan) == 1  # Only politician 0

        members_may = await membership_repository.get_active_by_group(
            setup_membership_group["id"], date(2023, 5, 15)
        )
        assert len(members_may) == 2  # Politicians 0 and 1

        members_aug = await membership_repository.get_active_by_group(
            setup_membership_group["id"], date(2023, 8, 15)
        )
        assert len(members_aug) == 2  # Politicians 1 and 2

        members_now = await membership_repository.get_active_by_group(
            setup_membership_group["id"], date.today()
        )
        assert len(members_now) == 1  # Only politician 2 (no end date)

    @pytest.mark.asyncio
    async def test_membership_constraints(
        self, db_session, setup_test_data, setup_membership_group, membership_repository
    ):
        """Test database constraints and edge cases"""
        # Add a membership
        await membership_repository.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
        )

        # Try to add duplicate membership with same start_date
        # (should return existing membership per create_membership implementation)
        duplicate = await membership_repository.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
        )
        assert duplicate.id is not None

        # Test with future dates
        future_membership = await membership_repository.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date.today() + timedelta(days=30),
        )
        assert future_membership.start_date > date.today()
