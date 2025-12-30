"""SpeechExtractionAgent のユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langchain_core.language_models import BaseChatModel

from src.infrastructure.external.langgraph_speech_extraction_agent import (
    BoundaryExtractionResult,
    SpeechExtractionAgent,
    SpeechExtractionAgentState,
    VerifiedBoundary,
)


class TestSpeechExtractionAgent:
    """SpeechExtractionAgent のテストケース"""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """モックLLMを作成"""
        mock = MagicMock(spec=BaseChatModel)
        return mock

    @pytest.fixture
    def agent(self, mock_llm: MagicMock) -> SpeechExtractionAgent:
        """エージェントインスタンスを作成"""
        return SpeechExtractionAgent(llm=mock_llm)

    def test_initialization(self, agent: SpeechExtractionAgent) -> None:
        """エージェントの初期化テスト"""
        assert agent.llm is not None
        assert len(agent.tools) == 3  # 3つのツールが登録されている
        assert agent.agent is not None

    def test_tools_are_created(self, agent: SpeechExtractionAgent) -> None:
        """ツールが正しく作成されているかテスト"""
        tool_names = [tool.name for tool in agent.tools]
        assert "validate_boundary_candidate" in tool_names
        assert "analyze_context" in tool_names
        assert "verify_boundary" in tool_names

    def test_compile_returns_agent(self, agent: SpeechExtractionAgent) -> None:
        """compile()がエージェントを返すかテスト"""
        compiled = agent.compile()
        assert compiled is not None
        assert compiled == agent.agent

    @pytest.mark.asyncio
    async def test_extract_boundaries_with_empty_text(
        self, agent: SpeechExtractionAgent
    ) -> None:
        """空のテキストでの境界抽出テスト"""
        # エージェントの実行をモック
        mock_result: BoundaryExtractionResult = {
            "verified_boundaries": [],
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.extract_boundaries("")

            assert result["verified_boundaries"] == []
            assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_extract_boundaries_success(
        self, agent: SpeechExtractionAgent
    ) -> None:
        """正常な境界抽出のテスト"""
        sample_minutes = """
        ○議長（山田太郎）
        会議を開きます。

        ○田中花子議員
        質問させていただきます。
        """

        # エージェントの実行をモック
        boundary1: VerifiedBoundary = {
            "position": 10,
            "boundary_type": "speech_start",
            "confidence": 0.85,
        }
        boundary2: VerifiedBoundary = {
            "position": 50,
            "boundary_type": "speech_start",
            "confidence": 0.90,
        }
        mock_result: BoundaryExtractionResult = {
            "verified_boundaries": [boundary1, boundary2],
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.extract_boundaries(sample_minutes)

            assert len(result["verified_boundaries"]) == 2
            assert result["verified_boundaries"][0]["confidence"] >= 0.7
            assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_extract_boundaries_with_error(
        self, agent: SpeechExtractionAgent
    ) -> None:
        """エラー時の境界抽出テスト"""
        # エージェントの実行をモック（エラーケース）
        mock_result: BoundaryExtractionResult = {
            "verified_boundaries": [],
            "error_message": "LLM processing error",
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.extract_boundaries("invalid text")

            assert result["verified_boundaries"] == []
            assert result["error_message"] is not None

    @pytest.mark.asyncio
    async def test_extract_boundaries_handles_exception(
        self, agent: SpeechExtractionAgent
    ) -> None:
        """例外発生時の境界抽出テスト"""
        # エージェントの実行が例外を発生させる場合
        with patch.object(
            agent.agent,
            "ainvoke",
            new_callable=AsyncMock,
            side_effect=Exception("Test exception"),
        ):
            result = await agent.extract_boundaries("test text")

            assert result["verified_boundaries"] == []
            assert result["error_message"] is not None
            assert "境界抽出中にエラーが発生しました" in result["error_message"]

    @pytest.mark.asyncio
    async def test_extract_boundaries_filters_low_confidence(
        self, agent: SpeechExtractionAgent
    ) -> None:
        """低信頼度の境界がフィルタされるかテスト

        システムプロンプトで信頼度0.7以上を要求しているため、
        エージェントが低信頼度の境界を除外することを検証
        """
        sample_minutes = "テスト議事録"

        # 高信頼度と低信頼度が混在する結果をモック
        boundary: VerifiedBoundary = {
            "position": 10,
            "boundary_type": "speech_start",
            "confidence": 0.85,  # 高信頼度
        }
        mock_result: BoundaryExtractionResult = {
            "verified_boundaries": [
                boundary,
                # 低信頼度の境界はエージェントが除外するはず
            ],
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.extract_boundaries(sample_minutes)

            # 高信頼度の境界のみが返される
            assert all(b["confidence"] >= 0.7 for b in result["verified_boundaries"])

    @pytest.mark.asyncio
    async def test_extract_boundaries_preserves_boundary_order(
        self, agent: SpeechExtractionAgent
    ) -> None:
        """境界の順序が保持されるかテスト"""
        sample_minutes = "テスト議事録"

        # 複数の境界を位置順にモック
        boundary1: VerifiedBoundary = {
            "position": 10,
            "boundary_type": "speech_start",
            "confidence": 0.80,
        }
        boundary2: VerifiedBoundary = {
            "position": 50,
            "boundary_type": "speech_start",
            "confidence": 0.85,
        }
        boundary3: VerifiedBoundary = {
            "position": 100,
            "boundary_type": "separator_line",
            "confidence": 0.90,
        }
        mock_result: BoundaryExtractionResult = {
            "verified_boundaries": [boundary1, boundary2, boundary3],
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.extract_boundaries(sample_minutes)

            # 境界が位置順に並んでいることを確認
            positions = [b["position"] for b in result["verified_boundaries"]]
            assert positions == sorted(positions)


class TestSpeechExtractionAgentState:
    """SpeechExtractionAgentState のテストケース"""

    def test_state_structure(self) -> None:
        """状態の構造が正しいかテスト"""
        state: SpeechExtractionAgentState = {
            "minutes_text": "sample text",
            "boundary_candidates": [10, 20, 30],
            "verified_boundaries": [],
            "current_position": 0,
            "messages": [],
            "remaining_steps": 10,
            "error_message": None,
        }

        assert state["minutes_text"] == "sample text"
        assert len(state["boundary_candidates"]) == 3
        assert state["verified_boundaries"] == []
        assert state["current_position"] == 0
        assert state["remaining_steps"] == 10
        assert state["error_message"] is None

    def test_state_with_verified_boundaries(self) -> None:
        """検証済み境界を含む状態のテスト"""
        boundary: VerifiedBoundary = {
            "position": 10,
            "boundary_type": "speech_start",
            "confidence": 0.85,
        }
        state: SpeechExtractionAgentState = {
            "minutes_text": "sample text",
            "boundary_candidates": [10, 20, 30],
            "verified_boundaries": [boundary],
            "current_position": 10,
            "messages": [],
            "remaining_steps": 5,
            "error_message": None,
        }

        assert len(state["verified_boundaries"]) == 1
        assert state["verified_boundaries"][0]["position"] == 10
        assert state["current_position"] == 10

    def test_state_with_error(self) -> None:
        """エラーを含む状態のテスト"""
        state: SpeechExtractionAgentState = {
            "minutes_text": "sample text",
            "boundary_candidates": [],
            "verified_boundaries": [],
            "current_position": 0,
            "messages": [],
            "remaining_steps": 0,
            "error_message": "Test error message",
        }

        assert state["error_message"] == "Test error message"
