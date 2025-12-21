"""Integration tests for page classification workflow.

These tests verify the end-to-end flow from HTML content through
classification to navigation decision.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.domain.value_objects.page_classification import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    PageType,
)
from src.infrastructure.external.langgraph_nodes.decision_node import (
    should_explore_children,
)
from src.infrastructure.external.llm_page_classifier_service import (
    LLMPageClassifierService,
)


class TestPageClassificationIntegration:
    """Integration tests for page classification workflow with BAML."""

    @pytest.mark.asyncio
    async def test_index_page_classification_to_exploration(self):
        """Test complete flow: index page classification → explore children decision.

        This integration test verifies:
        1. HTML is classified as INDEX_PAGE with high confidence using BAML
        2. Decision node correctly decides to explore children
        3. Constants are used consistently throughout the flow
        """
        from baml_client import types

        # Setup: Mock BAML to return INDEX_PAGE classification
        mock_baml_result = types.PageClassification(
            page_type="index_page",
            confidence=DEFAULT_CONFIDENCE_THRESHOLD + 0.1,
            reason="Contains prefecture links",
            has_child_links=True,
            has_member_info=False,
        )

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            # Execute: Classify page
            classifier = LLMPageClassifierService()
            html_content = "<html><body><a href='/tokyo'>Tokyo</a></body></html>"
            classification = await classifier.classify_page(
                html_content=html_content,
                current_url="https://example.com/regions",
                party_name="Test Party",
            )

            # Verify: Classification is correct
            assert classification.page_type == PageType.INDEX_PAGE
            assert classification.confidence >= DEFAULT_CONFIDENCE_THRESHOLD
            assert (
                classification.should_explore_children(max_depth_reached=False) is True
            )

            # Execute: Decision node
            state = {
                "classification": {
                    "page_type": classification.page_type.value,
                    "confidence": classification.confidence,
                },
                "depth": 1,
                "max_depth": 3,
                "pending_urls": [],
            }
            decision = should_explore_children(state)  # type: ignore[arg-type]

            # Verify: Decision is to explore children
            assert decision == "explore_children"

    @pytest.mark.asyncio
    async def test_member_list_page_classification_to_extraction(self):
        """Test complete flow: member list page → extract members decision.

        This integration test verifies:
        1. HTML is classified as MEMBER_LIST_PAGE with high confidence using BAML
        2. Decision node correctly decides to extract members
        3. Member extraction decision is consistent with domain logic
        """
        from baml_client import types

        # Setup: Mock BAML to return MEMBER_LIST_PAGE classification
        mock_baml_result = types.PageClassification(
            page_type="member_list_page",
            confidence=0.95,
            reason="Contains multiple member profiles",
            has_child_links=False,
            has_member_info=True,
        )

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            # Execute: Classify page
            classifier = LLMPageClassifierService()
            html_content = (
                "<html><body>"
                "<div class='member'>Yamada Taro</div>"
                "<div class='member'>Suzuki Hanako</div>"
                "</body></html>"
            )
            classification = await classifier.classify_page(
                html_content=html_content,
                current_url="https://example.com/members/tokyo",
                party_name="Test Party",
            )

            # Verify: Classification is correct
            assert classification.page_type == PageType.MEMBER_LIST_PAGE
            assert classification.confidence >= DEFAULT_CONFIDENCE_THRESHOLD
            assert classification.should_extract_members() is True
            assert (
                classification.should_explore_children(max_depth_reached=False) is False
            )

            # Execute: Decision node
            state = {
                "classification": {
                    "page_type": classification.page_type.value,
                    "confidence": classification.confidence,
                },
                "depth": 2,
                "max_depth": 3,
                "pending_urls": [],
            }
            decision = should_explore_children(state)  # type: ignore[arg-type]

            # Verify: Decision is to extract members
            assert decision == "extract_members"

    @pytest.mark.asyncio
    async def test_low_confidence_classification_skips_page(self):
        """Test complete flow: low confidence classification → skip decision.

        This integration test verifies:
        1. HTML is classified but with low confidence using BAML
        2. Domain logic correctly rejects low confidence
        3. Decision node correctly decides to skip
        4. Threshold constant is used consistently
        """
        from baml_client import types

        # Setup: Mock BAML to return low confidence classification
        mock_baml_result = types.PageClassification(
            page_type="index_page",
            confidence=DEFAULT_CONFIDENCE_THRESHOLD - 0.1,
            reason="Uncertain classification",
            has_child_links=True,
            has_member_info=False,
        )

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            # Execute: Classify page
            classifier = LLMPageClassifierService()
            html_content = "<html><body>Ambiguous content</body></html>"
            classification = await classifier.classify_page(
                html_content=html_content,
                current_url="https://example.com/page",
                party_name="Test Party",
            )

            # Verify: Classification has low confidence
            assert classification.confidence < DEFAULT_CONFIDENCE_THRESHOLD
            assert classification.is_confident() is False
            assert (
                classification.should_explore_children(max_depth_reached=False) is False
            )

            # Execute: Decision node
            state = {
                "classification": {
                    "page_type": classification.page_type.value,
                    "confidence": classification.confidence,
                },
                "depth": 1,
                "max_depth": 3,
                "pending_urls": [("https://example.com/next", 1)],
            }
            decision = should_explore_children(state)  # type: ignore[arg-type]

            # Verify: Decision is to continue (skip this page)
            assert decision == "continue"

    @pytest.mark.asyncio
    async def test_max_depth_prevents_exploration(self):
        """Test that max depth enforcement works end-to-end.

        This integration test verifies:
        1. Even with confident INDEX_PAGE classification using BAML
        2. Max depth enforcement prevents further exploration
        3. Domain and infrastructure layers coordinate correctly
        """
        from baml_client import types

        # Setup: Mock BAML to return INDEX_PAGE with high confidence
        mock_baml_result = types.PageClassification(
            page_type="index_page",
            confidence=0.95,
            reason="Clear index page",
            has_child_links=True,
            has_member_info=False,
        )

        with patch(
            "src.infrastructure.external.llm_page_classifier_service.b.ClassifyPage",
            new_callable=AsyncMock,
        ) as mock_classify:
            mock_classify.return_value = mock_baml_result

            # Execute: Classify page
            classifier = LLMPageClassifierService()
            classification = await classifier.classify_page(
                html_content="<html>...</html>",
                current_url="https://example.com/deep/page",
            )

            # Verify: Classification would normally allow exploration
            assert classification.page_type == PageType.INDEX_PAGE
            assert classification.is_confident()

            # But: Max depth is reached
            assert (
                classification.should_explore_children(max_depth_reached=True) is False
            )

            # Execute: Decision node at max depth
            state = {
                "classification": {
                    "page_type": classification.page_type.value,
                    "confidence": classification.confidence,
                },
                "depth": 3,
                "max_depth": 3,
                "pending_urls": [("https://example.com/next", 3)],
            }
            decision = should_explore_children(state)  # type: ignore[arg-type]

            # Verify: Decision is to continue (not explore deeper)
            assert decision == "continue"
