"""Tests for PoliticianPartyExtractedPolitician entity."""

from datetime import datetime
from unittest.mock import patch

from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)


class TestPoliticianPartyExtractedPolitician:
    """Test cases for PoliticianPartyExtractedPolitician entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        extracted = PoliticianPartyExtractedPolitician(name="山田太郎")

        assert extracted.name == "山田太郎"
        assert extracted.party_id is None
        assert extracted.district is None
        assert extracted.profile_url is None
        assert extracted.status == "pending"
        assert extracted.extracted_at is not None
        assert extracted.reviewed_at is None
        assert extracted.reviewer_id is None
        assert extracted.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        extracted_time = datetime(2024, 1, 15, 10, 0, 0)
        reviewed_time = datetime(2024, 1, 16, 14, 30, 0)

        extracted = PoliticianPartyExtractedPolitician(
            id=10,
            name="田中花子",
            party_id=5,
            district="東京1区",
            profile_url="https://example.com/tanaka",
            status="approved",
            extracted_at=extracted_time,
            reviewed_at=reviewed_time,
            reviewer_id=7,
        )

        assert extracted.id == 10
        assert extracted.name == "田中花子"
        assert extracted.party_id == 5
        assert extracted.district == "東京1区"
        assert extracted.profile_url == "https://example.com/tanaka"
        assert extracted.status == "approved"
        assert extracted.extracted_at == extracted_time
        assert extracted.reviewed_at == reviewed_time
        assert extracted.reviewer_id == 7

    def test_str_representation(self) -> None:
        """Test string representation."""
        extracted = PoliticianPartyExtractedPolitician(
            name="佐藤一郎",
            status="pending",
        )
        expected = "PoliticianPartyExtractedPolitician(name=佐藤一郎, status=pending)"
        assert str(extracted) == expected

    def test_is_pending_status(self) -> None:
        """Test is_pending method."""
        pending = PoliticianPartyExtractedPolitician(
            name="Test",
            status="pending",
        )
        assert pending.is_pending() is True

        reviewed = PoliticianPartyExtractedPolitician(
            name="Test",
            status="reviewed",
        )
        assert reviewed.is_pending() is False

    def test_is_reviewed_status(self) -> None:
        """Test is_reviewed method."""
        reviewed = PoliticianPartyExtractedPolitician(
            name="Test",
            status="reviewed",
        )
        assert reviewed.is_reviewed() is True

        pending = PoliticianPartyExtractedPolitician(
            name="Test",
            status="pending",
        )
        assert pending.is_reviewed() is False

    def test_is_approved_status(self) -> None:
        """Test is_approved method."""
        approved = PoliticianPartyExtractedPolitician(
            name="Test",
            status="approved",
        )
        assert approved.is_approved() is True

        rejected = PoliticianPartyExtractedPolitician(
            name="Test",
            status="rejected",
        )
        assert rejected.is_approved() is False

    def test_is_rejected_status(self) -> None:
        """Test is_rejected method."""
        rejected = PoliticianPartyExtractedPolitician(
            name="Test",
            status="rejected",
        )
        assert rejected.is_rejected() is True

        approved = PoliticianPartyExtractedPolitician(
            name="Test",
            status="approved",
        )
        assert approved.is_rejected() is False

    def test_mark_as_reviewed(self) -> None:
        """Test mark_as_reviewed method."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            mock_now = datetime(2024, 1, 16, 10, 0, 0)
            mock_dt.now.return_value = mock_now

            extracted = PoliticianPartyExtractedPolitician(
                name="Test",
                status="pending",
            )

            extracted.mark_as_reviewed(reviewer_id=5)

            assert extracted.status == "reviewed"
            assert extracted.reviewed_at == mock_now
            assert extracted.reviewer_id == 5

    def test_approve(self) -> None:
        """Test approve method."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            mock_now = datetime(2024, 1, 16, 10, 0, 0)
            mock_dt.now.return_value = mock_now

            extracted = PoliticianPartyExtractedPolitician(
                name="Test",
                status="pending",
            )

            extracted.approve(reviewer_id=7)

            assert extracted.status == "approved"
            assert extracted.reviewed_at == mock_now
            assert extracted.reviewer_id == 7
            assert extracted.is_approved() is True

    def test_reject(self) -> None:
        """Test reject method."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            mock_now = datetime(2024, 1, 16, 10, 0, 0)
            mock_dt.now.return_value = mock_now

            extracted = PoliticianPartyExtractedPolitician(
                name="Test",
                status="pending",
            )

            extracted.reject(reviewer_id=9)

            assert extracted.status == "rejected"
            assert extracted.reviewed_at == mock_now
            assert extracted.reviewer_id == 9
            assert extracted.is_rejected() is True

    def test_default_extracted_at(self) -> None:
        """Test that extracted_at defaults to current datetime."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            mock_now = datetime(2024, 1, 15, 10, 0, 0)
            mock_dt.now.return_value = mock_now

            extracted = PoliticianPartyExtractedPolitician(name="Test")

            assert extracted.extracted_at == mock_now

    def test_inheritance_from_base_entity(self) -> None:
        """Test PoliticianPartyExtractedPolitician inherits from BaseEntity."""
        extracted = PoliticianPartyExtractedPolitician(
            id=42,
            name="Test",
        )

        # Check that id is properly set through BaseEntity
        assert extracted.id == 42

        # Create without id
        extracted_no_id = PoliticianPartyExtractedPolitician(name="Test")
        assert extracted_no_id.id is None

    def test_complex_workflow_scenarios(self) -> None:
        """Test complex real-world workflow scenarios."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            # Extraction time
            extraction_time = datetime(2024, 1, 15, 10, 0, 0)
            review_time = datetime(2024, 1, 16, 14, 0, 0)

            mock_dt.now.return_value = extraction_time

            # 1. Extract politician data
            extracted = PoliticianPartyExtractedPolitician(
                name="山田太郎",
                party_id=1,
                district="東京1区",
                profile_url="https://example.com/yamada",
            )
            assert extracted.is_pending() is True
            assert extracted.extracted_at == extraction_time

            # 2. Review and approve
            mock_dt.now.return_value = review_time
            extracted.approve(reviewer_id=5)
            assert extracted.is_approved() is True
            assert extracted.reviewed_at == review_time
            assert extracted.reviewer_id == 5

    def test_rejection_workflow(self) -> None:
        """Test rejection workflow."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            extraction_time = datetime(2024, 1, 15, 10, 0, 0)
            rejection_time = datetime(2024, 1, 16, 14, 0, 0)

            mock_dt.now.return_value = extraction_time

            # Extract politician data
            extracted = PoliticianPartyExtractedPolitician(
                name="Invalid Name",
                party_id=1,
            )

            # Reject
            mock_dt.now.return_value = rejection_time
            extracted.reject(reviewer_id=3)
            assert extracted.is_rejected() is True
            assert extracted.reviewed_at == rejection_time

    def test_various_statuses(self) -> None:
        """Test all possible status values."""
        statuses = ["pending", "reviewed", "approved", "rejected"]

        for status in statuses:
            extracted = PoliticianPartyExtractedPolitician(
                name="Test",
                status=status,
            )
            assert extracted.status == status

    def test_various_districts(self) -> None:
        """Test various district formats."""
        districts = [
            "東京1区",
            "大阪10区",
            "北海道比例",
            "全国比例",
            "参議院東京選挙区",
            None,
        ]

        for district in districts:
            extracted = PoliticianPartyExtractedPolitician(
                name="Test",
                district=district,
            )
            assert extracted.district == district

    def test_edge_cases(self) -> None:
        """Test edge cases for PoliticianPartyExtractedPolitician entity."""
        # Empty string fields
        extracted_empty = PoliticianPartyExtractedPolitician(
            name="Test",
            district="",
            profile_url="",
        )
        assert extracted_empty.district == ""
        assert extracted_empty.profile_url == ""

        # Very long name
        long_name = "山田" * 50
        extracted_long = PoliticianPartyExtractedPolitician(name=long_name)
        assert extracted_long.name == long_name

        # Special characters in name
        special_name = "山田・太郎（やまだ・たろう）"
        extracted_special = PoliticianPartyExtractedPolitician(name=special_name)
        assert extracted_special.name == special_name

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        extracted = PoliticianPartyExtractedPolitician(
            name="Test",
            party_id=None,
            district=None,
            profile_url=None,
            reviewed_at=None,
            reviewer_id=None,
        )

        assert extracted.party_id is None
        assert extracted.district is None
        assert extracted.profile_url is None
        assert extracted.reviewed_at is None
        assert extracted.reviewer_id is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        extracted1 = PoliticianPartyExtractedPolitician(name="Test 1")
        assert extracted1.id is None

        # With ID
        extracted2 = PoliticianPartyExtractedPolitician(name="Test 2", id=100)
        assert extracted2.id == 100

        # ID can be any integer
        extracted3 = PoliticianPartyExtractedPolitician(name="Test 3", id=999999)
        assert extracted3.id == 999999

    def test_status_check_methods_comprehensive(self) -> None:
        """Test all status check methods comprehensively."""
        # Pending status
        pending = PoliticianPartyExtractedPolitician(name="Test", status="pending")
        assert pending.is_pending() is True
        assert pending.is_reviewed() is False
        assert pending.is_approved() is False
        assert pending.is_rejected() is False

        # Reviewed status
        reviewed = PoliticianPartyExtractedPolitician(name="Test", status="reviewed")
        assert reviewed.is_pending() is False
        assert reviewed.is_reviewed() is True
        assert reviewed.is_approved() is False
        assert reviewed.is_rejected() is False

        # Approved status
        approved = PoliticianPartyExtractedPolitician(name="Test", status="approved")
        assert approved.is_pending() is False
        assert approved.is_reviewed() is False
        assert approved.is_approved() is True
        assert approved.is_rejected() is False

        # Rejected status
        rejected = PoliticianPartyExtractedPolitician(name="Test", status="rejected")
        assert rejected.is_pending() is False
        assert rejected.is_reviewed() is False
        assert rejected.is_approved() is False
        assert rejected.is_rejected() is True

    def test_multiple_reviews(self) -> None:
        """Test changing status multiple times."""
        with patch(
            "src.domain.entities.politician_party_extracted_politician.datetime"
        ) as mock_dt:
            time1 = datetime(2024, 1, 16, 10, 0, 0)
            time2 = datetime(2024, 1, 17, 10, 0, 0)
            time3 = datetime(2024, 1, 18, 10, 0, 0)

            extracted = PoliticianPartyExtractedPolitician(name="Test")

            # First review
            mock_dt.now.return_value = time1
            extracted.mark_as_reviewed(reviewer_id=1)
            assert extracted.status == "reviewed"
            assert extracted.reviewed_at == time1
            assert extracted.reviewer_id == 1

            # Approve
            mock_dt.now.return_value = time2
            extracted.approve(reviewer_id=2)
            assert extracted.status == "approved"
            assert extracted.reviewed_at == time2
            assert extracted.reviewer_id == 2

            # Reject (overriding approval - edge case)
            mock_dt.now.return_value = time3
            extracted.reject(reviewer_id=3)
            assert extracted.status == "rejected"
            assert extracted.reviewed_at == time3
            assert extracted.reviewer_id == 3

    def test_profile_url_formats(self) -> None:
        """Test various profile URL formats."""
        urls = [
            "https://example.com/profile",
            "http://party.jp/members/12345",
            "https://www.politician-site.com/",
            "https://example.com/政治家",
            None,
        ]

        for url in urls:
            extracted = PoliticianPartyExtractedPolitician(
                name="Test",
                profile_url=url,
            )
            assert extracted.profile_url == url

    def test_datetime_precision(self) -> None:
        """Test datetime fields with various precision levels."""
        # With microseconds
        dt_micro = datetime(2024, 1, 15, 10, 30, 45, 123456)
        extracted_micro = PoliticianPartyExtractedPolitician(
            name="Test",
            extracted_at=dt_micro,
        )
        assert extracted_micro.extracted_at == dt_micro

        # Without microseconds
        dt_no_micro = datetime(2024, 1, 15, 10, 30, 45)
        extracted_no_micro = PoliticianPartyExtractedPolitician(
            name="Test",
            reviewed_at=dt_no_micro,
        )
        assert extracted_no_micro.reviewed_at == dt_no_micro
