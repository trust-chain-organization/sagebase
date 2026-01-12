"""Tests for ParliamentaryGroupMemberMatchingService."""

from unittest.mock import AsyncMock

import pytest

from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.entities.politician import Politician
from src.domain.services.parliamentary_group_member_matching_service import (
    ParliamentaryGroupMemberMatchingService,
)
from src.domain.types import LLMMatchResult


class TestParliamentaryGroupMemberMatchingService:
    """Test cases for ParliamentaryGroupMemberMatchingService."""

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_speaker_service(self):
        """Create mock speaker domain service."""
        from unittest.mock import MagicMock

        service = MagicMock()
        service.normalize_speaker_name = lambda name: name.replace("議員", "").strip()
        service.calculate_name_similarity = lambda n1, n2: (
            1.0 if n1.replace("議員", "").strip() == n2.strip() else 0.3
        )
        return service

    @pytest.fixture
    def matching_service(
        self, mock_politician_repo, mock_llm_service, mock_speaker_service
    ):
        """Create ParliamentaryGroupMemberMatchingService instance."""
        return ParliamentaryGroupMemberMatchingService(
            politician_repository=mock_politician_repo,
            llm_service=mock_llm_service,
            speaker_service=mock_speaker_service,
        )

    @pytest.mark.asyncio
    async def test_find_matching_politician_rule_based_high_confidence(
        self, matching_service, mock_politician_repo
    ):
        """Test rule-based matching with high confidence."""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎議員",
            source_url="http://example.com",
            extracted_party_name="自由民主党",
        )
        politician = Politician(
            name="田中太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
            id=100,
        )
        mock_politician_repo.search_by_name.return_value = [politician]

        # Act
        (
            politician_id,
            confidence,
            reason,
        ) = await matching_service.find_matching_politician(member)

        # Assert
        assert politician_id == 100
        assert confidence >= 0.8
        assert "Rule-based" in reason

    @pytest.mark.asyncio
    async def test_find_matching_politician_llm_based(
        self, matching_service, mock_politician_repo, mock_llm_service
    ):
        """Test LLM-based matching when rule-based confidence is low."""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="佐藤花子",
            source_url="http://example.com",
            extracted_party_name="立憲民主党",
        )
        politician = Politician(
            name="佐藤はな子",
            prefecture="東京都",
            district="東京2区",
            political_party_id=2,
            id=200,
        )
        mock_politician_repo.search_by_name.return_value = [politician]
        mock_politician_repo.get_all.return_value = [politician]

        # Mock LLM response
        llm_result: LLMMatchResult = {
            "matched": True,
            "confidence": 0.85,
            "reason": "LLM matched with high confidence",
            "matched_id": 200,
            "metadata": {},
        }
        mock_llm_service.match_conference_member.return_value = llm_result

        # Act
        (
            politician_id,
            confidence,
            reason,
        ) = await matching_service.find_matching_politician(member)

        # Assert
        assert politician_id == 200
        assert confidence == 0.85
        assert "LLM" in reason

    @pytest.mark.asyncio
    async def test_find_matching_politician_no_match(
        self, matching_service, mock_politician_repo, mock_llm_service
    ):
        """Test when no matching politician is found."""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="Unknown Person",
            source_url="http://example.com",
        )
        mock_politician_repo.search_by_name.return_value = []
        mock_politician_repo.get_all.return_value = []
        mock_llm_service.match_conference_member.return_value = None

        # Act
        (
            politician_id,
            confidence,
            reason,
        ) = await matching_service.find_matching_politician(member)

        # Assert
        assert politician_id is None
        assert confidence == 0.0
        assert "No matching" in reason

    def test_determine_matching_status_matched(self, matching_service):
        """Test status determination for matched (≥0.7)."""
        assert matching_service.determine_matching_status(0.9) == "matched"
        assert matching_service.determine_matching_status(0.7) == "matched"

    def test_determine_matching_status_no_match(self, matching_service):
        """Test status determination for no_match (<0.7)."""
        assert matching_service.determine_matching_status(0.6) == "no_match"
        assert matching_service.determine_matching_status(0.5) == "no_match"
        assert matching_service.determine_matching_status(0.4) == "no_match"
        assert matching_service.determine_matching_status(0.0) == "no_match"
