"""Tests for PartyMemberExtractionService domain service."""

from unittest.mock import AsyncMock

import pytest

from src.domain.services.party_member_extraction_service import (
    ExtractedMember,
    IPartyMemberExtractionService,
    MemberExtractionResult,
)


class TestExtractedMember:
    """Test cases for ExtractedMember dataclass."""

    def test_initialization_with_required_fields(self) -> None:
        """Test dataclass initialization with required fields only."""
        member = ExtractedMember(name="山田太郎")

        assert member.name == "山田太郎"
        assert member.position is None
        assert member.electoral_district is None
        assert member.prefecture is None
        assert member.profile_url is None
        assert member.party_position is None

    def test_initialization_with_all_fields(self) -> None:
        """Test dataclass initialization with all fields."""
        member = ExtractedMember(
            name="田中花子",
            position="参議院議員",
            electoral_district="東京都選挙区",
            prefecture="東京都",
            profile_url="https://example.com/tanaka",
            party_position="幹事長",
        )

        assert member.name == "田中花子"
        assert member.position == "参議院議員"
        assert member.electoral_district == "東京都選挙区"
        assert member.prefecture == "東京都"
        assert member.profile_url == "https://example.com/tanaka"
        assert member.party_position == "幹事長"

    def test_various_positions(self) -> None:
        """Test various position values."""
        positions = [
            "衆議院議員",
            "参議院議員",
            "地方議員",
            "都道府県議会議員",
            "市区町村議会議員",
            None,
        ]

        for position in positions:
            member = ExtractedMember(name="テスト", position=position)
            assert member.position == position

    def test_various_electoral_districts(self) -> None:
        """Test various electoral district values."""
        districts = [
            "東京1区",
            "大阪10区",
            "北海道比例",
            "全国比例",
            "東京都選挙区",
            "参議院全国比例",
            None,
        ]

        for district in districts:
            member = ExtractedMember(name="テスト", electoral_district=district)
            assert member.electoral_district == district

    def test_various_party_positions(self) -> None:
        """Test various party position values."""
        party_positions = [
            "総裁",
            "幹事長",
            "政調会長",
            "総務会長",
            "国対委員長",
            "代表",
            "副代表",
            None,
        ]

        for party_position in party_positions:
            member = ExtractedMember(name="テスト", party_position=party_position)
            assert member.party_position == party_position

    def test_edge_cases(self) -> None:
        """Test edge cases for ExtractedMember."""
        # Empty strings
        member_empty = ExtractedMember(
            name="テスト",
            position="",
            electoral_district="",
            prefecture="",
            profile_url="",
            party_position="",
        )
        assert member_empty.position == ""

        # Very long name
        long_name = "山田" * 50
        member_long = ExtractedMember(name=long_name)
        assert member_long.name == long_name

        # Special characters
        special_name = "山田・太郎（やまだ・たろう）"
        member_special = ExtractedMember(name=special_name)
        assert member_special.name == special_name


class TestMemberExtractionResult:
    """Test cases for MemberExtractionResult dataclass."""

    def test_initialization_successful_extraction(self) -> None:
        """Test successful extraction result."""
        members = [
            ExtractedMember(name="山田太郎", position="衆議院議員"),
            ExtractedMember(name="田中花子", position="参議院議員"),
        ]

        result = MemberExtractionResult(
            members=members,
            source_url="https://example.com/members",
            extraction_successful=True,
        )

        assert len(result.members) == 2
        assert result.source_url == "https://example.com/members"
        assert result.extraction_successful is True
        assert result.error_message is None

    def test_initialization_failed_extraction(self) -> None:
        """Test failed extraction result."""
        result = MemberExtractionResult(
            members=[],
            source_url="https://example.com/members",
            extraction_successful=False,
            error_message="Failed to parse HTML",
        )

        assert len(result.members) == 0
        assert result.extraction_successful is False
        assert result.error_message == "Failed to parse HTML"

    def test_empty_members_list(self) -> None:
        """Test result with empty members list."""
        result = MemberExtractionResult(
            members=[],
            source_url="https://example.com/empty",
            extraction_successful=True,
        )

        assert len(result.members) == 0
        assert result.extraction_successful is True

    def test_large_members_list(self) -> None:
        """Test result with large number of members."""
        members = [ExtractedMember(name=f"議員{i}") for i in range(100)]

        result = MemberExtractionResult(
            members=members,
            source_url="https://example.com/members",
            extraction_successful=True,
        )

        assert len(result.members) == 100

    def test_various_error_messages(self) -> None:
        """Test various error messages."""
        error_messages = [
            "HTMLパースエラー",
            "タイムアウト",
            "ネットワークエラー",
            "不正なHTML構造",
            None,
        ]

        for error_msg in error_messages:
            result = MemberExtractionResult(
                members=[],
                source_url="https://example.com",
                extraction_successful=error_msg is None,
                error_message=error_msg,
            )
            assert result.error_message == error_msg


class MockPartyMemberExtractionService(IPartyMemberExtractionService):
    """Mock implementation of IPartyMemberExtractionService for testing."""

    def __init__(self) -> None:
        self.mock = AsyncMock(
            return_value=MemberExtractionResult(
                members=[],
                source_url="",
                extraction_successful=True,
            )
        )

    async def extract_from_html(
        self,
        html_content: str,
        source_url: str,
        party_name: str,
    ) -> MemberExtractionResult:
        """Mock implementation of extract_from_html."""
        return await self.mock(
            html_content=html_content,
            source_url=source_url,
            party_name=party_name,
        )


