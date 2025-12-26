"""LLM-based implementation of link classification service."""

import logging

from baml_client.async_client import b
from src.domain.services.interfaces.llm_link_classifier_service import (
    ILLMLinkClassifierService,
    LinkClassification,
    LinkClassificationResult,
    LinkType,
)
from src.domain.value_objects.link import Link


logger = logging.getLogger(__name__)


class LLMLinkClassifierService(ILLMLinkClassifierService):
    """LLM-based implementation of link classification using BAML.

    This infrastructure service uses BAML to classify links into different
    types with type-safe structured output.
    """

    async def classify_links(
        self,
        links: list[Link],
        party_name: str = "",
        context: str = "",
    ) -> LinkClassificationResult:
        """Classify links using BAML.

        Args:
            links: List of Link value objects to classify
            party_name: Name of the political party (optional context)
            context: Additional context about the page (optional)

        Returns:
            LinkClassificationResult with classifications and summary
        """
        if not links:
            return LinkClassificationResult(classifications=[], summary={})

        # Prepare links for BAML prompt
        links_text = "\n".join(
            [
                (
                    f"{i + 1}. URL: {link.url}\n"
                    f"   テキスト: {link.text}\n"
                    f"   タイトル: {link.title}"
                )
                for i, link in enumerate(links)
            ]
        )

        # Call BAML function
        try:
            baml_results = await b.ClassifyLinks(
                links=links_text,
                party_name=party_name or "不明",
                context=context or "コンテキスト情報なし",
            )

            # Convert BAML results to domain model
            classifications: list[LinkClassification] = []
            for baml_result in baml_results:
                try:
                    # Parse link_type as enum
                    link_type_str = baml_result.link_type
                    try:
                        link_type = LinkType(link_type_str)
                    except ValueError:
                        logger.warning(
                            f"Invalid link_type '{link_type_str}', using OTHER"
                        )
                        link_type = LinkType.OTHER

                    classification = LinkClassification(
                        url=baml_result.url,
                        link_type=link_type,
                        confidence=baml_result.confidence,
                        reason=baml_result.reason,
                    )
                    classifications.append(classification)
                except Exception as e:
                    logger.warning(
                        f"Failed to convert BAML result to domain model: {e}"
                    )
                    continue

            # Create summary
            summary: dict[str, int] = {}
            for classification in classifications:
                link_type = classification.link_type.value
                summary[link_type] = summary.get(link_type, 0) + 1

            return LinkClassificationResult(
                classifications=classifications,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"Error classifying links with BAML: {e}")
            # Return empty result on error
            return LinkClassificationResult(classifications=[], summary={})

    def filter_by_type(
        self,
        result: LinkClassificationResult,
        link_types: list[LinkType],
        min_confidence: float = 0.7,
    ) -> list[str]:
        """Filter classified links by type and confidence.

        Args:
            result: LinkClassificationResult to filter
            link_types: List of LinkType enums to include
            min_confidence: Minimum confidence threshold

        Returns:
            List of URLs matching the criteria
        """
        filtered_urls: list[str] = []

        for classification in result.classifications:
            if (
                classification.link_type in link_types
                and classification.confidence >= min_confidence
            ):
                filtered_urls.append(classification.url)

        return filtered_urls
