"""LangGraph node for extracting party members from a page."""

import logging
from collections.abc import Awaitable, Callable

from src.domain.services.interfaces.web_scraper_service import IWebScraperService
from src.domain.services.party_member_extraction_service import (
    IPartyMemberExtractionService,
)
from src.infrastructure.external.langgraph_state_adapter import (
    LangGraphPartyScrapingStateOptional,
)


logger = logging.getLogger(__name__)


def create_extract_members_node(
    scraper: IWebScraperService,
    member_extractor: IPartyMemberExtractionService,
) -> Callable[
    [LangGraphPartyScrapingStateOptional],
    Awaitable[LangGraphPartyScrapingStateOptional],
]:
    """Create a LangGraph node for extracting party members.

    This node:
    1. Fetches HTML content for the current URL
    2. Extracts politician member data using domain service
    3. Adds extracted members to the state

    Args:
        scraper: Web scraper service for fetching HTML
        member_extractor: Domain service for member extraction

    Returns:
        Async node function compatible with LangGraph
    """

    async def extract_members_node(
        state: LangGraphPartyScrapingStateOptional,
    ) -> LangGraphPartyScrapingStateOptional:
        """Extract members from the current page.

        This node uses LLM-based extraction to identify politician
        information from member list pages.

        Args:
            state: Current LangGraph state

        Returns:
            Updated state with newly extracted members
        """
        current_url = state.get("current_url", "")
        party_name = state.get("party_name", "")
        extracted_members = state.get("extracted_members", [])

        if not current_url:
            logger.warning("No current URL to extract members from")
            return state

        logger.info(f"Extracting members from: {current_url}")

        try:
            # Fetch HTML content
            html_content = await scraper.fetch_html(current_url)

            if not html_content:
                logger.warning(f"No HTML content fetched from: {current_url}")
                return state

            # Extract members using domain service
            result = await member_extractor.extract_from_html(
                html_content=html_content,
                source_url=current_url,
                party_name=party_name,
            )

            if not result.extraction_successful:
                logger.warning(
                    f"Extraction failed for {current_url}: {result.error_message}"
                )
                return state

            if not result.members:
                logger.info(f"No members extracted from {current_url}")
                return state

            # Convert members to dict format
            new_members = [
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

            # Deduplicate by name
            existing_names = {m.get("name") for m in extracted_members}
            unique_new_members = [
                m for m in new_members if m.get("name") not in existing_names
            ]

            # Add to extracted members
            extracted_members.extend(unique_new_members)

            duplicates_count = len(new_members) - len(unique_new_members)
            logger.info(
                f"Extracted {len(new_members)} members from {current_url} "
                f"({len(unique_new_members)} new, {duplicates_count} duplicates)"
            )

            return {
                **state,
                "extracted_members": extracted_members,
            }

        except Exception as e:
            logger.error(
                f"Error extracting members from {current_url}: {e}",
                exc_info=True,
            )
            # Return state unchanged on error (fail gracefully)
            return state

    return extract_members_node
