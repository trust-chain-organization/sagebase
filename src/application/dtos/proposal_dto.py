"""DTOs for proposal use cases."""

from dataclasses import dataclass


@dataclass
class ScrapeProposalInputDTO:
    """Input DTO for scraping proposal information."""

    url: str
    meeting_id: int | None = None


@dataclass
class ScrapeProposalOutputDTO:
    """Output DTO for scraped proposal information."""

    title: str
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None


@dataclass
class CreateProposalDTO:
    """DTO for creating a new proposal."""

    title: str
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None
    conference_id: int | None = None


@dataclass
class UpdateProposalDTO:
    """DTO for updating an existing proposal."""

    id: int
    title: str | None = None
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None
    conference_id: int | None = None


@dataclass
class ProposalDTO:
    """DTO representing a proposal entity."""

    id: int
    title: str
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None
    conference_id: int | None = None
