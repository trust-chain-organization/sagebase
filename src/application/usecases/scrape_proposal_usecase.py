"""Use case for scraping proposal information from URLs."""

import logging

from src.application.dtos.proposal_dto import (
    ProposalDTO,
    ScrapeProposalInputDTO,
    ScrapeProposalOutputDTO,
)
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.services.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)
from src.domain.types.scraper_types import ScrapedProposal


logger = logging.getLogger(__name__)


class ScrapeProposalUseCase:
    """Use case for scraping and storing proposal information."""

    def __init__(
        self,
        proposal_repository: ProposalRepository,
        proposal_scraper_service: IProposalScraperService,
    ):
        """Initialize the scrape proposal use case.

        Args:
            proposal_repository: Repository for managing proposals
            proposal_scraper_service: Service for scraping proposal information
        """
        self.proposal_repo = proposal_repository
        self.scraper = proposal_scraper_service

    async def execute(
        self, input_dto: ScrapeProposalInputDTO
    ) -> ScrapeProposalOutputDTO:
        """Execute the proposal scraping process.

        Args:
            input_dto: Input data containing the URL and optional meeting ID

        Returns:
            Output DTO containing the scraped proposal information

        Raises:
            ValueError: If the URL is not supported
            RuntimeError: If scraping fails
        """
        logger.info(f"Starting to scrape proposal from URL: {input_dto.url}")

        # Check if URL is supported
        if not self.scraper.is_supported_url(input_dto.url):
            raise ValueError(f"Unsupported URL: {input_dto.url}")

        # Scrape the proposal information
        try:
            scraped_data: ScrapedProposal = await self.scraper.scrape_proposal(
                input_dto.url
            )
        except Exception as e:
            logger.error(f"Failed to scrape proposal from {input_dto.url}: {str(e)}")
            raise RuntimeError(f"Failed to scrape proposal: {str(e)}") from e

        # Create output DTO with scraped data
        output_dto = ScrapeProposalOutputDTO(
            title=scraped_data.title,
            detail_url=scraped_data.url,
            status_url=None,
            votes_url=None,
            meeting_id=input_dto.meeting_id,
        )

        logger.info(f"Successfully scraped proposal: {output_dto.title[:50]}...")
        return output_dto

    async def scrape_and_save(self, input_dto: ScrapeProposalInputDTO) -> ProposalDTO:
        """Scrape proposal information and save it to the database.

        Args:
            input_dto: Input data containing the URL and optional meeting ID

        Returns:
            DTO of the saved proposal

        Raises:
            ValueError: If the URL is not supported or proposal already exists
            RuntimeError: If scraping or saving fails
        """
        # First scrape the proposal
        scraped_dto = await self.execute(input_dto)

        # Check by URL (detail_url)
        if scraped_dto.detail_url:
            existing_by_url = await self.proposal_repo.find_by_url(
                scraped_dto.detail_url
            )
            if existing_by_url:
                logger.warning(
                    f"Proposal with URL {scraped_dto.detail_url} already exists"
                )
                return self._entity_to_dto(existing_by_url)

        # Create new proposal entity
        proposal = Proposal(
            title=scraped_dto.title,
            detail_url=scraped_dto.detail_url,
            status_url=scraped_dto.status_url,
            votes_url=scraped_dto.votes_url,
            meeting_id=scraped_dto.meeting_id,
        )

        # Save to database
        saved_proposal = await self.proposal_repo.create(proposal)
        logger.info(f"Saved proposal with ID: {saved_proposal.id}")

        return self._entity_to_dto(saved_proposal)

    async def update_existing_proposal(self, proposal_id: int, url: str) -> ProposalDTO:
        """Update an existing proposal with scraped information.

        Args:
            proposal_id: ID of the proposal to update
            url: URL to scrape proposal information from

        Returns:
            DTO of the updated proposal

        Raises:
            ValueError: If proposal not found or URL not supported
            RuntimeError: If scraping or updating fails
        """
        # Get existing proposal
        existing = await self.proposal_repo.get_by_id(proposal_id)
        if not existing:
            raise ValueError(f"Proposal with ID {proposal_id} not found")

        # Scrape new information
        input_dto = ScrapeProposalInputDTO(url=url, meeting_id=existing.meeting_id)
        scraped_dto = await self.execute(input_dto)

        # Update the existing proposal
        existing.title = scraped_dto.title or existing.title
        existing.detail_url = scraped_dto.detail_url or existing.detail_url
        existing.status_url = scraped_dto.status_url or existing.status_url
        existing.votes_url = scraped_dto.votes_url or existing.votes_url

        # Save updated proposal
        updated_proposal = await self.proposal_repo.update(existing)
        logger.info(f"Updated proposal with ID: {updated_proposal.id}")

        return self._entity_to_dto(updated_proposal)

    def _entity_to_dto(self, proposal: Proposal) -> ProposalDTO:
        """Convert a Proposal entity to a ProposalDTO.

        Args:
            proposal: The proposal entity

        Returns:
            The proposal DTO
        """
        if proposal.id is None:
            raise RuntimeError("Proposal ID should not be None")
        return ProposalDTO(
            id=proposal.id,
            title=proposal.title,
            detail_url=proposal.detail_url,
            status_url=proposal.status_url,
            votes_url=proposal.votes_url,
            meeting_id=proposal.meeting_id,
            conference_id=proposal.conference_id,
        )
