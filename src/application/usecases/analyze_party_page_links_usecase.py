"""Use case for analyzing party page links."""

import logging

from src.application.dtos.link_analysis_dto import (
    AnalyzeLinksInputDTO,
    AnalyzeLinksOutputDTO,
    LinkClassificationDTO,
)
from src.domain.services.interfaces.html_link_extractor_service import (
    IHtmlLinkExtractorService,
)
from src.domain.services.interfaces.llm_link_classifier_service import (
    ILLMLinkClassifierService,
    LinkType,
)
from src.domain.services.link_analysis_domain_service import LinkAnalysisDomainService


logger = logging.getLogger(__name__)


class AnalyzePartyPageLinksUseCase:
    """Use case for analyzing and classifying links on party member pages.

    This use case orchestrates the following workflow:
    1. Extract all links from HTML content
    2. Filter links to identify child pages
    3. Classify links using LLM
    4. Return structured results with classifications
    """

    def __init__(
        self,
        html_extractor: IHtmlLinkExtractorService,
        link_classifier: ILLMLinkClassifierService,
        link_analysis_service: LinkAnalysisDomainService,
    ):
        """Initialize the use case with required services.

        Args:
            html_extractor: Service for extracting links from HTML
            link_classifier: Service for classifying links with LLM
            link_analysis_service: Domain service for link hierarchy analysis
        """
        self._html_extractor = html_extractor
        self._link_classifier = link_classifier
        self._link_analysis = link_analysis_service

    async def execute(self, input_dto: AnalyzeLinksInputDTO) -> AnalyzeLinksOutputDTO:
        """Execute the link analysis use case.

        Args:
            input_dto: Input data containing HTML and context

        Returns:
            AnalyzeLinksOutputDTO with analysis results

        Raises:
            ValueError: If input_dto is invalid
        """
        if not input_dto.html_content:
            raise ValueError("HTML content cannot be empty")
        if not input_dto.current_url:
            raise ValueError("Current URL cannot be empty")

        logger.info(f"Analyzing links for URL: {input_dto.current_url}")

        # Step 1: Extract all links from HTML
        all_links = self._html_extractor.extract_links(
            input_dto.html_content, input_dto.current_url
        )
        logger.info(f"Extracted {len(all_links)} total links")
        print(
            f"DEBUG LinkAnalysis: Extracted {len(all_links)} total links "
            f"from {input_dto.current_url}"
        )
        if all_links:
            sample_urls = [link.url for link in all_links[:5]]
            print(f"DEBUG LinkAnalysis: Sample links = {sample_urls}")

        # Step 2: Filter for child pages and siblings
        child_links = self._link_analysis.filter_child_pages(
            all_links, input_dto.current_url
        )
        sibling_links = self._link_analysis.filter_sibling_pages(
            all_links, input_dto.current_url
        )

        print(
            f"DEBUG LinkAnalysis: After filtering - "
            f"child_links={len(child_links)}, sibling_links={len(sibling_links)}"
        )
        if child_links:
            sample_child_urls = [link.url for link in child_links[:5]]
            print(f"DEBUG LinkAnalysis: Sample child links = {sample_child_urls}")

        # Combine child and sibling links for classification
        links_to_classify = list(set(child_links + sibling_links))

        # Exclude current page
        links_to_classify = self._link_analysis.exclude_current_page(
            links_to_classify, input_dto.current_url
        )

        logger.info(
            f"Identified {len(child_links)} child links, "
            f"{len(sibling_links)} sibling links, "
            f"{len(links_to_classify)} total to classify"
        )
        print(
            f"DEBUG LinkAnalysis: {len(links_to_classify)} links to classify "
            f"(after excluding current page)"
        )

        # Step 3: Classify links if any exist
        if links_to_classify:
            classification_result = await self._link_classifier.classify_links(
                links_to_classify,
                party_name=input_dto.party_name,
                context=input_dto.context,
            )
            classifications_count = len(classification_result.classifications)
            print(f"DEBUG LinkAnalysis: LLM classified {classifications_count} links")
            # Show classification breakdown
            from collections import Counter

            type_counts = Counter(
                c.link_type.value for c in classification_result.classifications
            )
            print(f"DEBUG LinkAnalysis: Classification breakdown = {dict(type_counts)}")
        else:
            # No links to classify
            from src.domain.services.interfaces.llm_link_classifier_service import (
                LinkClassificationResult,
            )

            classification_result = LinkClassificationResult(
                classifications=[], summary={}
            )

        # Step 4: Convert to DTOs and extract specific URL lists
        classification_dtos = [
            LinkClassificationDTO(
                url=c.url,
                link_type=c.link_type.value,
                confidence=c.confidence,
                reason=c.reason,
            )
            for c in classification_result.classifications
        ]

        # Extract member list URLs (including hierarchical navigation pages)
        # For hierarchical exploration, we include:
        # - PREFECTURE_LIST: Prefecture-level member list pages
        # - CITY_LIST: City/municipality-level member list pages
        # - MEMBER_LIST: Direct member list pages
        hierarchical_types = {
            LinkType.PREFECTURE_LIST,
            LinkType.CITY_LIST,
            LinkType.MEMBER_LIST,
        }
        threshold = input_dto.min_confidence_threshold
        member_list_urls = [
            c.url
            for c in classification_result.classifications
            if c.link_type in hierarchical_types and c.confidence >= threshold
        ]

        profile_urls = [
            c.url
            for c in classification_result.classifications
            if c.link_type == LinkType.MEMBER_PROFILE and c.confidence >= threshold
        ]

        logger.info(
            f"Classification complete: {len(member_list_urls)} navigable pages "
            f"(member lists + hierarchical), {len(profile_urls)} profiles"
        )
        print(
            f"DEBUG LinkAnalysis: Final result - "
            f"{len(member_list_urls)} navigable pages "
            f"(member lists + hierarchical), "
            f"{len(profile_urls)} profiles (confidence >= 0.7)"
        )

        # Return output DTO
        return AnalyzeLinksOutputDTO(
            all_links_count=len(all_links),
            child_links_count=len(links_to_classify),
            classifications=classification_dtos,
            summary=classification_result.summary,
            member_list_urls=member_list_urls,
            profile_urls=profile_urls,
        )
