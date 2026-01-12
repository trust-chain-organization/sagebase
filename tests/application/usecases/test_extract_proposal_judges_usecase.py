"""Tests for ExtractProposalJudgesUseCase"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.proposal_judge_dto import (
    CreateProposalJudgesInputDTO,
    ExtractProposalJudgesInputDTO,
    MatchProposalJudgesInputDTO,
)
from src.application.usecases.extract_proposal_judges_usecase import (
    ExtractProposalJudgesUseCase,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.politician import Politician
from src.domain.entities.proposal_judge import ProposalJudge


class TestExtractProposalJudgesUseCase:
    """Test ExtractProposalJudgesUseCase"""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories"""
        proposal_repo = AsyncMock()
        politician_repo = AsyncMock()
        extracted_repo = AsyncMock()
        judge_repo = AsyncMock()
        return proposal_repo, politician_repo, extracted_repo, judge_repo

    @pytest.fixture
    def mock_services(self):
        """Create mock services"""
        scraper_service = AsyncMock()
        scraper_service.is_supported_url = MagicMock(return_value=True)
        llm_service = AsyncMock()
        return scraper_service, llm_service

    @pytest.fixture
    def use_case(self, mock_repositories, mock_services):
        """Create use case instance with mocks"""
        proposal_repo, politician_repo, extracted_repo, judge_repo = mock_repositories
        scraper_service, llm_service = mock_services

        return ExtractProposalJudgesUseCase(
            proposal_repository=proposal_repo,
            politician_repository=politician_repo,
            extracted_proposal_judge_repository=extracted_repo,
            proposal_judge_repository=judge_repo,
            web_scraper_service=scraper_service,
            llm_service=llm_service,
        )

    @pytest.mark.asyncio
    async def test_extract_judges_success(self, use_case, mock_repositories):
        """Test successful extraction of proposal judges"""
        # Arrange
        _, _, extracted_repo, _ = mock_repositories
        # Mock repository to return no existing data (so we'll proceed with scraping)
        extracted_repo.get_by_proposal.return_value = []

        # Mock the scraper service on the use_case instance directly
        use_case.scraper.scrape_proposal_judges.return_value = [
            {"name": "山田太郎", "party": "○○党", "judgment": "APPROVE"},
            {"name": "田中花子", "party": "△△党", "judgment": "OPPOSE"},
            {"name": "佐藤一郎", "party": None, "judgment": "ABSTAIN"},
        ]

        # Mock repository to return created entities
        created_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=1,
                extracted_politician_name="山田太郎",
                extracted_party_name="○○党",
                extracted_judgment="APPROVE",
                source_url="http://example.com",
            ),
            ExtractedProposalJudge(
                id=2,
                proposal_id=1,
                extracted_politician_name="田中花子",
                extracted_party_name="△△党",
                extracted_judgment="OPPOSE",
                source_url="http://example.com",
            ),
            ExtractedProposalJudge(
                id=3,
                proposal_id=1,
                extracted_politician_name="佐藤一郎",
                extracted_party_name=None,
                extracted_judgment="ABSTAIN",
                source_url="http://example.com",
            ),
        ]
        extracted_repo.create.side_effect = created_judges

        input_dto = ExtractProposalJudgesInputDTO(
            url="http://example.com/proposal/123",
            proposal_id=1,
        )

        # Act
        result = await use_case.extract_judges(input_dto)

        # Assert
        assert result.proposal_id == 1
        assert result.extracted_count == 3
        assert len(result.judges) == 3
        assert result.judges[0].extracted_name == "山田太郎"
        assert result.judges[0].extracted_judgment == "APPROVE"
        assert result.judges[1].extracted_name == "田中花子"
        assert result.judges[1].extracted_judgment == "OPPOSE"
        assert result.judges[2].extracted_name == "佐藤一郎"
        assert result.judges[2].extracted_judgment == "ABSTAIN"

    @pytest.mark.asyncio
    async def test_extract_judges_unsupported_url(self, use_case, mock_services):
        """Test extraction with unsupported URL"""
        # Arrange
        scraper_service, _ = mock_services
        scraper_service.is_supported_url.return_value = False

        input_dto = ExtractProposalJudgesInputDTO(
            url="http://unsupported.com/page",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported URL"):
            await use_case.extract_judges(input_dto)

    @pytest.mark.asyncio
    async def test_extract_judges_with_existing_data(self, use_case, mock_repositories):
        """Test extraction when data already exists"""
        # Arrange
        _, _, extracted_repo, _ = mock_repositories
        existing_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=1,
                extracted_politician_name="既存データ",
                extracted_judgment="APPROVE",
                source_url="http://example.com",
            )
        ]
        extracted_repo.get_by_proposal.return_value = existing_judges

        input_dto = ExtractProposalJudgesInputDTO(
            url="http://example.com/proposal/123",
            proposal_id=1,
            force=False,
        )

        # Act
        result = await use_case.extract_judges(input_dto)

        # Assert
        assert result.extracted_count == 1
        assert result.judges[0].extracted_name == "既存データ"
        # Should not have called scraper
        use_case.scraper.scrape_proposal_judges.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_judges_success(
        self, use_case, mock_repositories, mock_services
    ):
        """Test successful matching of judges with politicians"""
        # Arrange
        _, politician_repo, extracted_repo, _ = mock_repositories
        _, llm_service = mock_services

        # Mock pending judges
        pending_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=1,
                extracted_politician_name="山田太郎",
                extracted_party_name="○○党",
                extracted_judgment="APPROVE",
                source_url="http://example.com",
                matching_status="pending",
            )
        ]
        extracted_repo.get_pending_by_proposal.return_value = pending_judges

        # Mock politician search
        politician = Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        politician_repo.search_by_name.return_value = [politician]
        politician_repo.get_by_id.return_value = politician

        # Mock LLM matching
        llm_service.match_conference_member.return_value = {
            "matched_id": 10,
            "confidence": 0.95,
            "reason": "Name exact match",
        }

        input_dto = MatchProposalJudgesInputDTO(proposal_id=1)

        # Act
        result = await use_case.match_judges(input_dto)

        # Assert
        assert result.matched_count == 1
        assert result.needs_review_count == 0
        assert result.no_match_count == 0
        assert len(result.results) == 1
        assert result.results[0].matched_politician_id == 10
        assert result.results[0].confidence_score == 0.95
        assert result.results[0].matching_status == "matched"

    @pytest.mark.asyncio
    async def test_match_judges_no_candidates(self, use_case, mock_repositories):
        """Test matching when no politician candidates are found"""
        # Arrange
        _, politician_repo, extracted_repo, _ = mock_repositories

        pending_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=1,
                extracted_politician_name="存在しない議員",
                extracted_judgment="APPROVE",
                source_url="http://example.com",
                matching_status="pending",
            )
        ]
        extracted_repo.get_all_pending.return_value = pending_judges

        # No politicians found
        politician_repo.search_by_name.return_value = []

        input_dto = MatchProposalJudgesInputDTO()

        # Act
        result = await use_case.match_judges(input_dto)

        # Assert
        assert result.matched_count == 0
        assert result.no_match_count == 1
        assert result.results[0].matching_status == "no_match"
        assert result.results[0].confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_create_judges_success(self, use_case, mock_repositories):
        """Test successful creation of proposal judges"""
        # Arrange
        _, politician_repo, extracted_repo, judge_repo = mock_repositories

        # Mock matched judges
        matched_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=1,
                extracted_politician_name="山田太郎",
                extracted_judgment="賛成",
                source_url="http://example.com",
                matched_politician_id=10,
                matching_status="matched",
                matching_confidence=0.95,
            )
        ]
        extracted_repo.get_all_matched.return_value = matched_judges

        # Mock politician
        politician = Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        politician_repo.get_by_id.return_value = politician

        # Mock no existing judge
        judge_repo.get_by_proposal_and_politician.return_value = None

        # Mock created judge
        created_judge = ProposalJudge(
            id=100,
            proposal_id=1,
            politician_id=10,
            approve="賛成",
        )
        judge_repo.create.return_value = created_judge

        input_dto = CreateProposalJudgesInputDTO()

        # Act
        result = await use_case.create_judges(input_dto)

        # Assert
        assert result.created_count == 1
        assert result.skipped_count == 0
        assert len(result.judges) == 1
        assert result.judges[0].politician_id == 10
        assert result.judges[0].politician_name == "山田太郎"
        assert result.judges[0].judgment == "賛成"

    @pytest.mark.asyncio
    async def test_create_judges_skip_existing(self, use_case, mock_repositories):
        """Test that existing judges are skipped"""
        # Arrange
        _, politician_repo, extracted_repo, judge_repo = mock_repositories

        matched_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=1,
                extracted_politician_name="山田太郎",
                extracted_judgment="賛成",
                source_url="http://example.com",
                matched_politician_id=10,
                matching_status="matched",
            )
        ]
        extracted_repo.get_all_matched.return_value = matched_judges

        # Mock existing judge
        existing_judge = ProposalJudge(
            id=100,
            proposal_id=1,
            politician_id=10,
            approve="賛成",
        )
        judge_repo.get_by_proposal_and_politician.return_value = existing_judge

        input_dto = CreateProposalJudgesInputDTO()

        # Act
        result = await use_case.create_judges(input_dto)

        # Assert
        assert result.created_count == 0
        assert result.skipped_count == 1
        assert len(result.judges) == 0

    @pytest.mark.asyncio
    async def test_create_judges_skip_no_proposal_id(self, use_case, mock_repositories):
        """Test that judges without proposal_id are skipped"""
        # Arrange
        _, _, extracted_repo, _ = mock_repositories

        matched_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=0,  # No proposal ID - use 0 instead of None
                extracted_politician_name="山田太郎",
                extracted_judgment="賛成",
                source_url="http://example.com",
                matched_politician_id=10,
                matching_status="matched",
            )
        ]
        extracted_repo.get_all_matched.return_value = matched_judges

        input_dto = CreateProposalJudgesInputDTO()

        # Act
        result = await use_case.create_judges(input_dto)

        # Assert
        assert result.created_count == 0
        assert result.skipped_count == 1
