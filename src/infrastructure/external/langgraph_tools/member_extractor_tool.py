"""LangGraph tools for party member extraction.

This module provides LangGraph @tool wrappers around the PartyMemberExtractor.
The tools act as an adapter between the LangGraph framework and the extraction logic.

TODO(Clean Architecture): This tool currently depends on legacy
src/party_member_extractor/ module. Should be refactored to use:
- Domain: PartyMemberExtractionService
- Application: ExtractPartyMembersUseCase with proper DTOs
- Infrastructure: Updated implementation using Clean Architecture
Track migration in a separate issue.
"""

import logging

from typing import Any

from langchain_core.tools import tool

from src.domain.services.interfaces.llm_service import ILLMService
from src.interfaces.factories.party_member_extractor_factory import (
    PartyMemberExtractorFactory,
)
from src.party_member_extractor.models import WebPageContent


logger = logging.getLogger(__name__)


def create_member_extractor_tools(
    llm_service: ILLMService | None = None,
    party_id: int | None = None,
) -> list[Any]:
    """Create LangGraph tools for party member extraction.

    Args:
        llm_service: Optional ILLMService instance.
                     If not provided, extractor will create a default one.
        party_id: Optional party ID for history tracking.

    Returns:
        List of LangGraph tools
    """

    @tool
    async def extract_members_from_page(
        url: str,
        html_content: str,
        party_name: str,
    ) -> dict[str, Any]:
        """Extract politician members from a party member list page.

        Analyzes HTML content from a party member list page and extracts
        structured information about politicians including their names,
        positions, electoral districts, and profile URLs.

        Args:
            url: Page URL for context and relative URL resolution
            html_content: Raw HTML content to analyze
            party_name: Name of the political party (for context and validation)

        Returns:
            Dictionary with:
            - members: List of extracted member dictionaries with fields:
              - name: Politician's full name
              - position: Official position (衆議院議員, 参議院議員, etc.)
              - electoral_district: Electoral district (東京1区, etc.)
              - prefecture: Prefecture (東京都, etc.)
              - profile_url: URL to member's profile page (if available)
              - party_position: Party role (代表, 幹事長, etc.)
            - count: Total number of members extracted
            - success: Boolean indicating if extraction was successful
            - party_name: Name of the party (echo of input for verification)

        Example:
            >>> result = await extract_members_from_page(
            ...     url="https://example.com/party/members",
            ...     html_content="<html>...</html>",
            ...     party_name="Example Party"
            ... )
            >>> print(result["count"])
            15
            >>> print(result["members"][0]["name"])
            "山田太郎"
        """
        try:
            # Create extractor instance
            extractor = PartyMemberExtractorFactory.create(
                llm_service=llm_service,
            )

            # Create WebPageContent from inputs
            page = WebPageContent(
                url=url,
                html_content=html_content,
                page_number=1,  # Single page extraction
            )

            # Extract members
            # Use extract_from_pages with a single page
            # This works for both Pydantic and BAML implementations
            result = await extractor.extract_from_pages([page], party_name)

            if result is None:
                logger.warning(f"No members extracted from {url}")
                return {
                    "members": [],
                    "count": 0,
                    "success": False,
                    "party_name": party_name,
                    "error": "No members could be extracted from the page",
                }

            # Convert to dict format for LangGraph
            members_dict = [
                {
                    "name": member.name,
                    "position": member.position,
                    "electoral_district": member.electoral_district,
                    "prefecture": member.prefecture,
                    "profile_url": member.profile_url,
                    "party_position": member.party_position,
                }
                for member in result.members
            ]

            return {
                "members": members_dict,
                "count": len(members_dict),
                "success": True,
                "party_name": party_name,
            }

        except Exception as e:
            logger.error(f"Error extracting members from page: {e}", exc_info=True)
            return {
                "members": [],
                "count": 0,
                "success": False,
                "party_name": party_name,
                "error": str(e),
            }

    return [extract_members_from_page]
