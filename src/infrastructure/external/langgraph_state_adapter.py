"""Adapter to convert between domain state and LangGraph state."""

import copy
from dataclasses import asdict
from typing import Annotated, Any

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.value_objects.scraping_config import ScrapingConfig


class LangGraphPartyScrapingState(TypedDict):
    """LangGraph-specific state definition.

    This is an infrastructure concern - it adapts the domain state
    to LangGraph's requirements (TypedDict with message annotations).
    """

    # Required fields
    current_url: str
    visited_urls: set[str]
    depth: int
    max_depth: int
    extracted_members: list[dict[str, Any]]
    party_name: str
    party_id: int
    pending_urls: list[tuple[str, int]]
    messages: Annotated[list[BaseMessage], add_messages]
    error_message: str | None
    scraping_config: dict[str, Any]  # ScrapingConfig as dict


class LangGraphPartyScrapingStateOptional(LangGraphPartyScrapingState, total=False):
    """Extended state with optional fields for page classification."""

    classification: dict[str, Any]  # PageClassification metadata
    html_content: str  # Current page HTML content


def domain_to_langgraph_state(
    domain_state: PartyScrapingState,
) -> LangGraphPartyScrapingState:
    """Convert domain state to LangGraph state.

    Args:
        domain_state: Framework-independent domain state

    Returns:
        LangGraph-compatible state with message handling
    """
    # Convert to LangGraph format (deep copy to prevent mutation)
    # Cast to list[dict[str, Any]] for TypedDict compatibility
    extracted_members_copy: list[dict[str, Any]] = [
        dict(m) for m in copy.deepcopy(list(domain_state.extracted_members))
    ]

    lg_state: LangGraphPartyScrapingState = {
        "current_url": domain_state.current_url,
        "visited_urls": set(domain_state.visited_urls),  # frozenset -> set
        "depth": domain_state.depth,
        "max_depth": domain_state.max_depth,
        "extracted_members": extracted_members_copy,
        "party_name": domain_state.party_name,
        "party_id": domain_state.party_id,
        "pending_urls": list(domain_state.pending_urls),  # tuple -> list
        "messages": [
            HumanMessage(content=f"Starting scraping from {domain_state.current_url}")
        ],
        "error_message": domain_state.error_message,
        "scraping_config": asdict(domain_state.scraping_config),
    }

    return lg_state


def langgraph_to_domain_state(
    lg_state: LangGraphPartyScrapingState,
) -> PartyScrapingState:
    """Convert LangGraph state back to domain state.

    Args:
        lg_state: LangGraph state after processing

    Returns:
        Framework-independent domain state
    """
    # Create domain state - note that we can't directly assign to private fields
    # We need to use the public API to populate the state
    # Reconstruct ScrapingConfig from dict
    config_dict = lg_state["scraping_config"]
    scraping_config = ScrapingConfig(**config_dict)

    domain_state = PartyScrapingState(
        current_url=lg_state["current_url"],
        party_name=lg_state["party_name"],
        party_id=lg_state["party_id"],
        max_depth=lg_state["max_depth"],
        scraping_config=scraping_config,
        depth=lg_state["depth"],
        error_message=lg_state.get("error_message"),
    )

    # Populate collections using the public API
    for url in lg_state["visited_urls"]:
        domain_state.mark_visited(url)

    for url, depth in lg_state["pending_urls"]:
        domain_state.add_pending_url(url, depth)

    # Deep copy members to prevent mutation
    for member in copy.deepcopy(lg_state["extracted_members"]):
        domain_state.add_extracted_member(member)  # type: ignore[arg-type]

    return domain_state
