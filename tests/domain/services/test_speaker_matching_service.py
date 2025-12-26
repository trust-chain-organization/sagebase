"""Tests for SpeakerMatchingService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.exceptions import ExternalServiceException
from src.domain.services.speaker_matching_service import SpeakerMatchingService


class TestSpeakerMatchingService:
    """Test cases for SpeakerMatchingService."""

    @pytest.fixture
    def mock_speaker_repository(self):
        """Create a mock speaker repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        mock = MagicMock()
        mock.get_prompt.return_value = MagicMock()
        mock.invoke_with_retry = MagicMock()
        return mock

    @pytest.fixture
    def sample_speakers(self) -> list[dict]:
        """Create sample speakers for testing (as dicts from repository)."""
        return [
            {
                "id": 1,
                "name": "山田太郎",
            },
            {
                "id": 2,
                "name": "佐藤花子",
            },
            {
                "id": 3,
                "name": "鈴木一郎",
            },
        ]

    @pytest.mark.asyncio
    async def test_exact_speaker_match(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test exact speaker name match."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(speaker_name="山田太郎")

        # Assert
        # Rule-based matching should succeed with high confidence
        assert result.matched is True
        assert result.confidence >= 0.9
        assert result.speaker_id == 1
        assert result.speaker_name == "山田太郎"

    @pytest.mark.asyncio
    async def test_match_with_honorific_title(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test matching with honorific title (議員、委員長等)."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        # Mock LLM response
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 2,
            "speaker_name": "佐藤花子",
            "confidence": 0.95,
            "reason": "敬称・役職を除いた名前が一致",
        }

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(speaker_name="佐藤花子委員長")

        # Assert
        assert result.matched is True
        assert result.speaker_id == 2
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_match_with_conference_affiliation(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test matching with conference affiliation information."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        # Mock affiliated speakers for a specific conference
        mock_speaker_repository.get_affiliated_speakers.return_value = [
            {"speaker_id": 1, "conference_id": 10}
        ]

        # Mock LLM response
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 1,
            "speaker_name": "山田太郎",
            "confidence": 0.98,
            "reason": "会議体所属情報により信頼度向上",
        }

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", meeting_date="2024-01-15", conference_id=10
        )

        # Assert
        assert result.matched is True
        assert result.speaker_id == 1
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_empty_speaker_list(self, mock_llm_service, mock_speaker_repository):
        """Test behavior when speaker list is empty."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = []
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(speaker_name="山田太郎")

        # Assert
        assert result.matched is False
        assert result.confidence == 0.0
        assert "利用可能な発言者リストが空です" in result.reason

    @pytest.mark.asyncio
    async def test_low_confidence_treated_as_no_match(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test that low confidence results are treated as no match."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        # Mock LLM response with low confidence
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 1,
            "speaker_name": "山田太郎",
            "confidence": 0.6,  # Low confidence (< 0.8 threshold)
            "reason": "類似性が低い",
        }

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(speaker_name="山田次郎")

        # Assert
        # Low confidence (< 0.8) should be treated as no match
        assert result.matched is False
        assert result.speaker_id is None
        assert result.speaker_name is None

    @pytest.mark.asyncio
    async def test_normalized_name_matching(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test matching using normalized names."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        # Mock LLM response
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 3,
            "speaker_name": "鈴木一郎",
            "confidence": 0.93,
            "reason": "正規化された名前が一致",
        }

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        # Test with spacing variations
        result = await service.find_best_match(speaker_name="鈴木　一郎")

        # Assert
        assert result.matched is True
        assert result.speaker_id == 3
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_multiple_candidates_selection(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test selecting best match when multiple candidates exist."""
        # Arrange
        # Add another speaker with similar name
        speakers_with_duplicates = sample_speakers + [
            {
                "id": 4,
                "name": "山田太郎",
            }
        ]
        mock_speaker_repository.get_all_for_matching.return_value = (
            speakers_with_duplicates
        )
        mock_speaker_repository.get_affiliated_speakers.return_value = [
            {"speaker_id": 1, "conference_id": 10}  # First one is affiliated
        ]

        # Mock LLM response selecting the affiliated one
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 1,  # Should match the affiliated one
            "speaker_name": "山田太郎",
            "confidence": 0.99,
            "reason": "会議体所属情報により確実性が高い",
        }

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", meeting_date="2024-01-15", conference_id=10
        )

        # Assert
        # Rule-based matching should work for exact match
        assert result.matched is True
        assert result.speaker_id == 1
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_hybrid_matching_rule_based_first(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test hybrid matching: rule-based takes precedence with high confidence."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act
        result = await service.find_best_match(speaker_name="山田太郎")

        # Assert
        # Should use rule-based matching without calling LLM
        assert result.matched is True
        assert result.speaker_id == 1
        assert result.confidence >= 0.9
        # LLM should not be called if rule-based matching succeeds with high confidence
        mock_llm_service.invoke_with_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_error_handling(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test error handling when LLM returns unexpected format."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        # Mock LLM to raise an exception
        mock_llm_service.invoke_with_retry.side_effect = ExternalServiceException(
            service_name="LLM",
            operation="speaker_matching",
            reason="Test error",
        )

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act & Assert
        # Should handle the error gracefully
        with pytest.raises(ExternalServiceException):
            # Use a name that won't match rule-based to trigger LLM
            await service.find_best_match(speaker_name="存在しない発言者")

    @pytest.mark.asyncio
    async def test_match_with_various_honorifics(
        self, mock_llm_service, mock_speaker_repository, sample_speakers
    ):
        """Test matching with various Japanese honorifics."""
        # Arrange
        mock_speaker_repository.get_all_for_matching.return_value = sample_speakers
        mock_speaker_repository.get_affiliated_speakers.return_value = []

        test_cases = [
            "佐藤花子議員",
            "佐藤花子委員",
            "佐藤花子委員長",
            "佐藤花子君",
        ]

        # Mock LLM responses
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "speaker_id": 2,
            "speaker_name": "佐藤花子",
            "confidence": 0.95,
            "reason": "敬称を除いた名前が一致",
        }

        service = SpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # Act & Assert
        for speaker_name in test_cases:
            result = await service.find_best_match(speaker_name=speaker_name)
            assert result.matched is True
            assert result.speaker_id == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
