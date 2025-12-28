"""Tests for data coverage statistics TypedDict classes."""

from src.domain.entities.data_coverage_stats import (
    ActivityData,
    GoverningBodyStats,
    MeetingStats,
    SpeakerMatchingStats,
)


class TestGoverningBodyStats:
    """Test cases for GoverningBodyStats TypedDict."""

    def test_initialization_with_all_fields(self) -> None:
        """Test TypedDict initialization with all fields."""
        stats: GoverningBodyStats = {
            "total": 100,
            "with_conferences": 80,
            "with_meetings": 60,
            "coverage_percentage": 80.0,
        }

        assert stats["total"] == 100
        assert stats["with_conferences"] == 80
        assert stats["with_meetings"] == 60
        assert stats["coverage_percentage"] == 80.0

    def test_field_types(self) -> None:
        """Test that fields have correct types."""
        stats: GoverningBodyStats = {
            "total": 1966,
            "with_conferences": 500,
            "with_meetings": 250,
            "coverage_percentage": 25.44,
        }

        assert isinstance(stats["total"], int)
        assert isinstance(stats["with_conferences"], int)
        assert isinstance(stats["with_meetings"], int)
        assert isinstance(stats["coverage_percentage"], float)

    def test_various_values(self) -> None:
        """Test various realistic values."""
        test_cases = [
            {
                "total": 1966,
                "with_conferences": 1000,
                "with_meetings": 500,
                "coverage_percentage": 50.86,
            },
            {
                "total": 100,
                "with_conferences": 0,
                "with_meetings": 0,
                "coverage_percentage": 0.0,
            },
            {
                "total": 50,
                "with_conferences": 50,
                "with_meetings": 50,
                "coverage_percentage": 100.0,
            },
        ]

        for case in test_cases:
            stats: GoverningBodyStats = case
            assert stats["total"] >= 0
            assert stats["with_conferences"] >= 0
            assert stats["with_meetings"] >= 0
            assert 0.0 <= stats["coverage_percentage"] <= 100.0

    def test_edge_cases(self) -> None:
        """Test edge cases for GoverningBodyStats."""
        # Zero values
        zero_stats: GoverningBodyStats = {
            "total": 0,
            "with_conferences": 0,
            "with_meetings": 0,
            "coverage_percentage": 0.0,
        }
        assert zero_stats["total"] == 0

        # Large values
        large_stats: GoverningBodyStats = {
            "total": 999999,
            "with_conferences": 999999,
            "with_meetings": 999999,
            "coverage_percentage": 100.0,
        }
        assert large_stats["total"] == 999999


class TestMeetingStats:
    """Test cases for MeetingStats TypedDict."""

    def test_initialization_with_all_fields(self) -> None:
        """Test TypedDict initialization with all fields."""
        stats: MeetingStats = {
            "total_meetings": 500,
            "with_minutes": 400,
            "with_conversations": 300,
            "average_conversations_per_meeting": 25.5,
            "meetings_by_conference": {"東京都議会": 100, "大阪市議会": 50},
        }

        assert stats["total_meetings"] == 500
        assert stats["with_minutes"] == 400
        assert stats["with_conversations"] == 300
        assert stats["average_conversations_per_meeting"] == 25.5
        assert stats["meetings_by_conference"]["東京都議会"] == 100

    def test_field_types(self) -> None:
        """Test that fields have correct types."""
        stats: MeetingStats = {
            "total_meetings": 100,
            "with_minutes": 80,
            "with_conversations": 60,
            "average_conversations_per_meeting": 15.75,
            "meetings_by_conference": {"会議体A": 50, "会議体B": 50},
        }

        assert isinstance(stats["total_meetings"], int)
        assert isinstance(stats["with_minutes"], int)
        assert isinstance(stats["with_conversations"], int)
        assert isinstance(stats["average_conversations_per_meeting"], float)
        assert isinstance(stats["meetings_by_conference"], dict)

    def test_empty_meetings_by_conference(self) -> None:
        """Test with empty meetings_by_conference dict."""
        stats: MeetingStats = {
            "total_meetings": 0,
            "with_minutes": 0,
            "with_conversations": 0,
            "average_conversations_per_meeting": 0.0,
            "meetings_by_conference": {},
        }

        assert len(stats["meetings_by_conference"]) == 0

    def test_various_meetings_by_conference(self) -> None:
        """Test various meetings_by_conference values."""
        stats: MeetingStats = {
            "total_meetings": 300,
            "with_minutes": 250,
            "with_conversations": 200,
            "average_conversations_per_meeting": 20.0,
            "meetings_by_conference": {
                "東京都議会": 100,
                "大阪市議会": 50,
                "北海道議会": 75,
                "福岡市議会": 75,
            },
        }

        assert len(stats["meetings_by_conference"]) == 4
        assert sum(stats["meetings_by_conference"].values()) == 300

    def test_edge_cases(self) -> None:
        """Test edge cases for MeetingStats."""
        # Zero average
        zero_avg_stats: MeetingStats = {
            "total_meetings": 100,
            "with_minutes": 0,
            "with_conversations": 0,
            "average_conversations_per_meeting": 0.0,
            "meetings_by_conference": {},
        }
        assert zero_avg_stats["average_conversations_per_meeting"] == 0.0

        # High average
        high_avg_stats: MeetingStats = {
            "total_meetings": 10,
            "with_minutes": 10,
            "with_conversations": 10,
            "average_conversations_per_meeting": 500.0,
            "meetings_by_conference": {"会議体": 10},
        }
        assert high_avg_stats["average_conversations_per_meeting"] == 500.0


