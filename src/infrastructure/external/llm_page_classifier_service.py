"""LLM-based implementation of page classification service."""

import logging

from baml_client.async_client import b

from src.domain.services.interfaces.page_classifier_service import (
    IPageClassifierService,
)
from src.domain.value_objects.page_classification import PageClassification, PageType


logger = logging.getLogger(__name__)

# Maximum length of HTML content to send to LLM for classification
MAX_HTML_EXCERPT_LENGTH = 3000


class LLMPageClassifierService(IPageClassifierService):
    """LLM-based implementation of page classification using BAML.

    This infrastructure service uses BAML to classify web pages
    to guide hierarchical navigation strategy with type-safe structured output.
    """

    async def classify_page(
        self,
        html_content: str,
        current_url: str,
        party_name: str = "",
    ) -> PageClassification:
        """Classify a web page using BAML.

        Args:
            html_content: HTML content of the page to classify
            current_url: URL of the current page (for context)
            party_name: Name of the political party (optional, for context)

        Returns:
            PageClassification with type, confidence, and metadata

        Raises:
            ValueError: If html_content or current_url is empty
        """
        if not html_content:
            raise ValueError("HTML content cannot be empty")
        if not current_url:
            raise ValueError("Current URL cannot be empty")

        # Truncate HTML for prompt efficiency
        html_excerpt = html_content[:MAX_HTML_EXCERPT_LENGTH]

        # Call BAML function
        try:
            baml_result = await b.ClassifyPage(
                html_excerpt=html_excerpt,
                current_url=current_url,
                party_name=party_name or "不明",
            )

            # Convert BAML result to domain model
            page_type_str = baml_result.page_type
            try:
                page_type = PageType(page_type_str)
            except ValueError:
                logger.warning(
                    f"Invalid page_type '{page_type_str}', defaulting to OTHER"
                )
                page_type = PageType.OTHER

            classification = PageClassification(
                page_type=page_type,
                confidence=baml_result.confidence,
                reason=baml_result.reason,
                has_child_links=baml_result.has_child_links,
                has_member_info=baml_result.has_member_info,
            )

            logger.info(
                f"Classified {current_url} as {classification.page_type.value} "
                f"(confidence: {classification.confidence:.2f})"
            )

            return classification

        except Exception as e:
            logger.error(f"Error classifying page with BAML: {e}")
            # Return a safe default classification on error
            return PageClassification(
                page_type=PageType.OTHER,
                confidence=0.0,
                reason=f"Failed to classify page: {str(e)}",
                has_child_links=False,
                has_member_info=False,
            )
