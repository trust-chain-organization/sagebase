"""Tests for conference member CLI commands"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.interfaces.cli.commands.conference_member_commands import (
    ConferenceMemberCommands,
)


class TestConferenceMemberCommands:
    """Test cases for conference member CLI commands"""

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

    def test_extract_conference_members_success(self, runner, mock_progress):
        """Test successful extraction of conference members"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.conference_member_commands.ConferenceMemberExtractor"
            ) as mock_extractor_class:
                # Setup mocks
                mock_conf_repo = MagicMock()
                mock_conf_repo.get_conference_by_id.return_value = {
                    "id": 1,
                    "name": "本会議",
                    "members_introduction_url": "https://example.com/members",
                }
                mock_conf_repo.close = Mock()

                mock_member_repo = MagicMock()
                mock_member_repo.get_extraction_summary.return_value = {
                    "total": 5,
                    "pending": 0,
                    "matched": 5,
                    "no_match": 0,
                    "needs_review": 0,
                }
                mock_member_repo.close = Mock()

                # Set up RepositoryAdapter to return different repos based on the type
                def adapter_side_effect(impl_class):
                    # Check ExtractedConferenceMember first (contains "Conference")
                    if "ExtractedConferenceMember" in impl_class.__name__:
                        return mock_member_repo
                    elif "Conference" in impl_class.__name__:
                        return mock_conf_repo
                    return MagicMock()

                mock_adapter_class.side_effect = adapter_side_effect

                mock_extractor = Mock()
                mock_extractor.extract_and_save_members = AsyncMock(
                    return_value={
                        "extracted_count": 5,
                        "saved_count": 5,
                        "failed_count": 0,
                    }
                )
                mock_extractor.close = Mock()
                mock_extractor_class.return_value = mock_extractor

                # Execute
                result = runner.invoke(
                    ConferenceMemberCommands.extract_conference_members,
                    ["--conference-id", "1"],
                )

                # Assert
                assert result.exit_code == 0
                assert (
                    "📋 会議体メンバー情報の抽出を開始します（ステップ1/3）"
                    in result.output
                )
                assert "=== 抽出完了 ===" in result.output
                assert "✅ 抽出総数: 5人" in result.output
                assert "✅ 保存総数: 5人" in result.output
                mock_extractor.extract_and_save_members.assert_called_once()

    def test_extract_conference_members_with_force(self, runner, mock_progress):
        """Test extraction with force flag"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            with patch(
                "src.interfaces.cli.commands.conference_member_commands.ConferenceMemberExtractor"
            ) as mock_extractor_class:
                # Setup mocks
                mock_conf_repo = Mock()
                mock_conf_repo.get_conference_by_id.return_value = {
                    "id": 1,
                    "name": "本会議",
                    "members_introduction_url": "https://example.com/members",
                }
                mock_conf_repo.close = Mock()

                mock_member_repo = Mock()
                # Ensure delete_extracted_members returns an integer, not a Mock
                mock_member_repo.delete_extracted_members = Mock(return_value=2)
                mock_member_repo.get_extraction_summary.return_value = {
                    "total": 3,
                    "pending": 0,
                    "matched": 3,
                    "no_match": 0,
                    "needs_review": 0,
                }
                mock_member_repo.close = Mock()

                # Set up RepositoryAdapter to return different repos based on the type
                def adapter_side_effect(impl_class):
                    # Check ExtractedConferenceMember first (contains "Conference")
                    if "ExtractedConferenceMember" in impl_class.__name__:
                        return mock_member_repo
                    elif "Conference" in impl_class.__name__:
                        return mock_conf_repo
                    return Mock()

                mock_adapter_class.side_effect = adapter_side_effect

                mock_extractor = Mock()
                mock_extractor.extract_and_save_members = AsyncMock(
                    return_value={
                        "extracted_count": 3,
                        "saved_count": 3,
                        "failed_count": 0,
                    }
                )
                mock_extractor.close = Mock()
                mock_extractor_class.return_value = mock_extractor

                # Execute with --force
                result = runner.invoke(
                    ConferenceMemberCommands.extract_conference_members,
                    ["--conference-id", "1", "--force"],
                )

                # Assert
                assert result.exit_code == 0
                assert "既存の抽出データ2件を削除しました" in result.output
                mock_member_repo.delete_extracted_members.assert_called_once_with(1)
                mock_extractor.extract_and_save_members.assert_called_once()

    def test_match_conference_members_success(self, runner, mock_progress):
        """Test successful matching of conference members"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.ConferenceMemberCommands._create_manage_members_usecase"
        ) as mock_usecase_creator:
            # Setup mocks
            mock_usecase = Mock()
            mock_usecase.match_members = AsyncMock(
                return_value={
                    "total": 5,
                    "matched": 3,
                    "needs_review": 1,
                    "no_match": 1,
                    "error": 0,
                }
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute
            result = runner.invoke(
                ConferenceMemberCommands.match_conference_members,
                ["--conference-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "🔍 議員情報のマッチングを開始します（ステップ2/3）" in result.output
            assert "=== マッチング完了 ===" in result.output
            assert "処理総数: 5件" in result.output
            assert "✅ マッチ成功: 3件" in result.output
            assert "⚠️  要確認: 1件" in result.output
            assert "❌ 該当なし: 1件" in result.output

    def test_match_conference_members_no_conference_id(self, runner, mock_progress):
        """Test matching without conference_id (processes all)"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.ConferenceMemberCommands._create_manage_members_usecase"
        ) as mock_usecase_creator:
            # Setup mocks
            mock_usecase = Mock()
            mock_usecase.match_members = AsyncMock(
                return_value={
                    "total": 10,
                    "matched": 8,
                    "needs_review": 1,
                    "no_match": 1,
                    "error": 0,
                }
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute without conference-id
            result = runner.invoke(ConferenceMemberCommands.match_conference_members)

            # Assert
            assert result.exit_code == 0
            assert "🔍 議員情報のマッチングを開始します（ステップ2/3）" in result.output
            mock_usecase.match_members.assert_called_once_with(None)

    def test_create_affiliations_success(self, runner, mock_progress):
        """Test successful creation of affiliations"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.ConferenceMemberCommands._create_manage_members_usecase"
        ) as mock_usecase_creator:
            # Setup mocks
            mock_usecase = Mock()
            mock_usecase.create_affiliations = AsyncMock(
                return_value={
                    "total": 3,
                    "created": 3,
                    "failed": 0,
                }
            )
            mock_usecase_creator.return_value = mock_usecase

            # Execute
            result = runner.invoke(
                ConferenceMemberCommands.create_affiliations,
                ["--conference-id", "1", "--start-date", "2024-01-01"],
            )

            # Assert
            assert result.exit_code == 0
            assert "🏛️ 政治家所属情報の作成を開始します（ステップ3/3）" in result.output
            assert "=== 所属情報作成完了 ===" in result.output
            assert "処理総数: 3件" in result.output
            assert "✅ 作成/更新: 3件" in result.output

    def test_create_affiliations_with_default_date(self, runner, mock_progress):
        """Test creating affiliations with default date (today)"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.ConferenceMemberCommands._create_manage_members_usecase"
        ) as mock_usecase_creator:
            with patch(
                "src.interfaces.cli.commands.conference_member_commands.date"
            ) as mock_date:
                # Mock today's date
                mock_date.today.return_value = date(2024, 3, 15)
                mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

                # Setup mocks
                mock_usecase = Mock()
                mock_usecase.create_affiliations = AsyncMock(
                    return_value={
                        "total": 1,
                        "created": 1,
                        "failed": 0,
                    }
                )
                mock_usecase_creator.return_value = mock_usecase

                # Execute without start-date
                result = runner.invoke(
                    ConferenceMemberCommands.create_affiliations,
                    ["--conference-id", "1"],
                )

                # Assert
                assert result.exit_code == 0
                # Check that today's date was used
                mock_usecase.create_affiliations.assert_called_once_with(
                    1, date(2024, 3, 15)
                )

    def test_member_status_success(self, runner):
        """Test member status command"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mocks
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
                ConferenceMemberCommands.member_status, ["--conference-id", "1"]
            )

            # Assert
            assert result.exit_code == 0
            assert "総件数: 10件" in result.output
            assert "✅ マッチ済: 6件" in result.output
            assert "⚠️  要確認: 2件" in result.output
            assert "📋 未処理: 1件" in result.output
            assert "❌ 該当なし: 1件" in result.output

    def test_extract_conference_members_error(self, runner):
        """Test extraction error handling"""
        with patch(
            "src.interfaces.cli.commands.conference_member_commands.RepositoryAdapter"
        ) as mock_adapter_class:
            # Setup mock conference repo that returns None
            mock_conf_repo = MagicMock()
            mock_conf_repo.get_conference_by_id.return_value = None
            mock_conf_repo.close = Mock()
            mock_adapter_class.return_value = mock_conf_repo

            # Execute
            result = runner.invoke(
                ConferenceMemberCommands.extract_conference_members,
                ["--conference-id", "999"],
            )

            # Assert
            assert (
                result.exit_code == 0
            )  # Command returns normally after printing error
            assert "会議体ID 999 が見つかりません" in result.output

    def test_invalid_date_format(self, runner):
        """Test invalid date format error"""
        result = runner.invoke(
            ConferenceMemberCommands.create_affiliations,
            ["--conference-id", "1", "--start-date", "invalid-date"],
        )

        assert result.exit_code == 2
        assert "Invalid value for '--start-date'" in result.output
