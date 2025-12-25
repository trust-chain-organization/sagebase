"""政党メンバー抽出器ファクトリーのテスト

PartyMemberExtractorFactoryの動作を検証します。
"""

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
