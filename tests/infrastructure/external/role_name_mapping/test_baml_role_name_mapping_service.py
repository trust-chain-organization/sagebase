"""Tests for BAML Role-Name Mapping Service

役職-人名マッピング抽出サービスのテスト。
BAMLクライアントをモックして、外部サービス呼び出しなしでテストを実行します。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.role_name_mapping_dto import (
    RoleNameMappingDTO,
    RoleNameMappingResultDTO,
)
from src.infrastructure.external.role_name_mapping import BAMLRoleNameMappingService


pytestmark = pytest.mark.baml


@pytest.fixture
def mock_baml_client():
    """BAMLクライアントをモック"""
    with patch(
        "src.infrastructure.external.role_name_mapping.baml_role_name_mapping_service.b"
    ) as mock_b:
        mock_extract = AsyncMock()
        mock_b.ExtractRoleNameMapping = mock_extract
        yield mock_b


class TestBAMLRoleNameMappingService:
    """BAML Role-Name Mapping Service tests"""

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_success(self, mock_baml_client):
        """正常な役職-人名マッピング抽出テスト"""
        # BAMLの戻り値をモック
        mock_mapping1 = MagicMock()
        mock_mapping1.role = "議長"
        mock_mapping1.name = "伊藤条一"
        mock_mapping1.member_number = "100番"

        mock_mapping2 = MagicMock()
        mock_mapping2.role = "副議長"
        mock_mapping2.name = "梶谷大志"
        mock_mapping2.member_number = "82番"

        mock_result = MagicMock()
        mock_result.mappings = [mock_mapping1, mock_mapping2]
        mock_result.attendee_section_found = True
        mock_result.confidence = 0.95

        mock_baml_client.ExtractRoleNameMapping.return_value = mock_result

        # サービスを実行
        service = BAMLRoleNameMappingService()
        attendee_text = """
