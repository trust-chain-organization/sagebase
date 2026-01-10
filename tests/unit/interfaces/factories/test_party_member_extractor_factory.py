"""政党メンバー抽出器ファクトリーのテスト

PartyMemberExtractorFactoryの動作を検証します。
"""

from unittest.mock import MagicMock

from src.domain.interfaces.party_member_extractor_service import (
    IPartyMemberExtractorService,
)
from src.infrastructure.external.party_member_extractor.baml_extractor import (
    BAMLPartyMemberExtractor,
)
from src.interfaces.factories.party_member_extractor_factory import (
    PartyMemberExtractorFactory,
)


class TestPartyMemberExtractorFactory:
    """PartyMemberExtractorFactoryのテスト"""

    def test_create_baml_extractor(self) -> None:
        """BAML実装を返すこと"""
        # Act
        extractor = PartyMemberExtractorFactory.create()

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)
        assert isinstance(extractor, BAMLPartyMemberExtractor)

    def test_create_returns_interface_type(self) -> None:
        """ファクトリーがインターフェース型を返すこと"""
        # Act
        extractor = PartyMemberExtractorFactory.create()

        # Assert
        assert isinstance(extractor, IPartyMemberExtractorService)

    def test_create_with_llm_service(self) -> None:
        """llm_serviceパラメータを渡してもBAML実装を作成できること（後方互換性）"""
        # Arrange
        mock_llm_service = MagicMock()

        # Act
        extractor = PartyMemberExtractorFactory.create(
            llm_service=mock_llm_service,
        )

        # Assert
        assert isinstance(extractor, BAMLPartyMemberExtractor)
