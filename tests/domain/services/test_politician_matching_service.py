"""Tests for PoliticianMatchingService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.exceptions import ExternalServiceException
from src.domain.services.politician_matching_service import (
    PoliticianMatch,
    PoliticianMatchingService,
)


# Test constants
POLITICIAN_MATCH_THRESHOLD = 0.7
HIGH_CONFIDENCE = 0.9


def assert_successful_match(
    result: PoliticianMatch,
    expected_id: int,
    expected_name: str,
    min_confidence: float = POLITICIAN_MATCH_THRESHOLD,
) -> None:
    """Helper to assert successful politician match.

    Args:
        result: The match result to verify
        expected_id: Expected politician ID
        expected_name: Expected politician name
        min_confidence: Minimum confidence threshold (default: 0.7)
    """
    assert result.matched is True
    assert result.politician_id == expected_id
    assert result.politician_name == expected_name
    assert result.confidence >= min_confidence


def assert_no_match(result: PoliticianMatch) -> None:
    """Helper to assert no match result.

    Args:
        result: The match result to verify
    """
    assert result.matched is False
    assert result.politician_id is None


class TestPoliticianMatchingService:
    """Test cases for PoliticianMatchingService."""

    @pytest.fixture
    def mock_politician_repository(self) -> AsyncMock:
        """Create a mock politician repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_llm_service(self) -> MagicMock:
        """Create a mock LLM service."""
        mock = MagicMock()
        mock.get_prompt.return_value = MagicMock()
        mock.invoke_with_retry = MagicMock()
        return mock

    @pytest.fixture
    def sample_politicians(self) -> list[dict[str, Any]]:
        """Create sample politicians for testing (as dicts from repository)."""
        return [
            {
                "id": 1,
                "name": "山田太郎",
                "party_name": "テスト党",
                "position": "衆議院議員",
                "prefecture": "東京都",
                "electoral_district": "東京1区",
            },
            {
                "id": 2,
                "name": "佐藤花子",
                "party_name": "テスト党",
                "position": "参議院議員",
                "prefecture": "大阪府",
                "electoral_district": None,
            },
            {
                "id": 3,
                "name": "鈴木一郎",
                "party_name": "サンプル党",
                "position": "衆議院議員",
                "prefecture": "神奈川県",
                "electoral_district": "神奈川3区",
            },
        ]

    @pytest.fixture
    def service(
        self, mock_llm_service: MagicMock, mock_politician_repository: AsyncMock
    ) -> PoliticianMatchingService:
        """Create PoliticianMatchingService for testing.

        Args:
            mock_llm_service: Mocked LLM service
            mock_politician_repository: Mocked politician repository

        Returns:
            PoliticianMatchingService instance for testing
        """
        return PoliticianMatchingService(mock_llm_service, mock_politician_repository)

    @pytest.mark.asyncio
    async def test_exact_match_with_party(
        self,
        service: PoliticianMatchingService,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test exact name match with matching party.

        Business Rule: Exact name + party match returns confidence = 1.0

        Given: Politician "山田太郎" exists in "テスト党"
        When: Searching for exact match with party
        Then: Returns matched=True with high confidence
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party="テスト党"
        )

        # Assert
        assert_successful_match(
            result,
            expected_id=1,
            expected_name="山田太郎",
            min_confidence=HIGH_CONFIDENCE,
        )

    @pytest.mark.asyncio
    async def test_match_with_honorific(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test matching with honorific (敬称) in speaker name.

        Business Rule: Honorifics (議員, 氏, etc.) should be stripped before matching

        Given: Politician "佐藤花子" exists
        When: Searching for "佐藤花子議員" (with honorific)
        Then: Returns matched=True after honorific removal
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response for honorific matching
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 2,
            "politician_name": "佐藤花子",
            "political_party_name": "テスト党",
            "confidence": 0.95,
            "reason": "敬称を除いた名前が完全一致",
        }

        # Act
        result = await service.find_best_match(
            speaker_name="佐藤花子議員", speaker_party="テスト党"
        )

        # Assert
        assert_successful_match(result, expected_id=2, expected_name="佐藤花子")

    @pytest.mark.asyncio
    async def test_no_match_nonexistent_name(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test no match when name doesn't exist.

        Business Rule: Non-existent names should return no match

        Given: No politician named "存在しない太郎" exists
        When: Searching for this name
        Then: Returns matched=False with null politician_id
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response for no match
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": False,
            "politician_id": None,
            "politician_name": None,
            "political_party_name": None,
            "confidence": 0.3,
            "reason": "候補者が見つかりません",
        }

        # Act
        result = await service.find_best_match(
            speaker_name="存在しない太郎", speaker_party="テスト党"
        )

        # Assert
        assert_no_match(result)

    @pytest.mark.asyncio
    async def test_low_confidence_treated_as_no_match(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test that low confidence results are treated as no match.

        Business Rule: Match confidence < 0.7 is rejected to avoid false positives

        Given: LLM returns low confidence (0.5) for similar name
        When: Confidence is below threshold
        Then: Result treated as no match with null politician_id
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response with low confidence
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 1,
            "politician_name": "山田太郎",
            "political_party_name": "テスト党",
            "confidence": 0.5,  # Low confidence (< 0.7 threshold)
            "reason": "類似性が低い",
        }

        # Act
        result = await service.find_best_match(
            speaker_name="山田次郎", speaker_party="テスト党"
        )

        # Assert
        assert_no_match(result)
        assert result.politician_name is None

    @pytest.mark.asyncio
    async def test_empty_politician_list(
        self,
        service: PoliticianMatchingService,
        mock_politician_repository: AsyncMock,
    ) -> None:
        """Test behavior when politician list is empty.

        Edge Case: Empty politician database

        Given: No politicians exist in the database
        When: Attempting to match any name
        Then: Returns no match with specific error message
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = []

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party="テスト党"
        )

        # Assert
        assert_no_match(result)
        assert result.confidence == 0.0
        assert "利用可能な政治家リストが空です" in result.reason

    @pytest.mark.asyncio
    async def test_match_without_party_info(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test matching when party information is not provided.

        Business Rule: Matching possible without party info if name is unique

        Given: Only one "山田太郎" exists
        When: Searching without party information
        Then: Returns matched=True based on name alone
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 1,
            "politician_name": "山田太郎",
            "political_party_name": "テスト党",
            "confidence": 0.85,
            "reason": "名前が一致",
        }

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party=None
        )

        # Assert
        assert_successful_match(result, expected_id=1, expected_name="山田太郎")

    @pytest.mark.asyncio
    async def test_kana_name_variation_matching(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test matching with kana name variations.

        Business Rule: LLM should handle hiragana/katakana/kanji variations

        Given: Politician "鈴木一郎" exists
        When: Searching with hiragana "すずきいちろう"
        Then: LLM matches based on pronunciation
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response for kana matching
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 3,
            "politician_name": "鈴木一郎",
            "political_party_name": "サンプル党",
            "confidence": 0.92,
            "reason": "読み仮名が一致",
        }

        # Act
        result = await service.find_best_match(
            speaker_name="すずきいちろう", speaker_party="サンプル党"
        )

        # Assert
        assert_successful_match(result, expected_id=3, expected_name="鈴木一郎")

    @pytest.mark.asyncio
    async def test_multiple_candidates_best_match(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test selecting best match when multiple candidates exist.

        Business Rule: When multiple matches exist, party info disambiguates

        Given: Two "山田太郎" exist in different parties
        When: Searching with party="テスト党"
        Then: Returns the one from "テスト党"
        """
        # Arrange
        # Add another politician with similar name
        politicians_with_duplicates = sample_politicians + [
            {
                "id": 4,
                "name": "山田太郎",
                "party_name": "別の党",
                "position": "衆議院議員",
                "prefecture": "北海道",
                "electoral_district": "北海道1区",
            }
        ]
        mock_politician_repository.get_all_for_matching.return_value = (
            politicians_with_duplicates
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party="テスト党"
        )

        # Assert
        # Rule-based matching should work for exact match with party
        assert_successful_match(
            result,
            expected_id=1,
            expected_name="山田太郎",
            min_confidence=HIGH_CONFIDENCE,
        )

    @pytest.mark.asyncio
    async def test_llm_error_handling(
        self,
        service: PoliticianMatchingService,
        mock_llm_service: MagicMock,
        mock_politician_repository: AsyncMock,
        sample_politicians: list[dict[str, Any]],
    ) -> None:
        """Test error handling when LLM raises exception.

        Error Handling: LLM errors should propagate to caller

        Given: LLM service raises ExternalServiceException
        When: Attempting to match (after rule-based fails)
        Then: Exception propagates to caller
        """
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM to raise an exception
        mock_llm_service.invoke_with_retry.side_effect = ExternalServiceException(
            service_name="LLM",
            operation="politician_matching",
            reason="Test error",
        )

        # Act & Assert
        # Should raise ExternalServiceException
        with pytest.raises(ExternalServiceException):
            # Use a name that won't match rule-based to trigger LLM
            await service.find_best_match(
                speaker_name="存在しない政治家", speaker_party="存在しない党"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
