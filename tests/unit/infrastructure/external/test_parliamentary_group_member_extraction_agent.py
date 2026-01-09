"""議員団メンバー抽出エージェントのユニットテスト

Issue #905: [LangGraph+BAML] 議員団メンバー抽出のエージェント化
"""

# ruff: noqa: E501  # テストファイルでは長い行を許容

from unittest.mock import AsyncMock, patch

import pytest


class TestParliamentaryGroupMemberExtractionAgent:
    """ParliamentaryGroupMemberExtractionAgentのテスト"""

    @pytest.fixture
    def mock_extractor(self):
        """モックextractorを作成"""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def agent(self, mock_extractor):
        """エージェントインスタンスを作成"""
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        return ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

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
        from src.domain.dtos.parliamentary_group_member_dto import (
            ExtractedParliamentaryGroupMemberDTO,
        )
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        # モックの設定
        mock_extractor.extract_members_from_html.return_value = [
            ExtractedParliamentaryGroupMemberDTO(
                name="田中太郎",
                role="団長",
                party_name="〇〇党",
                district="東京1区",
                additional_info=None,
            ),
            ExtractedParliamentaryGroupMemberDTO(
                name="山田花子",
                role="幹事長",
                party_name="△△党",
                district="大阪2区",
                additional_info=None,
            ),
        ]

        agent = ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            parliamentary_group_name="自民党市議団",
        )

        assert result.success is True
        assert len(result.members) == 2
        assert isinstance(result.members[0], ExtractedParliamentaryGroupMemberDTO)
        assert result.members[0].name == "田中太郎"
        assert result.members[1].name == "山田花子"

    @pytest.mark.asyncio
    async def test_extract_members_handles_extraction_error(self, mock_extractor):
        """extract_membersが抽出エラーを適切に処理すること"""
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        # extractorがエラーを投げるようにモック
        mock_extractor.extract_members_from_html.side_effect = Exception(
            "BAML extraction error"
        )

        agent = ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            parliamentary_group_name="自民党市議団",
        )

        assert result.success is False
        assert result.error_message is not None
        assert "BAML extraction error" in result.error_message

    @pytest.mark.asyncio
    async def test_extract_members_empty_result(self, mock_extractor):
        """extract_membersが空の結果を正しく処理すること"""
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        # 空の結果を返すようにモック
        mock_extractor.extract_members_from_html.return_value = []

        agent = ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>empty</html>",
            parliamentary_group_name="自民党市議団",
        )

        assert result.success is False
        assert len(result.members) == 0
        assert "メンバーが抽出されませんでした" in result.error_message

    @pytest.mark.asyncio
    async def test_extract_members_with_duplicates(self, mock_extractor):
        """重複メンバーが除去されること"""
        from src.domain.dtos.parliamentary_group_member_dto import (
            ExtractedParliamentaryGroupMemberDTO,
        )
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        # 重複を含むメンバーを返す
        mock_extractor.extract_members_from_html.return_value = [
            ExtractedParliamentaryGroupMemberDTO(
                name="田中太郎", role="団長", party_name="〇〇党", district="東京1区"
            ),
            ExtractedParliamentaryGroupMemberDTO(
                name="田中太郎", role="幹事", party_name="〇〇党", district="東京1区"
            ),  # 重複
            ExtractedParliamentaryGroupMemberDTO(
                name="山田花子", role="幹事長", party_name="△△党", district="大阪2区"
            ),
        ]

        agent = ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            parliamentary_group_name="自民党市議団",
        )

        assert result.success is True
        # 重複除去後は2名になるはず
        assert len(result.members) == 2


