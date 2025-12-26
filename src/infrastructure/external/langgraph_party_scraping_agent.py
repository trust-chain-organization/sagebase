"""LangGraph-based implementation of party scraping agent."""

import logging

from dataclasses import replace

from langgraph.graph import END, START, StateGraph

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.services.interfaces.party_scraping_agent import IPartyScrapingAgent

from .langgraph_state_adapter import (
    LangGraphPartyScrapingState,
    domain_to_langgraph_state,
    langgraph_to_domain_state,
)

logger = logging.getLogger(__name__)


class LangGraphPartyScrapingAgent(IPartyScrapingAgent):
    """LangGraph-based implementation of hierarchical party scraping.

    This is an infrastructure implementation that uses LangGraph for
    state management and workflow orchestration. The domain layer
    only knows about the IPartyScrapingAgent interface.
    """

    def __init__(self):
        """Initialize the LangGraph agent."""
        self._compiled_agent = None
        self._is_initialized = False
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize and compile the LangGraph workflow."""
        try:
            workflow = self._create_workflow()
            self._compiled_agent = workflow.compile()
            self._is_initialized = True
            logger.info("LangGraph party scraping agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph agent: {e}")
            self._is_initialized = False
            raise

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph StateGraph workflow.

        Returns:
            Configured StateGraph ready for compilation
        """
        workflow = StateGraph(LangGraphPartyScrapingState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_state_node)
        workflow.add_node("check_completion", self._check_completion_node)

        # Define edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "check_completion")

        # Add conditional edge for completion check
        workflow.add_conditional_edges(
            "check_completion",
            self._should_continue,
            {
                "continue": "check_completion",  # Loop back (placeholder)
                "end": END,
            },
        )

        logger.info("LangGraph workflow created successfully")
        return workflow

    def _initialize_state_node(
        self, state: LangGraphPartyScrapingState
    ) -> LangGraphPartyScrapingState:
        """Initialize the state for a new scraping session.

        Args:
            state: Current LangGraph state

        Returns:
            Updated state with initialized values
        """
        logger.info(
            f"Initializing scraping for party: {state.get('party_name', 'Unknown')}"
        )

        # Ensure required fields are present
        if "visited_urls" not in state:
            state["visited_urls"] = set()
        if "extracted_members" not in state:
            state["extracted_members"] = []
        if "pending_urls" not in state:
            state["pending_urls"] = []
        if "depth" not in state:
            state["depth"] = 0
        if "messages" not in state:
            state["messages"] = []

        return state

    def _check_completion_node(
        self, state: LangGraphPartyScrapingState
    ) -> LangGraphPartyScrapingState:
        """Check if the scraping is complete.

        Args:
            state: Current LangGraph state

        Returns:
            Updated state
        """
        pending_count = len(state.get("pending_urls", []))
        extracted_count = len(state.get("extracted_members", []))

        logger.info(
            f"Completion check: {extracted_count} members extracted, "
            f"{pending_count} URLs pending"
        )

        return state

    def _should_continue(self, state: LangGraphPartyScrapingState) -> str:
        """Determine if the agent should continue processing or finish.

        Args:
            state: Current LangGraph state

        Returns:
            "continue" if there are pending URLs, "end" otherwise
        """
        pending_urls = state.get("pending_urls", [])

        if pending_urls:
            logger.debug(f"Continuing: {len(pending_urls)} URLs remaining")
            return "continue"
        else:
            logger.info("All URLs processed, ending scraping session")
            return "end"

    async def scrape(self, initial_state: PartyScrapingState) -> PartyScrapingState:
        """Execute hierarchical scraping using LangGraph.

        This method:
        1. Converts domain state to LangGraph state
        2. Invokes the compiled LangGraph agent
        3. Converts result back to domain state

        Args:
            initial_state: Domain state to start scraping from

        Returns:
            Final domain state with scraping results

        Raises:
            RuntimeError: If agent is not initialized
            ValueError: If initial_state is invalid
        """
        if not self._is_initialized or self._compiled_agent is None:
            raise RuntimeError("Agent not initialized. Call _initialize_agent() first.")

        if not initial_state.current_url:
            raise ValueError("initial_state must have a current_url")

        logger.info(
            f"Starting scraping for party {initial_state.party_name} "
            f"from {initial_state.current_url}"
        )

        # Convert domain state to LangGraph state
        lg_state = domain_to_langgraph_state(initial_state)

        try:
            # Invoke the LangGraph agent
            result_lg_state = self._compiled_agent.invoke(lg_state)

            # Convert back to domain state
            # Type: ignore for LangGraph's return type complexity
            final_state = langgraph_to_domain_state(result_lg_state)  # type: ignore[arg-type]

            logger.info(
                f"Scraping completed: {final_state.total_extracted()} members extracted"
            )

            return final_state

        except Exception as e:
            error_msg = f"Scraping failed: {str(e)}"
            logger.error(error_msg)

            # Return new state with error (do not mutate input)
            return replace(initial_state, error_message=error_msg)

    def is_initialized(self) -> bool:
        """Check if the agent is properly initialized.

        Returns:
            True if agent is ready, False otherwise
        """
        return self._is_initialized and self._compiled_agent is not None
