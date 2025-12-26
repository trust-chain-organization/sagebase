"""Tests for BAML Speaker Matching Service

These tests are marked with @pytest.mark.baml and should run in separate BAML CI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.services.baml_speaker_matching_service import BAMLSpeakerMatchingService


pytestmark = pytest.mark.baml


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    return MagicMock()


@pytest.fixture
def mock_speaker_repository():
    """Mock speaker repository"""
    repo = AsyncMock()

    # テスト用の発言者データ
    repo.get_all_for_matching.return_value = [
        {"id": 1, "name": "山田太郎"},
        {"id": 2, "name": "佐藤花子"},
        {"id": 3, "name": "鈴木一郎"},
    ]

    # 会議体所属情報（空）
    repo.get_affiliated_speakers.return_value = []

    return repo


@pytest.fixture
def mock_baml_client():
    """Mock BAML client"""
    with patch("src.domain.services.baml_speaker_matching_service.b") as mock_b:
        mock_match_speaker = AsyncMock()
        mock_b.MatchSpeaker = mock_match_speaker
        yield mock_b


class TestBAMLSpeakerMatchingService:
    """BAML Speaker Matching Service tests"""

    @pytest.mark.asyncio
    async def test_rule_based_exact_match(
        self, mock_llm_service, mock_speaker_repository
    ):
        """完全一致のテスト（ルールベースマッチング、LLMをスキップ）"""
        service = BAMLSpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        result = await service.find_best_match("山田太郎")

        assert result.matched is True
        assert result.speaker_id == 1
        assert result.speaker_name == "山田太郎"
        assert result.confidence == 1.0
        assert result.reason == "完全一致"

    @pytest.mark.asyncio
    async def test_rule_based_bracket_match(
        self, mock_llm_service, mock_speaker_repository
    ):
        """括弧内名前一致のテスト（ルールベース）"""
        service = BAMLSpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        result = await service.find_best_match("委員長(山田太郎)")

        assert result.matched is True
        assert result.speaker_id == 1
        assert result.speaker_name == "山田太郎"
        assert result.confidence == 0.95
        assert "括弧内名前一致" in result.reason

    @pytest.mark.asyncio
    async def test_baml_matching_when_rule_based_fails(
        self, mock_llm_service, mock_speaker_repository, mock_baml_client
    ):
        """ルールベースが失敗した場合にBAMLを使用するテスト"""
        # BAMLの戻り値を設定
        mock_baml_client.MatchSpeaker.return_value = MagicMock(
            matched=True,
            speaker_id=2,
            speaker_name="佐藤花子",
            confidence=0.85,
            reason="音韻的類似性",
        )

        service = BAMLSpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # ルールベースでマッチしない名前
        result = await service.find_best_match("サトウハナコ")

        assert result.matched is True
        assert result.speaker_id == 2
        assert result.speaker_name == "佐藤花子"
        assert result.confidence == 0.85
        # BAMLが呼ばれたことを確認
        mock_baml_client.MatchSpeaker.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_baml_low_confidence_returns_no_match(
        self, mock_llm_service, mock_speaker_repository, mock_baml_client
    ):
        """BAML信頼度が低い場合はマッチしないテスト"""
        # BAMLの戻り値を設定（低信頼度）
        mock_baml_client.MatchSpeaker.return_value = MagicMock(
            matched=True,
            speaker_id=2,
            speaker_name="佐藤花子",
            confidence=0.5,  # 閾値0.8未満
            reason="低信頼度",
        )

        service = BAMLSpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        result = await service.find_best_match("タナカジロウ")

        assert result.matched is False
        assert result.speaker_id is None
        assert result.speaker_name is None
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_empty_speaker_list(self, mock_llm_service, mock_speaker_repository):
        """発言者リストが空の場合のテスト"""
        mock_speaker_repository.get_all_for_matching.return_value = []

        service = BAMLSpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        result = await service.find_best_match("山田太郎")

        assert result.matched is False
        assert result.confidence == 0.0
        assert "空です" in result.reason

    @pytest.mark.asyncio
    async def test_partial_match_triggers_baml(
        self, mock_llm_service, mock_speaker_repository, mock_baml_client
    ):
        """部分一致の場合はBAMLが呼ばれるテスト（信頼度0.8 < 0.9）"""
        # BAMLの戻り値を設定
        mock_baml_client.MatchSpeaker.return_value = MagicMock(
            matched=True,
            speaker_id=1,
            speaker_name="山田太郎",
            confidence=0.9,
            reason="BAMLによる確認",
        )

        service = BAMLSpeakerMatchingService(mock_llm_service, mock_speaker_repository)

        # "山田" が "山田太郎" に含まれる（部分一致、信頼度0.8）
        result = await service.find_best_match("山田")

        assert result.matched is True
        assert result.speaker_id == 1
        # BAMLが呼ばれたことを確認
        mock_baml_client.MatchSpeaker.assert_awaited_once()
