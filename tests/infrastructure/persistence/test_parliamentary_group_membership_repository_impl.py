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
