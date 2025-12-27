"""Tests for BAML Politician Matching Service

These tests are marked with @pytest.mark.baml and should run in separate BAML CI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.services.baml_politician_matching_service import (
    BAMLPoliticianMatchingService,
)


pytestmark = pytest.mark.baml


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    return MagicMock()


@pytest.fixture
def mock_politician_repository():
    """Mock politician repository"""
    repo = AsyncMock()

    # テスト用の政治家データ
    repo.get_all_for_matching.return_value = [
        {"id": 1, "name": "山田太郎", "party_name": "自由民主党"},
        {"id": 2, "name": "佐藤花子", "party_name": "立憲民主党"},
        {"id": 3, "name": "鈴木一郎", "party_name": "公明党"},
    ]

    return repo


@pytest.fixture
def mock_baml_client():
    """Mock BAML client"""
    with patch("src.domain.services.baml_politician_matching_service.b") as mock_b:
        mock_match_politician = AsyncMock()
        mock_b.MatchPolitician = mock_match_politician
        yield mock_b


class TestBAMLPoliticianMatchingService:
    """BAML Politician Matching Service tests"""

    @pytest.mark.asyncio
    async def test_rule_based_exact_match_with_party(
        self, mock_llm_service, mock_politician_repository
    ):
        """名前と政党の完全一致テスト（ルールベース、LLMスキップ）"""
        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        result = await service.find_best_match("山田太郎", speaker_party="自由民主党")

        assert result.matched is True
        assert result.politician_id == 1
        assert result.politician_name == "山田太郎"
        assert result.political_party_name == "自由民主党"
        assert result.confidence == 1.0
        assert "完全一致" in result.reason

    @pytest.mark.asyncio
    async def test_rule_based_name_only_match(
        self, mock_llm_service, mock_politician_repository
    ):
        """名前のみ一致テスト（唯一の候補）"""
        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        result = await service.find_best_match("佐藤花子")

        assert result.matched is True
        assert result.politician_id == 2
        assert result.politician_name == "佐藤花子"
        assert result.confidence == 0.9
        assert "唯一の候補" in result.reason

    @pytest.mark.asyncio
    async def test_rule_based_honorific_removal_triggers_baml(
        self, mock_llm_service, mock_politician_repository, mock_baml_client
    ):
        """敬称除去後の一致でBAMLが呼ばれるテスト（信頼度0.85 < 0.9）"""
        # BAMLの戻り値を設定
        mock_baml_client.MatchPolitician.return_value = MagicMock(
            matched=True,
            politician_id=1,
            politician_name="山田太郎",
            political_party_name="自由民主党",
            confidence=0.95,
            reason="BAMLによる確認",
        )

        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        result = await service.find_best_match("山田太郎議員")

        assert result.matched is True
        assert result.politician_id == 1
        # BAMLが呼ばれたことを確認
        mock_baml_client.MatchPolitician.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_baml_matching_when_rule_based_fails(
        self, mock_llm_service, mock_politician_repository, mock_baml_client
    ):
        """ルールベース失敗時にBAMLを使用するテスト"""
        # BAMLの戻り値を設定
        mock_baml_client.MatchPolitician.return_value = MagicMock(
            matched=True,
            politician_id=3,
            politician_name="鈴木一郎",
            political_party_name="公明党",
            confidence=0.8,
            reason="表記ゆれマッチング",
        )

        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # ルールベースでマッチしない表記
        result = await service.find_best_match("スズキイチロウ")

        assert result.matched is True
        assert result.politician_id == 3
        assert result.politician_name == "鈴木一郎"
        assert result.confidence == 0.8
        # BAMLが呼ばれたことを確認
        mock_baml_client.MatchPolitician.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_baml_low_confidence_returns_no_match(
        self, mock_llm_service, mock_politician_repository, mock_baml_client
    ):
        """BAML信頼度が低い場合はマッチしないテスト"""
        # BAMLの戻り値を設定（低信頼度）
        mock_baml_client.MatchPolitician.return_value = MagicMock(
            matched=True,
            politician_id=2,
            politician_name="佐藤花子",
            political_party_name="立憲民主党",
            confidence=0.5,  # 閾値0.7未満
            reason="低信頼度",
        )

        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        result = await service.find_best_match("タナカジロウ")

        assert result.matched is False
        assert result.politician_id is None
        assert result.politician_name is None
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_empty_politician_list(
        self, mock_llm_service, mock_politician_repository
    ):
        """政治家リストが空の場合のテスト"""
        mock_politician_repository.get_all_for_matching.return_value = []

        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        result = await service.find_best_match("山田太郎")

        assert result.matched is False
        assert result.confidence == 0.0
        assert "空です" in result.reason
