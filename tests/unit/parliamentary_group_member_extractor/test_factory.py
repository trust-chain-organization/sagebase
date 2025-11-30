"""Tests for ParliamentaryGroupMemberExtractor factory"""

from unittest.mock import patch

from src.infrastructure.external.parliamentary_group_member_extractor.factory import (  # noqa: E501
    ParliamentaryGroupMemberExtractorFactory,
)


class TestParliamentaryGroupMemberExtractorFactory:
    """Test cases for ParliamentaryGroupMemberExtractorFactory"""

    def test_create_pydantic_implementation_default(self):
        """Test that factory creates Pydantic implementation by default"""
        # USE_BAML_PARLIAMENTARY_GROUP_EXTRACTORが設定されていない場合、
        # Pydantic実装を返す（デフォルト）
        with patch.dict("os.environ", {}, clear=False):
            # USE_BAML_PARLIAMENTARY_GROUP_EXTRACTORを削除（もし存在すれば）
            import os

            os.environ.pop("USE_BAML_PARLIAMENTARY_GROUP_EXTRACTOR", None)
            extractor = ParliamentaryGroupMemberExtractorFactory.create()

            # Assert - should be PydanticParliamentaryGroupMemberExtractor (default)
            assert (
                extractor.__class__.__name__
                == "PydanticParliamentaryGroupMemberExtractor"
            )

    def test_create_pydantic_implementation_explicit_false(self):
        """Test that factory creates Pydantic implementation when explicitly disabled"""  # noqa: E501
        with patch.dict(
            "os.environ", {"USE_BAML_PARLIAMENTARY_GROUP_EXTRACTOR": "false"}
        ):
            extractor = ParliamentaryGroupMemberExtractorFactory.create()

            # Assert - should be PydanticParliamentaryGroupMemberExtractor
            assert (
                extractor.__class__.__name__
                == "PydanticParliamentaryGroupMemberExtractor"
            )

    def test_create_baml_implementation(self):
        """Test that factory creates BAML implementation when enabled"""
        with patch.dict(
            "os.environ", {"USE_BAML_PARLIAMENTARY_GROUP_EXTRACTOR": "true"}
        ):
            extractor = ParliamentaryGroupMemberExtractorFactory.create()

            # Assert - should be BAMLParliamentaryGroupMemberExtractor
            assert (
                extractor.__class__.__name__ == "BAMLParliamentaryGroupMemberExtractor"
            )

    def test_create_baml_implementation_case_insensitive(self):
        """Test that factory handles case-insensitive environment variable"""
        with patch.dict(
            "os.environ", {"USE_BAML_PARLIAMENTARY_GROUP_EXTRACTOR": "TRUE"}
        ):
            extractor = ParliamentaryGroupMemberExtractorFactory.create()

            # Assert - should be BAMLParliamentaryGroupMemberExtractor
            assert (
                extractor.__class__.__name__ == "BAMLParliamentaryGroupMemberExtractor"
            )
