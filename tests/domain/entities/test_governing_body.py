"""Tests for GoverningBody entity."""

from tests.fixtures.entity_factories import create_governing_body

from src.domain.entities.governing_body import GoverningBody


class TestGoverningBody:
    """Test cases for GoverningBody entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        body = GoverningBody(name="東京都")

        assert body.name == "東京都"
        assert body.type is None
        assert body.organization_code is None
        assert body.organization_type is None
        assert body.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        body = GoverningBody(
            id=1,
            name="東京都",
            type="都道府県",
            organization_code="130001",
            organization_type="prefecture",
        )

        assert body.id == 1
        assert body.name == "東京都"
        assert body.type == "都道府県"
        assert body.organization_code == "130001"
        assert body.organization_type == "prefecture"

    def test_str_representation_with_type(self) -> None:
        """Test string representation when type is provided."""
        body = create_governing_body(name="大阪府", type="都道府県")

        assert str(body) == "大阪府 (都道府県)"

    def test_str_representation_without_type(self) -> None:
        """Test string representation when type is not provided."""
        body = GoverningBody(name="京都市")

        assert str(body) == "京都市"

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        body = create_governing_body()

        assert body.id == 1
        assert body.name == "東京都"
        assert body.type == "都道府県"
        assert body.organization_code == "130001"
        assert body.organization_type == "prefecture"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        body = create_governing_body(
            id=99,
            name="横浜市",
            type="市町村",
            organization_code="141003",
            organization_type="city",
        )

        assert body.id == 99
        assert body.name == "横浜市"
        assert body.type == "市町村"
        assert body.organization_code == "141003"
        assert body.organization_type == "city"

    def test_different_governing_body_types(self) -> None:
        """Test different types of governing bodies."""
        # National level
        national = GoverningBody(name="日本国", type="国", organization_type="national")
        assert national.name == "日本国"
        assert national.type == "国"
        assert str(national) == "日本国 (国)"

        # Prefecture level
        prefecture = GoverningBody(
            name="北海道",
            type="都道府県",
            organization_code="010006",
            organization_type="prefecture",
        )
        assert prefecture.name == "北海道"
        assert prefecture.organization_code == "010006"
        assert str(prefecture) == "北海道 (都道府県)"

        # City level
        city = GoverningBody(
            name="札幌市",
            type="市町村",
            organization_code="011002",
            organization_type="city",
        )
        assert city.name == "札幌市"
        assert city.organization_code == "011002"
        assert str(city) == "札幌市 (市町村)"

    def test_inheritance_from_base_entity(self) -> None:
        """Test that GoverningBody properly inherits from BaseEntity."""
        body = create_governing_body(id=42)

        # Check that id is properly set through BaseEntity
        assert body.id == 42

        # Create without id
        body_no_id = GoverningBody(name="Test City")
        assert body_no_id.id is None

    def test_organization_code_format(self) -> None:
        """Test various organization code formats."""
        # Standard 6-digit code
        standard = GoverningBody(name="Test1", organization_code="123456")
        assert standard.organization_code == "123456"

        # Code with leading zeros
        with_zeros = GoverningBody(name="Test2", organization_code="001234")
        assert with_zeros.organization_code == "001234"

        # No code
        no_code = GoverningBody(name="Test3")
        assert no_code.organization_code is None

    def test_all_prefecture_types(self) -> None:
        """Test all types of prefectures in Japan."""
        # 都 (Tokyo Metropolis)
        tokyo = GoverningBody(
            name="東京都", type="都道府県", organization_type="prefecture"
        )
        assert str(tokyo) == "東京都 (都道府県)"

        # 道 (Hokkaido)
        hokkaido = GoverningBody(
            name="北海道", type="都道府県", organization_type="prefecture"
        )
        assert str(hokkaido) == "北海道 (都道府県)"

        # 府 (Osaka/Kyoto)
        osaka = GoverningBody(
            name="大阪府", type="都道府県", organization_type="prefecture"
        )
        assert str(osaka) == "大阪府 (都道府県)"

        # 県 (Regular prefecture)
        kanagawa = GoverningBody(
            name="神奈川県", type="都道府県", organization_type="prefecture"
        )
        assert str(kanagawa) == "神奈川県 (都道府県)"

    def test_special_wards_and_towns(self) -> None:
        """Test special wards and towns."""
        # Special ward (Tokyo)
        shibuya = GoverningBody(
            name="渋谷区",
            type="特別区",
            organization_code="131130",
            organization_type="special_ward",
        )
        assert shibuya.name == "渋谷区"
        assert shibuya.type == "特別区"
        assert str(shibuya) == "渋谷区 (特別区)"

        # Town
        town = GoverningBody(
            name="箱根町",
            type="町",
            organization_code="143820",
            organization_type="town",
        )
        assert town.name == "箱根町"
        assert town.type == "町"
        assert str(town) == "箱根町 (町)"

        # Village
        village = GoverningBody(
            name="檜原村",
            type="村",
            organization_code="133078",
            organization_type="village",
        )
        assert village.name == "檜原村"
        assert village.type == "村"
        assert str(village) == "檜原村 (村)"