出席議員（96人）
　　　議長　　　100番　　伊藤条一君
　　　副議長　　 82番　　梶谷大志君
"""
        result = await service.extract_role_name_mapping(attendee_text)

        # 検証
        assert result.attendee_section_found is True
        assert result.confidence == 0.95
        assert len(result.mappings) == 2

        assert result.mappings[0].role == "議長"
        assert result.mappings[0].name == "伊藤条一"
        assert result.mappings[0].member_number == "100番"

        assert result.mappings[1].role == "副議長"
        assert result.mappings[1].name == "梶谷大志"
        assert result.mappings[1].member_number == "82番"

        # to_dict() のテスト
        mapping_dict = result.to_dict()
        assert mapping_dict == {"議長": "伊藤条一", "副議長": "梶谷大志"}

        # BAML呼び出しの検証
        mock_baml_client.ExtractRoleNameMapping.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_none_input(self, mock_baml_client):
        """Noneが渡された場合のテスト"""
        service = BAMLRoleNameMappingService()

        result = await service.extract_role_name_mapping(None)

        assert result.attendee_section_found is False
        assert result.confidence == 0.0
        assert len(result.mappings) == 0

        # BAML呼び出しがないことを検証
        mock_baml_client.ExtractRoleNameMapping.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_empty_text(self, mock_baml_client):
        """空のテキストの場合のテスト"""
        service = BAMLRoleNameMappingService()

        result = await service.extract_role_name_mapping("")

        assert result.attendee_section_found is False
        assert result.confidence == 0.0
        assert len(result.mappings) == 0

        # BAML呼び出しがないことを検証
        mock_baml_client.ExtractRoleNameMapping.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_whitespace_only(self, mock_baml_client):
        """空白のみのテキストの場合のテスト"""
        service = BAMLRoleNameMappingService()

        result = await service.extract_role_name_mapping("   \n\t   ")

        assert result.attendee_section_found is False
        assert result.confidence == 0.0
        assert len(result.mappings) == 0

        # BAML呼び出しがないことを検証
        mock_baml_client.ExtractRoleNameMapping.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_no_section_found(self, mock_baml_client):
        """出席者セクションが見つからない場合のテスト"""
        mock_result = MagicMock()
        mock_result.mappings = []
        mock_result.attendee_section_found = False
        mock_result.confidence = 0.0

        mock_baml_client.ExtractRoleNameMapping.return_value = mock_result

        service = BAMLRoleNameMappingService()
        result = await service.extract_role_name_mapping("一般的なテキスト...")

        assert result.attendee_section_found is False
        assert result.confidence == 0.0
        assert len(result.mappings) == 0

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_error_handling(self, mock_baml_client):
        """エラー時のハンドリングテスト"""
        mock_baml_client.ExtractRoleNameMapping.side_effect = Exception(
            "BAML API Error"
        )

        service = BAMLRoleNameMappingService()
        result = await service.extract_role_name_mapping("テスト用テキスト")

        # エラー時は空の結果を返す
        assert result.attendee_section_found is False
        assert result.confidence == 0.0
        assert len(result.mappings) == 0

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_with_multiple_roles(
        self, mock_baml_client
    ):
        """複数の役職を含むテスト"""
        # 知事、副知事などの説明員も含む
        mock_mappings = []
        roles_and_names = [
            ("議長", "伊藤条一", "100番"),
            ("副議長", "梶谷大志", "82番"),
            ("知事", "鈴木直道", None),
            ("副知事", "濱坂真一", None),
        ]

        for role, name, member_number in roles_and_names:
            mock_mapping = MagicMock()
            mock_mapping.role = role
            mock_mapping.name = name
            mock_mapping.member_number = member_number
            mock_mappings.append(mock_mapping)

        mock_result = MagicMock()
        mock_result.mappings = mock_mappings
        mock_result.attendee_section_found = True
        mock_result.confidence = 0.92

        mock_baml_client.ExtractRoleNameMapping.return_value = mock_result

        service = BAMLRoleNameMappingService()
        result = await service.extract_role_name_mapping("出席者情報テキスト")

        assert len(result.mappings) == 4
        assert result.confidence == 0.92

        mapping_dict = result.to_dict()
        assert mapping_dict == {
            "議長": "伊藤条一",
            "副議長": "梶谷大志",
            "知事": "鈴木直道",
            "副知事": "濱坂真一",
        }

    @pytest.mark.asyncio
    async def test_extract_role_name_mapping_truncates_long_text(
        self, mock_baml_client
    ):
        """長いテキストが切り詰められることをテスト"""
        mock_result = MagicMock()
        mock_result.mappings = []
        mock_result.attendee_section_found = True
        mock_result.confidence = 0.5

        mock_baml_client.ExtractRoleNameMapping.return_value = mock_result

        service = BAMLRoleNameMappingService()

        # 50000文字を超えるテキストを作成
        long_text = "a" * 60000

        await service.extract_role_name_mapping(long_text)

        # BAML呼び出しの引数を検証
        call_args = mock_baml_client.ExtractRoleNameMapping.call_args
        passed_text = call_args[0][0]  # positional argument

        # 切り詰められたテキストは50000 + 3("...")文字
        assert len(passed_text) == 50003
        assert passed_text.endswith("...")


class TestRoleNameMappingResultDTO:
    """RoleNameMappingResultDTO tests"""

    def test_to_dict_empty(self):
        """空のマッピングの場合のto_dict()テスト"""
        result = RoleNameMappingResultDTO(
            mappings=[],
            attendee_section_found=False,
            confidence=0.0,
        )

        assert result.to_dict() == {}

    def test_to_dict_with_mappings(self):
        """マッピングがある場合のto_dict()テスト"""
        result = RoleNameMappingResultDTO(
            mappings=[
                RoleNameMappingDTO(role="議長", name="山田太郎", member_number="1番"),
                RoleNameMappingDTO(role="副議長", name="佐藤花子", member_number=None),
            ],
            attendee_section_found=True,
            confidence=0.9,
        )

        expected = {"議長": "山田太郎", "副議長": "佐藤花子"}
        assert result.to_dict() == expected

    def test_default_values(self):
        """デフォルト値のテスト"""
        result = RoleNameMappingResultDTO()

        assert result.mappings == []
        assert result.attendee_section_found is False
        assert result.confidence == 0.0

    def test_to_dict_with_duplicate_roles(self):
        """同一役職が複数存在する場合のto_dict()テスト

        同一役職が複数存在する場合、後の値で上書きされることを確認します。
        """
        result = RoleNameMappingResultDTO(
            mappings=[
                RoleNameMappingDTO(role="委員", name="田中一郎", member_number=None),
                RoleNameMappingDTO(role="委員", name="高橋二郎", member_number=None),
                RoleNameMappingDTO(role="委員長", name="山田太郎", member_number=None),
            ],
            attendee_section_found=True,
            confidence=0.9,
        )

        # 同一役職「委員」は後の値（高橋二郎）で上書きされる
        expected = {"委員": "高橋二郎", "委員長": "山田太郎"}
        assert result.to_dict() == expected

        # 全ての委員を取得したい場合はmappingsリストを直接参照
        all_members = [m.name for m in result.mappings if m.role == "委員"]
        assert all_members == ["田中一郎", "高橋二郎"]
