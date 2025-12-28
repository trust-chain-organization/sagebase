"""Tests for ParliamentaryGroupMembership entity."""

from datetime import date, datetime
from uuid import uuid4

from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)


class TestParliamentaryGroupMembership:
    """Test cases for ParliamentaryGroupMembership entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
        )

        assert membership.politician_id == 1
        assert membership.parliamentary_group_id == 2
        assert membership.start_date == date(2024, 1, 1)
        assert membership.end_date is None
        assert membership.role is None
        assert membership.created_by_user_id is None
        assert membership.created_at is None
        assert membership.updated_at is None
        assert membership.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        user_id = uuid4()
        created_time = datetime(2024, 1, 1, 10, 0, 0)
        updated_time = datetime(2024, 1, 15, 14, 30, 0)

        membership = ParliamentaryGroupMembership(
            id=10,
            politician_id=5,
            parliamentary_group_id=3,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            role="幹事長",
            created_by_user_id=user_id,
            created_at=created_time,
            updated_at=updated_time,
        )

        assert membership.id == 10
        assert membership.politician_id == 5
        assert membership.parliamentary_group_id == 3
        assert membership.start_date == date(2024, 1, 1)
        assert membership.end_date == date(2024, 12, 31)
        assert membership.role == "幹事長"
        assert membership.created_by_user_id == user_id
        assert membership.created_at == created_time
        assert membership.updated_at == updated_time

    def test_is_active_current_membership(self) -> None:
        """Test is_active returns True for current membership (no end_date)."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=None,
        )

        # Should be active today
        assert membership.is_active() is True
        assert membership.is_active(date.today()) is True

    def test_is_active_with_end_date_in_future(self) -> None:
        """Test is_active returns True when end_date is in the future."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Should be active on a date between start and end
        assert membership.is_active(date(2024, 6, 15)) is True
        # Should be active on start date
        assert membership.is_active(date(2024, 1, 1)) is True
        # Should be active on end date
        assert membership.is_active(date(2024, 12, 31)) is True

    def test_is_active_with_end_date_in_past(self) -> None:
        """Test is_active returns False when end_date is in the past."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )

        # Should not be active today
        assert membership.is_active() is False
        # Should not be active after end date
        assert membership.is_active(date(2021, 1, 1)) is False

    def test_is_active_before_start_date(self) -> None:
        """Test is_active returns False when checking before start_date."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 6, 1),
            end_date=None,
        )

        # Should not be active before start date
        assert membership.is_active(date(2024, 5, 31)) is False

    def test_overlaps_with_no_overlap(self) -> None:
        """Test overlaps_with returns False when ranges don't overlap."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Range before membership
        assert membership.overlaps_with(date(2023, 1, 1), date(2023, 12, 31)) is False
        # Range after membership
        assert membership.overlaps_with(date(2025, 1, 1), date(2025, 12, 31)) is False

    def test_overlaps_with_full_overlap(self) -> None:
        """Test overlaps_with returns True when ranges fully overlap."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Range contains membership
        assert membership.overlaps_with(date(2023, 1, 1), date(2025, 12, 31)) is True
        # Same range
        assert membership.overlaps_with(date(2024, 1, 1), date(2024, 12, 31)) is True

    def test_overlaps_with_partial_overlap(self) -> None:
        """Test overlaps_with returns True when ranges partially overlap."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Overlap at start
        assert membership.overlaps_with(date(2023, 6, 1), date(2024, 6, 30)) is True
        # Overlap at end
        assert membership.overlaps_with(date(2024, 6, 1), date(2025, 6, 30)) is True

    def test_overlaps_with_no_end_date(self) -> None:
        """Test overlaps_with when membership has no end_date."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=None,  # Ongoing membership
        )

        # Should overlap with any range after start_date
        assert membership.overlaps_with(date(2024, 6, 1), date(2024, 12, 31)) is True
        assert membership.overlaps_with(date(2025, 1, 1), date(2025, 12, 31)) is True
        # Should not overlap with range before start_date
        assert membership.overlaps_with(date(2023, 1, 1), date(2023, 12, 31)) is False

    def test_overlaps_with_no_range_end_date(self) -> None:
        """Test overlaps_with when range has no end_date."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Range starts before membership ends
        assert membership.overlaps_with(date(2024, 6, 1), None) is True
        # Range starts after membership ends
        assert membership.overlaps_with(date(2025, 1, 1), None) is False

    def test_various_roles(self) -> None:
        """Test various parliamentary group roles."""
        roles = [
            "幹事長",
            "政調会長",
            "総務会長",
            "国対委員長",
            "代表",
            "副代表",
            "会長",
            "事務局長",
            None,
        ]

        for role in roles:
            membership = ParliamentaryGroupMembership(
                politician_id=1,
                parliamentary_group_id=2,
                start_date=date(2024, 1, 1),
                role=role,
            )
            assert membership.role == role

    def test_inheritance_from_base_entity(self) -> None:
        """Test that ParliamentaryGroupMembership properly inherits from BaseEntity."""
        membership = ParliamentaryGroupMembership(
            id=42,
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
        )

        # Check that id is properly set through BaseEntity
        assert membership.id == 42

        # Create without id
        membership_no_id = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
        )
        assert membership_no_id.id is None

    def test_complex_membership_scenarios(self) -> None:
        """Test complex real-world membership scenarios."""
        user_id = uuid4()

        # Current leader of group
        leader = ParliamentaryGroupMembership(
            id=1,
            politician_id=10,
            parliamentary_group_id=5,
            start_date=date(2023, 4, 1),
            end_date=None,
            role="代表",
            created_by_user_id=user_id,
            created_at=datetime(2023, 4, 1, 10, 0, 0),
        )
        assert leader.is_active() is True
        assert leader.role == "代表"

        # Former member
        former_member = ParliamentaryGroupMembership(
            id=2,
            politician_id=11,
            parliamentary_group_id=5,
            start_date=date(2020, 1, 1),
            end_date=date(2023, 3, 31),
            role=None,
            created_by_user_id=user_id,
            created_at=datetime(2020, 1, 1, 10, 0, 0),
        )
        assert former_member.is_active() is False

        # Future member
        future_member = ParliamentaryGroupMembership(
            id=3,
            politician_id=12,
            parliamentary_group_id=5,
            start_date=date(2026, 4, 1),
            end_date=None,
            role="幹事長",
            created_by_user_id=user_id,
            created_at=datetime.now(),
        )
        assert future_member.is_active() is False
        assert future_member.is_active(date(2026, 5, 1)) is True

    def test_edge_cases(self) -> None:
        """Test edge cases for ParliamentaryGroupMembership entity."""
        # Same start and end date
        same_day = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )
        assert same_day.is_active(date(2024, 1, 1)) is True
        assert same_day.is_active(date(2024, 1, 2)) is False

        # Very long membership period
        long_membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(1990, 1, 1),
            end_date=date(2024, 12, 31),
        )
        assert long_membership.is_active(date(2000, 1, 1)) is True

        # Empty string role
        empty_role = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            role="",
        )
        assert empty_role.role == ""

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=None,
            role=None,
            created_by_user_id=None,
            created_at=None,
            updated_at=None,
        )

        assert membership.end_date is None
        assert membership.role is None
        assert membership.created_by_user_id is None
        assert membership.created_at is None
        assert membership.updated_at is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        membership1 = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
        )
        assert membership1.id is None

        # With ID
        membership2 = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            id=100,
        )
        assert membership2.id == 100

        # ID can be any integer
        membership3 = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            id=999999,
        )
        assert membership3.id == 999999

    def test_overlaps_with_edge_cases(self) -> None:
        """Test overlaps_with with edge cases."""
        # Membership that touches but doesn't overlap
        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Range ends exactly when membership starts
        assert membership.overlaps_with(date(2023, 1, 1), date(2023, 12, 31)) is False
        # Range starts exactly when membership ends + 1
        assert membership.overlaps_with(date(2025, 1, 1), date(2025, 12, 31)) is False

    def test_datetime_precision(self) -> None:
        """Test datetime fields with various precision levels."""
        # With microseconds
        dt_micro = datetime(2024, 1, 15, 10, 30, 45, 123456)
        membership_micro = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            created_at=dt_micro,
        )
        assert membership_micro.created_at == dt_micro

        # Without microseconds
        dt_no_micro = datetime(2024, 1, 15, 10, 30, 45)
        membership_no_micro = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=2,
            start_date=date(2024, 1, 1),
            updated_at=dt_no_micro,
        )
        assert membership_no_micro.updated_at == dt_no_micro

    def test_multiple_politicians_same_group(self) -> None:
        """Test multiple politicians in the same parliamentary group."""
        group_id = 5

        member1 = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=group_id,
            start_date=date(2024, 1, 1),
            role="代表",
        )

        member2 = ParliamentaryGroupMembership(
            politician_id=2,
            parliamentary_group_id=group_id,
            start_date=date(2024, 1, 1),
            role="幹事長",
        )

        member3 = ParliamentaryGroupMembership(
            politician_id=3,
            parliamentary_group_id=group_id,
            start_date=date(2024, 1, 1),
            role=None,
        )

        assert member1.parliamentary_group_id == group_id
        assert member2.parliamentary_group_id == group_id
        assert member3.parliamentary_group_id == group_id
        assert member1.politician_id != member2.politician_id
        assert member2.politician_id != member3.politician_id

    def test_politician_changes_groups(self) -> None:
        """Test politician changing parliamentary groups over time."""
        politician_id = 10

        # First group membership
        first_membership = ParliamentaryGroupMembership(
            politician_id=politician_id,
            parliamentary_group_id=1,
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
        )

        # Second group membership
        second_membership = ParliamentaryGroupMembership(
            politician_id=politician_id,
            parliamentary_group_id=2,
            start_date=date(2023, 1, 1),
            end_date=None,
        )

        assert first_membership.is_active(date(2021, 6, 1)) is True
        assert first_membership.is_active(date(2023, 6, 1)) is False
        assert second_membership.is_active(date(2021, 6, 1)) is False
        assert second_membership.is_active(date(2023, 6, 1)) is True
