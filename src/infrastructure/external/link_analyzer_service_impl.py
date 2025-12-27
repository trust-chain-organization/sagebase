"""Infrastructure implementation of link analyzer service.

This adapter wraps the AnalyzePartyPageLinksUseCase to provide
link analysis capabilities through the domain interface.
"""

import logging

from src.application.dtos.link_analysis_dto import AnalyzeLinksInputDTO
from src.application.usecases.analyze_party_page_links_usecase import (
    AnalyzePartyPageLinksUseCase,
)
from src.domain.services.interfaces.link_analyzer_service import ILinkAnalyzerService


logger = logging.getLogger(__name__)


class LinkAnalyzerServiceImpl(ILinkAnalyzerService):
    """Infrastructure implementation using AnalyzePartyPageLinksUseCase.

    This adapter allows infrastructure nodes to use link analysis
    through the domain interface without directly depending on
    application layer use cases.
    """

    def __init__(self, link_analysis_usecase: AnalyzePartyPageLinksUseCase):
        """Initialize the link analyzer service.

        Args:
            link_analysis_usecase: Application layer use case for link analysis
        """
        self._link_analysis_usecase = link_analysis_usecase

    async def analyze_member_list_links(
        self,
        html_content: str,
        current_url: str,
        party_name: str,
        context: str = "",
        min_confidence_threshold: float = 0.7,
    ) -> list[str]:
        """Analyze HTML and return high-confidence member list URLs.

        Args:
            html_content: Raw HTML content to analyze
            current_url: URL of the current page
            party_name: Name of the party (for context)
            context: Additional context about the page (optional)
            min_confidence_threshold: Minimum confidence for link
                classification (default: 0.7)

        Returns:
            List of URLs classified as member list pages

        Raises:
            ValueError: If html_content is empty or invalid
        """
        if not html_content:
            raise ValueError("html_content cannot be empty")

        logger.debug(f"Analyzing links for {current_url}")

        # Create input DTO for use case
        input_dto = AnalyzeLinksInputDTO(
            html_content=html_content,
            current_url=current_url,
            party_name=party_name,
            context=context,
            min_confidence_threshold=min_confidence_threshold,
        )

        # Execute use case
        output_dto = await self._link_analysis_usecase.execute(input_dto)

        # Return member list URLs (high-confidence child pages)
        return output_dto.member_list_urls
