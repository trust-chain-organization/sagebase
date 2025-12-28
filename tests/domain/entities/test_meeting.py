"""Tests for Meeting entity."""

from datetime import date

from tests.fixtures.entity_factories import create_meeting

from src.domain.entities.meeting import Meeting


class TestMeeting:
    """Test cases for Meeting entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        meeting = Meeting(conference_id=1)

        assert meeting.conference_id == 1
        assert meeting.date is None
        assert meeting.url is None
        assert meeting.name is None
        assert meeting.gcs_pdf_uri is None
        assert meeting.gcs_text_uri is None
        assert meeting.attendees_mapping is None
        assert meeting.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        attendees: dict[str, str | None] = {"議員": "山田太郎", "市長": "田中一郎"}
        meeting = Meeting(
            id=10,
            conference_id=5,
            date=date(2024, 1, 15),
            url="https://example.com/meeting.pdf",
            name="令和6年第1回定例会",
            gcs_pdf_uri="gs://bucket/meeting.pdf",
            gcs_text_uri="gs://bucket/meeting.txt",
            attendees_mapping=attendees,
        )

        assert meeting.id == 10
        assert meeting.conference_id == 5
        assert meeting.date == date(2024, 1, 15)
        assert meeting.url == "https://example.com/meeting.pdf"
        assert meeting.name == "令和6年第1回定例会"
        assert meeting.gcs_pdf_uri == "gs://bucket/meeting.pdf"
        assert meeting.gcs_text_uri == "gs://bucket/meeting.txt"
        assert meeting.attendees_mapping == attendees

    def test_str_representation_with_name(self) -> None:
        """Test string representation with name."""
        meeting = Meeting(
            conference_id=1,
            name="令和6年第1回定例会",
        )
        assert str(meeting) == "令和6年第1回定例会"

        meeting_with_all = Meeting(
            id=1,
            conference_id=1,
            date=date(2024, 1, 15),
            name="令和6年第1回定例会",
        )
        assert str(meeting_with_all) == "令和6年第1回定例会"

    def test_str_representation_with_date_only(self) -> None:
        """Test string representation with date but no name."""
        meeting = Meeting(
            conference_id=1,
            date=date(2024, 1, 15),
        )
        assert str(meeting) == "Meeting on 2024-01-15"

    def test_str_representation_with_id_only(self) -> None:
        """Test string representation with ID but no name or date."""
        meeting = Meeting(
            id=42,
            conference_id=1,
        )
        assert str(meeting) == "Meeting #42"

    def test_str_representation_minimal(self) -> None:
        """Test string representation with minimal fields."""
        meeting = Meeting(conference_id=1)
        assert str(meeting) == "Meeting"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        meeting = create_meeting()

        assert meeting.id == 1
        assert meeting.conference_id == 1
        assert meeting.date == date(2023, 1, 1)
        assert meeting.name == "定例会"
        assert meeting.url == "https://example.com/meeting.pdf"
        assert meeting.gcs_pdf_uri is None
        assert meeting.gcs_text_uri is None

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        attendees: dict[str, str | None] = {"議長": "佐藤太郎"}
        meeting = create_meeting(
            id=99,
            conference_id=10,
            date=date(2024, 3, 20),
            url="https://custom.example.com/meeting.pdf",
            name="令和6年予算特別委員会",
            gcs_pdf_uri="gs://custom/meeting.pdf",
            gcs_text_uri="gs://custom/meeting.txt",
            attendees_mapping=attendees,
        )

        assert meeting.id == 99
        assert meeting.conference_id == 10
        assert meeting.date == date(2024, 3, 20)
        assert meeting.url == "https://custom.example.com/meeting.pdf"
        assert meeting.name == "令和6年予算特別委員会"
        assert meeting.gcs_pdf_uri == "gs://custom/meeting.pdf"
        assert meeting.gcs_text_uri == "gs://custom/meeting.txt"
        assert meeting.attendees_mapping == attendees

    def test_various_meeting_names(self) -> None:
        """Test various meeting names."""
        names = [
            "令和6年第1回定例会",
            "令和6年第2回臨時会",
            "令和6年予算特別委員会",
            "令和6年決算特別委員会",
            "令和6年総務委員会",
            None,
        ]

        for name in names:
            meeting = Meeting(conference_id=1, name=name)
            assert meeting.name == name

    def test_various_dates(self) -> None:
        """Test various date formats."""
        dates_list = [
            date(2024, 1, 1),
            date(2024, 12, 31),
            date(2023, 6, 15),
            date(2025, 3, 20),
            None,
        ]

        for meeting_date in dates_list:
            meeting = Meeting(conference_id=1, date=meeting_date)
            assert meeting.date == meeting_date

    def test_gcs_uri_formats(self) -> None:
        """Test various GCS URI formats."""
        test_cases = [
            (
                "gs://sagebase-bucket/meetings/2024/meeting-001.pdf",
                "gs://sagebase-bucket/meetings/2024/meeting-001.txt",
            ),
            (
                "gs://tokyo-meetings/2024-01-15.pdf",
                "gs://tokyo-meetings/2024-01-15.txt",
            ),
            (None, None),
        ]

        for pdf_uri, text_uri in test_cases:
            meeting = Meeting(
                conference_id=1,
                gcs_pdf_uri=pdf_uri,
                gcs_text_uri=text_uri,
            )
            assert meeting.gcs_pdf_uri == pdf_uri
            assert meeting.gcs_text_uri == text_uri

    def test_attendees_mapping_variations(self) -> None:
        """Test various attendees mapping formats."""
        test_cases: list[dict[str, str | None] | None] = [
            {"議長": "山田太郎", "副議長": "田中花子"},
            {"市長": "佐藤一郎"},
            {"議員": "鈴木二郎", "職員": "高橋三郎", "市民": "伊藤四郎"},
            {},
            None,
        ]

        for attendees in test_cases:
            meeting = Meeting(
                conference_id=1,
                attendees_mapping=attendees,
            )
            assert meeting.attendees_mapping == attendees

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Meeting properly inherits from BaseEntity."""
        meeting = create_meeting(id=42)

        # Check that id is properly set through BaseEntity
        assert meeting.id == 42

        # Create without id
        meeting_no_id = Meeting(conference_id=1)
        assert meeting_no_id.id is None

    def test_complex_meeting_scenarios(self) -> None:
        """Test complex real-world meeting scenarios."""
        # Regular session
        attendees1: dict[str, str | None] = {"議長": "山田太郎", "副議長": "田中花子"}
        regular_session = Meeting(
            id=1,
            conference_id=1,
            date=date(2024, 3, 1),
            url="https://example.com/session-2024-03-01.pdf",
            name="令和6年第1回定例会",
            gcs_pdf_uri="gs://meetings/2024/03/session-01.pdf",
            gcs_text_uri="gs://meetings/2024/03/session-01.txt",
            attendees_mapping=attendees1,
        )
        assert str(regular_session) == "令和6年第1回定例会"
        assert regular_session.date == date(2024, 3, 1)

        # Special committee
        attendees2: dict[str, str | None] = {"委員長": "佐藤一郎"}
        special_committee = Meeting(
            id=2,
            conference_id=2,
            date=date(2024, 3, 15),
            url="https://example.com/committee-2024-03-15.pdf",
            name="令和6年予算特別委員会",
            attendees_mapping=attendees2,
        )
        assert str(special_committee) == "令和6年予算特別委員会"

        # Minimal meeting
        minimal = Meeting(
            conference_id=3,
            date=date(2024, 4, 1),
        )
        assert str(minimal) == "Meeting on 2024-04-01"

    def test_edge_cases(self) -> None:
        """Test edge cases for Meeting entity."""
        # Empty strings
        meeting_empty = Meeting(
            conference_id=1,
            name="",
            url="",
            gcs_pdf_uri="",
            gcs_text_uri="",
        )
        # Empty string is falsy, so __str__ should check date next
        assert meeting_empty.name == ""
        # Since name is empty (falsy), should not use it in str
        assert "Meeting" in str(meeting_empty)

        # Very long name
        long_name = "令和6年" * 50
        meeting_long = Meeting(
            conference_id=1,
            name=long_name,
        )
        assert meeting_long.name == long_name

        # Special characters in name
        special_name = "令和6年第1回定例会（予算審議）"
        meeting_special = Meeting(
            conference_id=1,
            name=special_name,
        )
        assert meeting_special.name == special_name
        assert str(meeting_special) == special_name

        # Very long URL
        long_url = "https://example.com/" + "a" * 200
        meeting_long_url = Meeting(
            conference_id=1,
            url=long_url,
        )
        assert meeting_long_url.url == long_url

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        meeting = Meeting(
            conference_id=1,
            date=None,
            url=None,
            name=None,
            gcs_pdf_uri=None,
            gcs_text_uri=None,
            attendees_mapping=None,
        )

        assert meeting.date is None
        assert meeting.url is None
        assert meeting.name is None
        assert meeting.gcs_pdf_uri is None
        assert meeting.gcs_text_uri is None
        assert meeting.attendees_mapping is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        meeting1 = Meeting(conference_id=1)
        assert meeting1.id is None

        # With ID
        meeting2 = Meeting(conference_id=1, id=100)
        assert meeting2.id == 100

        # ID can be any integer
        meeting3 = Meeting(conference_id=1, id=999999)
        assert meeting3.id == 999999

    def test_str_representation_priority(self) -> None:
        """Test __str__ method priority (name > date > id > default)."""
        # Priority 1: name
        meeting1 = Meeting(
            id=1,
            conference_id=1,
            date=date(2024, 1, 1),
            name="Test Meeting",
        )
        assert str(meeting1) == "Test Meeting"

        # Priority 2: date (no name)
        meeting2 = Meeting(
            id=2,
            conference_id=1,
            date=date(2024, 1, 1),
        )
        assert str(meeting2) == "Meeting on 2024-01-01"

        # Priority 3: id (no name, no date)
        meeting3 = Meeting(
            id=3,
            conference_id=1,
        )
        assert str(meeting3) == "Meeting #3"

        # Priority 4: default (no name, no date, no id)
        meeting4 = Meeting(conference_id=1)
        assert str(meeting4) == "Meeting"
