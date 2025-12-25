"""Tests for MemberExtractorFactory"""

from src.infrastructure.external.conference_member_extractor.baml_extractor import (
    BAMLMemberExtractor,
)
from src.infrastructure.external.conference_member_extractor.factory import (
    MemberExtractorFactory,
)


class TestMemberExtractorFactory:
    """Test cases for MemberExtractorFactory

    Note: MemberExtractorFactory now always returns BAML implementation.
    Pydantic and A/B test implementations have been removed.
    """

    def test_create_returns_baml_extractor(self):
        """Factoryが常にBAML extractorを返すことを確認"""
        extractor = MemberExtractorFactory.create()
        assert isinstance(extractor, BAMLMemberExtractor)
