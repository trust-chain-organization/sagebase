"""Integration tests for BAMLSpeakerMatchingService with Agent

Issue #800の統合テスト。
BAMLSpeakerMatchingServiceに統合された名寄せAgentのハイブリッドマッチング処理をテスト。

マッチングフロー:
1. ルールベースマッチング（高速パス、信頼度0.9以上）
2. Agentマッチング（use_agent=Trueの場合、反復的評価）
3. BAMLマッチング（フォールバック、Agentエラー時）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.services.baml_speaker_matching_service import (
    BAMLSpeakerMatchingService,
)


# NOTE: Agentマッチングのテストは、実際のLLM呼び出しを必要とするため、
# モックを使用してテストします。


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


class TestAgentIntegration:
    """Agent統合のテスト"""

    @pytest.mark.asyncio
    async def test_rule_based_match_skips_agent(
        self, mock_llm_service, mock_speaker_repository
    ):
        """ルールベースマッチング（高速パス）がAgentをスキップするテスト

        信頼度0.9以上の場合、Agentは呼び出されない。
        """
        # use_agent=Falseでエージェントを無効化（簡単なテスト）
        service = BAMLSpeakerMatchingService(
            mock_llm_service, mock_speaker_repository, use_agent=False
        )

        # 完全一致（信頼度1.0）
        result = await service.find_best_match("山田太郎")

        assert result.matched is True
        assert result.speaker_id == 1
        assert result.speaker_name == "山田太郎"
        assert result.confidence == 1.0
        assert result.reason == "完全一致"

        # Agentが初期化されていないことを確認
        assert service.matching_agent is None

    @pytest.mark.asyncio
    async def test_agent_matching_when_rule_based_fails(
        self, mock_llm_service, mock_speaker_repository
    ):
        """ルールベースが失敗した場合にAgentマッチングが呼ばれるテスト

        信頼度0.9未満の場合、Agentマッチングが試行される。
        """
        # SpeakerMatchingAgentをモック化（実際のインポート元）
        with patch(
            "src.infrastructure.external.langgraph_speaker_matching_agent.SpeakerMatchingAgent"  # noqa: E501
        ) as mock_agent_class:
            # モックエージェントの作成
            mock_agent_instance = AsyncMock()
            mock_agent_class.return_value = mock_agent_instance

            # Agentの戻り値を設定
            mock_agent_instance.match_speaker.return_value = {
                "matched": True,
                "politician_id": 2,
                "politician_name": "佐藤花子",
                "confidence": 0.85,
                "reason": "Agentによるマッチング",
            }

            # ChatGoogleGenerativeAIをモック化
            with patch(
                "src.domain.services.baml_speaker_matching_service.ChatGoogleGenerativeAI"  # noqa: E501
            ) as mock_llm_class:
                mock_llm_class.return_value = MagicMock()

                # use_agent=Trueでサービスを初期化
                service = BAMLSpeakerMatchingService(
                    mock_llm_service, mock_speaker_repository, use_agent=True
                )

                # ルールベースでマッチしない名前
                result = await service.find_best_match("サトウハナコ")

                # Agentが呼ばれたことを確認
                mock_agent_instance.match_speaker.assert_called_once_with(
                    speaker_name="サトウハナコ",
                    meeting_date=None,
                    conference_id=None,
                )

                # Agent結果が返されることを確認
                assert result.matched is True
                assert result.speaker_id == 2
                assert result.speaker_name == "佐藤花子"
                assert result.confidence == 0.85
                assert result.reason == "Agentによるマッチング"

    @pytest.mark.asyncio
    async def test_baml_fallback_when_agent_fails(
        self, mock_llm_service, mock_speaker_repository
    ):
        """Agentが失敗した場合にBAMLマッチングにフォールバックするテスト"""
        # SpeakerMatchingAgentをモック化（実際のインポート元）
        with patch(
            "src.infrastructure.external.langgraph_speaker_matching_agent.SpeakerMatchingAgent"  # noqa: E501
        ) as mock_agent_class:
            # モックエージェントの作成
            mock_agent_instance = AsyncMock()
            mock_agent_class.return_value = mock_agent_instance

            # Agentがエラーを投げる
            mock_agent_instance.match_speaker.side_effect = RuntimeError("Agent error")

            # ChatGoogleGenerativeAIをモック化
            with patch(
                "src.domain.services.baml_speaker_matching_service.ChatGoogleGenerativeAI"  # noqa: E501
            ) as mock_llm_class:
                mock_llm_class.return_value = MagicMock()

                # BAMLクライアントをモック化
                with patch(
                    "src.domain.services.baml_speaker_matching_service.b"
                ) as mock_b:
                    # AsyncMockを使用して非同期呼び出しをサポート
                    mock_baml_result = MagicMock(
                        matched=True,
                        speaker_id=2,
                        speaker_name="佐藤花子",
                        confidence=0.82,
                        reason="BAMLフォールバック",
                    )
                    mock_b.MatchSpeaker = AsyncMock(return_value=mock_baml_result)

                    # use_agent=Trueでサービスを初期化
                    service = BAMLSpeakerMatchingService(
                        mock_llm_service, mock_speaker_repository, use_agent=True
                    )

                    # ルールベースでマッチしない名前
                    result = await service.find_best_match("サトウハナコ")

                    # Agentが呼ばれたことを確認
                    mock_agent_instance.match_speaker.assert_called_once()

                    # BAMLがフォールバックとして呼ばれたことを確認
                    mock_b.MatchSpeaker.assert_called_once()

                    # BAML結果が返されることを確認
                    assert result.matched is True
                    assert result.speaker_id == 2
                    assert result.speaker_name == "佐藤花子"
                    assert result.confidence == 0.82
                    assert result.reason == "BAMLフォールバック"

    @pytest.mark.asyncio
    async def test_agent_low_confidence_falls_back_to_baml(
        self, mock_llm_service, mock_speaker_repository
    ):
        """Agentの信頼度が低い場合にBAMLにフォールバックするテスト

        信頼度0.8未満の場合、BAMLマッチングにフォールバック。
        """
        # SpeakerMatchingAgentをモック化（実際のインポート元）
        with patch(
            "src.infrastructure.external.langgraph_speaker_matching_agent.SpeakerMatchingAgent"  # noqa: E501
        ) as mock_agent_class:
            # モックエージェントの作成
            mock_agent_instance = AsyncMock()
            mock_agent_class.return_value = mock_agent_instance

            # Agentの戻り値を設定（低い信頼度）
            mock_agent_instance.match_speaker.return_value = {
                "matched": False,  # 信頼度が低いためマッチなし
                "politician_id": None,
                "politician_name": None,
                "confidence": 0.75,
                "reason": "確信度が閾値に達しませんでした",
            }

            # ChatGoogleGenerativeAIをモック化
            with patch(
                "src.domain.services.baml_speaker_matching_service.ChatGoogleGenerativeAI"  # noqa: E501
            ) as mock_llm_class:
                mock_llm_class.return_value = MagicMock()

                # BAMLクライアントをモック化
                with patch(
                    "src.domain.services.baml_speaker_matching_service.b"
                ) as mock_b:
                    # AsyncMockを使用して非同期呼び出しをサポート
                    mock_baml_result = MagicMock(
                        matched=True,
                        speaker_id=2,
                        speaker_name="佐藤花子",
                        confidence=0.82,
                        reason="BAMLフォールバック",
                    )
                    mock_b.MatchSpeaker = AsyncMock(return_value=mock_baml_result)

                    # use_agent=Trueでサービスを初期化
                    service = BAMLSpeakerMatchingService(
                        mock_llm_service, mock_speaker_repository, use_agent=True
                    )

                    # ルールベースでマッチしない名前
                    result = await service.find_best_match("サトウハナコ")

                    # Agentが呼ばれたことを確認
                    mock_agent_instance.match_speaker.assert_called_once()

                    # BAMLがフォールバックとして呼ばれたことを確認
                    mock_b.MatchSpeaker.assert_called_once()

                    # BAML結果が返されることを確認
                    assert result.matched is True
                    assert result.speaker_id == 2
                    assert result.speaker_name == "佐藤花子"
                    assert result.confidence == 0.82
                    assert result.reason == "BAMLフォールバック"

    @pytest.mark.asyncio
    async def test_agent_initialization_failure_falls_back_to_baml_only_mode(
        self, mock_llm_service, mock_speaker_repository
    ):
        """Agent初期化失敗時にBAMLのみモードにフォールバックするテスト"""
        # ChatGoogleGenerativeAIの初期化がエラーを投げる
        with patch(
            "src.domain.services.baml_speaker_matching_service.ChatGoogleGenerativeAI",
            side_effect=ValueError("GOOGLE_API_KEY not set"),
        ):
            # use_agent=Trueでサービスを初期化
            service = BAMLSpeakerMatchingService(
                mock_llm_service, mock_speaker_repository, use_agent=True
            )

            # Agentが無効化されていることを確認
            assert service.use_agent is False
            assert service.matching_agent is None

            # BAMLクライアントをモック化
            with patch("src.domain.services.baml_speaker_matching_service.b") as mock_b:
                # AsyncMockを使用して非同期呼び出しをサポート
                mock_baml_result = MagicMock(
                    matched=True,
                    speaker_id=2,
                    speaker_name="佐藤花子",
                    confidence=0.82,
                    reason="BAML matching",
                )
                mock_b.MatchSpeaker = AsyncMock(return_value=mock_baml_result)

                # ルールベースでマッチしない名前
                result = await service.find_best_match("サトウハナコ")

                # BAMLが呼ばれたことを確認
                mock_b.MatchSpeaker.assert_called_once()

                # BAML結果が返されることを確認
                assert result.matched is True
                assert result.speaker_id == 2
                assert result.speaker_name == "佐藤花子"
                assert result.confidence == 0.82
                assert result.reason == "BAML matching"
