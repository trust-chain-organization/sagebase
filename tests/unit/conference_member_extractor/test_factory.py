"""Tests for MemberExtractorFactory"""

from unittest.mock import patch

from src.infrastructure.external.conference_member_extractor.ab_test_extractor import (
    ABTestMemberExtractor,
)
from src.infrastructure.external.conference_member_extractor.baml_extractor import (
    BAMLMemberExtractor,
)
from src.infrastructure.external.conference_member_extractor.factory import (
    MemberExtractorFactory,
)
from src.infrastructure.external.conference_member_extractor.pydantic_extractor import (
    PydanticMemberExtractor,
)


class TestMemberExtractorFactory:
    """Test cases for MemberExtractorFactory"""

    def test_create_pydantic_extractor_with_false_flags(self):
        """フラグがfalseの場合にPydantic extractorを返すことを確認"""
        with patch.dict(
            "os.environ",
            {
                "USE_BAML_MEMBER_EXTRACTION": "false",
                "ENABLE_MEMBER_EXTRACTION_AB_TEST": "false",
            },
        ):
            extractor = MemberExtractorFactory.create()
            assert isinstance(extractor, PydanticMemberExtractor)

    def test_create_baml_extractor_when_flag_enabled(self):
        """USE_BAML_MEMBER_EXTRACTION=trueでBAML extractorを返すことを確認"""
        with patch.dict(
            "os.environ",
            {
                "USE_BAML_MEMBER_EXTRACTION": "true",
                "ENABLE_MEMBER_EXTRACTION_AB_TEST": "false",
            },
        ):
            extractor = MemberExtractorFactory.create()
            assert isinstance(extractor, BAMLMemberExtractor)

    def test_create_baml_extractor_case_insensitive(self):
        """フラグの大文字小文字を区別しないことを確認"""
        with patch.dict(
            "os.environ",
            {
                "USE_BAML_MEMBER_EXTRACTION": "TRUE",
                "ENABLE_MEMBER_EXTRACTION_AB_TEST": "FALSE",
            },
        ):
            extractor = MemberExtractorFactory.create()
            assert isinstance(extractor, BAMLMemberExtractor)

    def test_create_ab_test_extractor_when_flag_enabled(self):
        """ENABLE_MEMBER_EXTRACTION_AB_TEST=trueでABTest extractorを返すことを確認"""
        with patch.dict(
            "os.environ",
            {
                "USE_BAML_MEMBER_EXTRACTION": "false",
                "ENABLE_MEMBER_EXTRACTION_AB_TEST": "true",
            },
        ):
            extractor = MemberExtractorFactory.create()
            assert isinstance(extractor, ABTestMemberExtractor)

    def test_ab_test_flag_takes_precedence(self):
        """ABテストフラグが優先されることを確認"""
        with patch.dict(
            "os.environ",
            {
                "USE_BAML_MEMBER_EXTRACTION": "true",
                "ENABLE_MEMBER_EXTRACTION_AB_TEST": "true",
            },
        ):
            extractor = MemberExtractorFactory.create()
            # ABテストフラグが優先される
            assert isinstance(extractor, ABTestMemberExtractor)

    def test_create_pydantic_with_invalid_flag_value(self):
        """無効なフラグ値の場合にPydantic extractorを返すことを確認"""
        with patch.dict(
            "os.environ",
            {
                "USE_BAML_MEMBER_EXTRACTION": "invalid",
                "ENABLE_MEMBER_EXTRACTION_AB_TEST": "maybe",
            },
        ):
            extractor = MemberExtractorFactory.create()
            assert isinstance(extractor, PydanticMemberExtractor)