class TestParliamentaryGroupMemberExtractorFactory:
    """ParliamentaryGroupMemberExtractorFactoryのテスト"""

    def test_create_returns_baml_extractor(self):
        """create()がBAMLParliamentaryGroupMemberExtractorを返すこと"""
        from src.infrastructure.external.parliamentary_group_member_extractor.baml_extractor import (
            BAMLParliamentaryGroupMemberExtractor,
        )
        from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
            ParliamentaryGroupMemberExtractorFactory,
        )

        extractor = ParliamentaryGroupMemberExtractorFactory.create()
        assert isinstance(extractor, BAMLParliamentaryGroupMemberExtractor)

    def test_create_agent_returns_agent(self):
        """create_agent()がParliamentaryGroupMemberExtractionAgentを返すこと"""
        with patch(
            "src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent.create_parliamentary_group_member_extraction_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
                ParliamentaryGroupMemberExtractionAgent,
            )
            from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
                ParliamentaryGroupMemberExtractorFactory,
            )

            agent = ParliamentaryGroupMemberExtractorFactory.create_agent()
            assert isinstance(agent, ParliamentaryGroupMemberExtractionAgent)


class TestInterfaceCompliance:
    """インターフェース準拠のテスト"""

    def test_agent_implements_interface(self):
        """エージェントがインターフェースを実装していること"""
        with patch(
            "src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent.create_parliamentary_group_member_extraction_tools"
        ) as mock_tools:
            mock_tools.return_value = []

            from src.domain.interfaces.parliamentary_group_member_extraction_agent import (
                IParliamentaryGroupMemberExtractionAgent,
            )
            from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
                ParliamentaryGroupMemberExtractionAgent,
            )

            agent = ParliamentaryGroupMemberExtractionAgent()
            assert isinstance(agent, IParliamentaryGroupMemberExtractionAgent)


class TestWorkflowSteps:
    """ワークフローステップのテスト"""

    @pytest.mark.asyncio
    async def test_all_three_tools_exist(self):
        """3つのツールが存在すること"""
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        mock_extractor = AsyncMock()
        agent = ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

        # 3つのツールが存在することを確認
        assert len(agent.tools) == 3
        assert "extract_members_from_html" in agent._tools_by_name
        assert "validate_extracted_members" in agent._tools_by_name
        assert "deduplicate_members" in agent._tools_by_name

    @pytest.mark.asyncio
    async def test_workflow_processes_all_steps(self):
        """ワークフローが抽出→検証→重複除去の順で処理すること"""
        from src.domain.dtos.parliamentary_group_member_dto import (
            ExtractedParliamentaryGroupMemberDTO,
        )
        from src.infrastructure.external.langgraph_parliamentary_group_member_extraction_agent import (
            ParliamentaryGroupMemberExtractionAgent,
        )

        mock_extractor = AsyncMock()
        mock_extractor.extract_members_from_html.return_value = [
            ExtractedParliamentaryGroupMemberDTO(
                name="田中太郎", role="団長", party_name="〇〇党", district="東京1区"
            ),
            ExtractedParliamentaryGroupMemberDTO(
                name="山田花子", role="幹事長", party_name="△△党", district="大阪2区"
            ),
        ]

        agent = ParliamentaryGroupMemberExtractionAgent(member_extractor=mock_extractor)

        result = await agent.extract_members(
            html_content="<html>test</html>",
            parliamentary_group_name="自民党市議団",
        )

        # 抽出が呼ばれ、結果が返されていることを確認
        mock_extractor.extract_members_from_html.assert_called_once()
        assert result.success is True
        assert len(result.members) == 2


class TestDTOIntegration:
    """DTOの統合テスト"""

    def test_extraction_result_dto_structure(self):
        """ParliamentaryGroupMemberExtractionResultの構造が正しいこと"""
        from src.domain.dtos.parliamentary_group_member_dto import (
            ExtractedParliamentaryGroupMemberDTO,
            ParliamentaryGroupMemberExtractionResult,
        )

        result = ParliamentaryGroupMemberExtractionResult(
            members=[
                ExtractedParliamentaryGroupMemberDTO(
                    name="田中太郎",
                    role="団長",
                    party_name="〇〇党",
                    district="東京1区",
                    additional_info="元衆議院議員",
                ),
            ],
            success=True,
            validation_errors=[],
            error_message=None,
        )

        assert len(result.members) == 1
        assert result.success is True
        assert result.validation_errors == []
        assert result.error_message is None
        assert result.members[0].name == "田中太郎"
        assert result.members[0].district == "東京1区"