class TestSpeakerMatchingStats:
    """Test cases for SpeakerMatchingStats TypedDict."""

    def test_initialization_with_all_fields(self) -> None:
        """Test TypedDict initialization with all fields."""
        stats: SpeakerMatchingStats = {
            "total_speakers": 1000,
            "matched_speakers": 800,
            "unmatched_speakers": 200,
            "matching_rate": 80.0,
            "total_conversations": 5000,
            "linked_conversations": 4000,
            "linkage_rate": 80.0,
        }

        assert stats["total_speakers"] == 1000
        assert stats["matched_speakers"] == 800
        assert stats["unmatched_speakers"] == 200
        assert stats["matching_rate"] == 80.0
        assert stats["total_conversations"] == 5000
        assert stats["linked_conversations"] == 4000
        assert stats["linkage_rate"] == 80.0

    def test_field_types(self) -> None:
        """Test that fields have correct types."""
        stats: SpeakerMatchingStats = {
            "total_speakers": 500,
            "matched_speakers": 400,
            "unmatched_speakers": 100,
            "matching_rate": 80.0,
            "total_conversations": 2500,
            "linked_conversations": 2000,
            "linkage_rate": 80.0,
        }

        assert isinstance(stats["total_speakers"], int)
        assert isinstance(stats["matched_speakers"], int)
        assert isinstance(stats["unmatched_speakers"], int)
        assert isinstance(stats["matching_rate"], float)
        assert isinstance(stats["total_conversations"], int)
        assert isinstance(stats["linked_conversations"], int)
        assert isinstance(stats["linkage_rate"], float)

    def test_matching_consistency(self) -> None:
        """Test that matched + unmatched = total."""
        stats: SpeakerMatchingStats = {
            "total_speakers": 1000,
            "matched_speakers": 750,
            "unmatched_speakers": 250,
            "matching_rate": 75.0,
            "total_conversations": 5000,
            "linked_conversations": 3750,
            "linkage_rate": 75.0,
        }

        assert (
            stats["matched_speakers"] + stats["unmatched_speakers"]
            == stats["total_speakers"]
        )

    def test_various_matching_rates(self) -> None:
        """Test various matching rates."""
        test_cases = [
            {
                "total_speakers": 100,
                "matched_speakers": 100,
                "unmatched_speakers": 0,
                "matching_rate": 100.0,
                "total_conversations": 500,
                "linked_conversations": 500,
                "linkage_rate": 100.0,
            },
            {
                "total_speakers": 100,
                "matched_speakers": 50,
                "unmatched_speakers": 50,
                "matching_rate": 50.0,
                "total_conversations": 500,
                "linked_conversations": 250,
                "linkage_rate": 50.0,
            },
            {
                "total_speakers": 100,
                "matched_speakers": 0,
                "unmatched_speakers": 100,
                "matching_rate": 0.0,
                "total_conversations": 500,
                "linked_conversations": 0,
                "linkage_rate": 0.0,
            },
        ]

        for case in test_cases:
            stats: SpeakerMatchingStats = case
            assert 0.0 <= stats["matching_rate"] <= 100.0
            assert 0.0 <= stats["linkage_rate"] <= 100.0

    def test_edge_cases(self) -> None:
        """Test edge cases for SpeakerMatchingStats."""
        # All zeros
        zero_stats: SpeakerMatchingStats = {
            "total_speakers": 0,
            "matched_speakers": 0,
            "unmatched_speakers": 0,
            "matching_rate": 0.0,
            "total_conversations": 0,
            "linked_conversations": 0,
            "linkage_rate": 0.0,
        }
        assert zero_stats["matching_rate"] == 0.0


