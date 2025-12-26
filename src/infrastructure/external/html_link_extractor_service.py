"""BeautifulSoup4-based implementation of HTML link extraction."""

import logging

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.domain.services.interfaces.html_link_extractor_service import (
    IHtmlLinkExtractorService,
)
from src.domain.value_objects.link import Link


logger = logging.getLogger(__name__)


class BeautifulSoupLinkExtractor(IHtmlLinkExtractorService):
    """BeautifulSoup4 implementation of link extraction from HTML.

    This infrastructure service uses BeautifulSoup4 to parse HTML and extract
    links. It implements the IHtmlLinkExtractorService interface, allowing
    the implementation to be swapped without affecting domain or application
    layers.
    """

    def extract_links(self, html_content: str, base_url: str) -> list[Link]:
        """Extract all valid links from HTML content.

        This method:
        1. Parses HTML using BeautifulSoup4
        2. Finds all <a> tags with href attributes
        3. Filters out invalid links (anchors, javascript, mailto, tel)
        4. Resolves relative URLs to absolute URLs
        5. Creates Link value objects

        Args:
            html_content: Raw HTML content to parse
            base_url: Base URL for resolving relative links

        Returns:
            List of Link value objects with absolute URLs

        Raises:
            ValueError: If html_content is empty or base_url is invalid
        """
        if not html_content:
            raise ValueError("HTML content cannot be empty")
        if not base_url:
            raise ValueError("Base URL cannot be empty")

        soup = BeautifulSoup(html_content, "html.parser")
        links: list[Link] = []

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")  # type: ignore[assignment]

            # Skip invalid link types
            if not href or href.startswith(  # type: ignore[arg-type]
                ("#", "javascript:", "mailto:", "tel:")
            ):
                continue

            try:
                # Resolve relative URLs to absolute URLs
                absolute_url = urljoin(base_url, href)  # type: ignore[arg-type]

                # Extract link metadata
                text = anchor.get_text(strip=True)
                rel = anchor.get("rel", [])  # type: ignore[assignment,arg-type]
                rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)  # type: ignore[arg-type]
                title = str(anchor.get("title", ""))  # type: ignore[assignment]

                # Create Link value object
                link = Link(url=absolute_url, text=text, rel=rel_str, title=title)

                links.append(link)

            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to create link from {href}: {e}")
                continue

        logger.info(f"Extracted {len(links)} links from HTML content")
        return links
