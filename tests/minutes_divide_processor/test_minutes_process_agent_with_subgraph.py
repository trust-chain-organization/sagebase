"""MinutesProcessAgentのサブグラフ統合テスト

Issue #797の受入条件を検証：
- MinutesProcessAgentに発言抽出Agentノードが追加されている
- エッジとフロー制御が適切に設定されている
- 既存のdetect_attendee_boundaryとsplit_minutes_by_boundaryがAgent化されている
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.minutes_divide_processor.models import MinutesProcessState


class TestMinutesProcessAgentSubgraphIntegration:
    """SpeechExtractionAgentサブグラフ統合のテスト"""

    @pytest.fixture
    def mock_llm(self):
        """モックLLMの作成"""
        mock = MagicMock()
        mock.model_name = "gemini-2.0-flash-exp"
        return mock

    @pytest.fixture
    def sample_minutes_text(self):
        """テスト用議事録テキスト"""
        return """
令和6年第1回定例会

出席者：
委員長 山田太郎
副委員長 佐藤花子

---

○委員長（山田太郎） ただいまから会議を開催いたします。
◆委員（佐藤花子） 予算案について質問いたします。
"""

    @pytest.mark.asyncio
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch(
        "src.infrastructure.external.langgraph_speech_extraction_agent.SpeechExtractionAgent"
    )
    async def test_subgraph_node_exists(
        self, mock_speech_agent_class, mock_chat_model, sample_minutes_text
    ):
        """サブグラフノードが追加されていることを確認"""
        # Arrange
        mock_speech_agent = MagicMock()
        mock_speech_agent_class.return_value = mock_speech_agent

        # モックのサブグラフを設定
        mock_compiled_subgraph = AsyncMock()
        mock_compiled_subgraph.ainvoke = AsyncMock(
            return_value={
                "verified_boundaries": [
                    {
                        "position": 100,
                        "boundary_type": "separator_line",
                        "confidence": 0.9,
                    }
                ],
                "error_message": None,
            }
        )
        mock_speech_agent.compile.return_value = mock_compiled_subgraph

        # Act
        agent = MinutesProcessAgent()

        # Assert
        # グラフにextract_speech_boundaryノードが存在することを確認
        graph_dict = agent.graph.get_graph()
        # graph_dict.nodesは文字列のリスト
        node_names = list(graph_dict.nodes)

        assert "extract_speech_boundary" in node_names, (
            f"extract_speech_boundaryノードが追加されていません。"
            f"存在するノード: {node_names}"
        )

    @pytest.mark.asyncio
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch(
        "src.infrastructure.external.langgraph_speech_extraction_agent.SpeechExtractionAgent"
    )
    async def test_graph_edges_configured_correctly(
        self, mock_speech_agent_class, mock_chat_model
    ):
        """エッジが正しく設定されていることを確認"""
        # Arrange
        mock_speech_agent = MagicMock()
        mock_speech_agent_class.return_value = mock_speech_agent
        mock_speech_agent.compile.return_value = AsyncMock()

        # Act
        agent = MinutesProcessAgent()
        graph_dict = agent.graph.get_graph()

        # Assert
        # エッジの存在を確認
        edges = [(edge.source, edge.target) for edge in graph_dict.edges]

        # process_minutes → extract_speech_boundary
        assert (
            "process_minutes",
            "extract_speech_boundary",
        ) in edges, "process_minutes → extract_speech_boundaryのエッジがありません"

        # extract_speech_boundary → divide_minutes_to_keyword
        assert (
            "extract_speech_boundary",
            "divide_minutes_to_keyword",
        ) in edges, (
            "extract_speech_boundary → divide_minutes_to_keywordのエッジがありません"
        )

    @pytest.mark.asyncio
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch(
        "src.infrastructure.external.langgraph_speech_extraction_agent.SpeechExtractionAgent"
    )
    @patch("src.infrastructure.external.minutes_divider.factory.MinutesDividerFactory")
    async def test_extract_speech_boundary_node_execution(
        self,
        mock_divider_factory,
        mock_speech_agent_class,
        mock_chat_model,
        sample_minutes_text,
    ):
        """_extract_speech_boundaryノードが正しく実行されることを確認"""
        # Arrange
        # SpeechExtractionAgentのモック
        mock_speech_agent = MagicMock()
        mock_speech_agent_class.return_value = mock_speech_agent

        # サブグラフの実行結果をモック
        mock_compiled_subgraph = AsyncMock()
        mock_compiled_subgraph.ainvoke = AsyncMock(
            return_value={
                "verified_boundaries": [
                    {
                        "position": 150,
                        "boundary_type": "separator_line",
                        "confidence": 0.95,
                    }
                ],
                "error_message": None,
            }
        )
        mock_speech_agent.compile.return_value = mock_compiled_subgraph

        # MinutesDividerのモック
        mock_divider = MagicMock()
        mock_divider.pre_process.return_value = sample_minutes_text
        mock_divider.split_minutes_by_boundary.return_value = (
            "出席者部分",
            "○委員長（山田太郎） ただいまから会議を開催いたします。\n"
            "◆委員（佐藤花子） 予算案について質問いたします。",
        )
        mock_divider_factory.create.return_value = mock_divider

        agent = MinutesProcessAgent()

        # 前処理を実行して processed_minutes_memory_id を取得
        process_result = await agent._process_minutes(
            MinutesProcessState(original_minutes=sample_minutes_text)
        )

        # Act
        state = MinutesProcessState(
            original_minutes=sample_minutes_text,
            processed_minutes_memory_id=process_result["processed_minutes_memory_id"],
        )
        result = await agent._extract_speech_boundary(state)

        # Assert
        assert "boundary_extraction_result_memory_id" in result
        assert result["boundary_extraction_result_memory_id"] != ""

        # メモリから境界抽出結果を取得して確認
        memory_data = agent._get_from_memory(
            "boundary_extraction", result["boundary_extraction_result_memory_id"]
        )
        assert memory_data is not None
        assert "speech_part" in memory_data
        assert "boundary" in memory_data
        assert "boundary_result" in memory_data

        # サブグラフが呼び出されたことを確認
        mock_compiled_subgraph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch(
        "src.infrastructure.external.langgraph_speech_extraction_agent.SpeechExtractionAgent"
    )
    @patch("src.infrastructure.external.minutes_divider.factory.MinutesDividerFactory")
    async def test_boundary_result_conversion(
        self, mock_divider_factory, mock_speech_agent_class, mock_chat_model
    ):
        """BoundaryExtractionResultからMinutesBoundaryへの変換をテスト"""
        # Arrange
        mock_speech_agent = MagicMock()
        mock_speech_agent_class.return_value = mock_speech_agent
        mock_speech_agent.compile.return_value = AsyncMock()

        mock_divider = MagicMock()
        mock_divider_factory.create.return_value = mock_divider

        agent = MinutesProcessAgent()

        # Act
        boundary_result = {
            "verified_boundaries": [
                {"position": 100, "boundary_type": "speech_start", "confidence": 0.85},
                {
                    "position": 200,
                    "boundary_type": "separator_line",
                    "confidence": 0.92,
                },
            ],
            "error_message": None,
        }
        boundary = agent._convert_boundary_result(boundary_result)

        # Assert
        assert boundary.boundary_found is True
        assert boundary.boundary_type == "separator_line"  # 最高信頼度の境界
        assert boundary.confidence == 0.92
        assert "SpeechExtractionAgent検出" in boundary.reason

    @pytest.mark.asyncio
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch(
        "src.infrastructure.external.langgraph_speech_extraction_agent.SpeechExtractionAgent"
    )
    @patch("src.infrastructure.external.minutes_divider.factory.MinutesDividerFactory")
    async def test_no_boundary_found_handling(
        self, mock_divider_factory, mock_speech_agent_class, mock_chat_model
    ):
        """境界が見つからない場合のハンドリングをテスト"""
        # Arrange
        mock_speech_agent = MagicMock()
        mock_speech_agent_class.return_value = mock_speech_agent
        mock_speech_agent.compile.return_value = AsyncMock()

        mock_divider = MagicMock()
        mock_divider_factory.create.return_value = mock_divider

        agent = MinutesProcessAgent()

        # Act
        boundary_result = {"verified_boundaries": [], "error_message": None}
        boundary = agent._convert_boundary_result(boundary_result)

        # Assert
        assert boundary.boundary_found is False
        assert boundary.boundary_type == "none"
        assert boundary.confidence == 0.0
        assert boundary.boundary_text is None
        assert "境界が検出されませんでした" in boundary.reason
