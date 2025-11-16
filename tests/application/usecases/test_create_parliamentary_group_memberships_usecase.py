"""Tests for CreateParliamentaryGroupMembershipsUseCase."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.create_parliamentary_group_memberships_usecase import (
    CreateParliamentaryGroupMembershipsUseCase,
)
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)


class TestCreateParliamentaryGroupMembershipsUseCase:
    """Test cases for CreateParliamentaryGroupMembershipsUseCase."""

    @pytest.fixture
    def mock_member_repo(self):
        """Create mock member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_membership_repo(self):
        """Create mock membership repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_member_repo, mock_membership_repo):
        """Create CreateParliamentaryGroupMembershipsUseCase instance."""
        return CreateParliamentaryGroupMembershipsUseCase(
            member_repository=mock_member_repo,
            membership_repository=mock_membership_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_successful_creation(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test successful creation of memberships."""
        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        member1 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            extracted_role="団長",
            id=1,
        )
        member2 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="佐藤花子",
            source_url="http://example.com",
            matched_politician_id=200,
            matching_confidence=0.85,
            matching_status="matched",
            extracted_role="幹事長",
            id=2,
        )

        mock_member_repo.get_matched_members.return_value = [member1, member2]
        mock_membership_repo.create_membership.side_effect = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=100,
                parliamentary_group_id=1,
                start_date=date.today(),
                role="団長",
            ),
            ParliamentaryGroupMembership(
                id=2,
                politician_id=200,
                parliamentary_group_id=1,
                start_date=date.today(),
                role="幹事長",
            ),
        ]

        # Act
        result = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert result["created_count"] == 2
        assert result["skipped_count"] == 0
        assert len(result["created_memberships"]) == 2
        assert result["created_memberships"][0]["politician_id"] == 100
        assert result["created_memberships"][0]["role"] == "団長"
        assert result["created_memberships"][1]["politician_id"] == 200
        assert result["created_memberships"][1]["role"] == "幹事長"

    @pytest.mark.asyncio
    async def test_execute_skip_members_without_politician_id(
        self, use_case, mock_member_repo
    ):
        """Test skipping members without matched_politician_id."""
        # Arrange
        member1 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=None,  # No match
            matching_confidence=0.3,
            matching_status="no_match",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member1]

        # Act
        result = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert result["created_count"] == 0
        assert result["skipped_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_custom_start_date(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test creation with custom start date."""
        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        custom_date = date(2024, 1, 1)
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member]
        mock_membership_repo.create_membership.return_value = (
            ParliamentaryGroupMembership(
                id=1,
                politician_id=100,
                parliamentary_group_id=1,
                start_date=custom_date,
            )
        )

        # Act
        await use_case.execute(parliamentary_group_id=1, start_date=custom_date)

        # Assert
        mock_membership_repo.create_membership.assert_called_once()
        call_args = mock_membership_repo.create_membership.call_args
        assert call_args.kwargs["start_date"] == custom_date

    @pytest.mark.asyncio
    async def test_execute_handle_creation_error(
        self, use_case, mock_member_repo, mock_membership_repo, capsys
    ):
        """Test handling of membership creation errors."""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member]
        mock_membership_repo.create_membership.side_effect = Exception("DB Error")

        # Act
        result = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert result["created_count"] == 0
        assert result["skipped_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_saves_user_id_on_membership_creation(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test that user_id is saved when creating memberships."""
        from uuid import uuid4

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        test_user_id = uuid4()
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member]

        # Mock to capture the call arguments
        created_membership = ParliamentaryGroupMembership(
            id=1,
            politician_id=100,
            parliamentary_group_id=1,
            start_date=date.today(),
            created_by_user_id=test_user_id,
        )
        mock_membership_repo.create_membership.return_value = created_membership

        # Act
        result = await use_case.execute(parliamentary_group_id=1, user_id=test_user_id)

        # Assert
        assert result["created_count"] == 1
        call_args = mock_membership_repo.create_membership.call_args
        assert call_args.kwargs["created_by_user_id"] == test_user_id

    @pytest.mark.asyncio
    async def test_execute_without_user_id(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test that membership creation works when user_id is None."""
        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member]

        created_membership = ParliamentaryGroupMembership(
            id=1,
            politician_id=100,
            parliamentary_group_id=1,
            start_date=date.today(),
            created_by_user_id=None,
        )
        mock_membership_repo.create_membership.return_value = created_membership

        # Act
        result = await use_case.execute(
            parliamentary_group_id=1,
            user_id=None,  # Explicitly None
        )

        # Assert
        assert result["created_count"] == 1
        call_args = mock_membership_repo.create_membership.call_args
        assert call_args.kwargs["created_by_user_id"] is None

    @pytest.mark.asyncio
    async def test_execute_propagates_user_id_through_all_memberships(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test that user_id is propagated to all created memberships."""
        from uuid import uuid4

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        test_user_id = uuid4()
        members = [
            ExtractedParliamentaryGroupMember(
                parliamentary_group_id=1,
                extracted_name=f"議員{i}",
                source_url="http://example.com",
                matched_politician_id=100 + i,
                matching_confidence=0.9,
                matching_status="matched",
                id=i,
            )
            for i in range(1, 4)
        ]

        mock_member_repo.get_matched_members.return_value = members

        # Mock multiple creations
        mock_membership_repo.create_membership.side_effect = [
            ParliamentaryGroupMembership(
                id=i,
                politician_id=100 + i,
                parliamentary_group_id=1,
                start_date=date.today(),
                created_by_user_id=test_user_id,
            )
            for i in range(1, 4)
        ]

        # Act
        result = await use_case.execute(parliamentary_group_id=1, user_id=test_user_id)

        # Assert
        assert result["created_count"] == 3
        assert mock_membership_repo.create_membership.call_count == 3

        # Verify all calls had user_id
        for call in mock_membership_repo.create_membership.call_args_list:
            assert call.kwargs["created_by_user_id"] == test_user_id
