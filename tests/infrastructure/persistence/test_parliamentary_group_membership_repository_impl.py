"""Tests for ParliamentaryGroupMembershipRepositoryImpl."""

from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence import (
    parliamentary_group_membership_repository_impl as pgm_repo,
)


ParliamentaryGroupMembershipRepositoryImpl = (
    pgm_repo.ParliamentaryGroupMembershipRepositoryImpl
)


class MockColumn:
    """Mock SQLAlchemy column descriptor."""

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        """Mock equality comparison for SQLAlchemy filters."""
        return f"{self.name} == {other}"


class TestParliamentaryGroupMembershipRepositoryImpl:
    """Test cases for ParliamentaryGroupMembershipRepositoryImpl."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = MagicMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create parliamentary group membership repository."""
        return ParliamentaryGroupMembershipRepositoryImpl(mock_session)

    @pytest.mark.asyncio
    async def test_find_by_created_user_with_specific_user(
        self, repository, mock_session
    ):
        """Test find_by_created_user with specific user_id."""
        # Setup
        test_user_id = UUID("11111111-1111-1111-1111-111111111111")
        mock_rows = [
            MagicMock(),
            MagicMock(),
        ]

        # First membership with both joins
        mock_rows[0]._mapping = {
            "id": 1,
            "politician_id": 100,
            "parliamentary_group_id": 10,
            "start_date": date(2024, 1, 1),
            "end_date": None,
            "role": "代表",
            "created_by_user_id": test_user_id,
            "created_at": datetime(2024, 1, 15, 10, 30),
            "updated_at": datetime(2024, 1, 15, 10, 30),
            "parliamentary_group_name": "自民党会派",
            "politician_name": "山田太郎",
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        # Second membership without politician join
        mock_rows[1]._mapping = {
            "id": 2,
            "politician_id": 101,
            "parliamentary_group_id": 11,
            "start_date": date(2024, 2, 1),
            "end_date": date(2024, 12, 31),
            "role": None,
            "created_by_user_id": test_user_id,
            "created_at": datetime(2024, 2, 10, 14, 20),
            "updated_at": datetime(2024, 2, 10, 14, 20),
            "parliamentary_group_name": "民主党会派",
            "politician_name": None,
        }
        for key, value in mock_rows[1]._mapping.items():
            setattr(mock_rows[1], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.find_by_created_user(test_user_id)

        # Verify
        assert len(result) == 2
        assert result[0].membership.politician_id == 100
        assert result[0].membership.parliamentary_group_id == 10
        assert result[0].membership.role == "代表"
        assert result[0].membership.created_by_user_id == test_user_id
        assert result[0].membership.created_at == datetime(2024, 1, 15, 10, 30)
        assert result[0].membership.updated_at == datetime(2024, 1, 15, 10, 30)
        assert result[0].parliamentary_group is not None
        assert result[0].parliamentary_group.name == "自民党会派"
        assert result[0].politician is not None
        assert result[0].politician.name == "山田太郎"

        assert result[1].membership.politician_id == 101
        assert result[1].parliamentary_group is not None
        assert result[1].parliamentary_group.name == "民主党会派"
        assert result[1].politician is None  # No politician name in mock data

    @pytest.mark.asyncio
    async def test_find_by_created_user_all_users(self, repository, mock_session):
        """Test find_by_created_user with user_id=None (all users)."""
        # Setup
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "id": 1,
            "politician_id": 100,
            "parliamentary_group_id": 10,
            "start_date": date(2024, 1, 1),
            "end_date": None,
            "role": "代表",
            "created_by_user_id": UUID("11111111-1111-1111-1111-111111111111"),
            "created_at": datetime(2024, 1, 15, 10, 30),
            "updated_at": datetime(2024, 1, 15, 10, 30),
            "parliamentary_group_name": "自民党会派",
            "politician_name": "山田太郎",
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute - user_id=None should return all created memberships
        result = await repository.find_by_created_user(None)

        # Verify
        assert len(result) == 1
        assert result[0].membership.politician_id == 100
        assert result[0].membership.created_by_user_id == UUID(
            "11111111-1111-1111-1111-111111111111"
        )

    @pytest.mark.asyncio
    async def test_find_by_created_user_no_results(self, repository, mock_session):
        """Test find_by_created_user with no matching results."""
        # Setup
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.find_by_created_user(
            UUID("99999999-9999-9999-9999-999999999999")
        )

        # Verify
        assert len(result) == 0
        assert result == []

    @pytest.mark.asyncio
    async def test_find_by_created_user_without_joins(self, repository, mock_session):
        """Test find_by_created_user when join columns are None."""
        # Setup
        test_user_id = UUID("11111111-1111-1111-1111-111111111111")
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "id": 1,
            "politician_id": 100,
            "parliamentary_group_id": 10,
            "start_date": date(2024, 1, 1),
            "end_date": None,
            "role": "代表",
            "created_by_user_id": test_user_id,
            "created_at": datetime(2024, 1, 15, 10, 30),
            "updated_at": datetime(2024, 1, 15, 10, 30),
            "parliamentary_group_name": None,
            "politician_name": None,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.find_by_created_user(test_user_id)

        # Verify
        assert len(result) == 1
        assert result[0].membership.politician_id == 100
        assert result[0].membership.parliamentary_group_id == 10
        # No joins should be set
        assert result[0].parliamentary_group is None
        assert result[0].politician is None

    @pytest.mark.asyncio
    async def test_get_membership_creation_statistics_by_user_specific_user(
        self, repository, mock_session
    ):
        """Test get_membership_creation_statistics_by_user with specific user_id."""
        # Setup
        test_user_id = UUID("11111111-1111-1111-1111-111111111111")
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "created_by_user_id": test_user_id,
            "count": 10,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_statistics_by_user(
            user_id=test_user_id
        )

        # Verify
        assert len(result) == 1
        assert test_user_id in result
        assert result[test_user_id] == 10

    @pytest.mark.asyncio
    async def test_get_membership_creation_statistics_by_user_all_users(
        self, repository, mock_session
    ):
        """Test get_membership_creation_statistics_by_user with user_id=None."""
        # Setup
        user1 = UUID("11111111-1111-1111-1111-111111111111")
        user2 = UUID("22222222-2222-2222-2222-222222222222")
        mock_rows = [
            MagicMock(),
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "created_by_user_id": user1,
            "count": 10,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_rows[1]._mapping = {
            "created_by_user_id": user2,
            "count": 5,
        }
        for key, value in mock_rows[1]._mapping.items():
            setattr(mock_rows[1], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_statistics_by_user(
            user_id=None
        )

        # Verify
        assert len(result) == 2
        assert result[user1] == 10
        assert result[user2] == 5

    @pytest.mark.asyncio
    async def test_get_membership_creation_statistics_by_user_with_date_filter(
        self, repository, mock_session
    ):
        """Test get_membership_creation_statistics_by_user with date filters."""
        # Setup
        test_user_id = UUID("11111111-1111-1111-1111-111111111111")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "created_by_user_id": test_user_id,
            "count": 3,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_statistics_by_user(
            user_id=test_user_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Verify
        assert len(result) == 1
        assert result[test_user_id] == 3

    @pytest.mark.asyncio
    async def test_get_membership_creation_statistics_by_user_no_results(
        self, repository, mock_session
    ):
        """Test get_membership_creation_statistics_by_user with no matching results."""
        # Setup
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_statistics_by_user(
            user_id=UUID("99999999-9999-9999-9999-999999999999")
        )

        # Verify
        assert len(result) == 0
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_membership_creation_timeline_statistics_day_interval(
        self, repository, mock_session
    ):
        """Test get_membership_creation_timeline_statistics with day interval."""
        # Setup
        test_user_id = UUID("11111111-1111-1111-1111-111111111111")
        mock_rows = [
            MagicMock(),
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "date": "2024-01-01",
            "count": 5,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_rows[1]._mapping = {
            "date": "2024-01-02",
            "count": 3,
        }
        for key, value in mock_rows[1]._mapping.items():
            setattr(mock_rows[1], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_timeline_statistics(
            user_id=test_user_id,
            interval="day",
        )

        # Verify
        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["count"] == 5
        assert result[1]["date"] == "2024-01-02"
        assert result[1]["count"] == 3

    @pytest.mark.asyncio
    async def test_get_membership_creation_timeline_statistics_week_interval(
        self, repository, mock_session
    ):
        """Test get_membership_creation_timeline_statistics with week interval."""
        # Setup
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "date": "2024-01-01",
            "count": 15,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_timeline_statistics(
            interval="week",
        )

        # Verify
        assert len(result) == 1
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["count"] == 15

    @pytest.mark.asyncio
    async def test_get_membership_creation_timeline_statistics_month_interval(
        self, repository, mock_session
    ):
        """Test get_membership_creation_timeline_statistics with month interval."""
        # Setup
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "date": "2024-01-01",
            "count": 50,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_timeline_statistics(
            interval="month",
        )

        # Verify
        assert len(result) == 1
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["count"] == 50

    @pytest.mark.asyncio
    async def test_get_membership_creation_timeline_statistics_invalid_interval(
        self, repository, mock_session
    ):
        """Test get_membership_creation_timeline_statistics with invalid interval."""
        # Execute & Verify
        with pytest.raises(ValueError) as exc_info:
            await repository.get_membership_creation_timeline_statistics(
                interval="invalid",
            )

        assert "Invalid interval" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_membership_creation_timeline_statistics_with_filters(
        self, repository, mock_session
    ):
        """Test get_membership_creation_timeline_statistics with all filters."""
        # Setup
        test_user_id = UUID("11111111-1111-1111-1111-111111111111")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        mock_rows = [
            MagicMock(),
        ]

        mock_rows[0]._mapping = {
            "date": "2024-01-15",
            "count": 2,
        }
        for key, value in mock_rows[0]._mapping.items():
            setattr(mock_rows[0], key, value)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_timeline_statistics(
            user_id=test_user_id,
            start_date=start_date,
            end_date=end_date,
            interval="day",
        )

        # Verify
        assert len(result) == 1
        assert result[0]["date"] == "2024-01-15"
        assert result[0]["count"] == 2

    @pytest.mark.asyncio
    async def test_get_membership_creation_timeline_statistics_no_results(
        self, repository, mock_session
    ):
        """Test get_membership_creation_timeline_statistics with no results."""
        # Setup
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        async def async_execute(query, params=None):
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_membership_creation_timeline_statistics(
            user_id=UUID("99999999-9999-9999-9999-999999999999"),
        )

        # Verify
        assert len(result) == 0
        assert result == []
