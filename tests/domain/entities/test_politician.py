"""Tests for Politician entity."""

from tests.fixtures.entity_factories import create_politician

from src.domain.entities.politician import Politician


class TestPolitician:
    """Test cases for Politician entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        politician = Politician(name="山田太郎")

        assert politician.name == "山田太郎"
        assert politician.political_party_id is None
        assert politician.furigana is None
        assert politician.district is None
        assert politician.profile_page_url is None
        assert politician.party_position is None
        assert politician.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        politician = Politician(
            id=1,
            name="田中花子",
            political_party_id=10,
            furigana="たなかはなこ",
            district="東京1区",
            profile_page_url="https://example.com/tanaka",
            party_position="幹事長",
        )

        assert politician.id == 1
        assert politician.name == "田中花子"
        assert politician.political_party_id == 10
        assert politician.furigana == "たなかはなこ"
        assert politician.district == "東京1区"
        assert politician.profile_page_url == "https://example.com/tanaka"
        assert politician.party_position == "幹事長"

    def test_str_representation(self) -> None:
        """Test string representation."""
        politician = Politician(name="佐藤一郎")
        assert str(politician) == "佐藤一郎"

        politician_with_id = Politician(id=42, name="鈴木二郎")
        assert str(politician_with_id) == "鈴木二郎"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        politician = create_politician()

        assert politician.id == 1
        assert politician.name == "山田太郎"
        assert politician.political_party_id is None
        assert politician.furigana is None
        assert politician.district is None
        assert politician.profile_page_url is None
        assert politician.party_position is None

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        politician = create_politician(
            id=99,
            name="渡辺五郎",
            political_party_id=5,
            furigana="わたなべごろう",
            district="大阪3区",
            profile_page_url="https://example.com/watanabe",
            party_position="政調会長",
        )

        assert politician.id == 99
        assert politician.name == "渡辺五郎"
        assert politician.political_party_id == 5
        assert politician.furigana == "わたなべごろう"
        assert politician.district == "大阪3区"
        assert politician.profile_page_url == "https://example.com/watanabe"
        assert politician.party_position == "政調会長"

    def test_different_political_parties(self) -> None:
        """Test politicians with different political parties."""
        # Politician with party
        ldp_politician = Politician(name="自民太郎", political_party_id=1)
        assert ldp_politician.political_party_id == 1

        # Independent politician
        independent = Politician(name="無所属花子", political_party_id=None)
        assert independent.political_party_id is None

    def test_various_districts(self) -> None:
        """Test various district formats."""
        districts = [
            "東京1区",
            "大阪10区",
            "北海道比例",
            "全国比例",
            "参議院東京選挙区",
            "参議院全国比例",
            None,
        ]

        for district in districts:
            politician = Politician(name="Test Politician", district=district)
            assert politician.district == district

    def test_various_party_positions(self) -> None:
        """Test various party positions."""
        positions = [
            "総裁",
            "幹事長",
            "政調会長",
            "国対委員長",
            "選対委員長",
            "広報本部長",
            "青年局長",
            "女性局長",
            None,
        ]

        for position in positions:
            politician = Politician(name="Test Politician", party_position=position)
            assert politician.party_position == position

    def test_profile_url_formats(self) -> None:
        """Test various profile URL formats."""
        urls = [
            "https://example.com/profile",
            "http://party.jp/members/12345",
            "https://www.politician-site.com/",
            None,
        ]

        for url in urls:
            politician = Politician(name="Test Politician", profile_page_url=url)
            assert politician.profile_page_url == url

    def test_furigana_variations(self) -> None:
        """Test various furigana formats."""
        test_cases = [
            ("山田太郎", "やまだたろう"),
            ("田中花子", "たなかはなこ"),
            ("鈴木一郎", "すずきいちろう"),
            ("佐藤美咲", "さとうみさき"),
        ]

        for name, furigana in test_cases:
            politician = Politician(name=name, furigana=furigana)
            assert politician.name == name
            assert politician.furigana == furigana

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Politician properly inherits from BaseEntity."""
        politician = create_politician(id=42)

        # Check that id is properly set through BaseEntity
        assert politician.id == 42

        # Create without id
        politician_no_id = Politician(name="Test Politician")
        assert politician_no_id.id is None

    def test_complex_politician_scenarios(self) -> None:
        """Test complex real-world politician scenarios."""
        # Party leader
        party_leader = Politician(
            name="党首太郎",
            political_party_id=1,
            furigana="とうしゅたろう",
            district="東京1区",
            profile_page_url="https://example.com/leader",
            party_position="総裁",
        )
        assert party_leader.name == "党首太郎"
        assert party_leader.party_position == "総裁"
        assert str(party_leader) == "党首太郎"

        # Independent politician
        independent = Politician(
            name="無所属花子",
            political_party_id=None,
            furigana="むしょぞくはなこ",
            district="大阪3区",
            profile_page_url="https://example.com/independent",
            party_position=None,
        )
        assert independent.political_party_id is None
        assert independent.party_position is None

        # Proportional representation politician
        pr_politician = Politician(
            name="比例一郎",
            political_party_id=2,
            furigana="ひれいいちろう",
            district="全国比例",
            profile_page_url="https://example.com/pr",
            party_position="広報本部長",
        )
        assert pr_politician.district == "全国比例"

    def test_edge_cases(self) -> None:
        """Test edge cases for Politician entity."""
        # Empty strings
        politician_empty = Politician(
            name="Name",
            furigana="",
            district="",
            profile_page_url="",
            party_position="",
        )
        assert politician_empty.name == "Name"
        assert politician_empty.furigana == ""
        assert politician_empty.district == ""
        assert politician_empty.profile_page_url == ""
        assert politician_empty.party_position == ""

        # Very long names
        long_name = "山" * 50
        politician_long = Politician(name=long_name)
        assert politician_long.name == long_name
        assert str(politician_long) == long_name

        # Special characters in name
        special_name = "山田・太郎（やまだ・たろう）"
        politician_special = Politician(name=special_name)
        assert politician_special.name == special_name
        assert str(politician_special) == special_name

        # Very long URL
        long_url = "https://example.com/" + "a" * 200
        politician_long_url = Politician(name="Test", profile_page_url=long_url)
        assert politician_long_url.profile_page_url == long_url

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        politician = Politician(
            name="Test Politician",
            political_party_id=None,
            furigana=None,
            district=None,
            profile_page_url=None,
            party_position=None,
        )

        assert politician.political_party_id is None
        assert politician.furigana is None
        assert politician.district is None
        assert politician.profile_page_url is None
        assert politician.party_position is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        politician1 = Politician(name="Test 1")
        assert politician1.id is None

        # With ID
        politician2 = Politician(name="Test 2", id=100)
        assert politician2.id == 100

        # ID can be any integer
        politician3 = Politician(name="Test 3", id=999999)
        assert politician3.id == 999999
