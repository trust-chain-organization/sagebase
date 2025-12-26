"""Tests for ExtractedPolitician entity."""

from datetime import datetime

from tests.fixtures.entity_factories import create_extracted_politician

from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)


class TestExtractedPolitician:
    """Test cases for ExtractedPolitician entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        politician = PoliticianPartyExtractedPolitician(
            name="山田太郎",
        )

        assert politician.name == "山田太郎"
        assert politician.party_id is None
        assert politician.district is None
        assert politician.profile_url is None
        assert politician.status == "pending"
        assert isinstance(politician.extracted_at, datetime)
        assert politician.reviewed_at is None
        assert politician.reviewer_id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        extracted_at = datetime(2023, 1, 1, 12, 0, 0)
        reviewed_at = datetime(2023, 1, 2, 12, 0, 0)

        politician = PoliticianPartyExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            profile_url="https://example.com/profile",
            status="approved",
            extracted_at=extracted_at,
            reviewed_at=reviewed_at,
            reviewer_id=10,
        )

        assert politician.id == 1
        assert politician.name == "山田太郎"
        assert politician.party_id == 1
        assert politician.district == "東京1区"
        assert politician.profile_url == "https://example.com/profile"
        assert politician.status == "approved"
        assert politician.extracted_at == extracted_at
        assert politician.reviewed_at == reviewed_at
        assert politician.reviewer_id == 10

    def test_is_pending_method(self) -> None:
        """Test is_pending method with different statuses."""
        # Test with pending status
        pending_politician = create_extracted_politician(status="pending")
        assert pending_politician.is_pending() is True

        # Test with reviewed status
        reviewed_politician = create_extracted_politician(status="reviewed")
        assert reviewed_politician.is_pending() is False

        # Test with approved status
        approved_politician = create_extracted_politician(status="approved")
        assert approved_politician.is_pending() is False

        # Test with rejected status
        rejected_politician = create_extracted_politician(status="rejected")
        assert rejected_politician.is_pending() is False

    def test_is_reviewed_method(self) -> None:
        """Test is_reviewed method with different statuses."""
        # Test with reviewed status
        reviewed_politician = create_extracted_politician(status="reviewed")
        assert reviewed_politician.is_reviewed() is True

        # Test with pending status
        pending_politician = create_extracted_politician(status="pending")
        assert pending_politician.is_reviewed() is False

        # Test with approved status
        approved_politician = create_extracted_politician(status="approved")
        assert approved_politician.is_reviewed() is False

        # Test with rejected status
        rejected_politician = create_extracted_politician(status="rejected")
        assert rejected_politician.is_reviewed() is False

    def test_is_approved_method(self) -> None:
        """Test is_approved method with different statuses."""
        # Test with approved status
        approved_politician = create_extracted_politician(status="approved")
        assert approved_politician.is_approved() is True

        # Test with pending status
        pending_politician = create_extracted_politician(status="pending")
        assert pending_politician.is_approved() is False

        # Test with reviewed status
        reviewed_politician = create_extracted_politician(status="reviewed")
        assert reviewed_politician.is_approved() is False

        # Test with rejected status
        rejected_politician = create_extracted_politician(status="rejected")
        assert rejected_politician.is_approved() is False

    def test_is_rejected_method(self) -> None:
        """Test is_rejected method with different statuses."""
        # Test with rejected status
        rejected_politician = create_extracted_politician(status="rejected")
        assert rejected_politician.is_rejected() is True

        # Test with pending status
        pending_politician = create_extracted_politician(status="pending")
        assert pending_politician.is_rejected() is False

        # Test with reviewed status
        reviewed_politician = create_extracted_politician(status="reviewed")
        assert reviewed_politician.is_rejected() is False

        # Test with approved status
        approved_politician = create_extracted_politician(status="approved")
        assert approved_politician.is_rejected() is False

    def test_mark_as_reviewed(self) -> None:
        """Test mark_as_reviewed method."""
        politician = create_extracted_politician(status="pending")
        assert politician.status == "pending"
        assert politician.reviewed_at is None
        assert politician.reviewer_id is None

        before = datetime.now()
        politician.mark_as_reviewed(reviewer_id=5)
        after = datetime.now()

        assert politician.status == "reviewed"
        assert politician.reviewed_at is not None
        assert before <= politician.reviewed_at <= after
        assert politician.reviewer_id == 5

    def test_approve_method(self) -> None:
        """Test approve method."""
        politician = create_extracted_politician(status="pending")
        assert politician.status == "pending"
        assert politician.reviewed_at is None
        assert politician.reviewer_id is None

        before = datetime.now()
        politician.approve(reviewer_id=3)
        after = datetime.now()

        assert politician.status == "approved"
        assert politician.reviewed_at is not None
        assert before <= politician.reviewed_at <= after
        assert politician.reviewer_id == 3

    def test_reject_method(self) -> None:
        """Test reject method."""
        politician = create_extracted_politician(status="pending")
        assert politician.status == "pending"
        assert politician.reviewed_at is None
        assert politician.reviewer_id is None

        before = datetime.now()
        politician.reject(reviewer_id=7)
        after = datetime.now()

        assert politician.status == "rejected"
        assert politician.reviewed_at is not None
        assert before <= politician.reviewed_at <= after
        assert politician.reviewer_id == 7

    def test_str_representation(self) -> None:
        """Test string representation of the entity."""
        politician = create_extracted_politician(name="鈴木一郎", status="approved")

        expected = "PoliticianPartyExtractedPolitician(name=鈴木一郎, status=approved)"
        assert str(politician) == expected

    def test_different_statuses(self) -> None:
        """Test entity with different statuses."""
        statuses = ["pending", "reviewed", "approved", "rejected"]

        for status in statuses:
            politician = create_extracted_politician(status=status)
            assert politician.status == status

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        politician = create_extracted_politician()

        assert politician.id == 1
        assert politician.name == "山田太郎"
        assert politician.party_id == 1
        assert politician.district == "東京1区"
        assert politician.profile_url == "https://example.com/profile"
        assert politician.status == "pending"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        politician = create_extracted_politician(
            id=99,
            name="佐藤花子",
            status="approved",
            party_id=3,
            district="大阪1区",
        )

        assert politician.id == 99
        assert politician.name == "佐藤花子"
        assert politician.status == "approved"
        assert politician.party_id == 3
        assert politician.district == "大阪1区"
        # Verify defaults are still applied
        assert politician.profile_url == "https://example.com/profile"

    def test_extracted_at_default_value(self) -> None:
        """Test that extracted_at is set to current time by default."""
        before = datetime.now()
        politician = PoliticianPartyExtractedPolitician(name="Test")
        after = datetime.now()

        assert before <= politician.extracted_at <= after

    def test_politician_with_party_affiliation(self) -> None:
        """Test a politician with party affiliation."""
        politician = create_extracted_politician(
            name="田中次郎",
            party_id=2,
            district="京都2区",
        )

        assert politician.name == "田中次郎"
        assert politician.party_id == 2
        assert politician.district == "京都2区"

    def test_politician_without_party_affiliation(self) -> None:
        """Test a politician without party affiliation (independent)."""
        politician = create_extracted_politician(
            name="独立太郎",
            party_id=None,
            district="無所属",
        )

        assert politician.name == "独立太郎"
        assert politician.party_id is None
        assert politician.district == "無所属"

    def test_status_change_workflow(self) -> None:
        """Test the workflow of status changes."""
        politician = create_extracted_politician(status="pending")

        # Initially pending
        assert politician.is_pending() is True
        assert politician.is_reviewed() is False
        assert politician.is_approved() is False
        assert politician.is_rejected() is False

        # Mark as reviewed
        politician.mark_as_reviewed(reviewer_id=1)
        assert politician.is_pending() is False
        assert politician.is_reviewed() is True
        assert politician.is_approved() is False
        assert politician.is_rejected() is False

        # Approve
        politician.approve(reviewer_id=1)
        assert politician.is_pending() is False
        assert politician.is_reviewed() is False
        assert politician.is_approved() is True
        assert politician.is_rejected() is False
