"""Tests for ExtractedParliamentaryGroupMember entity."""

from datetime import datetime

from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from tests.fixtures.entity_factories import create_extracted_parliamentary_group_member


class TestExtractedParliamentaryGroupMember:
    """Test cases for ExtractedParliamentaryGroupMember entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/group-members",
        )

        assert member.parliamentary_group_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/group-members"
        assert member.extracted_role is None
        assert member.extracted_party_name is None
        assert member.extracted_district is None
        assert member.matched_politician_id is None
        assert member.matching_confidence is None
        assert member.matching_status == "pending"
        assert member.matched_at is None
        assert member.additional_info is None
        assert isinstance(member.extracted_at, datetime)

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        extracted_at = datetime(2023, 1, 1, 12, 0, 0)
        matched_at = datetime(2023, 1, 2, 12, 0, 0)

        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/group-members",
            extracted_role="団長",
            extracted_party_name="自由民主党",
            extracted_district="東京1区",
            extracted_at=extracted_at,
            matched_politician_id=10,
            matching_confidence=0.95,
            matching_status="matched",
            matched_at=matched_at,
            additional_info='{"note": "追加情報"}',
        )

        assert member.id == 1
        assert member.parliamentary_group_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/group-members"
        assert member.extracted_role == "団長"
        assert member.extracted_party_name == "自由民主党"
        assert member.extracted_district == "東京1区"
        assert member.extracted_at == extracted_at
        assert member.matched_politician_id == 10
        assert member.matching_confidence == 0.95
        assert member.matching_status == "matched"
        assert member.matched_at == matched_at
        assert member.additional_info == '{"note": "追加情報"}'

    def test_is_matched_method(self) -> None:
        """Test is_matched method with different statuses."""
        # Test with matched status
        matched_member = create_extracted_parliamentary_group_member(
            matching_status="matched"
        )
        assert matched_member.is_matched() is True

        # Test with pending status
        pending_member = create_extracted_parliamentary_group_member(
            matching_status="pending"
        )
        assert pending_member.is_matched() is False

        # Test with no_match status
        no_match_member = create_extracted_parliamentary_group_member(
            matching_status="no_match"
        )
        assert no_match_member.is_matched() is False

    def test_is_no_match_method(self) -> None:
        """Test is_no_match method with different statuses."""
        # Test with no_match status
        no_match_member = create_extracted_parliamentary_group_member(
            matching_status="no_match"
        )
        assert no_match_member.is_no_match() is True

        # Test with matched status
        matched_member = create_extracted_parliamentary_group_member(
            matching_status="matched"
        )
        assert matched_member.is_no_match() is False

        # Test with pending status
        pending_member = create_extracted_parliamentary_group_member(
            matching_status="pending"
        )
        assert pending_member.is_no_match() is False

    def test_is_pending_method(self) -> None:
        """Test is_pending method with different statuses."""
        # Test with pending status
        pending_member = create_extracted_parliamentary_group_member(
            matching_status="pending"
        )
        assert pending_member.is_pending() is True

        # Test with matched status
        matched_member = create_extracted_parliamentary_group_member(
            matching_status="matched"
        )
        assert matched_member.is_pending() is False

        # Test with no_match status
        no_match_member = create_extracted_parliamentary_group_member(
            matching_status="no_match"
        )
        assert no_match_member.is_pending() is False

    def test_str_representation(self) -> None:
        """Test string representation of the entity."""
        member = create_extracted_parliamentary_group_member(
            extracted_name="鈴木一郎", matching_status="matched"
        )

        expected = "ExtractedParliamentaryGroupMember(name=鈴木一郎, status=matched)"
        assert str(member) == expected

    def test_different_matching_statuses(self) -> None:
        """Test entity with different matching statuses."""
        statuses = ["pending", "matched", "no_match"]

        for status in statuses:
            member = create_extracted_parliamentary_group_member(matching_status=status)
            assert member.matching_status == status

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        member = create_extracted_parliamentary_group_member()

        assert member.id == 1
        assert member.parliamentary_group_id == 1
        assert member.extracted_name == "山田太郎"
        assert member.source_url == "https://example.com/group-members"
        assert member.extracted_role == "団長"
        assert member.extracted_party_name == "自由民主党"
        assert member.extracted_district == "東京1区"
        assert member.matching_status == "pending"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        member = create_extracted_parliamentary_group_member(
            id=99,
            extracted_name="佐藤花子",
            extracted_role="幹事長",
            matching_status="matched",
            matching_confidence=0.85,
            matched_politician_id=50,
        )

        assert member.id == 99
        assert member.extracted_name == "佐藤花子"
        assert member.extracted_role == "幹事長"
        assert member.matching_status == "matched"
        assert member.matching_confidence == 0.85
        assert member.matched_politician_id == 50
        # Verify defaults are still applied
        assert member.parliamentary_group_id == 1
        assert member.source_url == "https://example.com/group-members"

    def test_extracted_at_default_value(self) -> None:
        """Test that extracted_at is set to current time by default."""
        before = datetime.now()
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="Test",
            source_url="https://example.com",
        )
        after = datetime.now()

        assert before <= member.extracted_at <= after

    def test_matched_member_with_high_confidence(self) -> None:
        """Test a successfully matched member with high confidence."""
        member = create_extracted_parliamentary_group_member(
            matching_status="matched",
            matching_confidence=0.95,
            matched_politician_id=100,
            matched_at=datetime(2023, 1, 15, 10, 30, 0),
        )

        assert member.is_matched() is True
        assert member.is_no_match() is False
        assert member.is_pending() is False
        assert member.matching_confidence == 0.95
        assert member.matched_politician_id == 100
        assert member.matched_at == datetime(2023, 1, 15, 10, 30, 0)

    def test_member_with_no_match(self) -> None:
        """Test a member with no match after matching execution."""
        member = create_extracted_parliamentary_group_member(
            matching_status="no_match",
            matching_confidence=0.3,
            matched_politician_id=None,
        )

        assert member.is_matched() is False
        assert member.is_no_match() is True
        assert member.is_pending() is False
        assert member.matching_confidence == 0.3
        assert member.matched_politician_id is None

    def test_member_with_district_information(self) -> None:
        """Test member with district information."""
        member = create_extracted_parliamentary_group_member(
            extracted_district="大阪3区"
        )

        assert member.extracted_district == "大阪3区"

    def test_member_with_additional_info(self) -> None:
        """Test member with additional info field."""
        additional_info = '{"email": "test@example.com", "phone": "03-1234-5678"}'
        member = create_extracted_parliamentary_group_member(
            additional_info=additional_info
        )

        assert member.additional_info == additional_info
