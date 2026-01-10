"""Tests for BAML Politician Matching Service

These tests are marked with @pytest.mark.baml and should run in separate BAML CI.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.external.politician_matching import (
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
    with patch(
        "src.infrastructure.external.politician_matching.baml_politician_matching_service.b"
    ) as mock_b:
        mock_match_politician = AsyncMock()
        mock_b.MatchPolitician = mock_match_politician
        yield mock_b


class TestBAMLPoliticianMatchingService:
    """BAML Politician Matching Service tests"""

    @pytest.mark.asyncio
    async def test_rule_based_exact_match_with_party(
        self,
        mock_llm_service,
        mock_politician_repository,
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
        self,
        mock_llm_service,
        mock_politician_repository,
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
        self,
        mock_llm_service,
        mock_politician_repository,
        mock_baml_client,
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
        self,
        mock_llm_service,
        mock_politician_repository,
        mock_baml_client,
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
        self,
        mock_llm_service,
        mock_politician_repository,
        mock_baml_client,
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
        self,
        mock_llm_service,
        mock_politician_repository,
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "title_name",
        [
            "委員長",
            "副委員長",
            "議長",
            "副議長",
            "事務局長",
            "事務局次長",
            "参考人",
            "証人",
            "説明員",
            "政府委員",
            "幹事",
            "書記",
        ],
    )
    async def test_title_only_speaker_returns_no_match(
        self,
        mock_llm_service,
        mock_politician_repository,
        title_name,
    ):
        """役職のみの発言者はBAML呼び出しをスキップしてマッチなしを返すテスト"""
        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        result = await service.find_best_match(title_name)

        assert result.matched is False
        assert result.confidence == 0.0
        assert "役職名のみ" in result.reason
        # 政治家リストの取得が呼ばれていないことを確認（早期リターンのため）
        mock_politician_repository.get_all_for_matching.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_baml_validation_error_returns_no_match(
        self,
        mock_llm_service,
        mock_politician_repository,
        mock_baml_client,
    ):
        """BamlValidationError発生時にマッチなし結果を返すテスト"""
        from baml_py.errors import BamlValidationError

        # BAMLがValidationErrorを発生させる
        mock_baml_client.MatchPolitician.side_effect = BamlValidationError(
            prompt="test prompt",
            message="Failed to parse LLM response",
            raw_output="natural language output",
            detailed_message="The LLM did not return valid JSON",
        )

        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # ルールベースでマッチしない名前を使用してBAML呼び出しを発生させる
        result = await service.find_best_match("未知の人物")

        assert result.matched is False
        assert result.confidence == 0.0
        assert "LLMが構造化出力を返せませんでした" in result.reason

    @pytest.mark.asyncio
    async def test_is_title_only_speaker_method(
        self,
        mock_llm_service,
        mock_politician_repository,
    ):
        """_is_title_only_speakerメソッドのテスト"""
        service = BAMLPoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # 役職のみの発言者
        assert service._is_title_only_speaker("委員長") is True
        assert service._is_title_only_speaker("  議長  ") is True  # 空白はトリム

        # 通常の発言者名
        assert service._is_title_only_speaker("山田太郎") is False
        assert service._is_title_only_speaker("山田委員長") is False  # 名前+役職
        assert service._is_title_only_speaker("委員長山田") is False  # 役職+名前

        # 空文字・空白のみ（エッジケース）
        assert service._is_title_only_speaker("") is False  # 空文字
        assert service._is_title_only_speaker("   ") is False  # 空白のみ
