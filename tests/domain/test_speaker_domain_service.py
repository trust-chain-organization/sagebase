"""Tests for speaker domain service."""

import pytest

from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.services.speaker_domain_service import SpeakerDomainService


class TestSpeakerDomainService:
    """Test cases for SpeakerDomainService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return SpeakerDomainService()

    def test_normalize_speaker_name(self, service):
        """Test speaker name normalization."""
        # Test removing honorifics
        assert service.normalize_speaker_name("山田太郎議員") == "山田太郎"
        assert service.normalize_speaker_name("佐藤花子君") == "佐藤花子"
        assert service.normalize_speaker_name("田中一郎委員長") == "田中一郎"

        # Test trimming spaces
        assert service.normalize_speaker_name("  山田太郎  ") == "山田太郎"
        assert service.normalize_speaker_name("山田　太郎") == "山田　太郎"

    def test_extract_party_from_name(self, service):
        """Test extracting party from speaker name."""
        # Test with party in parentheses
        name, party = service.extract_party_from_name("山田太郎（自民党）")
        assert name == "山田太郎"
        assert party == "自民党"

        # Test with role and party
        name, party = service.extract_party_from_name("佐藤花子（委員長・公明党）")
        assert name == "佐藤花子"
        assert party == "委員長・公明党"

        # Test without party
        name, party = service.extract_party_from_name("田中一郎")
        assert name == "田中一郎"
        assert party is None

    def test_is_likely_politician(self, service):
        """Test politician likelihood detection."""
        # Test with is_politician flag
        speaker = Speaker(name="test", is_politician=True)
        assert service.is_likely_politician(speaker) is True

        # Test with party name
        speaker = Speaker(name="test", political_party_name="自民党")
        assert service.is_likely_politician(speaker) is True

        # Test with type
        speaker = Speaker(name="test", type="政治家")
        assert service.is_likely_politician(speaker) is True

        # Test with position
        speaker = Speaker(name="test", position="衆議院議員")
        assert service.is_likely_politician(speaker) is True

        # Test non-politician
        speaker = Speaker(name="test", type="参考人")
        assert service.is_likely_politician(speaker) is False

    def test_calculate_name_similarity(self, service):
        """Test name similarity calculation."""
        # Test exact match
        assert service.calculate_name_similarity("山田太郎", "山田太郎") == 1.0

        # Test with honorifics
        assert service.calculate_name_similarity("山田太郎議員", "山田太郎") == 1.0

        # Test partial match
        similarity = service.calculate_name_similarity("山田太郎", "山田次郎")
        assert 0 < similarity < 1

        # Test no match
        assert service.calculate_name_similarity("山田太郎", "佐藤花子") == 0.0

    def test_merge_speaker_info(self, service):
        """Test merging speaker information."""
        existing = Speaker(name="山田太郎", type="政治家", id=1)

        new_info = Speaker(
            name="山田太郎",
            political_party_name="自民党",
            position="衆議院議員",
            is_politician=True,
        )

        merged = service.merge_speaker_info(existing, new_info)

        assert merged.id == 1  # Keep existing ID
        assert merged.name == "山田太郎"
        assert merged.type == "政治家"  # Keep existing when new is None
        assert merged.political_party_name == "自民党"  # Use new value
        assert merged.position == "衆議院議員"  # Use new value
        assert merged.is_politician is True

    def test_validate_speaker_politician_link(self, service):
        """Test speaker-politician link validation."""
        speaker = Speaker(name="山田太郎", political_party_name="自民党")
        politician = Politician(
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )

        # Test valid link
        assert service.validate_speaker_politician_link(speaker, politician) is True

        # Test invalid link (different names)
        politician.name = "佐藤花子"
        assert service.validate_speaker_politician_link(speaker, politician) is False
