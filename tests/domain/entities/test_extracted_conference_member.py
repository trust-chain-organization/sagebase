"""Tests for ExtractedConferenceMember entity."""

from datetime import datetime

from tests.fixtures.entity_factories import create_extracted_conference_member

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember


class TestExtractedConferenceMember:
    """Test cases for ExtractedConferenceMember entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        member = ExtractedConferenceMember(
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
        )

        assert member.conference_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/members"
        assert member.extracted_role is None
        assert member.extracted_party_name is None
        assert member.matched_politician_id is None
        assert member.matching_confidence is None
        assert member.matching_status == "pending"
        assert member.matched_at is None
        assert member.additional_data is None
        assert isinstance(member.extracted_at, datetime)

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        extracted_at = datetime(2023, 1, 1, 12, 0, 0)
        matched_at = datetime(2023, 1, 2, 12, 0, 0)

        member = ExtractedConferenceMember(
            id=1,
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="議員",
            extracted_party_name="自由民主党",
            extracted_at=extracted_at,
            matched_politician_id=10,
            matching_confidence=0.95,
            matching_status="matched",
            matched_at=matched_at,
            additional_data='{"district": "東京1区"}',
        )

        assert member.id == 1
        assert member.conference_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/members"
        assert member.extracted_role == "議員"
        assert member.extracted_party_name == "自由民主党"
        assert member.extracted_at == extracted_at
        assert member.matched_politician_id == 10
        assert member.matching_confidence == 0.95
        assert member.matching_status == "matched"
        assert member.matched_at == matched_at
        assert member.additional_data == '{"district": "東京1区"}'

    def test_is_matched_method(self) -> None:
        """Test is_matched method with different statuses."""
        # Test with matched status
        matched_member = create_extracted_conference_member(matching_status="matched")
        assert matched_member.is_matched() is True

        # Test with pending status
        pending_member = create_extracted_conference_member(matching_status="pending")
        assert pending_member.is_matched() is False

        # Test with needs_review status
        review_member = create_extracted_conference_member(
            matching_status="needs_review"
        )
        assert review_member.is_matched() is False

        # Test with no_match status
        no_match_member = create_extracted_conference_member(matching_status="no_match")
        assert no_match_member.is_matched() is False

    def test_needs_review_method(self) -> None:
        """Test needs_review method with different statuses."""
        # Test with needs_review status
        review_member = create_extracted_conference_member(
            matching_status="needs_review"
        )
        assert review_member.needs_review() is True

        # Test with matched status
        matched_member = create_extracted_conference_member(matching_status="matched")
        assert matched_member.needs_review() is False

        # Test with pending status
        pending_member = create_extracted_conference_member(matching_status="pending")
        assert pending_member.needs_review() is False

        # Test with no_match status
        no_match_member = create_extracted_conference_member(matching_status="no_match")
        assert no_match_member.needs_review() is False

    def test_str_representation(self) -> None:
        """Test string representation of the entity."""
        member = create_extracted_conference_member(
            extracted_name="鈴木一郎", matching_status="matched"
        )

        expected = "ExtractedConferenceMember(name=鈴木一郎, status=matched)"
        assert str(member) == expected

    def test_different_matching_statuses(self) -> None:
        """Test entity with different matching statuses."""
        statuses = ["pending", "matched", "needs_review", "no_match"]

        for status in statuses:
            member = create_extracted_conference_member(matching_status=status)
            assert member.matching_status == status

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        member = create_extracted_conference_member()

        assert member.id == 1
        assert member.conference_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/members"
        assert member.extracted_role == "議員"
        assert member.extracted_party_name == "自由民主党"
        assert member.matching_status == "pending"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        member = create_extracted_conference_member(
            id=99,
            extracted_name="佐藤花子",
            matching_status="matched",
            matching_confidence=0.85,
            matched_politician_id=50,
        )

        assert member.id == 99
        assert member.extracted_name == "佐藤花子"
        assert member.matching_status == "matched"
        assert member.matching_confidence == 0.85
        assert member.matched_politician_id == 50
        # Verify defaults are still applied
        assert member.conference_id == 1
        assert member.source_url == "https://example.com/members"

    def test_extracted_at_default_value(self) -> None:
        """Test that extracted_at is set to current time by default."""
        before = datetime.now()
        member = ExtractedConferenceMember(
            conference_id=1, extracted_name="Test", source_url="https://example.com"
        )
        after = datetime.now()

        assert before <= member.extracted_at <= after

    def test_matched_member_with_high_confidence(self) -> None:
        """Test a successfully matched member with high confidence."""
        member = create_extracted_conference_member(
            matching_status="matched",
            matching_confidence=0.95,
            matched_politician_id=100,
            matched_at=datetime(2023, 1, 15, 10, 30, 0),
        )

        assert member.is_matched() is True
        assert member.needs_review() is False
        assert member.matching_confidence == 0.95
        assert member.matched_politician_id == 100
        assert member.matched_at == datetime(2023, 1, 15, 10, 30, 0)

    def test_member_needing_review_with_medium_confidence(self) -> None:
        """Test a member that needs manual review."""
        member = create_extracted_conference_member(
            matching_status="needs_review",
            matching_confidence=0.6,
            matched_politician_id=None,
        )

        assert member.is_matched() is False
        assert member.needs_review() is True
        assert member.matching_confidence == 0.6
        assert member.matched_politician_id is None
