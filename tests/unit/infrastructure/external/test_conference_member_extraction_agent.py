"""会議体メンバー抽出エージェントのユニットテスト

Issue #903: [LangGraph+BAML] 会議体メンバー抽出のエージェント化
"""

# ruff: noqa: E501  # テストファイルでは長い行を許容

from unittest.mock import AsyncMock, patch

import pytest


class TestConferenceMemberExtractionAgent:
    """ConferenceMemberExtractionAgentのテスト"""

    @pytest.fixture
    def mock_extractor(self):
        """モックextractorを作成"""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def agent(self, mock_extractor):
        """エージェントインスタンスを作成"""
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        return ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

    def test_agent_initialization(self, agent):
        """エージェントが正しく初期化されること"""
        assert agent.tools is not None
        assert len(agent.tools) == 3
        assert agent._tools_by_name is not None

    def test_agent_has_required_tools(self, agent):
        """必要なツールがすべて存在すること"""
        tool_names = [tool.name for tool in agent.tools]
        assert "extract_members_from_html" in tool_names
        assert "validate_extracted_members" in tool_names
        assert "deduplicate_members" in tool_names

    @pytest.mark.asyncio
    async def test_extract_members_success(self, mock_extractor):
        """extract_membersが正常にメンバーを抽出すること"""
        from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        # モックの設定
        mock_extractor.extract_members.return_value = [
            ExtractedMemberDTO(
                name="田中太郎",
                role="委員長",
                party_name="〇〇党",
                additional_info=None,
            ),
            ExtractedMemberDTO(
                name="山田花子",
                role="委員",
                party_name="△△党",
                additional_info=None,
            ),
        ]

        agent = ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            conference_name="総務委員会",
        )

        assert result["success"] is True
        assert len(result["members"]) == 2
        assert isinstance(result["members"][0], ExtractedMemberDTO)
        assert result["members"][0].name == "田中太郎"
        assert result["members"][1].name == "山田花子"

    @pytest.mark.asyncio
    async def test_extract_members_handles_extraction_error(self, mock_extractor):
        """extract_membersが抽出エラーを適切に処理すること"""
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        # extractorがエラーを投げるようにモック
        mock_extractor.extract_members.side_effect = Exception("BAML extraction error")

        agent = ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            conference_name="総務委員会",
        )

        assert result["success"] is False
        assert result["error_message"] is not None
        assert "BAML extraction error" in result["error_message"]

    @pytest.mark.asyncio
    async def test_extract_members_empty_result(self, mock_extractor):
        """extract_membersが空の結果を正しく処理すること"""
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        # 空の結果を返すようにモック
        mock_extractor.extract_members.return_value = []

        agent = ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>empty</html>",
            conference_name="総務委員会",
        )

        assert result["success"] is False
        assert len(result["members"]) == 0
        assert "メンバーが抽出されませんでした" in result["error_message"]

    @pytest.mark.asyncio
    async def test_extract_members_with_duplicates(self, mock_extractor):
        """重複メンバーが除去されること"""
        from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        # 重複を含むメンバーを返す
        mock_extractor.extract_members.return_value = [
            ExtractedMemberDTO(name="田中太郎", role="委員長", party_name="〇〇党"),
            ExtractedMemberDTO(
                name="田中太郎", role="委員", party_name="〇〇党"
            ),  # 重複
            ExtractedMemberDTO(name="山田花子", role="委員", party_name="△△党"),
        ]

        agent = ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            conference_name="総務委員会",
        )

        assert result["success"] is True
        # 重複除去後は2名になるはず
        assert len(result["members"]) == 2


class TestMemberExtractorFactory:
    """MemberExtractorFactoryのテスト"""

    def test_create_returns_baml_extractor(self):
        """create()がBAMLMemberExtractorを返すこと"""
        from src.infrastructure.external.conference_member_extractor.baml_extractor import (
            BAMLMemberExtractor,
        )
        from src.infrastructure.external.conference_member_extractor.factory import (
            MemberExtractorFactory,
        )

        extractor = MemberExtractorFactory.create()
        assert isinstance(extractor, BAMLMemberExtractor)

    def test_create_agent_returns_agent(self):
        """create_agent()がConferenceMemberExtractionAgentを返すこと"""
        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            from src.infrastructure.external.conference_member_extractor.factory import (
                MemberExtractorFactory,
            )
            from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                ConferenceMemberExtractionAgent,
            )

            agent = MemberExtractorFactory.create_agent()
            assert isinstance(agent, ConferenceMemberExtractionAgent)


class TestInterfaceCompliance:
    """インターフェース準拠のテスト"""

    def test_agent_implements_interface(self):
        """エージェントがインターフェースを実装していること"""
        with patch(
            "src.infrastructure.external.langgraph_conference_member_extraction_agent.create_conference_member_extraction_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            from src.domain.interfaces.conference_member_extraction_agent import (
                IConferenceMemberExtractionAgent,
            )
            from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
                ConferenceMemberExtractionAgent,
            )

            agent = ConferenceMemberExtractionAgent()
            assert isinstance(agent, IConferenceMemberExtractionAgent)


class TestWorkflowSteps:
    """ワークフローステップのテスト"""

    @pytest.mark.asyncio
    async def test_all_three_tools_exist(self):
        """3つのツールが存在すること"""
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        mock_extractor = AsyncMock()
        agent = ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

        # 3つのツールが存在することを確認
        assert len(agent.tools) == 3
        assert "extract_members_from_html" in agent._tools_by_name
        assert "validate_extracted_members" in agent._tools_by_name
        assert "deduplicate_members" in agent._tools_by_name

    @pytest.mark.asyncio
    async def test_workflow_processes_all_steps(self):
        """ワークフローが抽出→検証→重複除去の順で処理すること"""
        from src.domain.dtos.conference_member_dto import ExtractedMemberDTO
        from src.infrastructure.external.langgraph_conference_member_extraction_agent import (
            ConferenceMemberExtractionAgent,
        )

        mock_extractor = AsyncMock()
        mock_extractor.extract_members.return_value = [
            ExtractedMemberDTO(name="田中太郎", role="委員長", party_name="〇〇党"),
            ExtractedMemberDTO(name="山田花子", role="委員", party_name="△△党"),
        ]

        agent = ConferenceMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            conference_name="総務委員会",
        )

        # 抽出が呼ばれ、結果が返されていることを確認
        mock_extractor.extract_members.assert_called_once()
        assert result["success"] is True
        assert len(result["members"]) == 2
