"""LangGraph node for exploring child page links."""

import logging
from collections.abc import Awaitable, Callable

from src.domain.services.interfaces.link_analyzer_service import ILinkAnalyzerService
from src.domain.services.interfaces.web_scraper_service import IWebScraperService
from src.infrastructure.external.langgraph_state_adapter import (
    LangGraphPartyScrapingStateOptional,
)
from src.party_member_extractor.utils.url_normalizer import normalize_url


logger = logging.getLogger(__name__)


def create_explore_children_node(
    scraper: IWebScraperService,
    link_analyzer: ILinkAnalyzerService,
) -> Callable[
    [LangGraphPartyScrapingStateOptional],
    Awaitable[LangGraphPartyScrapingStateOptional],
]:
    """Create a LangGraph node for exploring child page links.

    This node:
    1. Fetches HTML content for the current URL
    2. Analyzes links to find child member list pages
    3. Adds discovered child pages to pending_urls queue

    Args:
        scraper: Web scraper service for fetching HTML
        link_analyzer: Domain service for analyzing page links

    Returns:
        Async node function compatible with LangGraph
    """

    async def explore_children_node(
        state: LangGraphPartyScrapingStateOptional,
    ) -> LangGraphPartyScrapingStateOptional:
        """Explore child pages and add them to the queue.

        This node extracts links from the current page and identifies
        potential child member list pages to visit next.

        Args:
            state: Current LangGraph state

        Returns:
            Updated state with new pending URLs
        """
        current_url = state.get("current_url", "")
        party_name = state.get("party_name", "")
        depth = state.get("depth", 0)
        max_depth = state.get("max_depth", 2)
        pending_urls = state.get("pending_urls", [])
        visited_urls = state.get("visited_urls", set())
        scraping_config = state.get("scraping_config", {})
        min_confidence_threshold = scraping_config.get("min_confidence_threshold", 0.7)

        if not current_url:
            logger.warning("No current URL to explore children from")
            return state

        logger.info(f"Exploring children of: {current_url} (depth={depth})")

        try:
            # Fetch HTML content
            html_content = await scraper.fetch_html(current_url)

            if not html_content:
                logger.warning(f"No HTML content fetched from: {current_url}")
                return state

            # Analyze links using domain service
            member_list_urls = await link_analyzer.analyze_member_list_links(
                html_content=html_content,
                current_url=current_url,
                party_name=party_name,
                context=f"Exploring children at depth {depth}",
                min_confidence_threshold=min_confidence_threshold,
            )

            print(
                f"DEBUG ExploreChildren: Found {len(member_list_urls)} links from {current_url}"
            )
            if member_list_urls:
                print(
                    f"DEBUG ExploreChildren: Links = {member_list_urls[:5]}"
                )  # Show first 5

            # Add member_list_urls to pending queue (they are high-confidence children)
            added_count = 0
            for url in member_list_urls:
                try:
                    normalized_url = normalize_url(url)

                    # Skip if already visited
                    if normalized_url in visited_urls:
                        logger.debug(f"Skipping already visited URL: {normalized_url}")
                        continue

                    # Skip if exceeds depth
                    next_depth = depth + 1
                    if next_depth > max_depth:
                        logger.debug(
                            f"Skipping URL beyond max depth {max_depth}: "
                            f"{normalized_url}"
                        )
                        continue

                    # Add to pending queue
                    pending_urls.append((normalized_url, next_depth))
                    added_count += 1
                    logger.info(
                        f"Added child URL to queue at depth {next_depth}: "
                        f"{normalized_url}"
                    )

                except ValueError as e:
                    logger.error(f"Failed to normalize URL '{url}': {e}")
                    continue

            logger.info(
                f"Explored children of {current_url}: "
                f"found {len(member_list_urls)} links, "
                f"added {added_count} new URLs to queue"
            )

            return {
                **state,
                "pending_urls": pending_urls,
            }

        except Exception as e:
            logger.error(
                f"Error exploring children of {current_url}: {e}",
                exc_info=True,
            )
            # Return state unchanged on error (fail gracefully)
            return state

    return explore_children_node
