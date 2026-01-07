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

    def test_create_with_dependencies(self) -> None:
        """依存関係を注入してBAML実装を作成できること"""
        # Arrange
        mock_politician_repo = MagicMock()
        mock_update_usecase = MagicMock()

        # Act
        extractor = PartyMemberExtractorFactory.create(
            politician_repository=mock_politician_repo,
            update_politician_usecase=mock_update_usecase,
        )

        # Assert
        assert isinstance(extractor, BAMLPartyMemberExtractor)
        assert extractor._politician_repository is mock_politician_repo
        assert extractor._update_politician_usecase is mock_update_usecase

    def test_create_without_dependencies_maintains_backward_compatibility(self) -> None:
        """依存関係なしで作成しても後方互換性があること"""
        # Act
        extractor = PartyMemberExtractorFactory.create()

        # Assert
        assert isinstance(extractor, BAMLPartyMemberExtractor)
        assert extractor._politician_repository is None
        assert extractor._update_politician_usecase is None
