"""Tests for party member extractor factory"""

from unittest.mock import Mock

from src.party_member_extractor.factory import PartyMemberExtractorFactory


class TestPartyMemberExtractorFactory:
    """Test cases for PartyMemberExtractorFactory"""

    def test_create_baml_extractor(self):
        """BAML実装の作成テスト"""
        extractor = PartyMemberExtractorFactory.create()

        # Assert - should be BAML implementation
        assert extractor.__class__.__name__ == "BAMLPartyMemberExtractor"

    def test_create_with_parameters(self):
        """パラメータ付き作成テスト"""
        mock_llm_service = Mock()
        party_id = 456
        mock_proc_logger = Mock()

        extractor = PartyMemberExtractorFactory.create(
            llm_service=mock_llm_service,
            party_id=party_id,
            proc_logger=mock_proc_logger,
        )

        # Assert
        assert extractor.__class__.__name__ == "BAMLPartyMemberExtractor"
        # Verify parameters were passed correctly
        assert extractor.party_id == party_id

    def test_factory_returns_expected_interface(self):
        """Factoryが期待されるインターフェースを返すテスト"""
        extractor = PartyMemberExtractorFactory.create()

        # Assert - should have the expected public methods
        assert hasattr(extractor, "extract_from_pages")
