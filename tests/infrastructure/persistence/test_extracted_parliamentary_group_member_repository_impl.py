"""Tests for ExtractedParliamentaryGroupMemberRepositoryImpl."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fixtures.entity_factories import create_extracted_parliamentary_group_member

from src.infrastructure.persistence import (
    extracted_parliamentary_group_member_repository_impl as repo_impl,
)


ExtractedParliamentaryGroupMemberRepositoryImpl = (
    repo_impl.ExtractedParliamentaryGroupMemberRepositoryImpl
)


@pytest.mark.asyncio
class TestExtractedParliamentaryGroupMemberRepositoryImpl:
    """Test cases for ExtractedParliamentaryGroupMemberRepositoryImpl."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance with mock session."""
        return ExtractedParliamentaryGroupMemberRepositoryImpl(mock_session)

    async def test_get_pending_members(self, repository, mock_session) -> None:
        """Test getting pending members."""
        # Mock data
        mock_rows = [
            MagicMock(
                id=1,
                parliamentary_group_id=1,
                extracted_name="山田太郎",
                source_url="https://example.com",
                extracted_role="団長",
                extracted_party_name="自民党",
                extracted_district="東京1区",
                extracted_at=datetime.now(),
                matching_status="pending",
                matched_politician_id=None,
                matching_confidence=None,
                matched_at=None,
                additional_info=None,
            )
        ]

        # Setup mock
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        members = await repository.get_pending_members()

        # Assert
        assert len(members) == 1
        assert members[0].matching_status == "pending"
        mock_session.execute.assert_called_once()

    async def test_get_pending_members_with_group_filter(
        self, repository, mock_session
    ) -> None:
        """Test getting pending members filtered by group."""
        mock_rows = [
            MagicMock(
                id=1,
                parliamentary_group_id=1,
                extracted_name="山田太郎",
                source_url="https://example.com",
                extracted_role="団長",
                extracted_party_name="自民党",
                extracted_district="東京1区",
                extracted_at=datetime.now(),
                matching_status="pending",
                matched_politician_id=None,
                matching_confidence=None,
                matched_at=None,
                additional_info=None,
            )
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        members = await repository.get_pending_members(parliamentary_group_id=1)

        # Assert
        assert len(members) == 1
        assert members[0].parliamentary_group_id == 1
        mock_session.execute.assert_called_once()

    async def test_get_matched_members(self, repository, mock_session) -> None:
        """Test getting matched members."""
        mock_rows = [
            MagicMock(
                id=1,
                parliamentary_group_id=1,
                extracted_name="山田太郎",
                source_url="https://example.com",
                extracted_role="団長",
                extracted_party_name="自民党",
                extracted_district="東京1区",
                extracted_at=datetime.now(),
                matching_status="matched",
                matched_politician_id=1,
                matching_confidence=0.95,
                matched_at=datetime.now(),
                additional_info=None,
            )
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        members = await repository.get_matched_members()

        # Assert
        assert len(members) == 1
        assert members[0].matching_status == "matched"
        assert members[0].matched_politician_id == 1
        mock_session.execute.assert_called_once()

    async def test_get_matched_members_with_min_confidence(
        self, repository, mock_session
    ) -> None:
        """Test getting matched members with minimum confidence."""
        mock_rows = [
            MagicMock(
                id=1,
                parliamentary_group_id=1,
                extracted_name="山田太郎",
                source_url="https://example.com",
                extracted_role="団長",
                extracted_party_name="自民党",
                extracted_district="東京1区",
                extracted_at=datetime.now(),
                matching_status="matched",
                matched_politician_id=1,
                matching_confidence=0.95,
                matched_at=datetime.now(),
                additional_info=None,
            )
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        members = await repository.get_matched_members(min_confidence=0.8)

        # Assert
        assert len(members) == 1
        assert members[0].matching_confidence >= 0.8
        mock_session.execute.assert_called_once()

    async def test_update_matching_result(self, repository, mock_session) -> None:
        """Test updating matching result."""
        # Mock the update execution
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock get_by_id to return updated member
        updated_member = create_extracted_parliamentary_group_member(
            id=1,
            matching_status="matched",
            matched_politician_id=1,
            matching_confidence=0.95,
            matched_at=datetime.now(),
        )

        with patch.object(repository, "get_by_id", return_value=updated_member):
            # Execute
            result = await repository.update_matching_result(
                member_id=1, politician_id=1, confidence=0.95, status="matched"
            )

            # Assert
            assert result is not None
            assert result.matching_status == "matched"
            assert result.matched_politician_id == 1
            assert result.matching_confidence == 0.95
            mock_session.execute.assert_called_once()
            mock_session.flush.assert_called_once()

    async def test_update_matching_result_with_custom_timestamp(
        self, repository, mock_session
    ) -> None:
        """Test updating matching result with custom matched_at timestamp."""
        # Mock the update execution
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        custom_time = datetime(2023, 1, 15, 10, 30, 0)
        updated_member = create_extracted_parliamentary_group_member(
            id=1,
            matching_status="matched",
            matched_politician_id=1,
            matching_confidence=0.95,
            matched_at=custom_time,
        )

        with patch.object(repository, "get_by_id", return_value=updated_member):
            # Execute with custom matched_at
            result = await repository.update_matching_result(
                member_id=1,
                politician_id=1,
                confidence=0.95,
                status="matched",
                matched_at=custom_time,
            )

            # Assert
            assert result is not None
            assert result.matched_at == custom_time
            mock_session.execute.assert_called_once()
            mock_session.flush.assert_called_once()

    async def test_update_matching_result_with_none_values(
        self, repository, mock_session
    ) -> None:
        """Test updating matching result with None politician_id."""
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        updated_member = create_extracted_parliamentary_group_member(
            id=1,
            matching_status="no_match",
            matched_politician_id=None,
            matching_confidence=None,
        )

        with patch.object(repository, "get_by_id", return_value=updated_member):
            result = await repository.update_matching_result(
                member_id=1, politician_id=None, confidence=None, status="no_match"
            )

            assert result is not None
            assert result.matching_status == "no_match"
            assert result.matched_politician_id is None

    async def test_get_by_parliamentary_group(self, repository, mock_session) -> None:
        """Test getting members by parliamentary group."""
        mock_rows = [
            MagicMock(
                id=1,
                parliamentary_group_id=1,
                extracted_name="山田太郎",
                source_url="https://example.com",
                extracted_role="団長",
                extracted_party_name="自民党",
                extracted_district="東京1区",
                extracted_at=datetime.now(),
                matching_status="pending",
                matched_politician_id=None,
                matching_confidence=None,
                matched_at=None,
                additional_info=None,
            ),
            MagicMock(
                id=2,
                parliamentary_group_id=1,
                extracted_name="田中花子",
                source_url="https://example.com",
                extracted_role="幹事長",
                extracted_party_name="自民党",
                extracted_district="東京2区",
                extracted_at=datetime.now(),
                matching_status="matched",
                matched_politician_id=2,
                matching_confidence=0.85,
                matched_at=datetime.now(),
                additional_info=None,
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        members = await repository.get_by_parliamentary_group(1)

        # Assert
        assert len(members) == 2
        assert all(m.parliamentary_group_id == 1 for m in members)
        mock_session.execute.assert_called_once()

    async def test_get_extraction_summary(self, repository, mock_session) -> None:
        """Test getting extraction summary."""
        mock_rows = [
            MagicMock(matching_status="pending", count=2),
            MagicMock(matching_status="matched", count=3),
            MagicMock(matching_status="no_match", count=1),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Execute
        summary = await repository.get_extraction_summary()

        # Assert
        assert summary["total"] == 6
        assert summary["pending"] == 2
        assert summary["matched"] == 3
        assert summary["no_match"] == 1
        mock_session.execute.assert_called_once()

    async def test_bulk_create(self, repository, mock_session) -> None:
        """Test bulk creating members."""
        members = [
            create_extracted_parliamentary_group_member(
                id=None, extracted_name="山田太郎"
            ),
            create_extracted_parliamentary_group_member(
                id=None, extracted_name="田中花子"
            ),
        ]

        # Mock the insert execution
        mock_row1 = MagicMock(
            id=1,
            parliamentary_group_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_party_name="自由民主党",
            extracted_district="東京1区",
            extracted_at=datetime.now(),
            matching_status="pending",
            matched_politician_id=None,
            matching_confidence=None,
            matched_at=None,
            additional_info=None,
        )

        mock_row2 = MagicMock(
            id=2,
            parliamentary_group_id=1,
            extracted_name="田中花子",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_party_name="自由民主党",
            extracted_district="東京1区",
            extracted_at=datetime.now(),
            matching_status="pending",
            matched_politician_id=None,
            matching_confidence=None,
            matched_at=None,
            additional_info=None,
        )

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = mock_row1
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = mock_row2

        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_session.commit = AsyncMock()

        # Execute
        created = await repository.bulk_create(members)

        # Assert
        assert len(created) == 2
        assert created[0].id == 1
        assert created[0].extracted_name == "山田太郎"
        assert created[1].id == 2
        assert created[1].extracted_name == "田中花子"
        assert mock_session.execute.call_count == 2
        mock_session.flush.assert_called_once()

    async def test_bulk_create_skips_duplicates(self, repository, mock_session) -> None:
        """Test bulk_create skips duplicates using ON CONFLICT."""
        members = [
            create_extracted_parliamentary_group_member(
                id=None, extracted_name="山田太郎"
            ),
            create_extracted_parliamentary_group_member(
                id=None, extracted_name="田中花子"
            ),
        ]

        # First insert succeeds, second is duplicate (returns None)
        mock_row1 = MagicMock(
            id=1,
            parliamentary_group_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_party_name="自由民主党",
            extracted_district="東京1区",
            extracted_at=datetime.now(),
            matching_status="pending",
            matched_politician_id=None,
            matching_confidence=None,
            matched_at=None,
            additional_info=None,
        )

        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = mock_row1
        mock_result2 = MagicMock()
        mock_result2.fetchone.return_value = None  # Duplicate - ON CONFLICT DO NOTHING

        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        # Execute
        created = await repository.bulk_create(members)

        # Assert - only first member was created
        assert len(created) == 1
        assert created[0].id == 1
        assert created[0].extracted_name == "山田太郎"
        assert mock_session.execute.call_count == 2
        mock_session.flush.assert_called_once()
