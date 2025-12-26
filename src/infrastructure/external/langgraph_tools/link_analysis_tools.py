"""LangGraph tools for link analysis use cases.

This module provides LangGraph @tool wrappers around Clean Architecture use cases.
The tools act as an adapter between the LangGraph framework and our use cases.
"""

import logging

from typing import Any

from langchain_core.tools import tool

from src.application.dtos.link_analysis_dto import (
    AnalyzeLinksInputDTO,
    AnalyzeLinksOutputDTO,
)
from src.application.usecases.analyze_party_page_links_usecase import (
    AnalyzePartyPageLinksUseCase,
)
from src.infrastructure.di.container import get_container

logger = logging.getLogger(__name__)


def create_link_analysis_tools(
    usecase: AnalyzePartyPageLinksUseCase | None = None,
) -> list[Any]:
    """Create LangGraph tools for link analysis.

    Args:
        usecase: Optional AnalyzePartyPageLinksUseCase instance.
                 If not provided, will be fetched from DI container.

    Returns:
        List of LangGraph tools
    """
    if usecase is None:
        container = get_container()
        usecase = container.usecases.analyze_party_page_links_usecase()

    # Assert usecase is not None for type checking
    assert usecase is not None, "Failed to initialize use case"

    @tool
    async def analyze_party_page_links(
        html_content: str,
        current_url: str,
        party_name: str = "",
        context: str = "",
    ) -> dict[str, Any]:
        """Analyze links on a party member page.

        Identifies child pages and member profiles by extracting all links
        from HTML content, filtering for child/sibling pages, then using LLM
        to classify them into types:
        - prefecture_list: 都道府県別リスト
        - city_list: 市区町村別リスト
        - member_list: 議員一覧
        - member_profile: 議員個人ページ
        - other: その他

        Args:
            html_content: Raw HTML content to analyze
            current_url: URL of the current page
            party_name: Name of the political party (optional, for context)
            context: Additional context about the page (optional)

        Returns:
            Dictionary with:
            - all_links_count: Total number of links found
            - child_links_count: Number of child/sibling links analyzed
            - classifications: List of link classifications with type,
              confidence, reason
            - summary: Count of links by type
            - member_list_urls: List of URLs classified as member_list
              (confidence >= 0.7)
            - profile_urls: List of URLs classified as member_profile
              (confidence >= 0.7)

        Example:
            >>> result = await analyze_party_page_links(
            ...     html_content="<html>...</html>",
            ...     current_url="https://example.com/party/members",
            ...     party_name="Example Party"
            ... )
            >>> print(result["member_list_urls"])
            ["https://example.com/party/members/tokyo", ...]
        """
        try:
            input_dto = AnalyzeLinksInputDTO(
                html_content=html_content,
                current_url=current_url,
                party_name=party_name,
                context=context,
            )

            output_dto: AnalyzeLinksOutputDTO = await usecase.execute(input_dto)

            # Convert DTO to dict for LangGraph
            return {
                "all_links_count": output_dto.all_links_count,
                "child_links_count": output_dto.child_links_count,
                "classifications": [c.model_dump() for c in output_dto.classifications],
                "summary": output_dto.summary,
                "member_list_urls": output_dto.member_list_urls,
                "profile_urls": output_dto.profile_urls,
            }

        except Exception as e:
            logger.error(f"Error analyzing party page links: {e}")
            return {
                "all_links_count": 0,
                "child_links_count": 0,
                "classifications": [],
                "summary": {},
                "member_list_urls": [],
                "profile_urls": [],
                "error": str(e),
            }

    return [analyze_party_page_links]
