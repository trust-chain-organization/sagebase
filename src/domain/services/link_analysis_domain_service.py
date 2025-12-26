"""Domain service for analyzing link relationships and hierarchies."""

import logging

from urllib.parse import urlparse

from src.domain.value_objects.link import Link

logger = logging.getLogger(__name__)


class LinkAnalysisDomainService:
    """Domain service for link hierarchy and relationship analysis.

    This service contains pure business logic for analyzing relationships
    between URLs, determining parent-child relationships, and checking
    domain/subdomain relationships. It has no dependencies on external
    frameworks or infrastructure.
    """

    def is_child_page(self, link_url: str, parent_url: str) -> bool:
        """Determine if a link represents a child page of the parent.

        A child page is defined as a URL that:
        1. Is in the same domain/subdomain as the parent
        2. Either:
           a) Has a longer path with parent's path as prefix (traditional hierarchy)
           b) Contains member list patterns (for party sites with non-hierarchical paths)

        Args:
            link_url: The URL to check
            parent_url: The parent URL to compare against

        Returns:
            True if link_url is a child of parent_url, False otherwise

        Example:
            >>> service = LinkAnalysisDomainService()
            >>> service.is_child_page(
            ...     "https://example.com/party/members/tokyo",
            ...     "https://example.com/party/members"
            ... )
            True
            >>> service.is_child_page(
            ...     "https://www.jcp.or.jp/list/pref/1",
            ...     "https://www.jcp.or.jp/giin/"
            ... )
            True
        """
        try:
            link_parts = urlparse(link_url)
            parent_parts = urlparse(parent_url)

            # Must be same domain/subdomain
            if not self.is_same_domain_or_subdomain(link_url, parent_url):
                return False

            # Normalize paths (remove trailing slashes)
            link_path = link_parts.path.rstrip("/")
            parent_path = parent_parts.path.rstrip("/")

            # Get path segments
            link_segments = [s for s in link_path.split("/") if s]
            parent_segments = [s for s in parent_path.split("/") if s]

            # Check traditional hierarchy (parent path is prefix)
            if len(link_segments) > len(parent_segments):
                if link_segments[: len(parent_segments)] == parent_segments:
                    return True

            # Check for member list patterns (for non-hierarchical paths)
            # Common patterns in party member pages:
            # - /list/, /pref/, /member/, /district/, /region/, /area/
            # - Prefecture codes, city codes, etc.
            member_patterns = [
                "/list/",
                "/pref/",
                "/member/",
                "/district/",
                "/region/",
                "/area/",
                "/local/",
                "/chihou/",
                "/todofuken/",
                "/shiku/",
                "/city/",
                "/town/",
            ]

            link_path_lower = link_path.lower()

            # If link contains member patterns and is in same domain, consider it a child
            for pattern in member_patterns:
                if pattern in link_path_lower:
                    logger.debug(
                        f"Recognized {link_url} as child page due to pattern '{pattern}'"
                    )
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error checking child page relationship: {e}")
            return False

    def is_sibling_page(self, link_url: str, reference_url: str) -> bool:
        """Determine if a link is a sibling page (same level, different params).

        Sibling pages are at the same hierarchy level but may differ in:
        - Query parameters (e.g., ?page=2 vs ?page=3)
        - Fragment identifiers
        - Last path segment

        Args:
            link_url: The URL to check
            reference_url: The reference URL to compare against

        Returns:
            True if link_url is a sibling of reference_url, False otherwise
        """
        try:
            link_parts = urlparse(link_url)
            ref_parts = urlparse(reference_url)

            # Must be same domain
            if not self.is_same_domain_or_subdomain(link_url, reference_url):
                return False

            # Get path segments
            link_path = link_parts.path.rstrip("/")
            ref_path = ref_parts.path.rstrip("/")

            link_segments = [s for s in link_path.split("/") if s]
            ref_segments = [s for s in ref_path.split("/") if s]

            # Same number of segments
            if len(link_segments) != len(ref_segments):
                return False

            # Different query params or different last segment makes it a sibling
            if link_parts.query != ref_parts.query:
                return True

            if link_segments != ref_segments:
                return True

            return False

        except Exception as e:
            logger.warning(f"Error checking sibling page relationship: {e}")
            return False

    def is_same_domain_or_subdomain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain or subdomain.

        Args:
            url1: First URL to compare
            url2: Second URL to compare

        Returns:
            True if URLs are same domain or subdomains of each other

        Example:
            >>> service = LinkAnalysisDomainService()
            >>> service.is_same_domain_or_subdomain(
            ...     "https://sub.example.com/page",
            ...     "https://example.com"
            ... )
            True
        """
        try:
            url1_parts = urlparse(url1)
            url2_parts = urlparse(url2)

            domain1 = url1_parts.netloc.lower()
            domain2 = url2_parts.netloc.lower()

            # Exact match
            if domain1 == domain2:
                return True

            # Check if one is subdomain of the other
            if domain1.endswith("." + domain2) or domain2.endswith("." + domain1):
                return True

            return False

        except Exception as e:
            logger.warning(f"Error comparing domains for {url1} and {url2}: {e}")
            return False

    def filter_child_pages(self, links: list[Link], parent_url: str) -> list[Link]:
        """Filter a list of links to only include child pages.

        Args:
            links: List of Link value objects to filter
            parent_url: The parent URL to check against

        Returns:
            List of links that are children of parent_url
        """
        child_pages = []
        for link in links:
            is_child = self.is_child_page(link.url, parent_url)
            if is_child:
                child_pages.append(link)
                logger.debug(f"✓ Child page detected: {link.url}")
            else:
                logger.debug(f"✗ Not a child page: {link.url}")

        print(
            f"DEBUG filter_child_pages: Filtered {len(child_pages)} "
            f"child pages from {len(links)} total links"
        )
        return child_pages

    def filter_sibling_pages(self, links: list[Link], reference_url: str) -> list[Link]:
        """Filter a list of links to only include sibling pages.

        Args:
            links: List of Link value objects to filter
            reference_url: The reference URL to check against

        Returns:
            List of links that are siblings of reference_url
        """
        return [link for link in links if self.is_sibling_page(link.url, reference_url)]

    def exclude_current_page(self, links: list[Link], current_url: str) -> list[Link]:
        """Exclude the current page URL from a list of links.

        Args:
            links: List of Link value objects
            current_url: The current page URL to exclude

        Returns:
            List of links excluding the current page
        """
        return [link for link in links if link.url != current_url]
