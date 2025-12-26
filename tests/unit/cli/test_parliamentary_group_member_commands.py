"""Tests for parliamentary group member CLI commands"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.interfaces.cli.commands.parliamentary_group_member_commands import (
    ParliamentaryGroupMemberCommands,
)


class TestParliamentaryGroupMemberCommands:
    """Test cases for parliamentary group member CLI commands"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_progress(self):
        """Create a mock progress tracker"""
        with patch("src.interfaces.cli.progress.ProgressTracker") as mock:
            progress_instance = Mock()
            progress_instance.__enter__ = Mock(return_value=progress_instance)
            progress_instance.__exit__ = Mock(return_value=None)
            progress_instance.start = Mock()
            progress_instance.update = Mock()
            progress_instance.finish = Mock()
            progress_instance.set_description = Mock()
            mock.return_value = progress_instance
            yield progress_instance

    def test_extract_parliamentary_group_members_success(self, runner, mock_progress):
        """Test successful extraction of parliamentary group members"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberExtractorFactory"
            ) as mock_factory_class:
                # Setup mocks
                mock_group_repo = MagicMock()
                mock_group_repo.get_parliamentary_group_by_id.return_value = {
                    "id": 1,
                    "name": "自由民主党議員団",
                    "url": "https://example.com/members",
                }
                mock_group_repo.close = Mock()

                mock_extracted_repo = MagicMock()
                mock_extracted_repo.get_extraction_summary.return_value = {
                    "total": 5,
                    "pending": 0,
                    "matched": 5,
                    "no_match": 0,
                    "needs_review": 0,
                }
                mock_extracted_repo.save_extracted_members.return_value = 5
                mock_extracted_repo.close = Mock()

                # Set up RepositoryAdapter to return different repos
                def adapter_side_effect(impl_class):
                    if "ExtractedParliamentaryGroupMember" in impl_class.__name__:
                        return mock_extracted_repo
                    elif "ParliamentaryGroup" in impl_class.__name__:
                        return mock_group_repo
                    return MagicMock()

                mock_adapter_class.side_effect = adapter_side_effect

                # Mock extractor
                mock_extractor = Mock()
                mock_result = Mock()
                mock_result.error = None
                mock_result.extracted_members = [
                    Mock(name="山田太郎"),
                    Mock(name="佐藤花子"),
                    Mock(name="田中一郎"),
                    Mock(name="鈴木美咲"),
                    Mock(name="高橋健太"),
                ]
                mock_extractor.extract_members_sync.return_value = mock_result
                mock_extractor.close = Mock()
                mock_factory_class.create.return_value = mock_extractor

                # Execute
                result = runner.invoke(
                    ParliamentaryGroupMemberCommands.extract_parliamentary_group_members,
                    ["--parliamentary-group-id", "1"],
                )

                # Assert
                assert result.exit_code == 0
                assert (
                    "📋 議員団メンバー情報の抽出を開始します（ステップ1/3）"
                    in result.output
                )
                assert "=== 抽出完了 ===" in result.output
                assert "✅ 抽出総数: 5人" in result.output
                assert "✅ 保存総数: 5人" in result.output
                mock_extractor.extract_members_sync.assert_called_once()

    def test_extract_parliamentary_group_members_with_force(
        self, runner, mock_progress
    ):
        """Test extraction with force flag"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberExtractorFactory"
            ) as mock_factory_class:
                # Setup mocks
                mock_group_repo = Mock()
                mock_group_repo.get_parliamentary_group_by_id.return_value = {
                    "id": 1,
                    "name": "自由民主党議員団",
                    "url": "https://example.com/members",
                }
                mock_group_repo.close = Mock()

                mock_extracted_repo = Mock()
                mock_extracted_repo.delete_extracted_members = Mock(return_value=3)
                mock_extracted_repo.get_extraction_summary.return_value = {
                    "total": 2,
                    "pending": 0,
                    "matched": 2,
                    "no_match": 0,
                    "needs_review": 0,
                }
                mock_extracted_repo.save_extracted_members.return_value = 2
                mock_extracted_repo.close = Mock()

                # Set up RepositoryAdapter
                def adapter_side_effect(impl_class):
                    if "ExtractedParliamentaryGroupMember" in impl_class.__name__:
                        return mock_extracted_repo
                    elif "ParliamentaryGroup" in impl_class.__name__:
                        return mock_group_repo
                    return Mock()

                mock_adapter_class.side_effect = adapter_side_effect

                # Mock extractor
                mock_extractor = Mock()
                mock_result = Mock()
                mock_result.error = None
                mock_result.extracted_members = [
                    Mock(name="山田太郎"),
                    Mock(name="佐藤花子"),
                ]
                mock_extractor.extract_members_sync.return_value = mock_result
                mock_factory_class.create.return_value = mock_extractor

                # Execute with --force
                result = runner.invoke(
                    ParliamentaryGroupMemberCommands.extract_parliamentary_group_members,
                    ["--parliamentary-group-id", "1", "--force"],
                )

                # Assert
                assert result.exit_code == 0
                assert "既存の抽出データ3件を削除しました" in result.output
                mock_extracted_repo.delete_extracted_members.assert_called_once_with(1)
                mock_extractor.extract_members_sync.assert_called_once()

    def test_extract_parliamentary_group_members_not_found(self, runner, mock_progress):
        """Test extraction when parliamentary group not found"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mock that returns None
            mock_group_repo = MagicMock()
            mock_group_repo.get_parliamentary_group_by_id.return_value = None
            mock_group_repo.close = Mock()

            mock_extracted_repo = MagicMock()
            mock_extracted_repo.close = Mock()

            def adapter_side_effect(impl_class):
                if "ExtractedParliamentaryGroupMember" in impl_class.__name__:
                    return mock_extracted_repo
                elif "ParliamentaryGroup" in impl_class.__name__:
                    return mock_group_repo
                return MagicMock()

            mock_adapter_class.side_effect = adapter_side_effect

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.extract_parliamentary_group_members,
                ["--parliamentary-group-id", "999"],
            )

            # Assert
            assert result.exit_code == 0
            assert "議員団ID 999 が見つかりません" in result.output

    def test_extract_parliamentary_group_members_no_url(self, runner, mock_progress):
        """Test extraction when parliamentary group has no URL"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mock with no URL
            mock_group_repo = MagicMock()
            mock_group_repo.get_parliamentary_group_by_id.return_value = {
                "id": 1,
                "name": "自由民主党議員団",
                "url": None,  # No URL
            }
            mock_group_repo.close = Mock()

            mock_extracted_repo = MagicMock()
            mock_extracted_repo.close = Mock()

            def adapter_side_effect(impl_class):
                if "ExtractedParliamentaryGroupMember" in impl_class.__name__:
                    return mock_extracted_repo
                elif "ParliamentaryGroup" in impl_class.__name__:
                    return mock_group_repo
                return MagicMock()

            mock_adapter_class.side_effect = adapter_side_effect

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.extract_parliamentary_group_members,
                ["--parliamentary-group-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "にURLが設定されていません" in result.output

    def test_extract_parliamentary_group_members_all_groups(
        self, runner, mock_progress
    ):
        """Test extraction without group ID (process all)"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberExtractorFactory"
            ) as mock_factory_class:
                # Setup mocks
                mock_group_repo = MagicMock()
                mock_group_repo.get_all_parliamentary_groups.return_value = [
                    {
                        "id": 1,
                        "name": "自由民主党議員団",
                        "url": "https://example.com/ldp",
                    },
                    {
                        "id": 2,
                        "name": "立憲民主党議員団",
                        "url": "https://example.com/cdp",
                    },
                ]
                mock_group_repo.close = Mock()

                mock_extracted_repo = MagicMock()
                mock_extracted_repo.get_extraction_summary.return_value = {
                    "total": 10,
                    "pending": 0,
                    "matched": 10,
                    "no_match": 0,
                    "needs_review": 0,
                }
                mock_extracted_repo.save_extracted_members.return_value = 5
                mock_extracted_repo.close = Mock()

                def adapter_side_effect(impl_class):
                    if "ExtractedParliamentaryGroupMember" in impl_class.__name__:
                        return mock_extracted_repo
                    elif "ParliamentaryGroup" in impl_class.__name__:
                        return mock_group_repo
                    return MagicMock()

                mock_adapter_class.side_effect = adapter_side_effect

                # Mock extractor
                mock_extractor = Mock()
                mock_result = Mock()
                mock_result.error = None
                mock_result.extracted_members = [
                    Mock(name=f"議員{i}") for i in range(5)
                ]
                mock_extractor.extract_members_sync.return_value = mock_result
                mock_factory_class.create.return_value = mock_extractor

                # Execute without group ID
                result = runner.invoke(
                    ParliamentaryGroupMemberCommands.extract_parliamentary_group_members
                )

                # Assert
                assert result.exit_code == 0
                assert "処理対象: 2件の議員団" in result.output
                assert mock_extractor.extract_members_sync.call_count == 2

    def test_match_parliamentary_group_members_success(self, runner, mock_progress):
        """Test successful matching of parliamentary group members"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberCommands._create_match_members_usecase"
        ) as mock_usecase_creator:
            # Setup mock - UseCase.execute returns a list of dicts
            mock_usecase = Mock()
            mock_usecase.execute = AsyncMock(
                return_value=[
                    {"status": "matched"},
                    {"status": "matched"},
                    {"status": "matched"},
                    {"status": "needs_review"},
                    {"status": "no_match"},
                ]
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.match_parliamentary_group_members,
                ["--parliamentary-group-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "🔍 議員情報のマッチングを開始します（ステップ2/3）" in result.output
            assert "=== マッチング完了 ===" in result.output
            assert "処理総数: 5件" in result.output
            assert "✅ マッチ成功: 3件" in result.output
            assert "⚠️  要確認: 1件" in result.output
            assert "❌ 該当なし: 1件" in result.output

    def test_match_parliamentary_group_members_no_group_id(self, runner, mock_progress):
        """Test matching without group ID (process all)"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberCommands._create_match_members_usecase"
        ) as mock_usecase_creator:
            # Setup mock - UseCase.execute returns a list of dicts
            mock_usecase = Mock()
            mock_usecase.execute = AsyncMock(
                return_value=[{"status": "matched"} for _ in range(8)]
                + [{"status": "needs_review"}]
                + [{"status": "no_match"}]
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute without group ID
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.match_parliamentary_group_members
            )

            # Assert
            assert result.exit_code == 0
            assert "🔍 議員情報のマッチングを開始します（ステップ2/3）" in result.output
            mock_usecase.execute.assert_called_once_with(None)

    def test_match_parliamentary_group_members_with_errors(self, runner, mock_progress):
        """Test matching with some errors"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberCommands._create_match_members_usecase"
        ) as mock_usecase_creator:
            # Setup mock - UseCase.execute returns a list of dicts
            mock_usecase = Mock()
            mock_usecase.execute = AsyncMock(
                return_value=[
                    {"status": "matched"},
                    {"status": "matched"},
                    {"status": "needs_review"},
                    {"status": "no_match"},
                    {"status": "error"},  # One error
                ]
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.match_parliamentary_group_members,
                ["--parliamentary-group-id", "1"],
            )

            # Assert
            assert result.exit_code == 0

    def test_create_parliamentary_group_affiliations_success(
        self, runner, mock_progress
    ):
        """Test successful creation of affiliations"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberCommands._create_memberships_usecase"
        ) as mock_usecase_creator:
            # Setup mock - UseCase.execute returns a dict
            mock_usecase = Mock()
            mock_usecase.execute = AsyncMock(
                return_value={
                    "created_count": 3,
                    "skipped_count": 0,
                    "created_memberships": [],
                }
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.create_parliamentary_group_affiliations,
                ["--parliamentary-group-id", "1", "--start-date", "2024-01-01"],
            )

            # Assert
            assert result.exit_code == 0
            assert (
                "🏛️ 議員団メンバーシップの作成を開始します（ステップ3/3）"
                in result.output
            )
            assert "=== メンバーシップ作成完了 ===" in result.output
            assert "処理総数: 3件" in result.output
            assert "✅ 作成/更新: 3件" in result.output

    def test_create_parliamentary_group_affiliations_with_default_date(
        self, runner, mock_progress
    ):
        """Test creating affiliations with default date (today)"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberCommands._create_memberships_usecase"
        ) as mock_usecase_creator:
            with patch(
                "src.interfaces.cli.commands.parliamentary_group_member_commands.date"
            ) as mock_date:
                # Mock today's date
                mock_date.today.return_value = date(2024, 3, 15)
                mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

                # Setup mock - UseCase.execute returns a dict
                mock_usecase = Mock()
                mock_usecase.execute = AsyncMock(
                    return_value={
                        "created_count": 1,
                        "skipped_count": 0,
                        "created_memberships": [],
                    }
                )
                mock_usecase_creator.return_value = mock_usecase

                # Execute without start-date
                result = runner.invoke(
                    ParliamentaryGroupMemberCommands.create_parliamentary_group_affiliations,
                    ["--parliamentary-group-id", "1"],
                )

                # Assert
                assert result.exit_code == 0
                # Check that execute was called (date is passed inside)
                mock_usecase.execute.assert_called_once()

    def test_create_parliamentary_group_affiliations_with_failures(
        self, runner, mock_progress
    ):
        """Test creating affiliations with some failures"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.ParliamentaryGroupMemberCommands._create_memberships_usecase"
        ) as mock_usecase_creator:
            # Setup mock - UseCase.execute returns a dict
            mock_usecase = Mock()
            mock_usecase.execute = AsyncMock(
                return_value={
                    "created_count": 3,
                    "skipped_count": 2,
                    "created_memberships": [],
                }
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.create_parliamentary_group_affiliations,
                ["--parliamentary-group-id", "1", "--start-date", "2024-01-01"],
            )

            # Assert
            assert result.exit_code == 0
            assert "⚠️  スキップ: 2件" in result.output

    def test_parliamentary_group_member_status_success(self, runner):
        """Test status command"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mock
            mock_repo = MagicMock()
            mock_repo.get_extraction_summary.return_value = {
                "total": 10,
                "matched": 6,
                "needs_review": 2,
                "pending": 1,
                "no_match": 1,
            }
            mock_repo.get_pending_members.return_value = []
            mock_repo.get_matched_members.return_value = []
            mock_repo.close = Mock()
            mock_adapter_class.return_value = mock_repo

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.parliamentary_group_member_status,
                ["--parliamentary-group-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "総件数: 10件" in result.output
            assert "✅ マッチ済: 6件" in result.output
            assert "⚠️  要確認: 2件" in result.output
            assert "📋 未処理: 1件" in result.output
            assert "❌ 該当なし: 1件" in result.output

    def test_parliamentary_group_member_status_with_details(self, runner):
        """Test status command with member details"""
        with patch(
            "src.interfaces.cli.commands.parliamentary_group_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mock with member details
            mock_pending_member = Mock()
            mock_pending_member.extracted_name = "山田太郎"
            mock_pending_member.extracted_role = "団長"
            mock_pending_member.extracted_party_name = "自由民主党"

            mock_matched_member = Mock()
            mock_matched_member.extracted_name = "佐藤花子"
            mock_matched_member.extracted_role = "幹事長"
            mock_matched_member.matching_confidence = 0.95

            mock_repo = MagicMock()
            mock_repo.get_extraction_summary.return_value = {
                "total": 2,
                "matched": 1,
                "needs_review": 0,
                "pending": 1,
                "no_match": 0,
            }
            mock_repo.get_pending_members.return_value = [mock_pending_member]
            mock_repo.get_matched_members.return_value = [mock_matched_member]
            mock_repo.close = Mock()
            mock_adapter_class.return_value = mock_repo

            # Execute
            result = runner.invoke(
                ParliamentaryGroupMemberCommands.parliamentary_group_member_status,
                ["--parliamentary-group-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "山田太郎" in result.output
            assert "団長" in result.output
            assert "佐藤花子" in result.output
            assert "幹事長" in result.output

    def test_invalid_date_format(self, runner):
        """Test invalid date format error"""
        result = runner.invoke(
            ParliamentaryGroupMemberCommands.create_parliamentary_group_affiliations,
            ["--parliamentary-group-id", "1", "--start-date", "invalid-date"],
        )

        assert result.exit_code == 2
        assert "Invalid value for '--start-date'" in result.output
