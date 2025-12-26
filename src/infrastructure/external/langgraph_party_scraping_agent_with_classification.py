"""Enhanced LangGraph-based party scraping agent with page classification.

This module extends the base LangGraph agent with page classification
and recursive navigation capabilities (PBI-004).
"""

import logging
from dataclasses import replace

from langgraph.graph import END, START, StateGraph

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.services.interfaces.link_analyzer_service import ILinkAnalyzerService
from src.domain.services.interfaces.page_classifier_service import (
    IPageClassifierService,
)
from src.domain.services.interfaces.party_scraping_agent import IPartyScrapingAgent
from src.domain.services.interfaces.web_scraper_service import IWebScraperService
from src.domain.services.party_member_extraction_service import (
    IPartyMemberExtractionService,
)

from .langgraph_nodes.decision_node import should_explore_children
from .langgraph_nodes.explore_children_node import create_explore_children_node
from .langgraph_nodes.extract_members_node import create_extract_members_node
from .langgraph_nodes.page_classifier_node import create_page_classifier_node
from .langgraph_state_adapter import (
    LangGraphPartyScrapingState,
    domain_to_langgraph_state,
    langgraph_to_domain_state,
)


logger = logging.getLogger(__name__)


class LangGraphPartyScrapingAgentWithClassification(IPartyScrapingAgent):
    """Enhanced LangGraph agent with page classification and navigation.

    This implementation adds:
    - Page type classification (index_page, member_list_page, other)
    - Decision logic for navigation strategy
    - Support for hierarchical page exploration
    """

    def __init__(
        self,
        page_classifier: IPageClassifierService,
        scraper: IWebScraperService,
        member_extractor: IPartyMemberExtractionService,
        link_analyzer: ILinkAnalyzerService,
    ):
        """Initialize the enhanced LangGraph agent.

        Args:
            page_classifier: Service for classifying page types
            scraper: Web scraper service for fetching HTML content
            member_extractor: Domain service for member extraction
            link_analyzer: Domain service for analyzing page links
        """
        self._page_classifier = page_classifier
        self._scraper = scraper
        self._member_extractor = member_extractor
        self._link_analyzer = link_analyzer
        self._compiled_agent = None
        self._is_initialized = False
        self._initialize_agent()

    def _initialize_agent(self) -> None:
        """Initialize and compile the LangGraph workflow."""
        try:
            workflow = self._create_workflow()
            # Compile the workflow
            # Note: recursion_limit is set in ainvoke() config, not here
            self._compiled_agent = workflow.compile()
            self._is_initialized = True
            logger.info(
                "Enhanced LangGraph party scraping agent initialized successfully"
            )
        except Exception as e:
            logger.error(f"Failed to initialize enhanced LangGraph agent: {e}")
            self._is_initialized = False
            raise

    def _create_workflow(self) -> StateGraph:
        """Create the enhanced LangGraph StateGraph workflow.

        Workflow:
        1. Initialize state
        2. Pop next URL from pending queue
        3. Classify page type
        4. Decision: explore_children / extract_members / skip
        5. For explore_children: analyze links and add to pending
        6. For extract_members: extract member data
        7. Back to step 2 if pending URLs remain

        Returns:
            Configured StateGraph ready for compilation
        """
        workflow = StateGraph(LangGraphPartyScrapingState)

        # Create nodes
        classify_page_node = create_page_classifier_node(
            self._page_classifier, self._scraper
        )
        explore_children_node = create_explore_children_node(
            self._scraper, self._link_analyzer
        )
        extract_members_node = create_extract_members_node(
            self._scraper, self._member_extractor
        )

        # Add nodes
        workflow.add_node("initialize", self._initialize_state_node)
        workflow.add_node("pop_next_url", self._pop_next_url_node)
        workflow.add_node("classify_page", classify_page_node)
        workflow.add_node("explore_children", explore_children_node)
        workflow.add_node("extract_members", extract_members_node)

        # Define edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "pop_next_url")

        # After popping URL, check if we have a URL to process
        workflow.add_conditional_edges(
            "pop_next_url",
            self._has_current_url,
            {
                "classify": "classify_page",
                "end": END,
            },
        )

        # Decision node with conditional edges
        workflow.add_conditional_edges(
            "classify_page",
            should_explore_children,
            {
                "explore_children": "explore_children",
                "extract_members": "extract_members",
                "continue": "pop_next_url",
                "end": END,
            },
        )

        # After processing, loop back
        workflow.add_edge("explore_children", "pop_next_url")
        workflow.add_edge("extract_members", "pop_next_url")

        logger.info("Enhanced LangGraph workflow created successfully")
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
        print(
            f"DEBUG Agent: Initializing state for {state.get('party_name', 'Unknown')}"
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

        # Add initial URL to pending if not already visited
        current_url = state.get("current_url")
        if current_url and current_url not in state["visited_urls"]:
            state["pending_urls"].append((current_url, 0))

        return state

    def _pop_next_url_node(
        self, state: LangGraphPartyScrapingState
    ) -> LangGraphPartyScrapingState:
        """Pop the next URL from pending queue and mark it as current.

        Args:
            state: Current LangGraph state

        Returns:
            Updated state with current_url and depth set
        """
        pending_urls = state.get("pending_urls", [])

        if not pending_urls:
            logger.info("No more URLs to process")
            print("DEBUG Agent: No more URLs in pending queue")
            state["current_url"] = ""
            return state

        # Pop first URL from queue (FIFO)
        next_url, depth = pending_urls.pop(0)
        state["pending_urls"] = pending_urls

        # Mark as visited
        visited_urls = state.get("visited_urls", set())
        visited_urls.add(next_url)
        state["visited_urls"] = visited_urls

        # Update current URL and depth
        state["current_url"] = next_url
        state["depth"] = depth

        logger.info(f"Processing URL (depth={depth}): {next_url}")
        print(
            f"DEBUG Agent: Popped URL (depth={depth}): {next_url}, pending={len(pending_urls)}"
        )

        return state

    def _has_current_url(self, state: LangGraphPartyScrapingState) -> str:
        """Check if there's a current URL to process.

        Args:
            state: Current state

        Returns:
            "classify" if current_url exists, "end" otherwise
        """
        current_url = state.get("current_url", "")
        return "classify" if current_url else "end"

    async def scrape(self, initial_state: PartyScrapingState) -> PartyScrapingState:
        """Execute hierarchical scraping using enhanced LangGraph.

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
            # Invoke the LangGraph agent asynchronously
            # Use recursion_limit from scraping_config for flexibility:
            # - Large parties (e.g., JCP): 500 for 47 prefectures + cities
            # - Small parties: 50-100 for fewer pages
            # - Testing: 10 to limit API calls
            recursion_limit = initial_state.scraping_config.recursion_limit
            result_lg_state = await self._compiled_agent.ainvoke(
                lg_state, config={"recursion_limit": recursion_limit}
            )

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
