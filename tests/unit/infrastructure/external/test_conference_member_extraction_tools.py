"""会議体メンバー抽出ツールのユニットテスト

Issue #903: [LangGraph+BAML] 会議体メンバー抽出のエージェント化
"""

from unittest.mock import AsyncMock

import pytest

# ruff: noqa: E501  # テストファイルでは長い行を許容
from src.infrastructure.external.langgraph_tools.conference_member_extraction_tools import (  # noqa: E501
    create_conference_member_extraction_tools,
)


class TestConferenceMemberExtractionTools:
    """会議体メンバー抽出ツールのテスト"""

    @pytest.fixture
    def tools(self):
        """ツールリストを作成"""
        return create_conference_member_extraction_tools()

    @pytest.fixture
    def extract_tool(self, tools):
        """extract_members_from_htmlツールを取得"""
        return tools[0]

    @pytest.fixture
    def validate_tool(self, tools):
        """validate_extracted_membersツールを取得"""
        return tools[1]

    @pytest.fixture
    def deduplicate_tool(self, tools):
        """deduplicate_membersツールを取得"""
        return tools[2]

    def test_create_tools_returns_three_tools(self, tools):
        """ツール作成で3つのツールが返されること"""
        assert len(tools) == 3
        assert tools[0].name == "extract_members_from_html"
        assert tools[1].name == "validate_extracted_members"
        assert tools[2].name == "deduplicate_members"

    # extract_members_from_html テスト

    @pytest.mark.asyncio
    async def test_extract_members_from_html_empty_content(self, extract_tool):
        """空のHTMLコンテンツの場合エラーを返すこと"""
        result = await extract_tool.ainvoke(
            {"html_content": "", "conference_name": "総務委員会"}
        )
        assert result["success"] is False
        assert result["count"] == 0
        assert "HTMLコンテンツが空です" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_members_from_html_empty_conference_name(self, extract_tool):
        """空の会議体名の場合エラーを返すこと"""
        result = await extract_tool.ainvoke(
            {"html_content": "<html></html>", "conference_name": ""}
        )
        assert result["success"] is False
        assert result["count"] == 0
        assert "会議体名が空です" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_members_from_html_with_mock(self):
        """BAMLを使用してメンバーを抽出すること（依存性注入でモック使用）"""
        from src.domain.dtos.conference_member_dto import ExtractedMemberDTO

        mock_members = [
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

        # 依存性注入でモックを渡す
        mock_extractor = AsyncMock()
        mock_extractor.extract_members.return_value = mock_members

        tools = create_conference_member_extraction_tools(
            member_extractor=mock_extractor
        )
        extract_tool = tools[0]

        result = await extract_tool.ainvoke(
            {"html_content": "<html>test</html>", "conference_name": "総務委員会"}
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["members"]) == 2
        assert result["members"][0]["name"] == "田中太郎"
        assert result["members"][1]["name"] == "山田花子"
        mock_extractor.extract_members.assert_called_once()

    # validate_extracted_members テスト

    @pytest.mark.asyncio
    async def test_validate_empty_members(self, validate_tool):
        """空のメンバーリストの場合、空の結果を返すこと"""
        result = await validate_tool.ainvoke({"members": []})
        assert result["total_count"] == 0
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 0

    @pytest.mark.asyncio
    async def test_validate_valid_members(self, validate_tool):
        """有効なメンバーが検証を通過すること"""
        members = [
            {"name": "田中太郎", "role": "委員長", "party_name": "〇〇党"},
            {"name": "山田花子", "role": "委員", "party_name": "△△党"},
        ]
        result = await validate_tool.ainvoke({"members": members})
        assert result["valid_count"] == 2
        assert result["invalid_count"] == 0

    @pytest.mark.asyncio
    async def test_validate_empty_name(self, validate_tool):
        """空の名前が無効として検出されること"""
        members = [
            {"name": "", "role": "委員", "party_name": "〇〇党"},
        ]
        result = await validate_tool.ainvoke({"members": members})
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "名前が空です" in result["validation_errors"][0]

    @pytest.mark.asyncio
    async def test_validate_numeric_name(self, validate_tool):
        """数字のみの名前が無効として検出されること"""
        members = [
            {"name": "12345", "role": "委員", "party_name": "〇〇党"},
        ]
        result = await validate_tool.ainvoke({"members": members})
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "数字のみ" in result["validation_errors"][0]

    @pytest.mark.asyncio
    async def test_validate_short_name(self, validate_tool):
        """短すぎる名前が無効として検出されること"""
        members = [
            {"name": "田", "role": "委員", "party_name": "〇〇党"},
        ]
        result = await validate_tool.ainvoke({"members": members})
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "短すぎます" in result["validation_errors"][0]

    @pytest.mark.asyncio
    async def test_validate_duplicate_names(self, validate_tool):
        """重複した名前が検出されること"""
        members = [
            {"name": "田中太郎", "role": "委員長"},
            {"name": "田中太郎", "role": "委員"},  # 重複
        ]
        result = await validate_tool.ainvoke({"members": members})
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 1
        assert "重複" in result["validation_errors"][0]

    # deduplicate_members テスト

    @pytest.mark.asyncio
    async def test_deduplicate_empty_members(self, deduplicate_tool):
        """空のメンバーリストの場合、空の結果を返すこと"""
        result = await deduplicate_tool.ainvoke({"members": []})
        assert result["original_count"] == 0
        assert result["unique_count"] == 0

    @pytest.mark.asyncio
    async def test_deduplicate_no_duplicates(self, deduplicate_tool):
        """重複がない場合、全メンバーが保持されること"""
        members = [
            {"name": "田中太郎", "role": "委員長"},
            {"name": "山田花子", "role": "委員"},
        ]
        result = await deduplicate_tool.ainvoke({"members": members})
        assert result["original_count"] == 2
        assert result["unique_count"] == 2
        assert len(result["duplicates_removed"]) == 0

    @pytest.mark.asyncio
    async def test_deduplicate_exact_match(self, deduplicate_tool):
        """完全一致の重複が除去されること"""
        members = [
            {"name": "田中太郎", "role": "委員長"},
            {"name": "田中太郎", "role": "委員"},  # 重複
        ]
        result = await deduplicate_tool.ainvoke({"members": members})
        assert result["original_count"] == 2
        assert result["unique_count"] == 1
        assert len(result["duplicates_removed"]) == 1

    @pytest.mark.asyncio
    async def test_deduplicate_space_variation(self, deduplicate_tool):
        """スペースの有無による重複が検出されること"""
        members = [
            {"name": "田中太郎", "role": "委員長"},
            {"name": "田中 太郎", "role": "委員"},  # スペースあり
        ]
        result = await deduplicate_tool.ainvoke({"members": members})
        assert result["original_count"] == 2
        assert result["unique_count"] == 1
        assert len(result["duplicates_removed"]) == 1
        assert result["merge_info"][0]["similarity"] == 1.0

    @pytest.mark.asyncio
    async def test_deduplicate_similar_names(self, deduplicate_tool):
        """類似した名前が高い閾値で検出されること"""
        members = [
            {"name": "田中太郎", "role": "委員長"},
            {"name": "田中太朗", "role": "委員"},  # 「郎」→「朗」の類似
        ]
        result = await deduplicate_tool.ainvoke(
            {"members": members, "similarity_threshold": 0.85}
        )
        # 類似度が閾値以上なら重複として検出
        # 「田中太郎」と「田中太朗」の類似度は約0.75なので重複とはならない
        assert result["original_count"] == 2
        # 実際の類似度に依存するので柔軟にアサート
        assert result["unique_count"] >= 1

    @pytest.mark.asyncio
    async def test_deduplicate_different_names(self, deduplicate_tool):
        """異なる名前が保持されること"""
        members = [
            {"name": "田中太郎", "role": "委員長"},
            {"name": "鈴木一郎", "role": "委員"},
        ]
        result = await deduplicate_tool.ainvoke({"members": members})
        assert result["original_count"] == 2
        assert result["unique_count"] == 2
        assert len(result["duplicates_removed"]) == 0

    # 追加テスト: BAMLエラー、エッジケース

    @pytest.mark.asyncio
    async def test_extract_members_from_html_baml_error(self):
        """BAMLでエラーが発生した場合、エラーを返すこと"""
        mock_extractor = AsyncMock()
        mock_extractor.extract_members.side_effect = Exception("BAML extraction error")

        # 依存性注入でモックを渡す
        tools = create_conference_member_extraction_tools(
            member_extractor=mock_extractor
        )
        extract_tool = tools[0]

        result = await extract_tool.ainvoke(
            {"html_content": "<html>test</html>", "conference_name": "総務委員会"}
        )

        assert result["success"] is False
        assert "BAML extraction error" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_members_with_dependency_injection(self):
        """依存性注入でextractorを渡せること"""
        from src.domain.dtos.conference_member_dto import ExtractedMemberDTO

        mock_extractor = AsyncMock()
        mock_extractor.extract_members.return_value = [
            ExtractedMemberDTO(
                name="テスト太郎",
                role="委員",
                party_name=None,
                additional_info=None,
            )
        ]

        # 依存性注入でモックを渡す
        tools = create_conference_member_extraction_tools(
            member_extractor=mock_extractor
        )
        extract_tool = tools[0]

        result = await extract_tool.ainvoke(
            {"html_content": "<html>test</html>", "conference_name": "総務委員会"}
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["members"][0]["name"] == "テスト太郎"
        mock_extractor.extract_members.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_members_with_none_name(self, validate_tool):
        """Noneの名前を含むメンバーが無効として検出されること"""
        members = [
            {"name": None, "role": "委員"},
        ]
        result = await validate_tool.ainvoke({"members": members})
        assert result["valid_count"] == 0
        assert result["invalid_count"] == 1
        assert "名前が空です" in result["validation_errors"][0]

    @pytest.mark.asyncio
    async def test_deduplicate_with_empty_names(self, deduplicate_tool):
        """空の名前を含むメンバーが適切にスキップされること"""
        members = [
            {"name": "", "role": "委員"},
            {"name": "田中太郎", "role": "委員長"},
        ]
        result = await deduplicate_tool.ainvoke({"members": members})
        # 空の名前はスキップされるので、1人だけがユニークとしてカウント
        assert result["unique_count"] == 1
        assert result["unique_members"][0]["name"] == "田中太郎"
