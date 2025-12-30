"""SpeakerMatchingAgent のユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langchain_core.language_models import BaseChatModel

from src.infrastructure.external.langgraph_speaker_matching_agent import (
    MAX_REACT_STEPS,
    ConfidenceJudgement,
    MatchCandidate,
    SpeakerMatchingAgent,
    SpeakerMatchingAgentState,
)


class TestSpeakerMatchingAgent:
    """SpeakerMatchingAgent のテストケース"""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """モックLLMを作成"""
        mock = MagicMock(spec=BaseChatModel)
        return mock

    @pytest.fixture
    def mock_repos(self) -> tuple[MagicMock, MagicMock, MagicMock]:
        """モックリポジトリを作成"""
        mock_speaker_repo = MagicMock()
        mock_politician_repo = MagicMock()
        mock_affiliation_repo = MagicMock()
        return mock_speaker_repo, mock_politician_repo, mock_affiliation_repo

    @pytest.fixture
    def agent(
        self, mock_llm: MagicMock, mock_repos: tuple[MagicMock, MagicMock, MagicMock]
    ) -> SpeakerMatchingAgent:
        """エージェントインスタンスを作成"""
        speaker_repo, politician_repo, affiliation_repo = mock_repos
        return SpeakerMatchingAgent(
            llm=mock_llm,
            speaker_repo=speaker_repo,
            politician_repo=politician_repo,
            affiliation_repo=affiliation_repo,
        )

    def test_initialization(self, agent: SpeakerMatchingAgent) -> None:
        """エージェントの初期化テスト"""
        assert agent.llm is not None
        assert len(agent.tools) == 3  # 3つのツールが登録されている
        assert agent.agent is not None

    def test_tools_are_created(self, agent: SpeakerMatchingAgent) -> None:
        """ツールが正しく作成されているかテスト"""
        tool_names = [tool.name for tool in agent.tools]
        assert "evaluate_matching_candidates" in tool_names
        assert "search_additional_info" in tool_names
        assert "judge_confidence" in tool_names

    def test_compile_returns_agent(self, agent: SpeakerMatchingAgent) -> None:
        """compile()がエージェントを返すかテスト"""
        compiled = agent.compile()
        assert compiled is not None
        assert compiled == agent.agent

    @pytest.mark.asyncio
    async def test_match_speaker_with_empty_name(
        self, agent: SpeakerMatchingAgent
    ) -> None:
        """空の発言者名でのマッチングテスト"""
        # エージェントの実行をモック
        mock_result = {
            "speaker_name": "",
            "best_match": None,
            "best_confidence": None,
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.match_speaker("")
            assert result["matched"] is False
            assert result["politician_id"] is None

    @pytest.mark.asyncio
    async def test_match_speaker_success(self, agent: SpeakerMatchingAgent) -> None:
        """正常なマッチングのテスト"""
        speaker_name = "田中太郎"

        # エージェントの実行をモック
        best_match: MatchCandidate = {
            "politician_id": 123,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.95,
            "match_type": "exact",
            "is_affiliated": True,
        }
        best_confidence: ConfidenceJudgement = {
            "confidence": 0.95,
            "confidence_level": "high",
            "should_match": True,
            "reason": "名前が完全一致。会議体所属。",
            "contributing_factors": [],
            "recommendation": "高確信度でマッチング推奨",
        }
        mock_result = {
            "speaker_name": speaker_name,
            "best_match": best_match,
            "best_confidence": best_confidence,
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.match_speaker(speaker_name)

            assert result["matched"] is True
            assert result["politician_id"] == 123
            assert result["politician_name"] == "田中太郎"
            assert result["confidence"] == 0.95
            assert "完全一致" in result["reason"]

    @pytest.mark.asyncio
    async def test_match_speaker_no_match(self, agent: SpeakerMatchingAgent) -> None:
        """マッチしないケースのテスト"""
        speaker_name = "存在しない議員"

        # エージェントの実行をモック（確信度が低い）
        best_match: MatchCandidate = {
            "politician_id": 999,
            "politician_name": "類似名前",
            "party": None,
            "score": 0.5,
            "match_type": "fuzzy",
            "is_affiliated": False,
        }
        best_confidence: ConfidenceJudgement = {
            "confidence": 0.5,
            "confidence_level": "low",
            "should_match": False,  # 確信度が低いのでマッチしない
            "reason": "名前の類似度が低い",
            "contributing_factors": [],
            "recommendation": "マッチング非推奨",
        }
        mock_result = {
            "speaker_name": speaker_name,
            "best_match": best_match,
            "best_confidence": best_confidence,
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.match_speaker(speaker_name)

            assert result["matched"] is False
            assert result["politician_id"] is None
            assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_match_speaker_handles_exception(
        self, agent: SpeakerMatchingAgent
    ) -> None:
        """例外処理のテスト"""
        speaker_name = "田中太郎"

        # エージェントの実行時に例外を発生させる
        with patch.object(
            agent.agent,
            "ainvoke",
            new_callable=AsyncMock,
            side_effect=Exception("Test error"),
        ):
            result = await agent.match_speaker(speaker_name)

            assert result["matched"] is False
            assert result["error_message"] is not None
            assert "エラーが発生" in result["error_message"]

    @pytest.mark.asyncio
    async def test_match_speaker_with_context(
        self, agent: SpeakerMatchingAgent
    ) -> None:
        """会議体コンテキスト付きマッチングのテスト"""
        speaker_name = "田中太郎"
        meeting_date = "2024-01-15"
        conference_id = 1

        # エージェントの実行をモック
        best_match: MatchCandidate = {
            "politician_id": 123,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.95,
            "match_type": "exact",
            "is_affiliated": True,
        }
        best_confidence: ConfidenceJudgement = {
            "confidence": 0.98,
            "confidence_level": "high",
            "should_match": True,
            "reason": "名前が完全一致。会議体所属。",
            "contributing_factors": [],
            "recommendation": "高確信度でマッチング推奨",
        }
        mock_result = {
            "speaker_name": speaker_name,
            "meeting_date": meeting_date,
            "conference_id": conference_id,
            "best_match": best_match,
            "best_confidence": best_confidence,
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.match_speaker(
                speaker_name, meeting_date=meeting_date, conference_id=conference_id
            )

            assert result["matched"] is True
            assert result["confidence"] == 0.98

    @pytest.mark.asyncio
    async def test_match_speaker_low_confidence_boundary(
        self, agent: SpeakerMatchingAgent
    ) -> None:
        """確信度境界値（0.8）のテスト"""
        speaker_name = "田中太郎"

        # 確信度がちょうど0.8の場合（should_match=True）
        best_match: MatchCandidate = {
            "politician_id": 123,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.8,
            "match_type": "partial",
            "is_affiliated": False,
        }
        best_confidence: ConfidenceJudgement = {
            "confidence": 0.8,
            "confidence_level": "medium",
            "should_match": True,  # 0.8以上なのでTrue
            "reason": "名前が部分一致",
            "contributing_factors": [],
            "recommendation": "マッチング推奨（確認推奨）",
        }
        mock_result = {
            "speaker_name": speaker_name,
            "best_match": best_match,
            "best_confidence": best_confidence,
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.match_speaker(speaker_name)

            assert result["matched"] is True
            assert result["confidence"] == 0.8


class TestSpeakerMatchingAgentState:
    """SpeakerMatchingAgentState のテストケース"""

    def test_state_structure(self) -> None:
        """状態構造のテスト"""
        state: SpeakerMatchingAgentState = {
            "speaker_name": "田中太郎",
            "meeting_date": None,
            "conference_id": None,
            "candidates": [],
            "current_candidate_index": 0,
            "best_match": None,
            "best_confidence": None,
            "messages": [],
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        assert state["speaker_name"] == "田中太郎"
        assert state["candidates"] == []
        assert state["remaining_steps"] == MAX_REACT_STEPS

    def test_state_with_candidates(self) -> None:
        """候補付き状態のテスト"""
        candidate: MatchCandidate = {
            "politician_id": 123,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.95,
            "match_type": "exact",
            "is_affiliated": True,
        }

        state: SpeakerMatchingAgentState = {
            "speaker_name": "田中太郎",
            "meeting_date": "2024-01-15",
            "conference_id": 1,
            "candidates": [candidate],
            "current_candidate_index": 0,
            "best_match": candidate,
            "best_confidence": None,
            "messages": [],
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        assert len(state["candidates"]) == 1
        assert state["best_match"] is not None
        assert state["best_match"]["politician_id"] == 123

    def test_state_with_error(self) -> None:
        """エラー付き状態のテスト"""
        state: SpeakerMatchingAgentState = {
            "speaker_name": "田中太郎",
            "meeting_date": None,
            "conference_id": None,
            "candidates": [],
            "current_candidate_index": 0,
            "best_match": None,
            "best_confidence": None,
            "messages": [],
            "remaining_steps": 0,
            "error_message": "Test error message",
        }

        assert state["error_message"] == "Test error message"
        assert state["remaining_steps"] == 0

    def test_state_with_confidence_judgement(self) -> None:
        """確信度判定付き状態のテスト"""
        candidate: MatchCandidate = {
            "politician_id": 123,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.95,
            "match_type": "exact",
            "is_affiliated": True,
        }

        confidence: ConfidenceJudgement = {
            "confidence": 0.95,
            "confidence_level": "high",
            "should_match": True,
            "reason": "名前が完全一致。会議体所属。",
            "contributing_factors": [
                {
                    "factor": "base_score",
                    "impact": 0.95,
                    "description": "名前マッチングスコア（exact）",
                }
            ],
            "recommendation": "高確信度でマッチング推奨",
        }

        state: SpeakerMatchingAgentState = {
            "speaker_name": "田中太郎",
            "meeting_date": "2024-01-15",
            "conference_id": 1,
            "candidates": [candidate],
            "current_candidate_index": 0,
            "best_match": candidate,
            "best_confidence": confidence,
            "messages": [],
            "remaining_steps": 5,
            "error_message": None,
        }

        assert state["best_confidence"] is not None
        assert state["best_confidence"]["confidence"] == 0.95
        assert state["best_confidence"]["should_match"] is True
        assert len(state["best_confidence"]["contributing_factors"]) == 1
