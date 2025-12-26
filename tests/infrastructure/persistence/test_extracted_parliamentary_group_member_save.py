"""Tests for ExtractedParliamentaryGroupMemberRepositoryImpl.save_extracted_members."""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence import (
    extracted_parliamentary_group_member_repository_impl as epgmr_impl,
)


ExtractedParliamentaryGroupMemberRepositoryImpl = (
    epgmr_impl.ExtractedParliamentaryGroupMemberRepositoryImpl
)


class MockExtractedMember:
    """Mock ExtractedMember for testing."""

    def __init__(
        self, name: str, role: str | None = None, party_name: str | None = None
    ):
        self.name = name
        self.role = role
        self.party_name = party_name
        self.district = None
        self.additional_info = None


@pytest.mark.asyncio
async def test_save_extracted_members_prevents_duplicates():
    """Test that save_extracted_members prevents duplicates."""
    # Setup
    session = AsyncMock(spec=AsyncSession)
    repo = ExtractedParliamentaryGroupMemberRepositoryImpl(session)

    # Mock the database query to return no rows (ON CONFLICT DO NOTHING)
    mock_result = Mock()
    mock_result.fetchone.return_value = None  # No row inserted due to conflict
    session.execute = AsyncMock(return_value=mock_result)

    # Create test data
    members = [
        MockExtractedMember("山田太郎", "団長"),
        MockExtractedMember("田中花子", "幹事長"),
    ]

    # Execute
    saved_count = await repo.save_extracted_members(
        parliamentary_group_id=1, members=members, url="http://example.com"
    )

    # Assert
    assert saved_count == 0  # Both members already exist, so 0 saved
    assert session.flush.called


@pytest.mark.asyncio
async def test_save_extracted_members_saves_new_members():
    """Test that save_extracted_members saves new members."""
    # Setup
    session = AsyncMock(spec=AsyncSession)
    repo = ExtractedParliamentaryGroupMemberRepositoryImpl(session)

    # Mock the database query to return inserted IDs (successful inserts)
    def side_effect(*args, **kwargs):
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(id=1)  # Row inserted
        return mock_result

    session.execute = AsyncMock(side_effect=side_effect)

    # Create test data
    members = [
        MockExtractedMember("山田太郎", "団長"),
        MockExtractedMember("田中花子", "幹事長"),
    ]

    # Execute
    saved_count = await repo.save_extracted_members(
        parliamentary_group_id=1, members=members, url="http://example.com"
    )

    # Assert
    assert saved_count == 2  # Both members are new, so 2 saved
    assert session.execute.call_count == 2  # 2 inserts (no separate checks)
    assert session.flush.called


@pytest.mark.asyncio
async def test_save_extracted_members_mixed_duplicates():
    """Test that save_extracted_members handles mixed duplicates."""
    # Setup
    session = AsyncMock(spec=AsyncSession)
    repo = ExtractedParliamentaryGroupMemberRepositoryImpl(session)

    # Mock the database query: first insert conflicts (None), second succeeds (id=1)
    results = [
        None,  # First insert: conflict (duplicate)
        Mock(id=1),  # Second insert: success (new member)
    ]

    def side_effect(*args, **kwargs):
        mock_result = Mock()
        # Pop results from the list
        if results:
            mock_result.fetchone.return_value = results.pop(0)
        else:
            mock_result.fetchone.return_value = None
        return mock_result

    session.execute = AsyncMock(side_effect=side_effect)

    # Create test data
    members = [
        MockExtractedMember("山田太郎", "団長"),  # Duplicate
        MockExtractedMember("田中花子", "幹事長"),  # New
    ]

    # Execute
    saved_count = await repo.save_extracted_members(
        parliamentary_group_id=1, members=members, url="http://example.com"
    )

    # Assert
    assert saved_count == 1  # Only one member is new
    assert session.flush.called
