"""Tests for ParliamentaryGroupMemberExtractor factory"""

from src.infrastructure.external.parliamentary_group_member_extractor.factory import (  # noqa: E501
    ParliamentaryGroupMemberExtractorFactory,
)


class TestParliamentaryGroupMemberExtractorFactory:
    """Test cases for ParliamentaryGroupMemberExtractorFactory"""

    def test_create_baml_implementation(self):
        """Test that factory creates BAML implementation"""
        extractor = ParliamentaryGroupMemberExtractorFactory.create()

        # Assert - should be BAMLParliamentaryGroupMemberExtractor
        assert extractor.__class__.__name__ == "BAMLParliamentaryGroupMemberExtractor"
