"""Tests for parliamentary group member DTOs"""

from datetime import datetime

import pytest

from src.application.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
    ParliamentaryGroupMemberExtractionResultDTO,
)


class TestExtractedParliamentaryGroupMemberDTO:
    """Test cases for ExtractedParliamentaryGroupMemberDTO"""

    def test_create_with_all_fields(self):
        """Test creating DTO with all fields"""
        dto = ExtractedParliamentaryGroupMemberDTO(
            name="山田太郎",
            role="団長",
            party_name="自民党",
            district="東京都第1区",
            additional_info="備考あり",
        )

        assert dto.name == "山田太郎"
        assert dto.role == "団長"
        assert dto.party_name == "自民党"
        assert dto.district == "東京都第1区"
        assert dto.additional_info == "備考あり"

    def test_create_with_required_fields_only(self):
        """Test creating DTO with only required fields"""
        dto = ExtractedParliamentaryGroupMemberDTO(name="田中花子")

        assert dto.name == "田中花子"
        assert dto.role is None
        assert dto.party_name is None
        assert dto.district is None
        assert dto.additional_info is None

    def test_name_is_required(self):
        """Test that name field is required"""
        # dataclass requires name parameter, TypeError is raised if missing
        with pytest.raises(TypeError):
            ExtractedParliamentaryGroupMemberDTO()  # type: ignore

    def test_optional_fields_default_to_none(self):
        """Test that optional fields default to None"""
        dto = ExtractedParliamentaryGroupMemberDTO(name="佐藤次郎")

        # All optional fields should be None
        assert dto.role is None
        assert dto.party_name is None
        assert dto.district is None
        assert dto.additional_info is None

    def test_dto_is_mutable(self):
        """Test that DTO can be updated (Pydantic allows assignment)"""
        dto = ExtractedParliamentaryGroupMemberDTO(name="高橋花子")
        # Pydantic allows field assignment by default
        dto.role = "副団長"
        assert dto.role == "副団長"


class TestParliamentaryGroupMemberExtractionResultDTO:
    """Test cases for ParliamentaryGroupMemberExtractionResultDTO"""

    def test_create_success_result(self):
        """Test creating successful extraction result"""
        members = [
            ExtractedParliamentaryGroupMemberDTO(name="山田太郎", role="団長"),
            ExtractedParliamentaryGroupMemberDTO(name="田中花子"),
        ]
        extraction_date = datetime(2024, 1, 15, 10, 30, 0)

        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com/members",
            extracted_members=members,
            extraction_date=extraction_date,
            error=None,
        )

        assert result.parliamentary_group_id == 1
        assert result.url == "https://example.com/members"
        assert len(result.extracted_members) == 2
        assert result.extracted_members[0].name == "山田太郎"
        assert result.extraction_date == extraction_date
        assert result.error is None

    def test_create_error_result(self):
        """Test creating error result"""
        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com/members",
            extracted_members=[],
            error="HTMLの取得に失敗しました",
        )

        assert result.parliamentary_group_id == 1
        assert result.url == "https://example.com/members"
        assert result.extracted_members == []
        assert result.extraction_date is None
        assert result.error == "HTMLの取得に失敗しました"

    def test_parliamentary_group_id_is_required(self):
        """Test that parliamentary_group_id is required"""
        # dataclass requires all non-default parameters
        with pytest.raises(TypeError):
            ParliamentaryGroupMemberExtractionResultDTO(  # type: ignore
                url="https://example.com", extracted_members=[]
            )

    def test_url_is_required(self):
        """Test that url is required"""
        # dataclass requires all non-default parameters
        with pytest.raises(TypeError):
            ParliamentaryGroupMemberExtractionResultDTO(  # type: ignore
                parliamentary_group_id=1, extracted_members=[]
            )

    def test_extracted_members_is_required(self):
        """Test that extracted_members is required"""
        # dataclass requires all non-default parameters
        with pytest.raises(TypeError):
            ParliamentaryGroupMemberExtractionResultDTO(  # type: ignore
                parliamentary_group_id=1, url="https://example.com"
            )

    def test_extraction_date_defaults_to_none(self):
        """Test that extraction_date defaults to None"""
        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com",
            extracted_members=[],
        )

        assert result.extraction_date is None

    def test_error_defaults_to_none(self):
        """Test that error defaults to None"""
        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com",
            extracted_members=[],
        )

        assert result.error is None

    def test_empty_members_list_is_valid(self):
        """Test that empty extracted_members list is valid"""
        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com",
            extracted_members=[],
        )

        assert result.extracted_members == []
        assert isinstance(result.extracted_members, list)

    def test_members_list_with_multiple_items(self):
        """Test result with multiple members"""
        members = [
            ExtractedParliamentaryGroupMemberDTO(name=f"議員{i}", role=f"役職{i}")
            for i in range(5)
        ]

        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com",
            extracted_members=members,
        )

        assert len(result.extracted_members) == 5
        assert all(
            isinstance(m, ExtractedParliamentaryGroupMemberDTO)
            for m in result.extracted_members
        )

    def test_result_with_extraction_date_and_error_both_set(self):
        """Test result can have both extraction_date and error (unusual but valid)"""
        extraction_date = datetime(2024, 1, 15, 10, 30, 0)

        result = ParliamentaryGroupMemberExtractionResultDTO(
            parliamentary_group_id=1,
            url="https://example.com",
            extracted_members=[],
            extraction_date=extraction_date,
            error="部分的なエラー",
        )

        assert result.extraction_date == extraction_date
        assert result.error == "部分的なエラー"
