"""Tests for Speaker entity."""

from tests.fixtures.entity_factories import create_speaker

from src.domain.entities.speaker import Speaker


class TestSpeaker:
    """Test cases for Speaker entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        speaker = Speaker(name="山田太郎")

        assert speaker.name == "山田太郎"
        assert speaker.type is None
        assert speaker.political_party_name is None
        assert speaker.position is None
        assert speaker.is_politician is False
        assert speaker.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        speaker = Speaker(
            id=1,
            name="田中花子",
            type="議員",
            political_party_name="自由民主党",
            position="議長",
            is_politician=True,
        )

        assert speaker.id == 1
        assert speaker.name == "田中花子"
        assert speaker.type == "議員"
        assert speaker.political_party_name == "自由民主党"
        assert speaker.position == "議長"
        assert speaker.is_politician is True

    def test_str_representation_name_only(self) -> None:
        """Test string representation with name only."""
        speaker = Speaker(name="佐藤一郎")

        assert str(speaker) == "佐藤一郎"

    def test_str_representation_with_position(self) -> None:
        """Test string representation with position."""
        speaker = Speaker(name="鈴木二郎", position="副議長")

        assert str(speaker) == "鈴木二郎 (副議長)"

    def test_str_representation_with_party(self) -> None:
        """Test string representation with political party."""
        speaker = Speaker(name="高橋三郎", political_party_name="立憲民主党")

        assert str(speaker) == "高橋三郎 - 立憲民主党"

    def test_str_representation_with_position_and_party(self) -> None:
        """Test string representation with both position and party."""
        speaker = Speaker(
            name="伊藤四郎", position="委員長", political_party_name="公明党"
        )

        assert str(speaker) == "伊藤四郎 (委員長) - 公明党"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        speaker = create_speaker()

        assert speaker.id == 1
        assert speaker.name == "山田太郎"
        assert speaker.type == "議員"
        assert speaker.is_politician is True
        assert speaker.political_party_name is None
        assert speaker.position is None

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        speaker = create_speaker(
            id=99,
            name="渡辺五郎",
            type="市長",
            political_party_name="日本維新の会",
            position="市長",
            is_politician=True,
        )

        assert speaker.id == 99
        assert speaker.name == "渡辺五郎"
        assert speaker.type == "市長"
        assert speaker.political_party_name == "日本維新の会"
        assert speaker.position == "市長"
        assert speaker.is_politician is True

    def test_different_speaker_types(self) -> None:
        """Test different types of speakers."""
        # Politician speaker
        politician = Speaker(name="政治家太郎", type="議員", is_politician=True)
        assert politician.is_politician is True
        assert politician.type == "議員"

        # Government official
        official = Speaker(name="職員花子", type="職員", is_politician=False)
        assert official.is_politician is False
        assert official.type == "職員"

        # Citizen speaker
        citizen = Speaker(name="市民一郎", type="市民", is_politician=False)
        assert citizen.is_politician is False
        assert citizen.type == "市民"

    def test_various_positions(self) -> None:
        """Test various speaker positions."""
        positions = [
            "議長",
            "副議長",
            "委員長",
            "副委員長",
            "市長",
            "副市長",
            "知事",
            "副知事",
            "教育長",
            "部長",
            "課長",
            None,
        ]

        for position in positions:
            speaker = Speaker(name="Test Speaker", position=position)
            assert speaker.position == position

            if position:
                assert f"({position})" in str(speaker)
            else:
                assert "(" not in str(speaker)

    def test_various_political_parties(self) -> None:
        """Test various political party names."""
        parties = [
            "自由民主党",
            "立憲民主党",
            "公明党",
            "日本維新の会",
            "国民民主党",
            "日本共産党",
            "れいわ新選組",
            "社会民主党",
            "無所属",
            None,
        ]

        for party in parties:
            speaker = Speaker(name="Test Speaker", political_party_name=party)
            assert speaker.political_party_name == party

            if party:
                assert f"- {party}" in str(speaker)
            else:
                assert "-" not in str(speaker)

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Speaker properly inherits from BaseEntity."""
        speaker = create_speaker(id=42)

        # Check that id is properly set through BaseEntity
        assert speaker.id == 42

        # Create without id
        speaker_no_id = Speaker(name="Test Speaker")
        assert speaker_no_id.id is None

    def test_is_politician_flag_combinations(self) -> None:
        """Test various combinations with is_politician flag."""
        # Politician with party
        politician_with_party = Speaker(
            name="Party Politician",
            is_politician=True,
            political_party_name="Test Party",
        )
        assert politician_with_party.is_politician is True
        assert politician_with_party.political_party_name == "Test Party"

        # Politician without party (independent)
        independent = Speaker(
            name="Independent", is_politician=True, political_party_name=None
        )
        assert independent.is_politician is True
        assert independent.political_party_name is None

        # Non-politician with type
        non_politician = Speaker(name="Staff Member", is_politician=False, type="職員")
        assert non_politician.is_politician is False
        assert non_politician.type == "職員"

    def test_complex_speaker_scenarios(self) -> None:
        """Test complex real-world speaker scenarios."""
        # Mayor who is also a politician
        mayor = Speaker(
            name="市長太郎",
            type="市長",
            position="市長",
            political_party_name="自由民主党",
            is_politician=True,
        )
        assert str(mayor) == "市長太郎 (市長) - 自由民主党"

        # Committee chair
        chair = Speaker(
            name="委員長花子",
            type="議員",
            position="総務委員長",
            political_party_name="立憲民主党",
            is_politician=True,
        )
        assert str(chair) == "委員長花子 (総務委員長) - 立憲民主党"

        # Department head (non-politician)
        dept_head = Speaker(
            name="部長一郎", type="職員", position="総務部長", is_politician=False
        )
        assert str(dept_head) == "部長一郎 (総務部長)"

    def test_edge_cases(self) -> None:
        """Test edge cases for Speaker entity."""
        # Empty strings - they are falsy so won't appear in str representation
        speaker_empty = Speaker(
            name="Name", type="", political_party_name="", position=""
        )
        assert speaker_empty.type == ""
        assert speaker_empty.political_party_name == ""
        assert speaker_empty.position == ""
        # Empty strings are falsy and should not appear in str representation
        assert str(speaker_empty) == "Name"

        # Very long names
        long_name = "山" * 50
        speaker_long = Speaker(name=long_name)
        assert speaker_long.name == long_name
        assert str(speaker_long) == long_name

        # Special characters in name
        special_name = "山田・太郎（やまだ・たろう）"
        speaker_special = Speaker(name=special_name)
        assert speaker_special.name == special_name
        assert str(speaker_special) == special_name
