"""Tests for LLMLinkClassifierService."""

from unittest.mock import AsyncMock, patch

import pytest

from src.domain.services.interfaces.llm_link_classifier_service import (
    LinkClassificationResult,
    LinkType,
)
from src.domain.value_objects.link import Link
from src.infrastructure.external.llm_link_classifier_service import (
    LLMLinkClassifierService,
)


class TestLLMLinkClassifierService:
    """Test cases for LLMLinkClassifierService."""

    @pytest.fixture
    def sample_links(self):
        """Sample links for testing."""
        return [
            Link(
                url="https://example.com/members/tokyo",
                text="東京都",
                title="Tokyo Members",
            ),
            Link(
                url="https://example.com/members/osaka",
                text="大阪府",
                title="Osaka Members",
            ),
            Link(
                url="https://example.com/members", text="議員一覧", title="All Members"
            ),
        ]

    @pytest.mark.asyncio
    async def test_classify_links_success(self, sample_links):
        """Test successful link classification with BAML."""
        from baml_client import types

        # Mock BAML response
        mock_baml_results = [
            types.LinkClassification(
                url="https://example.com/members/tokyo",
                link_type="prefecture_list",
                confidence=0.95,
                reason="Contains prefecture name Tokyo",
            ),
            types.LinkClassification(
                url="https://example.com/members/osaka",
                link_type="prefecture_list",
                confidence=0.95,
                reason="Contains prefecture name Osaka",
            ),
            types.LinkClassification(
                url="https://example.com/members",
                link_type="member_list",
                confidence=0.9,
                reason="Contains keyword 'members' and '議員一覧'",
            ),
        ]

        with patch(
            "src.infrastructure.external.llm_link_classifier_service.b.ClassifyLinks",
            new_callable=AsyncMock,
        ) as mock_classify_links:
            mock_classify_links.return_value = mock_baml_results

            classifier = LLMLinkClassifierService()
            result = await classifier.classify_links(
                sample_links, party_name="Test Party", context="Member page"
            )

            # Verify result structure
            assert isinstance(result, LinkClassificationResult)
            assert len(result.classifications) == 3

            # Verify classifications
            assert result.classifications[0].link_type == LinkType.PREFECTURE_LIST
            assert result.classifications[0].confidence == 0.95
            assert result.classifications[1].link_type == LinkType.PREFECTURE_LIST
            assert result.classifications[2].link_type == LinkType.MEMBER_LIST

            # Verify summary
            assert result.summary["prefecture_list"] == 2
            assert result.summary["member_list"] == 1

    @pytest.mark.asyncio
    async def test_classify_links_empty_list(self):
        """Test classification with empty link list."""
        classifier = LLMLinkClassifierService()
        result = await classifier.classify_links([])

        assert len(result.classifications) == 0
        assert result.summary == {}

    @pytest.mark.asyncio
    async def test_classify_links_baml_error(self, sample_links):
        """Test handling of BAML service error."""
        # Mock BAML error
        with patch(
            "src.infrastructure.external.llm_link_classifier_service.b.ClassifyLinks",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.side_effect = Exception("BAML API error")

            classifier = LLMLinkClassifierService()
            result = await classifier.classify_links(sample_links)

            # Should return empty result on error
            assert len(result.classifications) == 0
            assert result.summary == {}

    @pytest.mark.asyncio
    async def test_classify_links_invalid_link_type(self, sample_links):
        """Test handling of invalid link_type in BAML response."""
        from baml_client import types

        # Mock BAML response with invalid link_type
        mock_baml_results = [
            types.LinkClassification(
                url="https://example.com/members",
                link_type="invalid_type",
                confidence=0.9,
                reason="Test",
            )
        ]

        with patch(
            "src.infrastructure.external.llm_link_classifier_service.b.ClassifyLinks",
            new_callable=AsyncMock,
        ) as mock_classify_links:
            mock_classify_links.return_value = mock_baml_results

            classifier = LLMLinkClassifierService()
            result = await classifier.classify_links([sample_links[0]])

            # Should fallback to OTHER type
            assert len(result.classifications) == 1
            assert result.classifications[0].link_type == LinkType.OTHER

    def test_filter_by_type_basic(self):
        """Test filtering by link type."""
        from src.domain.services.interfaces.llm_link_classifier_service import (
            LinkClassification,
        )

        # Create a sample result
        classifications = [
            LinkClassification(
                url="https://example.com/tokyo",
                link_type=LinkType.PREFECTURE_LIST,
                confidence=0.9,
                reason="Tokyo",
            ),
            LinkClassification(
                url="https://example.com/osaka",
                link_type=LinkType.PREFECTURE_LIST,
                confidence=0.85,
                reason="Osaka",
            ),
            LinkClassification(
                url="https://example.com/members",
                link_type=LinkType.MEMBER_LIST,
                confidence=0.95,
                reason="Members",
            ),
            LinkClassification(
                url="https://example.com/about",
                link_type=LinkType.OTHER,
                confidence=0.6,
                reason="Other",
            ),
        ]
        result = LinkClassificationResult(
            classifications=classifications,
            summary={"prefecture_list": 2, "member_list": 1, "other": 1},
        )

        classifier = LLMLinkClassifierService()

        # Filter for prefecture lists
        prefecture_urls = classifier.filter_by_type(result, [LinkType.PREFECTURE_LIST])
        assert len(prefecture_urls) == 2
        assert "https://example.com/tokyo" in prefecture_urls
        assert "https://example.com/osaka" in prefecture_urls

        # Filter for member lists
        member_urls = classifier.filter_by_type(result, [LinkType.MEMBER_LIST])
        assert len(member_urls) == 1
        assert "https://example.com/members" in member_urls

    def test_filter_by_type_with_confidence_threshold(self):
        """Test filtering with confidence threshold."""
        from src.domain.services.interfaces.llm_link_classifier_service import (
            LinkClassification,
        )

        classifications = [
            LinkClassification(
                url="https://example.com/high",
                link_type=LinkType.MEMBER_LIST,
                confidence=0.95,
                reason="High confidence",
            ),
            LinkClassification(
                url="https://example.com/medium",
                link_type=LinkType.MEMBER_LIST,
                confidence=0.75,
                reason="Medium confidence",
            ),
            LinkClassification(
                url="https://example.com/low",
                link_type=LinkType.MEMBER_LIST,
                confidence=0.5,
                reason="Low confidence",
            ),
        ]
        result = LinkClassificationResult(
            classifications=classifications, summary={"member_list": 3}
        )

        classifier = LLMLinkClassifierService()

        # Filter with high threshold
        high_confidence_urls = classifier.filter_by_type(
            result, [LinkType.MEMBER_LIST], min_confidence=0.8
        )
        assert len(high_confidence_urls) == 1
        assert "https://example.com/high" in high_confidence_urls

        # Filter with medium threshold
        medium_confidence_urls = classifier.filter_by_type(
            result, [LinkType.MEMBER_LIST], min_confidence=0.7
        )
        assert len(medium_confidence_urls) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
