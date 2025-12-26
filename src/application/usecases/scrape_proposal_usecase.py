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
            content=scraped_data.content,
            proposal_number=scraped_data.proposal_number,
            submission_date=scraped_data.submission_date,
            summary=scraped_data.summary,
            detail_url=scraped_data.url,  # Default to detail_url for scraped content
            status_url=None,  # Status URL can be set separately
            meeting_id=input_dto.meeting_id,
        )

        proposal_num = output_dto.proposal_number or "No number"
        logger.info(f"Successfully scraped proposal: {proposal_num}")
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

        # Check if proposal already exists (by URL or proposal number)
        if scraped_dto.proposal_number:
            existing = await self.proposal_repo.get_by_proposal_number(
                scraped_dto.proposal_number
            )
            if existing:
                logger.warning(f"Proposal {scraped_dto.proposal_number} already exists")
                return self._entity_to_dto(existing)

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
            content=scraped_dto.content,
            detail_url=scraped_dto.detail_url,
            status_url=scraped_dto.status_url,
            submission_date=scraped_dto.submission_date,
            proposal_number=scraped_dto.proposal_number,
            meeting_id=scraped_dto.meeting_id,
            summary=scraped_dto.summary,
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
        existing.content = scraped_dto.content or existing.content
        existing.detail_url = scraped_dto.detail_url or existing.detail_url
        existing.status_url = scraped_dto.status_url or existing.status_url
        existing.submission_date = (
            scraped_dto.submission_date or existing.submission_date
        )
        existing.proposal_number = (
            scraped_dto.proposal_number or existing.proposal_number
        )
        existing.summary = scraped_dto.summary or existing.summary

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
            content=proposal.content,
            detail_url=proposal.detail_url,
            status_url=proposal.status_url,
            submission_date=proposal.submission_date,
            proposal_number=proposal.proposal_number,
            meeting_id=proposal.meeting_id,
            summary=proposal.summary,
        )
