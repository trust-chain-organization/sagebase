"""Domain entity for party scraping state (framework-independent)."""

import copy
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse

from src.domain.value_objects.politician_member_data import PoliticianMemberData
from src.domain.value_objects.scraping_config import ScrapingConfig


@dataclass
class PartyScrapingState:
    """Framework-independent state for hierarchical party member scraping.

    This entity represents the state of a scraping session as it navigates
    through hierarchical party member pages. It contains only domain concepts
    and has no dependencies on external frameworks like LangGraph.

    Attributes:
        current_url: URL of the currently processed page
        party_name: Name of the political party being scraped
        party_id: Database ID of the political party
        max_depth: Maximum allowed navigation depth (0 = root level)
        scraping_config: Configuration for scraping behavior
        visited_urls: Set of normalized URLs already visited
        pending_urls: Queue of URLs to visit with their depth levels
        extracted_members: List of politician data extracted so far
        depth: Current depth in the navigation hierarchy
        error_message: Error message if scraping failed
    """

    current_url: str
    party_name: str
    party_id: int
    max_depth: int
    scraping_config: ScrapingConfig = field(default_factory=ScrapingConfig)
    _visited_urls: set[str] = field(default_factory=set)
    _pending_urls: deque[tuple[str, int]] = field(default_factory=deque)
    _extracted_members: list[PoliticianMemberData] = field(default_factory=list)
    _extracted_member_names: set[str] = field(default_factory=set)
    depth: int = 0
    error_message: str | None = None

    @property
    def visited_urls(self) -> frozenset[str]:
        """Get immutable view of visited URLs.

        Returns:
            Frozen set of visited URLs (cannot be modified externally)
        """
        return frozenset(self._visited_urls)

    @property
    def pending_urls(self) -> tuple[tuple[str, int], ...]:
        """Get immutable view of pending URLs.

        Returns:
            Tuple of pending URLs (cannot be modified externally)
        """
        return tuple(self._pending_urls)

    @property
    def extracted_members(self) -> tuple[PoliticianMemberData, ...]:
        """Get immutable view of extracted members.

        Returns:
            Tuple of extracted member data (cannot be modified externally)
        """
        return tuple(self._extracted_members)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for consistent comparison.

        Removes fragments, trailing slashes, and normalizes case of scheme/host.

        Args:
            url: Raw URL string

        Returns:
            Normalized URL string

        Raises:
            ValueError: If URL is invalid
        """
        if not url or not url.strip():
            raise ValueError("URL cannot be empty or whitespace")

        url = url.strip()

        try:
            parsed = urlparse(url)

            # Ensure scheme and netloc exist
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL format: {url}")

            # Normalize: lowercase scheme/netloc, remove fragment/trailing slash
            normalized = urlunparse(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path.rstrip("/") if parsed.path != "/" else "/",
                    parsed.params,
                    parsed.query,
                    "",  # Remove fragment
                )
            )

            return normalized

        except Exception as e:
            raise ValueError(f"Failed to normalize URL '{url}': {e}") from e

    def is_complete(self) -> bool:
        """Check if scraping is complete.

        Scraping is complete when there are no more URLs to process.

        Returns:
            True if no pending URLs remain, False otherwise
        """
        return len(self._pending_urls) == 0

    def has_visited(self, url: str) -> bool:
        """Check if a URL has already been visited.

        Args:
            url: The URL to check (will be normalized)

        Returns:
            True if the URL has been visited, False otherwise

        Raises:
            ValueError: If URL is invalid
        """
        normalized_url = self._normalize_url(url)
        return normalized_url in self._visited_urls

    def mark_visited(self, url: str) -> None:
        """Mark a URL as visited.

        Args:
            url: The URL to mark as visited (will be normalized)

        Raises:
            ValueError: If URL is invalid
        """
        normalized_url = self._normalize_url(url)
        self._visited_urls.add(normalized_url)

    def add_pending_url(self, url: str, depth: int) -> bool:
        """Add a URL to the pending queue if not already visited.

        Args:
            url: The URL to add (will be normalized)
            depth: The depth level of this URL

        Returns:
            True if URL was added, False if skipped (visited or beyond max depth)

        Raises:
            ValueError: If URL is invalid or depth is negative
        """
        if depth < 0:
            raise ValueError(f"Depth cannot be negative: {depth}")

        normalized_url = self._normalize_url(url)

        if self.has_visited(normalized_url):
            return False

        if depth > self.max_depth:
            return False

        self._pending_urls.append((normalized_url, depth))
        return True

    def pop_next_url(self) -> tuple[str, int] | None:
        """Get the next URL to process from the queue (FIFO order).

        Uses deque.popleft() for O(1) performance.

        Returns:
            Tuple of (url, depth) or None if queue is empty
        """
        if self._pending_urls:
            return self._pending_urls.popleft()
        return None

    def add_extracted_member(self, member: PoliticianMemberData) -> bool:
        """Add an extracted politician member to the results.

        Deduplicates by name to avoid duplicate politicians.

        Args:
            member: Politician member data

        Returns:
            True if member was added, False if duplicate (same name already exists)

        Raises:
            ValueError: If member has no name
        """
        if "name" not in member or not member["name"]:
            raise ValueError("Member must have a non-empty 'name' field")

        # Deduplicate by name
        name = member["name"]
        if name in self._extracted_member_names:
            return False

        # Deep copy to prevent external mutation
        member_copy = copy.deepcopy(member)
        self._extracted_members.append(member_copy)
        self._extracted_member_names.add(name)
        return True

    def add_extracted_members(self, members: list[PoliticianMemberData]) -> int:
        """Add multiple extracted politician members to the results.

        Deduplicates by name.

        Args:
            members: List of politician member data

        Returns:
            Number of members actually added (after deduplication)

        Raises:
            ValueError: If any member has no name
        """
        added_count = 0
        for member in members:
            if self.add_extracted_member(member):
                added_count += 1
        return added_count

    def at_max_depth(self) -> bool:
        """Check if current depth has reached maximum allowed depth.

        Returns:
            True if at max depth, False otherwise
        """
        return self.depth >= self.max_depth

    def total_extracted(self) -> int:
        """Get total number of members extracted.

        Returns:
            Count of extracted members
        """
        return len(self.extracted_members)

    def total_pending(self) -> int:
        """Get total number of pending URLs.

        Returns:
            Count of pending URLs
        """
        return len(self.pending_urls)
