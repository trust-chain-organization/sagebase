"""政治家マッチングエージェントのユニットテスト

Issue #904: [LangGraph+BAML] 政治家マッチングのエージェント化
"""

# ruff: noqa: E501  # テストファイルでは長い行を許容

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestPoliticianMatchingAgentTools:
    """政治家マッチングツールのテスト"""

    @pytest.fixture
    def mock_politician_repo(self):
        """モックPoliticianRepositoryを作成"""
        mock = AsyncMock()
        mock.get_all_for_matching.return_value = [
            {
                "id": 1,
                "name": "田中太郎",
                "party_name": "〇〇党",
            },
            {
                "id": 2,
                "name": "山田花子",
                "party_name": "△△党",
            },
            {
                "id": 3,
                "name": "佐藤一郎",
                "party_name": "〇〇党",
            },
        ]
        return mock

    @pytest.fixture
    def mock_affiliation_repo(self):
        """モックPoliticianAffiliationRepositoryを作成"""
        mock = AsyncMock()
        mock.get_by_politician.return_value = []
        return mock

    @pytest.mark.asyncio
    async def test_search_politician_candidates_exact_match(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """完全一致の候補検索"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        search_tool = next(t for t in tools if t.name == "search_politician_candidates")
        result = await search_tool.ainvoke({"speaker_name": "田中太郎"})

        assert "candidates" in result
        assert len(result["candidates"]) > 0
        # 完全一致の候補が最上位に
        assert result["candidates"][0]["politician_name"] == "田中太郎"
        assert result["candidates"][0]["score"] == 1.0
        assert result["candidates"][0]["match_type"] == "exact"

    @pytest.mark.asyncio
    async def test_search_politician_candidates_with_party_boost(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """政党一致でスコアがブーストされること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        search_tool = next(t for t in tools if t.name == "search_politician_candidates")
        result = await search_tool.ainvoke(
            {"speaker_name": "田中太郎", "speaker_party": "〇〇党"}
        )

        assert "candidates" in result
        top_candidate = result["candidates"][0]
        assert top_candidate["politician_name"] == "田中太郎"
        # 政党一致でスコアがブースト（1.0 + 0.15 = 1.15 → 1.0にクランプ）
        assert top_candidate["score"] == 1.0

    @pytest.mark.asyncio
    async def test_search_politician_candidates_empty_name(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """空の発言者名でエラーが返ること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        search_tool = next(t for t in tools if t.name == "search_politician_candidates")
        result = await search_tool.ainvoke({"speaker_name": ""})

        assert "error" in result
        assert result["candidates"] == []

    @pytest.mark.asyncio
    async def test_verify_politician_affiliation_found(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """政治家の所属検証が正常に動作すること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        verify_tool = next(
            t for t in tools if t.name == "verify_politician_affiliation"
        )
        result = await verify_tool.ainvoke({"politician_id": 1})

        assert result["politician_id"] == 1
        assert result["politician_name"] == "田中太郎"
        assert result["current_party"] == "〇〇党"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_verify_politician_affiliation_not_found(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """存在しない政治家IDでエラーが返ること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        verify_tool = next(
            t for t in tools if t.name == "verify_politician_affiliation"
        )
        result = await verify_tool.ainvoke({"politician_id": 999})

        assert "error" in result
        assert result["politician_name"] is None

    @pytest.mark.asyncio
    async def test_verify_politician_affiliation_party_match(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """期待政党との一致確認が正常に動作すること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        verify_tool = next(
            t for t in tools if t.name == "verify_politician_affiliation"
        )

        # 一致する場合
        result = await verify_tool.ainvoke(
            {"politician_id": 1, "expected_party": "〇〇党"}
        )
        assert result["party_matches"] is True

        # 一致しない場合
        result = await verify_tool.ainvoke(
            {"politician_id": 1, "expected_party": "△△党"}
        )
        assert result["party_matches"] is False

    @pytest.mark.asyncio
    async def test_match_politician_with_baml_success(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """BAMLマッチングが正常に動作すること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        # BAMLの結果をモック
        mock_baml_result = MagicMock()
        mock_baml_result.matched = True
        mock_baml_result.politician_id = 1
        mock_baml_result.politician_name = "田中太郎"
        mock_baml_result.political_party_name = "〇〇党"
        mock_baml_result.confidence = 0.95
        mock_baml_result.reason = "名前と政党が完全一致"

        with patch(
            "src.infrastructure.external.langgraph_tools.politician_matching_tools.b.MatchPolitician",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = mock_baml_result

            tools = create_politician_matching_tools(
                politician_repo=mock_politician_repo,
                affiliation_repo=mock_affiliation_repo,
            )

            match_tool = next(
                t for t in tools if t.name == "match_politician_with_baml"
            )

            candidates_json = '[{"politician_id": 1, "politician_name": "田中太郎", "party_name": "〇〇党"}]'
            result = await match_tool.ainvoke(
                {
                    "speaker_name": "田中太郎",
                    "speaker_type": "議員",
                    "speaker_party": "〇〇党",
                    "candidates_json": candidates_json,
                }
            )

            assert result["matched"] is True
            assert result["politician_id"] == 1
            assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_match_politician_with_baml_low_confidence(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """信頼度が低い場合はマッチなしになること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        mock_baml_result = MagicMock()
        mock_baml_result.matched = True
        mock_baml_result.politician_id = 1
        mock_baml_result.politician_name = "田中太郎"
        mock_baml_result.political_party_name = "〇〇党"
        mock_baml_result.confidence = 0.5  # 閾値(0.7)未満
        mock_baml_result.reason = "部分一致のみ"

        with patch(
            "src.infrastructure.external.langgraph_tools.politician_matching_tools.b.MatchPolitician",
            new_callable=AsyncMock,
        ) as mock_baml:
            mock_baml.return_value = mock_baml_result

            tools = create_politician_matching_tools(
                politician_repo=mock_politician_repo,
                affiliation_repo=mock_affiliation_repo,
            )

            match_tool = next(
                t for t in tools if t.name == "match_politician_with_baml"
            )

            candidates_json = '[{"politician_id": 1, "politician_name": "田中太郎", "party_name": "〇〇党"}]'
            result = await match_tool.ainvoke(
                {
                    "speaker_name": "田中",
                    "speaker_type": "議員",
                    "speaker_party": "不明",
                    "candidates_json": candidates_json,
                }
            )

            assert result["matched"] is False
            assert result["politician_id"] is None

    @pytest.mark.asyncio
    async def test_match_politician_with_baml_invalid_json(
        self, mock_politician_repo, mock_affiliation_repo
    ):
        """無効なJSONでエラーが返ること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        tools = create_politician_matching_tools(
            politician_repo=mock_politician_repo,
            affiliation_repo=mock_affiliation_repo,
        )

        match_tool = next(t for t in tools if t.name == "match_politician_with_baml")

        result = await match_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "speaker_type": "議員",
                "speaker_party": "〇〇党",
                "candidates_json": "invalid json",
            }
        )

        assert result["matched"] is False
        assert "error" in result


class TestPoliticianMatchingAgent:
    """PoliticianMatchingAgentのテスト"""

    @pytest.fixture
    def mock_llm(self):
        """モックLLMを作成"""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_politician_repo(self):
        """モックPoliticianRepositoryを作成"""
        mock = AsyncMock()
        mock.get_all_for_matching.return_value = [
            {"id": 1, "name": "田中太郎", "party_name": "〇〇党"},
            {"id": 2, "name": "山田花子", "party_name": "△△党"},
        ]
        return mock

    @pytest.fixture
    def mock_affiliation_repo(self):
        """モックPoliticianAffiliationRepositoryを作成"""
        mock = AsyncMock()
        mock.get_by_politician.return_value = []
        return mock

    def test_agent_initialization(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """エージェントが正しく初期化されること"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = [MagicMock(), MagicMock(), MagicMock()]

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = MagicMock()

                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )
                assert agent.tools is not None
                assert len(agent.tools) == 3
                assert agent.agent is not None

    def test_agent_has_required_tools(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """必要なツールがすべて存在すること"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            # 実際のツール名を持つモックを作成
            tool1 = MagicMock()
            tool1.name = "search_politician_candidates"
            tool2 = MagicMock()
            tool2.name = "verify_politician_affiliation"
            tool3 = MagicMock()
            tool3.name = "match_politician_with_baml"
            mock_tools.return_value = [tool1, tool2, tool3]

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = MagicMock()

                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )
                tool_names = [tool.name for tool in agent.tools]
                assert "search_politician_candidates" in tool_names
                assert "verify_politician_affiliation" in tool_names
                assert "match_politician_with_baml" in tool_names

    @pytest.mark.asyncio
    async def test_match_politician_success(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """match_politicianが正常にマッチングを返すこと"""
        # エージェントのainvokeをモック
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "best_match": {
                "matched": True,
                "politician_id": 1,
                "politician_name": "田中太郎",
                "political_party_name": "〇〇党",
                "confidence": 0.95,
                "reason": "名前と政党が完全一致",
            },
            "messages": [],
        }

        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = [MagicMock(), MagicMock(), MagicMock()]

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = mock_agent

                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                result = await agent.match_politician(
                    speaker_name="田中太郎",
                    speaker_type="議員",
                    speaker_party="〇〇党",
                )

                assert result["matched"] is True
                assert result["politician_id"] == 1
                assert result["politician_name"] == "田中太郎"
                assert result["confidence"] == 0.95
                assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_match_politician_no_match(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """マッチングが見つからない場合"""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "best_match": None,
            "messages": [],
        }

        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = [MagicMock(), MagicMock(), MagicMock()]

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = mock_agent

                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                result = await agent.match_politician(
                    speaker_name="存在しない人",
                )

                assert result["matched"] is False
                assert result["politician_id"] is None
                assert result["error_message"] is None

    @pytest.mark.asyncio
    async def test_match_politician_low_confidence(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """信頼度が低い場合はマッチなしになること"""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "best_match": {
                "matched": True,
                "politician_id": 1,
                "politician_name": "田中太郎",
                "political_party_name": "〇〇党",
                "confidence": 0.5,  # 閾値(0.7)未満
                "reason": "部分一致のみ",
            },
            "messages": [],
        }

        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = [MagicMock(), MagicMock(), MagicMock()]

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = mock_agent

                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                result = await agent.match_politician(speaker_name="田中")

                # 信頼度が閾値未満なのでマッチなし
                assert result["matched"] is False

    @pytest.mark.asyncio
    async def test_match_politician_exception(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """例外発生時のエラーハンドリング"""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("テストエラー")

        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = [MagicMock(), MagicMock(), MagicMock()]

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = mock_agent

                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                result = await agent.match_politician(speaker_name="田中太郎")

                assert result["matched"] is False
                assert result["error_message"] is not None
                assert "テストエラー" in result["error_message"]


class TestInterfaceCompliance:
    """インターフェース準拠のテスト"""

    def test_agent_implements_interface(self):
        """エージェントがインターフェースを実装していること"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ) as mock_react:
                mock_react.return_value = MagicMock()

                from src.domain.interfaces.politician_matching_agent import (
                    IPoliticianMatchingAgent,
                )
                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=MagicMock(),
                    politician_repo=AsyncMock(),
                    affiliation_repo=AsyncMock(),
                )
                assert isinstance(agent, IPoliticianMatchingAgent)


class TestNameSimilarity:
    """名前類似度計算のテスト"""

    def test_exact_match(self):
        """完全一致のテスト"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            _calculate_name_similarity,
        )

        score, match_type = _calculate_name_similarity("田中太郎", "田中太郎")
        assert score == 1.0
        assert match_type == "exact"

    def test_exact_match_with_honorific(self):
        """敬称付きでも一致すること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            _calculate_name_similarity,
        )

        score, match_type = _calculate_name_similarity("田中太郎議員", "田中太郎")
        assert score == 1.0
        assert match_type == "exact"

    def test_partial_match(self):
        """部分一致のテスト"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            PARTIAL_MATCH_SCORE,
            _calculate_name_similarity,
        )

        score, match_type = _calculate_name_similarity("田中", "田中太郎")
        assert score == PARTIAL_MATCH_SCORE
        assert match_type == "partial"

    def test_no_match(self):
        """一致なしのテスト"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            _calculate_name_similarity,
        )

        score, match_type = _calculate_name_similarity("山本", "田中太郎")
        assert score < 0.5
        assert match_type in ("fuzzy", "none")


class TestToolCreationValidation:
    """ツール作成時のバリデーションテスト"""

    def test_create_tools_requires_politician_repo(self):
        """politician_repoがNoneの場合はValueErrorが発生すること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        with pytest.raises(ValueError, match="politician_repo is required"):
            create_politician_matching_tools(
                politician_repo=None,
                affiliation_repo=AsyncMock(),
            )

    def test_create_tools_requires_affiliation_repo(self):
        """affiliation_repoがNoneの場合はValueErrorが発生すること"""
        from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
            create_politician_matching_tools,
        )

        with pytest.raises(ValueError, match="affiliation_repo is required"):
            create_politician_matching_tools(
                politician_repo=AsyncMock(),
                affiliation_repo=None,
            )


class TestExtractMatchFromMessages:
    """_extract_match_from_messagesメソッドのテスト"""

    @pytest.fixture
    def mock_llm(self):
        """モックLLMを作成"""
        return MagicMock()

    @pytest.fixture
    def mock_politician_repo(self):
        """モックPoliticianRepositoryを作成"""
        mock = AsyncMock()
        mock.get_all_for_matching.return_value = []
        return mock

    @pytest.fixture
    def mock_affiliation_repo(self):
        """モックPoliticianAffiliationRepositoryを作成"""
        mock = AsyncMock()
        mock.get_by_politician.return_value = []
        return mock

    def test_extract_match_from_valid_json_message(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """有効なJSONメッセージからマッチを抽出できること"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ):
                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                # マッチ成功のJSONを含むメッセージを作成
                mock_message = MagicMock()
                mock_message.content = '{"matched": true, "politician_id": 1, "politician_name": "田中太郎", "political_party_name": "〇〇党", "confidence": 0.9, "reason": "完全一致"}'

                result = agent._extract_match_from_messages([mock_message])

                assert result is not None
                assert result["matched"] is True
                assert result["politician_id"] == 1

    def test_extract_match_returns_none_for_low_confidence(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """信頼度が低いメッセージはNoneを返すこと"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ):
                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                # 信頼度が低いJSONを含むメッセージを作成
                mock_message = MagicMock()
                mock_message.content = '{"matched": true, "politician_id": 1, "politician_name": "田中太郎", "confidence": 0.5, "reason": "部分一致"}'

                result = agent._extract_match_from_messages([mock_message])

                assert result is None

    def test_extract_match_returns_none_for_invalid_json(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """無効なJSONメッセージはNoneを返すこと"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ):
                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                mock_message = MagicMock()
                mock_message.content = "これはJSONではありません matched confidence"

                result = agent._extract_match_from_messages([mock_message])

                assert result is None

    def test_extract_match_returns_none_for_empty_messages(
        self, mock_llm, mock_politician_repo, mock_affiliation_repo
    ):
        """空のメッセージリストはNoneを返すこと"""
        with patch(
            "src.infrastructure.external.langgraph_politician_matching_agent.create_politician_matching_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            with patch(
                "src.infrastructure.external.langgraph_politician_matching_agent.create_react_agent"
            ):
                from src.infrastructure.external.langgraph_politician_matching_agent import (
                    PoliticianMatchingAgent,
                )

                agent = PoliticianMatchingAgent(
                    llm=mock_llm,
                    politician_repo=mock_politician_repo,
                    affiliation_repo=mock_affiliation_repo,
                )

                result = agent._extract_match_from_messages([])

                assert result is None
