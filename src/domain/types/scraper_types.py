"""Type definitions for scraper services - Domain layer."""

from dataclasses import dataclass


@dataclass
class ScrapedProposal:
    """Data class for scraped proposal information."""

    url: str
    title: str

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for backward compatibility."""
        return {
            "url": self.url,
            "title": self.title,
        }
