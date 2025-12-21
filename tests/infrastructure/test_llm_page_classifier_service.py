"""Tests for LLM page classifier service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.value_objects.page_classification import PageClassification, PageType
from src.infrastructure.external.llm_page_classifier_service import (
    LLMPageClassifierService,
)


class TestLLMPageClassifierService:
    """Test LLM-based page classification service with BAML."""

    @pytest.mark.asyncio
    async def test_classify_index_page(self):
        """Test classifying an index page with BAML."""
        # Create mock BAML response
        mock_baml_result = Mock()
        mock_baml_result.page_type = "index_page"
        mock_baml_result.confidence = 0.9
        mock_baml_result.reason = "Page contains many prefecture links"
        mock_baml_result.has_child_links = True
        mock_baml_result.has_member_info = False

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            classifier = LLMPageClassifierService()
            result = await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="https://example.com/members",
                party_name="Test Party",
            )

            # Verify
            assert isinstance(result, PageClassification)
            assert result.page_type == PageType.INDEX_PAGE
            assert result.confidence == 0.9
            assert result.has_child_links is True
            assert result.has_member_info is False

    @pytest.mark.asyncio
    async def test_classify_member_list_page(self):
        """Test classifying a member list page with BAML."""
        # Create mock BAML response
        mock_baml_result = Mock()
        mock_baml_result.page_type = "member_list_page"
        mock_baml_result.confidence = 0.95
        mock_baml_result.reason = (
            "Contains multiple member profiles with names and positions"
        )
        mock_baml_result.has_child_links = False
        mock_baml_result.has_member_info = True

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            classifier = LLMPageClassifierService()
            result = await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="https://example.com/members/list",
                party_name="Test Party",
            )

            # Verify
            assert result.page_type == PageType.MEMBER_LIST_PAGE
            assert result.confidence == 0.95
            assert result.has_member_info is True

    @pytest.mark.asyncio
    async def test_classify_other_page(self):
        """Test classifying an other type page with BAML."""
        # Create mock BAML response
        mock_baml_result = Mock()
        mock_baml_result.page_type = "other"
        mock_baml_result.confidence = 0.8
        mock_baml_result.reason = "News page"
        mock_baml_result.has_child_links = False
        mock_baml_result.has_member_info = False

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            classifier = LLMPageClassifierService()
            result = await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="https://example.com/news",
                party_name="Test Party",
            )

            # Verify
            assert result.page_type == PageType.OTHER
            assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_empty_html_raises_error(self):
        """Test that empty HTML content raises ValueError."""
        classifier = LLMPageClassifierService()
        with pytest.raises(ValueError, match="HTML content cannot be empty"):
            await classifier.classify_page(
                html_content="",
                current_url="https://example.com",
            )

    @pytest.mark.asyncio
    async def test_empty_url_raises_error(self):
        """Test that empty URL raises ValueError."""
        classifier = LLMPageClassifierService()
        with pytest.raises(ValueError, match="Current URL cannot be empty"):
            await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="",
            )

    @pytest.mark.asyncio
    async def test_invalid_page_type_defaults_to_other(self):
        """Test that invalid page_type defaults to OTHER with BAML."""
        # Create mock BAML response with invalid page_type
        mock_baml_result = Mock()
        mock_baml_result.page_type = "invalid_type"
        mock_baml_result.confidence = 0.5
        mock_baml_result.reason = "Test"
        mock_baml_result.has_child_links = False
        mock_baml_result.has_member_info = False

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            classifier = LLMPageClassifierService()
            result = await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="https://example.com",
            )

            # Verify - should default to OTHER
            assert result.page_type == PageType.OTHER

    @pytest.mark.asyncio
    async def test_baml_error_returns_fallback(self):
        """Test that BAML errors return fallback classification."""
        # Mock BAML error
        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.side_effect = Exception("BAML API error")

            classifier = LLMPageClassifierService()
            result = await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="https://example.com",
            )

            # Verify - should return fallback
            assert result.page_type == PageType.OTHER
            assert result.confidence == 0.0
            assert "Failed to classify" in result.reason
