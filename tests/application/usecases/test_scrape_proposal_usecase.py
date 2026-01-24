"""Unit tests for ScrapeProposalUseCase."""

from unittest.mock import MagicMock, create_autospec

import pytest

from src.application.dtos.proposal_dto import (
    ProposalDTO,
    ScrapeProposalInputDTO,
    ScrapeProposalOutputDTO,
)
from src.application.usecases.scrape_proposal_usecase import ScrapeProposalUseCase
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.services.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)
from src.domain.types.scraper_types import ScrapedProposal


class TestScrapeProposalUseCase:
    """Test suite for ScrapeProposalUseCase."""

    @pytest.fixture
    def mock_proposal_repo(self) -> MagicMock:
        """Create a mock proposal repository."""
        return create_autospec(ProposalRepository, spec_set=True)

    @pytest.fixture
    def mock_scraper_service(self) -> MagicMock:
        """Create a mock proposal scraper service."""
        return create_autospec(IProposalScraperService, spec_set=True)

    @pytest.fixture
    def use_case(
        self, mock_proposal_repo: MagicMock, mock_scraper_service: MagicMock
    ) -> ScrapeProposalUseCase:
        """Create a ScrapeProposalUseCase instance."""
        return ScrapeProposalUseCase(mock_proposal_repo, mock_scraper_service)

    @pytest.mark.asyncio
    async def test_execute_success(
        self, use_case: ScrapeProposalUseCase, mock_scraper_service: MagicMock
    ) -> None:
        """Test successful execution of proposal scraping."""
        # Setup
        input_dto = ScrapeProposalInputDTO(
            url="https://www.shugiin.go.jp/test", meeting_id=123
        )

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = ScrapedProposal(
            title="環境基本法改正案",
            url=input_dto.url,
        )

        # Execute
        result = await use_case.execute(input_dto)

        # Assert
        assert isinstance(result, ScrapeProposalOutputDTO)
        assert result.title == "環境基本法改正案"
        assert result.detail_url == input_dto.url
        assert result.meeting_id == 123

    @pytest.mark.asyncio
    async def test_execute_unsupported_url(
        self, use_case: ScrapeProposalUseCase, mock_scraper_service: MagicMock
    ) -> None:
        """Test that unsupported URLs raise ValueError."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="not-a-valid-url")
        mock_scraper_service.is_supported_url.return_value = False

        # Execute and assert
        with pytest.raises(ValueError, match="Unsupported URL"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_execute_scraping_error(
        self, use_case: ScrapeProposalUseCase, mock_scraper_service: MagicMock
    ) -> None:
        """Test that scraping errors are properly handled."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="https://www.shugiin.go.jp/test")
        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.side_effect = Exception("Network error")

        # Execute and assert
        with pytest.raises(RuntimeError, match="Failed to scrape proposal"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_scrape_and_save_new_proposal(
        self,
        use_case: ScrapeProposalUseCase,
        mock_proposal_repo: MagicMock,
        mock_scraper_service: MagicMock,
    ) -> None:
        """Test scraping and saving a new proposal."""
        # Setup
        input_dto = ScrapeProposalInputDTO(
            url="https://www.shugiin.go.jp/test", meeting_id=123
        )

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = ScrapedProposal(
            title="環境基本法改正案",
            url=input_dto.url,
        )

        # No existing proposal
        mock_proposal_repo.find_by_url.return_value = None

        # Mock saved proposal
        saved_proposal = Proposal(
            id=1,
            title="環境基本法改正案",
            detail_url=input_dto.url,
            meeting_id=123,
        )
        mock_proposal_repo.create.return_value = saved_proposal

        # Execute
        result = await use_case.scrape_and_save(input_dto)

        # Assert
        assert isinstance(result, ProposalDTO)
        assert result.id == 1
        assert result.title == "環境基本法改正案"
        assert result.meeting_id == 123

        # Verify repository calls
        mock_proposal_repo.find_by_url.assert_called_once_with(input_dto.url)
        mock_proposal_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_and_save_existing_proposal_by_url(
        self,
        use_case: ScrapeProposalUseCase,
        mock_proposal_repo: MagicMock,
        mock_scraper_service: MagicMock,
    ) -> None:
        """Test that existing proposals by URL are not duplicated."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="https://www.shugiin.go.jp/test")

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = ScrapedProposal(
            title="環境基本法改正案",
            url=input_dto.url,
        )

        # Existing proposal found by URL
        existing_proposal = Proposal(
            id=2,
            title="環境基本法改正案",
            detail_url=input_dto.url,
        )
        mock_proposal_repo.find_by_url.return_value = existing_proposal

        # Execute
        result = await use_case.scrape_and_save(input_dto)

        # Assert
        assert result.id == 2
        assert result.detail_url == input_dto.url

        # Verify save was not called
        mock_proposal_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_existing_proposal(
        self,
        use_case: ScrapeProposalUseCase,
        mock_proposal_repo: MagicMock,
        mock_scraper_service: MagicMock,
    ) -> None:
        """Test updating an existing proposal with scraped data."""
        # Setup
        proposal_id = 1
        new_url = "https://www.shugiin.go.jp/new"

        # Existing proposal
        existing_proposal = Proposal(
            id=proposal_id,
            title="旧法案",
            meeting_id=123,
        )
        mock_proposal_repo.get_by_id.return_value = existing_proposal

        # Scraped data
        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = ScrapedProposal(
            title="新環境基本法改正案",
            url=new_url,
        )

        # Updated proposal
        updated_proposal = Proposal(
            id=proposal_id,
            title="新環境基本法改正案",
            detail_url=new_url,
            meeting_id=123,
        )
        mock_proposal_repo.update.return_value = updated_proposal

        # Execute
        result = await use_case.update_existing_proposal(proposal_id, new_url)

        # Assert
        assert result.id == proposal_id
        assert result.title == "新環境基本法改正案"
        assert result.detail_url == new_url
        assert result.meeting_id == 123

        # Verify repository calls
        mock_proposal_repo.get_by_id.assert_called_once_with(proposal_id)
        mock_proposal_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_proposal(
        self,
        use_case: ScrapeProposalUseCase,
        mock_proposal_repo: MagicMock,
        mock_scraper_service: MagicMock,
    ) -> None:
        """Test that updating a nonexistent proposal raises ValueError."""
        # Setup
        proposal_id = 999
        url = "https://www.shugiin.go.jp/test"
        mock_proposal_repo.get_by_id.return_value = None

        # Execute and assert
        with pytest.raises(ValueError, match="Proposal with ID 999 not found"):
            await use_case.update_existing_proposal(proposal_id, url)
