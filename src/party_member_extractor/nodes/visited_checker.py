"""Visited URL checker node for LangGraph workflow.

This module provides a LangGraph node function that checks if URLs have
been visited, enforces depth limits, and prevents infinite loops in the
party member scraping workflow.
"""

import logging

from typing import Any

from langchain_core.messages import HumanMessage

from ..utils.url_normalizer import normalize_url

logger = logging.getLogger(__name__)


def check_visited_and_depth(state: dict[str, Any]) -> dict[str, Any]:
    """Check if current URL is visited and enforce depth limits.

    This node function is designed to be used in a LangGraph workflow.
    It performs the following checks:
    1. Normalizes the current URL
    2. Checks if URL has been visited (prevents infinite loops)
    3. Marks URL as visited if new
    4. Checks if depth limit has been reached
    5. Updates state with visited status and logs

    Args:
        state: LangGraph state dict containing:
            - current_url: Current URL being processed
            - visited_urls: Set of normalized URLs already visited
            - depth: Current navigation depth
            - max_depth: Maximum allowed depth
            - messages: List of messages (for logging)

    Returns:
        Updated state dict with:
            - visited_urls: Updated with current URL if new
            - messages: Updated with status message
            - should_skip: Boolean flag indicating if processing should be skipped
            - skip_reason: Reason for skipping (if applicable)

    Example:
        >>> from langgraph.graph import StateGraph
        >>> workflow = StateGraph(state_schema)
        >>> workflow.add_node("check_visited", check_visited_and_depth)
        >>> workflow.add_edge("fetch_page", "check_visited")
    """
    current_url = state.get("current_url", "")
    visited_urls = state.get("visited_urls", set())
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 3)
    messages = state.get("messages", [])

    # Initialize flags
    should_skip = False
    skip_reason = None

    try:
        # Normalize URL for consistent comparison
        normalized_url = normalize_url(current_url)

        # Check if already visited (infinite loop prevention)
        if normalized_url in visited_urls:
            should_skip = True
            skip_reason = "already_visited"
            logger.info(
                f"URL already visited (infinite loop prevented): {normalized_url}"
            )
            messages.append(
                HumanMessage(
                    content=f"⚠️ Skipping already visited URL: {normalized_url}"
                )
            )
        else:
            # Check depth limit
            if depth > max_depth:
                should_skip = True
                skip_reason = "max_depth_exceeded"
                logger.info(
                    f"Max depth {max_depth} exceeded at depth {depth}: {normalized_url}"
                )
                messages.append(
                    HumanMessage(
                        content=(
                            f"⚠️ Max depth {max_depth} exceeded at depth {depth}, "
                            f"skipping: {normalized_url}"
                        )
                    )
                )
            else:
                # Mark as visited and log
                visited_urls.add(normalized_url)
                logger.info(
                    f"Processing URL at depth {depth}/{max_depth}: {normalized_url}"
                )
                messages.append(
                    HumanMessage(
                        content=(
                            f"✓ Processing URL at depth {depth}/{max_depth}: "
                            f"{normalized_url}"
                        )
                    )
                )

    except ValueError as e:
        # Handle invalid URLs
        should_skip = True
        skip_reason = "invalid_url"
        error_msg = f"Invalid URL: {current_url} - {e}"
        logger.error(error_msg)
        messages.append(HumanMessage(content=f"❌ {error_msg}"))

    # Return updated state
    return {
        **state,
        "visited_urls": visited_urls,
        "messages": messages,
        "should_skip": should_skip,
        "skip_reason": skip_reason,
    }


def add_pending_url_with_checks(
    state: dict[str, Any], url: str, depth: int
) -> dict[str, Any]:
    """Add a URL to pending queue with visited and depth checks.

    This is a helper function to add URLs to the pending queue while
    ensuring they haven't been visited and don't exceed depth limits.

    Args:
        state: LangGraph state dict
        url: URL to add to pending queue
        depth: Depth level for this URL

    Returns:
        Updated state with URL added to pending_urls if checks pass

    Raises:
        ValueError: If depth is negative or URL is invalid
    """
    if depth < 0:
        raise ValueError(f"Depth cannot be negative: {depth}")

    visited_urls = state.get("visited_urls", set())
    pending_urls = state.get("pending_urls", [])
    max_depth = state.get("max_depth", 3)
    messages = state.get("messages", [])

    try:
        # Normalize URL
        normalized_url = normalize_url(url)

        # Skip if already visited
        if normalized_url in visited_urls:
            logger.debug(f"Skipping already visited URL: {normalized_url}")
            return state

        # Skip if exceeds depth
        if depth > max_depth:
            logger.debug(f"Skipping URL beyond max depth {max_depth}: {normalized_url}")
            return state

        # Add to pending queue
        pending_urls.append((normalized_url, depth))
        logger.info(f"Added URL to pending queue at depth {depth}: {normalized_url}")
        messages.append(
            HumanMessage(content=f"➕ Added to queue (depth {depth}): {normalized_url}")
        )

        return {**state, "pending_urls": pending_urls, "messages": messages}

    except ValueError as e:
        error_msg = f"Failed to add URL '{url}': {e}"
        logger.error(error_msg)
        messages.append(HumanMessage(content=f"❌ {error_msg}"))
        return {**state, "messages": messages}
