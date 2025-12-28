"""Tests for Minutes entity."""

from datetime import datetime

from src.domain.entities.minutes import Minutes


class TestMinutes:
    """Test cases for Minutes entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        minutes = Minutes(meeting_id=1)

        assert minutes.meeting_id == 1
        assert minutes.url is None
        assert minutes.processed_at is None
        assert minutes.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        processed_time = datetime(2024, 1, 15, 10, 30, 0)
        minutes = Minutes(
            id=10,
            meeting_id=5,
            url="https://example.com/minutes/123.pdf",
            processed_at=processed_time,
        )

        assert minutes.id == 10
        assert minutes.meeting_id == 5
        assert minutes.url == "https://example.com/minutes/123.pdf"
        assert minutes.processed_at == processed_time

    def test_str_representation(self) -> None:
        """Test string representation."""
        minutes = Minutes(meeting_id=42)
        assert str(minutes) == "Minutes for meeting #42"

        minutes_with_id = Minutes(id=10, meeting_id=100)
        assert str(minutes_with_id) == "Minutes for meeting #100"

    def test_various_meeting_ids(self) -> None:
        """Test various meeting IDs."""
        meeting_ids = [1, 10, 100, 1000, 9999]

        for meeting_id in meeting_ids:
            minutes = Minutes(meeting_id=meeting_id)
            assert minutes.meeting_id == meeting_id
            assert str(minutes) == f"Minutes for meeting #{meeting_id}"

    def test_various_url_formats(self) -> None:
        """Test various URL formats."""
        urls = [
            "https://example.com/minutes/123.pdf",
            "http://city.jp/council/minutes/2024-01.pdf",
            "https://www.prefecture.go.jp/minutes.html",
            None,
        ]

        for url in urls:
            minutes = Minutes(meeting_id=1, url=url)
            assert minutes.url == url

    def test_processed_at_datetime(self) -> None:
        """Test processed_at with various datetime values."""
        # With datetime
        dt1 = datetime(2024, 1, 1, 0, 0, 0)
        minutes1 = Minutes(meeting_id=1, processed_at=dt1)
        assert minutes1.processed_at == dt1

        # With different datetime
        dt2 = datetime(2024, 12, 31, 23, 59, 59)
        minutes2 = Minutes(meeting_id=2, processed_at=dt2)
        assert minutes2.processed_at == dt2

        # Without processed_at
        minutes3 = Minutes(meeting_id=3)
        assert minutes3.processed_at is None

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Minutes properly inherits from BaseEntity."""
        minutes = Minutes(id=42, meeting_id=1)

        # Check that id is properly set through BaseEntity
        assert minutes.id == 42

        # Create without id
        minutes_no_id = Minutes(meeting_id=1)
        assert minutes_no_id.id is None

    def test_complex_minutes_scenarios(self) -> None:
        """Test complex real-world minutes scenarios."""
        # Newly created minutes (not processed yet)
        new_minutes = Minutes(
            meeting_id=1,
            url="https://example.com/minutes/new.pdf",
            processed_at=None,
        )
        assert new_minutes.processed_at is None
        assert new_minutes.url is not None

        # Processed minutes
        processed_minutes = Minutes(
            id=1,
            meeting_id=2,
            url="https://example.com/minutes/processed.pdf",
            processed_at=datetime(2024, 1, 15, 10, 30, 0),
        )
        assert processed_minutes.processed_at is not None
        assert str(processed_minutes) == "Minutes for meeting #2"

        # Minutes without URL (manual input)
        manual_minutes = Minutes(
            id=2,
            meeting_id=3,
            url=None,
            processed_at=datetime(2024, 1, 16, 14, 0, 0),
        )
        assert manual_minutes.url is None
        assert manual_minutes.processed_at is not None

    def test_edge_cases(self) -> None:
        """Test edge cases for Minutes entity."""
        # Empty string URL
        minutes_empty = Minutes(
            meeting_id=1,
            url="",
        )
        assert minutes_empty.url == ""

        # Very long URL
        long_url = "https://example.com/" + "a" * 500
        minutes_long_url = Minutes(meeting_id=1, url=long_url)
        assert minutes_long_url.url == long_url

        # Large meeting ID
        minutes_large_id = Minutes(meeting_id=999999)
        assert minutes_large_id.meeting_id == 999999

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        minutes = Minutes(
            meeting_id=1,
            url=None,
            processed_at=None,
        )

        assert minutes.url is None
        assert minutes.processed_at is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        minutes1 = Minutes(meeting_id=1)
        assert minutes1.id is None

        # With ID
        minutes2 = Minutes(meeting_id=1, id=100)
        assert minutes2.id == 100

        # ID can be any integer
        minutes3 = Minutes(meeting_id=1, id=999999)
        assert minutes3.id == 999999

    def test_datetime_precision(self) -> None:
        """Test datetime with various precision levels."""
        # With microseconds
        dt_micro = datetime(2024, 1, 15, 10, 30, 45, 123456)
        minutes_micro = Minutes(meeting_id=1, processed_at=dt_micro)
        assert minutes_micro.processed_at == dt_micro

        # Without microseconds
        dt_no_micro = datetime(2024, 1, 15, 10, 30, 45)
        minutes_no_micro = Minutes(meeting_id=2, processed_at=dt_no_micro)
        assert minutes_no_micro.processed_at == dt_no_micro

    def test_url_with_special_characters(self) -> None:
        """Test URLs with special characters."""
        urls_special = [
            "https://example.com/minutes/議事録.pdf",
            "https://example.com/minutes/2024年1月.pdf",
            "https://example.com/minutes/file%20name.pdf",
            "https://example.com/minutes/file?query=value&param=123",
        ]

        for url in urls_special:
            minutes = Minutes(meeting_id=1, url=url)
            assert minutes.url == url
