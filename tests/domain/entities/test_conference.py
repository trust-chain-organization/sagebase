"""Tests for Conference entity."""

from tests.fixtures.entity_factories import create_conference

from src.domain.entities.conference import Conference


class TestConference:
    """Test cases for Conference entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        conference = Conference(
            name="東京都議会",
            governing_body_id=1,
        )

        assert conference.name == "東京都議会"
        assert conference.governing_body_id == 1
        assert conference.type is None
        assert conference.members_introduction_url is None
        assert conference.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        conference = Conference(
            id=10,
            name="大阪市議会",
            governing_body_id=5,
            type="地方議会全体",
            members_introduction_url="https://example.com/members",
        )

        assert conference.id == 10
        assert conference.name == "大阪市議会"
        assert conference.governing_body_id == 5
        assert conference.type == "地方議会全体"
        assert conference.members_introduction_url == "https://example.com/members"

    def test_str_representation(self) -> None:
        """Test string representation."""
        conference = Conference(name="北海道議会", governing_body_id=1)
        assert str(conference) == "北海道議会"

        conference_with_id = Conference(
            id=42,
            name="福岡市議会",
            governing_body_id=2,
        )
        assert str(conference_with_id) == "福岡市議会"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        conference = create_conference()

        assert conference.id == 1
        assert conference.governing_body_id == 1
        assert conference.name == "議会全体"
        assert conference.type == "地方議会全体"
        assert conference.members_introduction_url is None

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        conference = create_conference(
            id=99,
            name="愛知県議会",
            governing_body_id=10,
            type="都道府県議会",
            members_introduction_url="https://aichi.example.com/members",
        )

        assert conference.id == 99
        assert conference.name == "愛知県議会"
        assert conference.governing_body_id == 10
        assert conference.type == "都道府県議会"
        assert (
            conference.members_introduction_url == "https://aichi.example.com/members"
        )

    def test_different_conference_types(self) -> None:
        """Test different types of conferences."""
        types = [
            "地方議会全体",
            "都道府県議会",
            "市区町村議会",
            "常任委員会",
            "特別委員会",
            "議会運営委員会",
            None,
        ]

        for conf_type in types:
            conference = Conference(
                name="Test Conference",
                governing_body_id=1,
                type=conf_type,
            )
            assert conference.type == conf_type

    def test_various_conference_names(self) -> None:
        """Test various conference names."""
        names = [
            "東京都議会",
            "大阪市議会",
            "札幌市議会",
            "福岡市議会本会議",
            "総務委員会",
            "予算特別委員会",
            "決算特別委員会",
            "文教委員会",
        ]

        for name in names:
            conference = Conference(name=name, governing_body_id=1)
            assert conference.name == name
            assert str(conference) == name

    def test_members_introduction_url_formats(self) -> None:
        """Test various URL formats for members introduction."""
        urls = [
            "https://example.com/members",
            "http://city.jp/council/members",
            "https://www.prefecture.go.jp/members.html",
            None,
        ]

        for url in urls:
            conference = Conference(
                name="Test Conference",
                governing_body_id=1,
                members_introduction_url=url,
            )
            assert conference.members_introduction_url == url

    def test_governing_body_id_variations(self) -> None:
        """Test various governing body IDs."""
        ids = [1, 10, 100, 1000, 9999]

        for gb_id in ids:
            conference = Conference(
                name="Test Conference",
                governing_body_id=gb_id,
            )
            assert conference.governing_body_id == gb_id

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Conference properly inherits from BaseEntity."""
        conference = create_conference(id=42)

        # Check that id is properly set through BaseEntity
        assert conference.id == 42

        # Create without id
        conference_no_id = Conference(
            name="Test Conference",
            governing_body_id=1,
        )
        assert conference_no_id.id is None

    def test_complex_conference_scenarios(self) -> None:
        """Test complex real-world conference scenarios."""
        # Prefectural assembly
        prefectural = Conference(
            id=1,
            name="東京都議会",
            governing_body_id=13,
            type="都道府県議会",
            members_introduction_url="https://tokyo.example.com/members",
        )
        assert str(prefectural) == "東京都議会"
        assert prefectural.type == "都道府県議会"

        # City council
        city_council = Conference(
            id=2,
            name="横浜市議会",
            governing_body_id=141,
            type="市区町村議会",
            members_introduction_url="https://yokohama.example.com/members",
        )
        assert str(city_council) == "横浜市議会"
        assert city_council.type == "市区町村議会"

        # Committee
        committee = Conference(
            id=3,
            name="総務委員会",
            governing_body_id=13,
            type="常任委員会",
            members_introduction_url=None,
        )
        assert str(committee) == "総務委員会"
        assert committee.type == "常任委員会"

    def test_edge_cases(self) -> None:
        """Test edge cases for Conference entity."""
        # Empty strings
        conference_empty = Conference(
            name="Name",
            governing_body_id=1,
            type="",
            members_introduction_url="",
        )
        assert conference_empty.name == "Name"
        assert conference_empty.type == ""
        assert conference_empty.members_introduction_url == ""

        # Very long names
        long_name = "東京都" * 50
        conference_long = Conference(
            name=long_name,
            governing_body_id=1,
        )
        assert conference_long.name == long_name
        assert str(conference_long) == long_name

        # Special characters in name
        special_name = "東京都議会（第1回定例会）"
        conference_special = Conference(
            name=special_name,
            governing_body_id=1,
        )
        assert conference_special.name == special_name
        assert str(conference_special) == special_name

        # Very long URL
        long_url = "https://example.com/" + "a" * 200
        conference_long_url = Conference(
            name="Test",
            governing_body_id=1,
            members_introduction_url=long_url,
        )
        assert conference_long_url.members_introduction_url == long_url

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        conference = Conference(
            name="Test Conference",
            governing_body_id=1,
            type=None,
            members_introduction_url=None,
        )

        assert conference.type is None
        assert conference.members_introduction_url is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        conference1 = Conference(name="Test 1", governing_body_id=1)
        assert conference1.id is None

        # With ID
        conference2 = Conference(name="Test 2", governing_body_id=1, id=100)
        assert conference2.id == 100

        # ID can be any integer
        conference3 = Conference(name="Test 3", governing_body_id=1, id=999999)
        assert conference3.id == 999999

    def test_committee_types(self) -> None:
        """Test various committee types."""
        committee_types = [
            ("総務委員会", "常任委員会"),
            ("文教委員会", "常任委員会"),
            ("予算特別委員会", "特別委員会"),
            ("決算特別委員会", "特別委員会"),
            ("議会運営委員会", "議会運営委員会"),
        ]

        for name, conf_type in committee_types:
            conference = Conference(
                name=name,
                governing_body_id=1,
                type=conf_type,
            )
            assert conference.name == name
            assert conference.type == conf_type