class TestActivityData:
    """Test cases for ActivityData TypedDict."""

    def test_initialization_with_all_fields(self) -> None:
        """Test TypedDict initialization with all fields."""
        activity: ActivityData = {
            "date": "2024-01-15",
            "meetings_count": 10,
            "conversations_count": 250,
            "speakers_count": 50,
            "politicians_count": 5,
        }

        assert activity["date"] == "2024-01-15"
        assert activity["meetings_count"] == 10
        assert activity["conversations_count"] == 250
        assert activity["speakers_count"] == 50
        assert activity["politicians_count"] == 5

    def test_field_types(self) -> None:
        """Test that fields have correct types."""
        activity: ActivityData = {
            "date": "2024-12-31",
            "meetings_count": 5,
            "conversations_count": 100,
            "speakers_count": 20,
            "politicians_count": 3,
        }

        assert isinstance(activity["date"], str)
        assert isinstance(activity["meetings_count"], int)
        assert isinstance(activity["conversations_count"], int)
        assert isinstance(activity["speakers_count"], int)
        assert isinstance(activity["politicians_count"], int)

    def test_various_dates(self) -> None:
        """Test various date formats."""
        dates = [
            "2024-01-01",
            "2024-06-15",
            "2024-12-31",
            "2023-02-28",
            "2024-02-29",  # Leap year
        ]

        for date_str in dates:
            activity: ActivityData = {
                "date": date_str,
                "meetings_count": 1,
                "conversations_count": 10,
                "speakers_count": 5,
                "politicians_count": 2,
            }
            assert activity["date"] == date_str

    def test_various_activity_levels(self) -> None:
        """Test various activity levels."""
        test_cases = [
            # High activity day
            {
                "date": "2024-01-15",
                "meetings_count": 50,
                "conversations_count": 1000,
                "speakers_count": 200,
                "politicians_count": 50,
            },
            # Low activity day
            {
                "date": "2024-01-16",
                "meetings_count": 1,
                "conversations_count": 10,
                "speakers_count": 3,
                "politicians_count": 1,
            },
            # No activity day
            {
                "date": "2024-01-17",
                "meetings_count": 0,
                "conversations_count": 0,
                "speakers_count": 0,
                "politicians_count": 0,
            },
        ]

        for case in test_cases:
            activity: ActivityData = case
            assert all(activity[key] >= 0 for key in activity if key != "date")

    def test_edge_cases(self) -> None:
        """Test edge cases for ActivityData."""
        # All zeros
        zero_activity: ActivityData = {
            "date": "2024-01-01",
            "meetings_count": 0,
            "conversations_count": 0,
            "speakers_count": 0,
            "politicians_count": 0,
        }
        assert zero_activity["meetings_count"] == 0

        # Large values
        large_activity: ActivityData = {
            "date": "2024-01-01",
            "meetings_count": 9999,
            "conversations_count": 99999,
            "speakers_count": 9999,
            "politicians_count": 9999,
        }
        assert large_activity["conversations_count"] == 99999

    def test_monthly_activity_data(self) -> None:
        """Test activity data for multiple days."""
        january_activity = [
            {
                "date": f"2024-01-{day:02d}",
                "meetings_count": day,
                "conversations_count": day * 10,
                "speakers_count": day * 2,
                "politicians_count": max(1, day // 5),
            }
            for day in range(1, 32)
        ]

        assert len(january_activity) == 31
        for activity in january_activity:
            assert activity["date"].startswith("2024-01-")
            assert activity["meetings_count"] >= 1
