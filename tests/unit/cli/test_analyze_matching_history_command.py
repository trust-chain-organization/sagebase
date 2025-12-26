"""Tests for analyze matching history CLI command"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest
from click.testing import CliRunner

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
)
from src.interfaces.cli.commands.analyze_matching_history import (
    AnalyzeMatchingHistoryCommand,
)


class TestAnalyzeMatchingHistoryCommand:
    """Test cases for analyze matching history CLI command"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session"""
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.fixture
    def mock_repo(self):
        """Create a mock LLM processing history repository"""
        repo = Mock()
        return repo

    @pytest.fixture
    def sample_histories(self):
        """Create sample LLM processing histories"""
        now = datetime.now()

        # Completed with match
        history1 = Mock(spec=LLMProcessingHistory)
        history1.id = 1
        history1.created_at = now - timedelta(days=1)
        history1.status = ProcessingStatus.COMPLETED
        history1.result = {
            "matched_id": 123,
            "confidence": 0.95,
            "method": "llm_matching",
        }
        history1.processing_metadata = {"conference_id": 1}
        history1.prompt_variables = {"speaker_name": "山田太郎"}
        history1.started_at = now - timedelta(days=1, hours=1)
        history1.completed_at = now - timedelta(days=1)
        history1.error_message = None

        # Completed without match
        history2 = Mock(spec=LLMProcessingHistory)
        history2.id = 2
        history2.created_at = now - timedelta(days=2)
        history2.status = ProcessingStatus.COMPLETED
        history2.result = {"matched_id": None, "reason": "no_match"}
        history2.processing_metadata = {"conference_id": 1}
        history2.prompt_variables = {"speaker_name": "佐藤花子"}
        history2.started_at = now - timedelta(days=2, hours=1)
        history2.completed_at = now - timedelta(days=2)
        history2.error_message = None

        # Failed
        history3 = Mock(spec=LLMProcessingHistory)
        history3.id = 3
        history3.created_at = now - timedelta(days=3)
        history3.status = ProcessingStatus.FAILED
        history3.result = None
        history3.processing_metadata = {"conference_id": 2}
        history3.prompt_variables = {"speaker_name": "田中一郎"}
        history3.started_at = now - timedelta(days=3, hours=1)
        history3.completed_at = None
        history3.error_message = "API rate limit exceeded"

        # Completed with low confidence
        history4 = Mock(spec=LLMProcessingHistory)
        history4.id = 4
        history4.created_at = now - timedelta(days=4)
        history4.status = ProcessingStatus.COMPLETED
        history4.result = {
            "matched_id": 456,
            "confidence": 0.65,
            "method": "rule_based",
        }
        history4.processing_metadata = {"conference_id": 1}
        history4.prompt_variables = {"speaker_name": "鈴木美咲"}
        history4.started_at = now - timedelta(days=4, hours=1)
        history4.completed_at = now - timedelta(days=4)
        history4.error_message = None

        return [history1, history2, history3, history4]

    def test_analyze_matching_history_basic(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test basic analyze matching history command"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--days", "30"],
                )

                # Assert
                assert result.exit_code == 0
                assert "Speaker Matching History Analysis" in result.output
                assert "Overall Statistics" in result.output
                assert "Total Processings: 4" in result.output
                assert "Completed: 3" in result.output
                assert "Failed: 1" in result.output
                mock_repo.get_by_processing_type.assert_awaited_once()

    def test_analyze_matching_history_with_conference_filter(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test analyze with conference ID filter"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute with conference filter
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--conference-id", "1"],
                )

                # Assert - should only show 3 records (conference_id=1)
                assert result.exit_code == 0
                assert "Conference ID: 1" in result.output
                assert "Total Processings: 3" in result.output

    def test_analyze_matching_history_completed_status_filter(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test analyze with completed status filter"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute with status filter
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--status", "completed"],
                )

                # Assert - should only show completed records
                assert result.exit_code == 0
                assert "Total Processings: 3" in result.output
                assert "Completed: 3 (100.0%)" in result.output

    def test_analyze_matching_history_failed_status_filter(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test analyze with failed status filter"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute with status filter
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--status", "failed"],
                )

                # Assert - should only show failed records
                assert result.exit_code == 0
                assert "Total Processings: 1" in result.output

    def test_analyze_matching_history_no_results(self, runner, mock_session, mock_repo):
        """Test analyze when no matching history found"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks with empty results
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--days", "30"],
                )

                # Assert
                assert result.exit_code == 0
                assert "No matching history found" in result.output

    def test_analyze_matching_history_with_csv_export(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test analyze with CSV export"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                with patch("builtins.open", mock_open()) as mock_file:
                    with patch("os.makedirs") as mock_makedirs:
                        # Setup mocks
                        mock_get_session.return_value = mock_session
                        mock_repo.get_by_processing_type = AsyncMock(
                            return_value=sample_histories
                        )
                        mock_repo_class.return_value = mock_repo

                        # Execute with CSV export
                        result = runner.invoke(
                            AnalyzeMatchingHistoryCommand.analyze_matching_history,
                            ["--export-csv", "test_results.csv"],
                        )

                        # Assert
                        assert result.exit_code == 0
                        assert "Results exported to test_results.csv" in result.output
                        mock_file.assert_called_once()
                        mock_makedirs.assert_called_once()

    def test_analyze_matching_history_shows_confidence_distribution(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test that confidence distribution is displayed"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--days", "30"],
                )

                # Assert
                assert result.exit_code == 0
                assert "Confidence Distribution" in result.output
                assert "Average Confidence" in result.output
                assert "High (≥0.9)" in result.output
                assert "Medium (0.7-0.9)" in result.output
                assert "Low (<0.7)" in result.output

    def test_analyze_matching_history_shows_matching_methods(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test that matching methods are displayed"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--days", "30"],
                )

                # Assert
                assert result.exit_code == 0
                assert "Matching Methods" in result.output
                assert "llm_matching" in result.output or "rule_based" in result.output

    def test_analyze_matching_history_shows_failure_patterns(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test that failure patterns are displayed"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--days", "30"],
                )

                # Assert
                assert result.exit_code == 0
                assert "Failure Patterns" in result.output
                assert (
                    "API rate limit exceeded" in result.output
                    or "no_match" in result.output
                )

    def test_analyze_matching_history_shows_recommendations(
        self, runner, mock_session, mock_repo, sample_histories
    ):
        """Test that recommendations are displayed"""
        with patch(
            "src.infrastructure.config.async_database.get_async_session"
        ) as mock_get_session:
            with patch(
                "src.infrastructure.persistence.LLMProcessingHistoryRepositoryImpl"
            ) as mock_repo_class:
                # Setup mocks
                mock_get_session.return_value = mock_session
                mock_repo.get_by_processing_type = AsyncMock(
                    return_value=sample_histories
                )
                mock_repo_class.return_value = mock_repo

                # Execute
                result = runner.invoke(
                    AnalyzeMatchingHistoryCommand.analyze_matching_history,
                    ["--days", "30"],
                )

                # Assert
                assert result.exit_code == 0
                assert "Recommendations" in result.output
