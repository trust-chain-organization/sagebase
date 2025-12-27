"""Tests for PoliticianAffiliation entity."""

from datetime import date

from tests.fixtures.entity_factories import create_politician_affiliation

from src.domain.entities.politician_affiliation import PoliticianAffiliation


class TestPoliticianAffiliation:
    """Test cases for PoliticianAffiliation entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        affiliation = PoliticianAffiliation(
            politician_id=1, conference_id=2, start_date=date(2023, 1, 1)
        )

        assert affiliation.politician_id == 1
        assert affiliation.conference_id == 2
        assert affiliation.start_date == date(2023, 1, 1)
        assert affiliation.end_date is None
        assert affiliation.role is None
        assert affiliation.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        affiliation = PoliticianAffiliation(
            id=1,
            politician_id=10,
            conference_id=20,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            role="議長",
        )

        assert affiliation.id == 1
        assert affiliation.politician_id == 10
        assert affiliation.conference_id == 20
        assert affiliation.start_date == date(2023, 1, 1)
        assert affiliation.end_date == date(2023, 12, 31)
        assert affiliation.role == "議長"

    def test_is_active_method(self) -> None:
        """Test is_active method for current and ended affiliations."""
        # Test active affiliation (no end date)
        active_affiliation = create_politician_affiliation(end_date=None)
        assert active_affiliation.is_active() is True

        # Test ended affiliation
        ended_affiliation = create_politician_affiliation(end_date=date(2023, 12, 31))
        assert ended_affiliation.is_active() is False

    def test_str_representation_active(self) -> None:
        """Test string representation for active affiliation."""
        affiliation = create_politician_affiliation(
            politician_id=5, conference_id=10, end_date=None
        )

        expected = "PoliticianAffiliation(politician=5, conference=10, active)"
        assert str(affiliation) == expected

    def test_str_representation_ended(self) -> None:
        """Test string representation for ended affiliation."""
        end_date = date(2023, 12, 31)
        affiliation = create_politician_affiliation(
            politician_id=5, conference_id=10, end_date=end_date
        )

        expected = (
            f"PoliticianAffiliation(politician=5, conference=10, ended {end_date})"
        )
        assert str(affiliation) == expected

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        affiliation = create_politician_affiliation()

        assert affiliation.id == 1
        assert affiliation.politician_id == 1
        assert affiliation.conference_id == 1
        assert affiliation.start_date == date(2023, 1, 1)
        assert affiliation.end_date is None
        assert affiliation.role == "議員"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        affiliation = create_politician_affiliation(
            id=99,
            politician_id=50,
            conference_id=30,
            start_date=date(2022, 4, 1),
            end_date=date(2023, 3, 31),
            role="委員長",
        )

        assert affiliation.id == 99
        assert affiliation.politician_id == 50
        assert affiliation.conference_id == 30
        assert affiliation.start_date == date(2022, 4, 1)
        assert affiliation.end_date == date(2023, 3, 31)
        assert affiliation.role == "委員長"

    def test_different_roles(self) -> None:
        """Test affiliation with different roles."""
        roles = ["議員", "議長", "副議長", "委員長", "副委員長", "幹事長", None]

        for role in roles:
            affiliation = create_politician_affiliation(role=role)
            assert affiliation.role == role

    def test_affiliation_timeline(self) -> None:
        """Test different affiliation timelines."""
        # Past affiliation
        past_affiliation = PoliticianAffiliation(
            politician_id=1,
            conference_id=1,
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
        )
        assert past_affiliation.is_active() is False

        # Current affiliation (started in past, no end)
        current_affiliation = PoliticianAffiliation(
            politician_id=1, conference_id=1, start_date=date(2022, 1, 1), end_date=None
        )
        assert current_affiliation.is_active() is True

        # Future start date (still active if no end date)
        future_affiliation = PoliticianAffiliation(
            politician_id=1, conference_id=1, start_date=date(2025, 1, 1), end_date=None
        )
        assert future_affiliation.is_active() is True

    def test_multiple_affiliations(self) -> None:
        """Test creating multiple affiliations for the same politician."""
        # Politician can have multiple affiliations to different conferences
        affiliation1 = create_politician_affiliation(
            id=1, politician_id=100, conference_id=1, role="議員"
        )

        affiliation2 = create_politician_affiliation(
            id=2, politician_id=100, conference_id=2, role="委員長"
        )

        assert affiliation1.politician_id == affiliation2.politician_id
        assert affiliation1.conference_id != affiliation2.conference_id
        assert affiliation1.role != affiliation2.role

    def test_affiliation_with_same_start_end_date(self) -> None:
        """Test affiliation that starts and ends on the same date."""
        same_date = date(2023, 6, 1)
        affiliation = PoliticianAffiliation(
            politician_id=1, conference_id=1, start_date=same_date, end_date=same_date
        )

        assert affiliation.start_date == affiliation.end_date
        assert affiliation.is_active() is False

    def test_inheritance_from_base_entity(self) -> None:
        """Test that PoliticianAffiliation properly inherits from BaseEntity."""
        affiliation = create_politician_affiliation(id=42)

        # Check that id is properly set through BaseEntity
        assert affiliation.id == 42

        # Create without id
        affiliation_no_id = PoliticianAffiliation(
            politician_id=1, conference_id=1, start_date=date(2023, 1, 1)
        )
        assert affiliation_no_id.id is None
