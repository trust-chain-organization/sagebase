"""LangGraph decision node for navigation strategy."""

import logging

from src.domain.value_objects.page_classification import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    PageType,
)
from src.infrastructure.external.langgraph_state_adapter import (
    LangGraphPartyScrapingStateOptional,
)


logger = logging.getLogger(__name__)


def should_explore_children(state: LangGraphPartyScrapingStateOptional) -> str:
    """Decision node to determine next action based on page classification.

    This function analyzes the page classification and current depth
    to decide whether to:
    - "explore_children": Navigate to child pages (index pages)
    - "extract_members": Extract member information (member list pages)
    - "skip": Skip this page and move to next pending URL

    Args:
        state: Current LangGraph state with classification metadata

    Returns:
        One of: "explore_children", "extract_members", "skip", "end"
    """
    classification = state.get("classification", {})
    page_type_str = classification.get("page_type", "other")
    confidence = classification.get("confidence", 0.0)
    depth = state.get("depth", 0)
    max_depth = state.get("max_depth", 2)
    pending_urls = state.get("pending_urls", [])

    logger.info(
        f"Decision node: page_type={page_type_str}, "
        f"confidence={confidence:.2f}, "
        f"depth={depth}, "
        f"max_depth={max_depth}, "
        f"pending_count={len(pending_urls)}"
    )
    print(
        f"DEBUG Decision: page_type={page_type_str}, "
        f"confidence={confidence:.2f}, depth={depth}/{max_depth}, "
        f"pending={len(pending_urls)}"
    )

    # Check if max depth reached
    if depth >= max_depth:
        logger.info(f"Max depth {max_depth} reached, skipping deeper navigation")
        return _move_to_next_url(state)

    # Convert page_type string to enum
    try:
        page_type = PageType(page_type_str)
    except ValueError:
        logger.warning(f"Invalid page_type: {page_type_str}, treating as OTHER")
        return _move_to_next_url(state)

    # Check confidence threshold
    if confidence < DEFAULT_CONFIDENCE_THRESHOLD:
        logger.info(
            f"Low confidence ({confidence:.2f}), "
            f"below threshold ({DEFAULT_CONFIDENCE_THRESHOLD}), "
            f"skipping to avoid false positives"
        )
        return _move_to_next_url(state)

    # Check for child links to prioritize exploration
    has_child_links = classification.get("has_child_links", False)

    # Make decision based on page type
    if page_type == PageType.INDEX_PAGE:
        logger.info("Index page detected, will explore child links")
        print("DEBUG Decision: INDEX_PAGE → explore_children")
        return "explore_children"

    elif page_type == PageType.MEMBER_LIST_PAGE:
        # If member list page has child links, explore them first
        # This handles cases where a page has both member info and hierarchical structure
        if has_child_links:
            logger.info(
                "Member list page with child links detected, "
                "prioritizing exploration for deeper member discovery"
            )
            print(
                "DEBUG Decision: MEMBER_LIST_PAGE + has_child_links → explore_children"
            )
            return "explore_children"
        else:
            logger.info("Member list page detected, will extract members")
            print("DEBUG Decision: MEMBER_LIST_PAGE → extract_members")
            return "extract_members"

    else:  # PageType.OTHER
        logger.info("Other page type, skipping")
        print("DEBUG Decision: OTHER → skip/continue")
        return _move_to_next_url(state)


def _move_to_next_url(state: LangGraphPartyScrapingStateOptional) -> str:
    """Helper to determine if we should continue to next URL or end.

    Args:
        state: Current state

    Returns:
        "continue" if there are pending URLs, "end" otherwise
    """
    pending_urls = state.get("pending_urls", [])

    if pending_urls:
        logger.debug(f"Moving to next URL ({len(pending_urls)} remaining)")
        return "continue"
    else:
        logger.info("No more URLs to process, ending")
        return "end"