class TestIPartyMemberExtractionService:
    """Test cases for IPartyMemberExtractionService interface."""

    @pytest.mark.asyncio
    async def test_interface_implementation(self) -> None:
        """Test that mock service implements the interface correctly."""
        service = MockPartyMemberExtractionService()

        # Verify the service has the required method
        assert hasattr(service, "extract_from_html")
        assert callable(service.extract_from_html)
        assert hasattr(service, "mock")

    @pytest.mark.asyncio
    async def test_extract_from_html_success(self) -> None:
        """Test successful extraction from HTML."""
        service = MockPartyMemberExtractionService()

        # Configure mock to return test data
        test_members = [
            ExtractedMember(
                name="山田太郎",
                position="衆議院議員",
                electoral_district="東京1区",
            ),
            ExtractedMember(
                name="田中花子",
                position="参議院議員",
                electoral_district="東京都選挙区",
            ),
        ]

        service.mock.return_value = MemberExtractionResult(
            members=test_members,
            source_url="https://example.com/members",
            extraction_successful=True,
        )

        # Call the method
        result = await service.extract_from_html(
            html_content="<html>...</html>",
            source_url="https://example.com/members",
            party_name="自由民主党",
        )

        # Verify result
        assert len(result.members) == 2
        assert result.extraction_successful is True
        assert result.error_message is None
        assert result.members[0].name == "山田太郎"
        assert result.members[1].name == "田中花子"

    @pytest.mark.asyncio
    async def test_extract_from_html_failure(self) -> None:
        """Test failed extraction from HTML."""
        service = MockPartyMemberExtractionService()

        # Configure mock to return failure
        service.mock.return_value = MemberExtractionResult(
            members=[],
            source_url="https://example.com/members",
            extraction_successful=False,
            error_message="Failed to parse HTML structure",
        )

        # Call the method
        result = await service.extract_from_html(
            html_content="<html>invalid</html>",
            source_url="https://example.com/members",
            party_name="自由民主党",
        )

        # Verify result
        assert len(result.members) == 0
        assert result.extraction_successful is False
        assert result.error_message == "Failed to parse HTML structure"

    @pytest.mark.asyncio
    async def test_extract_from_html_call_verification(self) -> None:
        """Test that extract_from_html is called with correct parameters."""
        service = MockPartyMemberExtractionService()

        html_content = "<html><body>Members list</body></html>"
        source_url = "https://example.com/members"
        party_name = "立憲民主党"

        await service.extract_from_html(
            html_content=html_content,
            source_url=source_url,
            party_name=party_name,
        )

        # Verify the method was called with correct arguments
        service.mock.assert_called_once_with(
            html_content=html_content,
            source_url=source_url,
            party_name=party_name,
        )

    @pytest.mark.asyncio
    async def test_extract_from_html_multiple_calls(self) -> None:
        """Test multiple calls to extract_from_html."""
        service = MockPartyMemberExtractionService()

        # Configure different return values
        service.mock.side_effect = [
            MemberExtractionResult(
                members=[ExtractedMember(name="議員1")],
                source_url="https://example.com/page1",
                extraction_successful=True,
            ),
            MemberExtractionResult(
                members=[ExtractedMember(name="議員2"), ExtractedMember(name="議員3")],
                source_url="https://example.com/page2",
                extraction_successful=True,
            ),
        ]

        # First call
        result1 = await service.extract_from_html(
            html_content="<html>page1</html>",
            source_url="https://example.com/page1",
            party_name="政党A",
        )
        assert len(result1.members) == 1
        assert result1.members[0].name == "議員1"

        # Second call
        result2 = await service.extract_from_html(
            html_content="<html>page2</html>",
            source_url="https://example.com/page2",
            party_name="政党B",
        )
        assert len(result2.members) == 2
        assert result2.members[0].name == "議員2"
        assert result2.members[1].name == "議員3"

        # Verify called twice
        assert service.mock.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_with_various_parties(self) -> None:
        """Test extraction for various political parties."""
        service = MockPartyMemberExtractionService()

        parties = [
            "自由民主党",
            "立憲民主党",
            "公明党",
            "日本共産党",
            "日本維新の会",
        ]

        for party_name in parties:
            service.mock.return_value = MemberExtractionResult(
                members=[ExtractedMember(name=f"{party_name}議員")],
                source_url=f"https://example.com/{party_name}",
                extraction_successful=True,
            )

            result = await service.extract_from_html(
                html_content="<html>members</html>",
                source_url=f"https://example.com/{party_name}",
                party_name=party_name,
            )

            assert result.extraction_successful is True
            assert len(result.members) == 1

    @pytest.mark.asyncio
    async def test_extract_with_complex_member_data(self) -> None:
        """Test extraction with complex member data."""
        service = MockPartyMemberExtractionService()

        complex_members = [
            ExtractedMember(
                name="山田太郎",
                position="衆議院議員",
                electoral_district="東京1区",
                prefecture="東京都",
                profile_url="https://example.com/yamada",
                party_position="幹事長",
            ),
            ExtractedMember(
                name="田中花子",
                position="参議院議員",
                electoral_district="大阪府選挙区",
                prefecture="大阪府",
                profile_url="https://example.com/tanaka",
                party_position="政調会長",
            ),
        ]

        service.mock.return_value = MemberExtractionResult(
            members=complex_members,
            source_url="https://example.com/members",
            extraction_successful=True,
        )

        result = await service.extract_from_html(
            html_content="<html>complex members</html>",
            source_url="https://example.com/members",
            party_name="自由民主党",
        )

        assert len(result.members) == 2
        assert all(m.profile_url is not None for m in result.members)
        assert all(m.party_position is not None for m in result.members)
