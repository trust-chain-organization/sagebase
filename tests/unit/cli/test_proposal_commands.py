"""Tests for proposal CLI commands"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.interfaces.cli.commands.proposal_commands import ProposalCommands


class TestProposalCommands:
    """Test cases for proposal CLI commands"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_container(self):
        """Create a mock DI container"""
        container = Mock()
        container.use_cases = Mock()
        container.database = Mock()
        return container

    @pytest.fixture
    def mock_extract_usecase(self):
        """Create a mock extract proposal judges use case"""
        usecase = Mock()
        # Mock extract_judges method
        result = Mock()
        result.extracted_count = 5
        result.judges = [
            Mock(
                extracted_name="山田太郎",
                extracted_party_name="自由民主党",
                extracted_judgment="賛成",
            ),
            Mock(
                extracted_name="佐藤花子",
                extracted_party_name="立憲民主党",
                extracted_judgment="反対",
            ),
        ]
        usecase.extract_judges = AsyncMock(return_value=result)

        # Mock match_judges method
        match_result = Mock()
        match_result.matched_count = 3
        match_result.needs_review_count = 1
        match_result.no_match_count = 1
        match_result.results = [
            Mock(
                matching_status="matched",
                judge_name="山田太郎",
                matched_politician_name="山田太郎",
                confidence_score=0.95,
            ),
            Mock(
                matching_status="needs_review",
                judge_name="佐藤花子",
                matched_politician_name="佐藤花子",
                confidence_score=0.65,
            ),
            Mock(
                matching_status="no_match",
                judge_name="田中一郎",
                matched_politician_name=None,
                confidence_score=0.3,
            ),
        ]
        usecase.match_judges = AsyncMock(return_value=match_result)

        # Mock create_judges method
        create_result = Mock()
        create_result.created_count = 3
        create_result.skipped_count = 0
        create_result.judges = [
            Mock(politician_name="山田太郎", judgment="賛成"),
            Mock(politician_name="佐藤花子", judgment="反対"),
            Mock(politician_name="田中一郎", judgment="賛成"),
        ]
        usecase.create_judges = AsyncMock(return_value=create_result)

        return usecase

    def test_extract_proposal_judges_success(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test successful extraction of proposal judges"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.extract_proposal_judges,
                ["--url", "https://example.com/proposal/123"],
            )

            # Assert
            assert result.exit_code == 0
            assert "📋 議案賛否情報の抽出を開始します（ステップ1/3）" in result.output
            assert "抽出完了: 5件の賛否情報を抽出しました" in result.output
            mock_extract_usecase.extract_judges.assert_awaited_once()

    def test_extract_proposal_judges_with_proposal_id(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test extraction with proposal ID"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.extract_proposal_judges,
                [
                    "--url",
                    "https://example.com/proposal/123",
                    "--proposal-id",
                    "1",
                    "--conference-id",
                    "2",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "抽出完了" in result.output

    def test_extract_proposal_judges_with_force(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test extraction with force flag"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.extract_proposal_judges,
                ["--url", "https://example.com/proposal/123", "--force"],
            )

            # Assert
            assert result.exit_code == 0
            assert "抽出完了" in result.output

    def test_extract_proposal_judges_init_container(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test extraction when container needs initialization"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            with patch(
                "src.interfaces.cli.commands.proposal_commands.init_container"
            ) as mock_init_container:
                # Simulate RuntimeError on first call
                mock_get_container.side_effect = RuntimeError(
                    "Container not initialized"
                )
                mock_init_container.return_value = mock_container
                usecase_attr = mock_container.use_cases
                usecase_attr.extract_proposal_judges_usecase.return_value = (
                    mock_extract_usecase
                )

                # Execute
                result = runner.invoke(
                    ProposalCommands.extract_proposal_judges,
                    ["--url", "https://example.com/proposal/123"],
                )

                # Assert
                assert result.exit_code == 0
                mock_init_container.assert_called_once()

    def test_match_proposal_judges_success(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test successful matching of proposal judges"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(ProposalCommands.match_proposal_judges)

            # Assert
            assert result.exit_code == 0
            assert (
                "🔍 議案賛否情報と政治家のマッチングを開始します（ステップ2/3）"
                in result.output
            )
            assert "マッチング完了" in result.output
            assert "matched=3" in result.output
            assert "needs_review=1" in result.output
            assert "no_match=1" in result.output

    def test_match_proposal_judges_with_proposal_id(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test matching with specific proposal ID"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.match_proposal_judges,
                ["--proposal-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "マッチング完了" in result.output

    def test_match_proposal_judges_with_judge_ids(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test matching with specific judge IDs"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.match_proposal_judges,
                ["--judge-ids", "1", "--judge-ids", "2"],
            )

            # Assert
            assert result.exit_code == 0
            assert "マッチング完了" in result.output

    def test_create_proposal_judges_success(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test successful creation of proposal judges"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(ProposalCommands.create_proposal_judges)

            # Assert
            assert result.exit_code == 0
            assert (
                "✍️ 議案賛否レコードの作成を開始します（ステップ3/3）" in result.output
            )
            assert "作成完了" in result.output
            assert "3件の賛否レコードを作成" in result.output

    def test_create_proposal_judges_with_proposal_id(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test creating judges with specific proposal ID"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.create_proposal_judges,
                ["--proposal-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "作成完了" in result.output

    def test_create_proposal_judges_with_judge_ids(
        self, runner, mock_container, mock_extract_usecase
    ):
        """Test creating judges with specific judge IDs"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            mock_get_container.return_value = mock_container
            mock_container.use_cases.extract_proposal_judges_usecase.return_value = (
                mock_extract_usecase
            )

            # Execute
            result = runner.invoke(
                ProposalCommands.create_proposal_judges,
                ["--judge-ids", "1", "--judge-ids", "2"],
            )

            # Assert
            assert result.exit_code == 0
            assert "作成完了" in result.output

    def test_proposal_judge_status_success(self, runner, mock_container):
        """Test status command"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            # Setup mocks
            mock_session = Mock()

            # Mock extracted judges query
            mock_extracted_result = [
                ("pending", 2),
                ("matched", 3),
                ("needs_review", 1),
                ("no_match", 1),
            ]

            # Mock judges count query
            mock_judges_result = Mock()
            mock_judges_result.fetchone.return_value = (3,)

            mock_session.execute.side_effect = [
                mock_extracted_result,
                mock_judges_result,
            ]
            mock_session.close = Mock()

            mock_container.database.session.return_value = mock_session
            mock_get_container.return_value = mock_container

            # Execute
            result = runner.invoke(ProposalCommands.proposal_judge_status)

            # Assert
            assert result.exit_code == 0
            assert "📊 議案賛否情報の処理状況" in result.output
            assert "合計: 7件" in result.output
            assert "未処理: 2件" in result.output
            assert "マッチ済み: 3件" in result.output
            assert "要確認: 1件" in result.output
            assert "マッチなし: 1件" in result.output
            assert "作成済み賛否レコード: 3件" in result.output

    def test_proposal_judge_status_with_proposal_id(self, runner, mock_container):
        """Test status command with specific proposal ID"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            # Setup mocks
            mock_session = Mock()

            mock_extracted_result = [
                ("pending", 1),
                ("matched", 2),
            ]

            mock_judges_result = Mock()
            mock_judges_result.fetchone.return_value = (2,)

            mock_session.execute.side_effect = [
                mock_extracted_result,
                mock_judges_result,
            ]
            mock_session.close = Mock()

            mock_container.database.session.return_value = mock_session
            mock_get_container.return_value = mock_container

            # Execute
            result = runner.invoke(
                ProposalCommands.proposal_judge_status,
                ["--proposal-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "📊 議案賛否情報の処理状況" in result.output

    def test_proposal_judge_status_with_pending_warning(self, runner, mock_container):
        """Test status command shows warning for pending items"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            # Setup mocks
            mock_session = Mock()

            mock_extracted_result = [
                ("pending", 5),  # Many pending items
            ]

            mock_judges_result = Mock()
            mock_judges_result.fetchone.return_value = (0,)

            mock_session.execute.side_effect = [
                mock_extracted_result,
                mock_judges_result,
            ]
            mock_session.close = Mock()

            mock_container.database.session.return_value = mock_session
            mock_get_container.return_value = mock_container

            # Execute
            result = runner.invoke(ProposalCommands.proposal_judge_status)

            # Assert
            assert result.exit_code == 0
            assert "未処理の賛否情報が5件あります" in result.output
            assert "match-proposal-judges" in result.output

    def test_proposal_judge_status_with_needs_review_warning(
        self, runner, mock_container
    ):
        """Test status command shows warning for needs_review items"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            # Setup mocks
            mock_session = Mock()

            mock_extracted_result = [
                ("matched", 5),
                ("needs_review", 3),
            ]

            mock_judges_result = Mock()
            mock_judges_result.fetchone.return_value = (5,)

            mock_session.execute.side_effect = [
                mock_extracted_result,
                mock_judges_result,
            ]
            mock_session.close = Mock()

            mock_container.database.session.return_value = mock_session
            mock_get_container.return_value = mock_container

            # Execute
            result = runner.invoke(ProposalCommands.proposal_judge_status)

            # Assert
            assert result.exit_code == 0
            assert "3件の" in result.output
            assert "賛否情報が手動確認待ちです" in result.output

    def test_proposal_judge_status_all_complete(self, runner, mock_container):
        """Test status command when all processing is complete"""
        with patch(
            "src.interfaces.cli.commands.proposal_commands.get_container"
        ) as mock_get_container:
            # Setup mocks
            mock_session = Mock()

            mock_extracted_result = [
                ("matched", 5),
            ]

            mock_judges_result = Mock()
            mock_judges_result.fetchone.return_value = (5,)

            mock_session.execute.side_effect = [
                mock_extracted_result,
                mock_judges_result,
            ]
            mock_session.close = Mock()

            mock_container.database.session.return_value = mock_session
            mock_get_container.return_value = mock_container

            # Execute
            result = runner.invoke(ProposalCommands.proposal_judge_status)

            # Assert
            assert result.exit_code == 0
            assert "✨ すべての賛否情報が処理済みです！" in result.output
