"""Value object for page type classification result."""

from dataclasses import dataclass
from enum import Enum


# Default confidence threshold for classification decisions
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


class PageType(Enum):
    """Page type classification for hierarchical navigation."""

    INDEX_PAGE = "index_page"
    MEMBER_LIST_PAGE = "member_list_page"
    OTHER = "other"


@dataclass(frozen=True)
class PageClassification:
    """Result of page type classification.

    This value object represents the classification of a web page
    in the context of hierarchical party member scraping.

    Attributes:
        page_type: Type of the page (index, member list, or other)
        confidence: Classification confidence score (0.0 to 1.0)
        reason: Human-readable explanation for the classification
        has_child_links: Whether the page contains child page links
        has_member_info: Whether the page contains member information
    """

    page_type: PageType
    confidence: float
    reason: str
    has_child_links: bool
    has_member_info: bool

    def __post_init__(self) -> None:
        """Validate the classification data."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def is_confident(self, threshold: float | None = None) -> bool:
        """Check if classification confidence meets threshold.

        Args:
            threshold: Minimum confidence level (default: DEFAULT_CONFIDENCE_THRESHOLD)

        Returns:
            True if confidence >= threshold
        """
        if threshold is None:
            threshold = DEFAULT_CONFIDENCE_THRESHOLD
        return self.confidence >= threshold

    def should_explore_children(self, max_depth_reached: bool) -> bool:
        """Determine if child pages should be explored.

        Args:
            max_depth_reached: Whether maximum depth has been reached

        Returns:
            True if should explore child pages, False otherwise
        """
        if max_depth_reached:
            return False

        # Explore children only for index pages with confident classification
        return self.page_type == PageType.INDEX_PAGE and self.is_confident()

    def should_extract_members(self) -> bool:
        """Determine if members should be extracted from this page.

        Returns:
            True if should extract members, False otherwise
        """
        # Extract members only from member list pages with confident classification
        return self.page_type == PageType.MEMBER_LIST_PAGE and self.is_confident()
