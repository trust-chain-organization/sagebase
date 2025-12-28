"""Tests for ParliamentaryGroup entity."""

from tests.fixtures.entity_factories import create_parliamentary_group

from src.domain.entities.parliamentary_group import ParliamentaryGroup


class TestParliamentaryGroup:
    """Test cases for ParliamentaryGroup entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        group = ParliamentaryGroup(
            name="自民党議員団",
            conference_id=1,
        )

        assert group.name == "自民党議員団"
        assert group.conference_id == 1
        assert group.url is None
        assert group.description is None
        assert group.is_active is True  # Default value
        assert group.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        group = ParliamentaryGroup(
            id=10,
            name="立憲民主党会派",
            conference_id=5,
            url="https://example.com/group",
            description="立憲民主党所属の議員で構成される会派",
            is_active=False,
        )

        assert group.id == 10
        assert group.name == "立憲民主党会派"
        assert group.conference_id == 5
        assert group.url == "https://example.com/group"
        assert group.description == "立憲民主党所属の議員で構成される会派"
        assert group.is_active is False

    def test_str_representation(self) -> None:
        """Test string representation."""
        group = ParliamentaryGroup(
            name="公明党議員団",
            conference_id=1,
        )
        assert str(group) == "公明党議員団"

        group_with_id = ParliamentaryGroup(
            id=42,
            name="日本維新の会",
            conference_id=2,
        )
        assert str(group_with_id) == "日本維新の会"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        group = create_parliamentary_group()

        assert group.id == 1
        assert group.name == "自民党議員団"
        assert group.conference_id == 1
        assert group.description is None
        assert group.is_active is True

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        group = create_parliamentary_group(
            id=99,
            name="国民民主党会派",
            conference_id=10,
            url="https://example.com/kokumin",
            description="国民民主党の議員団",
            is_active=False,
        )

        assert group.id == 99
        assert group.name == "国民民主党会派"
        assert group.conference_id == 10
        assert group.url == "https://example.com/kokumin"
        assert group.description == "国民民主党の議員団"
        assert group.is_active is False

    def test_various_group_names(self) -> None:
        """Test various parliamentary group names."""
        names = [
            "自由民主党議員団",
            "立憲民主党会派",
            "公明党議員団",
            "日本維新の会",
            "国民民主党会派",
            "日本共産党議員団",
            "れいわ新選組",
            "無所属の会",
            "市民クラブ",
            "改革ネット",
        ]

        for name in names:
            group = ParliamentaryGroup(name=name, conference_id=1)
            assert group.name == name
            assert str(group) == name

    def test_is_active_flag(self) -> None:
        """Test is_active flag variations."""
        # Default is True
        group_default = ParliamentaryGroup(
            name="Test Group",
            conference_id=1,
        )
        assert group_default.is_active is True

        # Explicitly set to True
        group_active = ParliamentaryGroup(
            name="Active Group",
            conference_id=1,
            is_active=True,
        )
        assert group_active.is_active is True

        # Explicitly set to False
        group_inactive = ParliamentaryGroup(
            name="Inactive Group",
            conference_id=1,
            is_active=False,
        )
        assert group_inactive.is_active is False

    def test_url_formats(self) -> None:
        """Test various URL formats."""
        urls = [
            "https://example.com/group",
            "http://city.jp/council/groups/1",
            "https://www.group-website.com/",
            None,
        ]

        for url in urls:
            group = ParliamentaryGroup(
                name="Test Group",
                conference_id=1,
                url=url,
            )
            assert group.url == url

    def test_description_variations(self) -> None:
        """Test various description formats."""
        descriptions = [
            "自由民主党所属の議員で構成される会派",
            "市民の声を代表する議員団",
            "改革を目指す超党派の会派",
            "",
            None,
        ]

        for desc in descriptions:
            group = ParliamentaryGroup(
                name="Test Group",
                conference_id=1,
                description=desc,
            )
            assert group.description == desc

    def test_conference_id_variations(self) -> None:
        """Test various conference IDs."""
        ids = [1, 10, 100, 1000, 9999]

        for conf_id in ids:
            group = ParliamentaryGroup(
                name="Test Group",
                conference_id=conf_id,
            )
            assert group.conference_id == conf_id

    def test_inheritance_from_base_entity(self) -> None:
        """Test that ParliamentaryGroup properly inherits from BaseEntity."""
        group = create_parliamentary_group(id=42)

        # Check that id is properly set through BaseEntity
        assert group.id == 42

        # Create without id
        group_no_id = ParliamentaryGroup(
            name="Test Group",
            conference_id=1,
        )
        assert group_no_id.id is None

    def test_complex_group_scenarios(self) -> None:
        """Test complex real-world parliamentary group scenarios."""
        # Major party group
        major_party = ParliamentaryGroup(
            id=1,
            name="自由民主党議員団",
            conference_id=1,
            url="https://example.com/ldp-group",
            description="自由民主党所属議員で構成される最大会派",
            is_active=True,
        )
        assert str(major_party) == "自由民主党議員団"
        assert major_party.is_active is True

        # Opposition group
        opposition = ParliamentaryGroup(
            id=2,
            name="立憲民主党・無所属の会",
            conference_id=1,
            url="https://example.com/cdp-group",
            description="立憲民主党と無所属議員による野党第一会派",
            is_active=True,
        )
        assert str(opposition) == "立憲民主党・無所属の会"

        # Dissolved group
        dissolved = ParliamentaryGroup(
            id=3,
            name="旧民主党会派",
            conference_id=1,
            description="2016年に解散した会派",
            is_active=False,
        )
        assert dissolved.is_active is False

    def test_edge_cases(self) -> None:
        """Test edge cases for ParliamentaryGroup entity."""
        # Empty strings
        group_empty = ParliamentaryGroup(
            name="Name",
            conference_id=1,
            url="",
            description="",
        )
        assert group_empty.name == "Name"
        assert group_empty.url == ""
        assert group_empty.description == ""

        # Very long name
        long_name = "自由民主党" * 50
        group_long = ParliamentaryGroup(
            name=long_name,
            conference_id=1,
        )
        assert group_long.name == long_name
        assert str(group_long) == long_name

        # Special characters in name
        special_name = "立憲民主党・無所属の会（市民派）"
        group_special = ParliamentaryGroup(
            name=special_name,
            conference_id=1,
        )
        assert group_special.name == special_name
        assert str(group_special) == special_name

        # Very long URL
        long_url = "https://example.com/" + "a" * 200
        group_long_url = ParliamentaryGroup(
            name="Test",
            conference_id=1,
            url=long_url,
        )
        assert group_long_url.url == long_url

        # Very long description
        long_desc = "説明" * 100
        group_long_desc = ParliamentaryGroup(
            name="Test",
            conference_id=1,
            description=long_desc,
        )
        assert group_long_desc.description == long_desc

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        group = ParliamentaryGroup(
            name="Test Group",
            conference_id=1,
            url=None,
            description=None,
        )

        assert group.url is None
        assert group.description is None
        assert group.is_active is True  # Default value

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        group1 = ParliamentaryGroup(name="Test 1", conference_id=1)
        assert group1.id is None

        # With ID
        group2 = ParliamentaryGroup(name="Test 2", conference_id=1, id=100)
        assert group2.id == 100

        # ID can be any integer
        group3 = ParliamentaryGroup(name="Test 3", conference_id=1, id=999999)
        assert group3.id == 999999

    def test_coalition_and_opposition_groups(self) -> None:
        """Test coalition and opposition group patterns."""
        # Coalition group
        coalition = ParliamentaryGroup(
            name="与党会派",
            conference_id=1,
            description="自民党と公明党による連立与党会派",
            is_active=True,
        )
        assert coalition.is_active is True

        # Opposition group
        opposition = ParliamentaryGroup(
            name="野党統一会派",
            conference_id=1,
            description="野党各党による統一会派",
            is_active=True,
        )
        assert opposition.is_active is True

        # Independent group
        independent = ParliamentaryGroup(
            name="無所属の会",
            conference_id=1,
            description="無所属議員による会派",
            is_active=True,
        )
        assert independent.name == "無所属の会"

    def test_regional_group_patterns(self) -> None:
        """Test regional parliamentary group patterns."""
        # Prefectural group
        prefectural = ParliamentaryGroup(
            name="都民ファーストの会",
            conference_id=1,
            description="東京都議会における地域政党",
            is_active=True,
        )
        assert prefectural.name == "都民ファーストの会"

        # City council group
        city = ParliamentaryGroup(
            name="市民の声",
            conference_id=2,
            description="市民の声を代表する会派",
            is_active=True,
        )
        assert city.name == "市民の声"

        # Reform group
        reform = ParliamentaryGroup(
            name="改革ネット",
            conference_id=3,
            description="地方議会改革を目指す超党派の会派",
            is_active=True,
        )
        assert reform.name == "改革ネット"
