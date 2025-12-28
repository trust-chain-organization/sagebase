"""Tests for PoliticalParty entity."""

from src.domain.entities.political_party import PoliticalParty


class TestPoliticalParty:
    """Test cases for PoliticalParty entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        party = PoliticalParty(name="自由民主党")

        assert party.name == "自由民主党"
        assert party.members_list_url is None
        assert party.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        party = PoliticalParty(
            id=1,
            name="立憲民主党",
            members_list_url="https://example.com/members",
        )

        assert party.id == 1
        assert party.name == "立憲民主党"
        assert party.members_list_url == "https://example.com/members"

    def test_str_representation(self) -> None:
        """Test string representation."""
        party = PoliticalParty(name="公明党")
        assert str(party) == "公明党"

        party_with_id = PoliticalParty(id=42, name="日本共産党")
        assert str(party_with_id) == "日本共産党"

    def test_various_party_names(self) -> None:
        """Test various political party names."""
        party_names = [
            "自由民主党",
            "立憲民主党",
            "公明党",
            "日本共産党",
            "日本維新の会",
            "国民民主党",
            "れいわ新選組",
            "社会民主党",
            "参政党",
            "NHK党",
        ]

        for name in party_names:
            party = PoliticalParty(name=name)
            assert party.name == name
            assert str(party) == name

    def test_various_url_formats(self) -> None:
        """Test various URL formats for members list."""
        urls = [
            "https://example.com/members",
            "http://party.jp/members/list",
            "https://www.party-site.com/members.html",
            "https://party.go.jp/members?year=2024",
            None,
        ]

        for url in urls:
            party = PoliticalParty(name="テスト政党", members_list_url=url)
            assert party.members_list_url == url

    def test_inheritance_from_base_entity(self) -> None:
        """Test that PoliticalParty properly inherits from BaseEntity."""
        party = PoliticalParty(id=42, name="テスト政党")

        # Check that id is properly set through BaseEntity
        assert party.id == 42

        # Create without id
        party_no_id = PoliticalParty(name="テスト政党")
        assert party_no_id.id is None

    def test_complex_party_scenarios(self) -> None:
        """Test complex real-world political party scenarios."""
        # Major party with members list
        major_party = PoliticalParty(
            id=1,
            name="自由民主党",
            members_list_url="https://www.jimin.jp/members/",
        )
        assert major_party.name == "自由民主党"
        assert major_party.members_list_url is not None
        assert str(major_party) == "自由民主党"

        # Minor party without members list
        minor_party = PoliticalParty(
            id=2,
            name="地域政党A",
            members_list_url=None,
        )
        assert minor_party.members_list_url is None

        # New party
        new_party = PoliticalParty(
            name="新党",
            members_list_url="https://new-party.com/members",
        )
        assert new_party.id is None
        assert new_party.name == "新党"

    def test_edge_cases(self) -> None:
        """Test edge cases for PoliticalParty entity."""
        # Empty string URL
        party_empty = PoliticalParty(
            name="テスト政党",
            members_list_url="",
        )
        assert party_empty.members_list_url == ""

        # Very long party name
        long_name = "非常に長い政党名" * 20
        party_long_name = PoliticalParty(name=long_name)
        assert party_long_name.name == long_name
        assert str(party_long_name) == long_name

        # Party name with special characters
        special_name = "政党（カッコ付き）・中黒入り"
        party_special = PoliticalParty(name=special_name)
        assert party_special.name == special_name
        assert str(party_special) == special_name

        # Very long URL
        long_url = "https://example.com/" + "a" * 500
        party_long_url = PoliticalParty(
            name="テスト政党",
            members_list_url=long_url,
        )
        assert party_long_url.members_list_url == long_url

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        party = PoliticalParty(
            name="テスト政党",
            members_list_url=None,
        )

        assert party.members_list_url is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        party1 = PoliticalParty(name="政党1")
        assert party1.id is None

        # With ID
        party2 = PoliticalParty(name="政党2", id=100)
        assert party2.id == 100

        # ID can be any integer
        party3 = PoliticalParty(name="政党3", id=999999)
        assert party3.id == 999999

    def test_party_names_with_english(self) -> None:
        """Test party names with English characters."""
        english_names = [
            "Liberal Democratic Party",
            "Constitutional Democratic Party",
            "NHK党",
            "Reiwa Shinsengumi",
        ]

        for name in english_names:
            party = PoliticalParty(name=name)
            assert party.name == name
            assert str(party) == name

    def test_party_names_with_numbers(self) -> None:
        """Test party names with numbers."""
        number_names = [
            "第1党",
            "政党123",
            "2024年新党",
        ]

        for name in number_names:
            party = PoliticalParty(name=name)
            assert party.name == name

    def test_url_with_special_characters(self) -> None:
        """Test URLs with special characters."""
        urls_special = [
            "https://example.com/メンバー",
            "https://example.com/members/2024年",
            "https://example.com/members?sort=name&order=asc",
            "https://example.com/members#section",
        ]

        for url in urls_special:
            party = PoliticalParty(name="テスト政党", members_list_url=url)
            assert party.members_list_url == url

    def test_historical_parties(self) -> None:
        """Test historical political parties."""
        historical_parties = [
            "民主党",
            "民進党",
            "自由党",
            "希望の党",
        ]

        for name in historical_parties:
            party = PoliticalParty(name=name)
            assert party.name == name
