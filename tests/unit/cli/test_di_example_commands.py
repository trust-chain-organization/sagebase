"""Tests for DI example CLI commands"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.interfaces.cli.commands.di_example_commands import (
    health_check_with_di,
    process_minutes_with_di,
    scrape_politicians_with_di,
    show_container_info,
)


class TestDIExampleCommands:
    """Test cases for DI example CLI commands"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_container(self):
        """Create a mock DI container"""
        container = Mock()
        container.use_cases = Mock()
        container.repositories = Mock()
        container.services = Mock()
        container.database = Mock()
        container.config = Mock(
            return_value={
                "database_url": "postgresql://localhost:5432/test",
                "llm_model": "gemini-2.0-flash",
                "llm_temperature": 0.0,
                "gcs_bucket_name": "test-bucket",
            }
        )
        return container

    def test_process_minutes_with_di_success(self, runner, mock_container):
        """Test successful processing of minutes with DI"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            mock_usecase = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_result.conversation_count = 10
            mock_result.speaker_count = 5
            mock_usecase.execute = AsyncMock(return_value=mock_result)

            mock_container.use_cases.process_minutes_usecase.return_value = mock_usecase
            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(
                process_minutes_with_di,
                ["--meeting-id", "1", "--environment", "testing"],
            )

            # Assert
            assert result.exit_code == 0
            assert "✅ Successfully processed meeting 1" in result.output
            assert "Conversations created: 10" in result.output
            assert "Speakers extracted: 5" in result.output

    def test_process_minutes_with_di_failure(self, runner, mock_container):
        """Test processing failure with DI"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            mock_usecase = Mock()
            mock_result = Mock()
            mock_result.success = False
            mock_result.error_message = "Database connection failed"
            mock_usecase.execute = AsyncMock(return_value=mock_result)

            mock_container.use_cases.process_minutes_usecase.return_value = mock_usecase
            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(
                process_minutes_with_di,
                ["--meeting-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "❌ Failed to process meeting 1" in result.output
            assert "Error: Database connection failed" in result.output

    def test_process_minutes_with_di_exception(self, runner):
        """Test exception handling in process_minutes_with_di"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock to raise exception
            mock_init.side_effect = Exception("Container initialization failed")

            # Execute
            result = runner.invoke(
                process_minutes_with_di,
                ["--meeting-id", "1"],
            )

            # Assert
            assert result.exit_code == 1
            assert "Error: Container initialization failed" in result.output

    def test_scrape_politicians_with_di_success_single_party(
        self, runner, mock_container
    ):
        """Test successful scraping of politicians with DI for single party"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.ApplicationContainer.create_for_environment"
        ) as mock_create:
            # Setup mock
            mock_usecase = Mock()
            mock_result = [
                Mock(name="山田太郎"),
                Mock(name="佐藤花子"),
            ]
            mock_usecase.execute = AsyncMock(return_value=mock_result)

            mock_container.use_cases.scrape_politicians_usecase.return_value = (
                mock_usecase
            )
            mock_create.return_value = mock_container

            # Execute
            result = runner.invoke(
                scrape_politicians_with_di,
                ["--party-id", "1"],
            )

            # Assert
            assert result.exit_code == 0
            assert "✅ Party 1: 2 politicians processed" in result.output

    def test_scrape_politicians_with_di_success_all_parties(
        self, runner, mock_container
    ):
        """Test successful scraping of all parties with DI"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.ApplicationContainer.create_for_environment"
        ) as mock_create:
            # Setup mock
            mock_usecase = Mock()
            mock_result = [Mock(name="山田太郎")]
            mock_usecase.execute = AsyncMock(return_value=mock_result)

            # Mock party repository
            mock_party1 = Mock()
            mock_party1.id = 1
            mock_party1.members_list_url = "https://example.com/party1"

            mock_party2 = Mock()
            mock_party2.id = 2
            mock_party2.members_list_url = "https://example.com/party2"

            mock_party_repo = Mock()
            mock_party_repo.find_all = AsyncMock(
                return_value=[mock_party1, mock_party2]
            )

            mock_container.use_cases.scrape_politicians_usecase.return_value = (
                mock_usecase
            )
            mock_container.repositories.political_party_repository.return_value = (
                mock_party_repo
            )
            mock_create.return_value = mock_container

            # Execute
            result = runner.invoke(
                scrape_politicians_with_di,
                ["--all-parties"],
            )

            # Assert
            assert result.exit_code == 0
            assert "✅ Party 1: 1 politicians processed" in result.output
            assert "✅ Party 2: 1 politicians processed" in result.output

    def test_scrape_politicians_with_di_dry_run(self, runner, mock_container):
        """Test dry run mode for scraping politicians"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.ApplicationContainer.create_for_environment"
        ) as mock_create:
            # Setup mock
            mock_usecase = Mock()
            mock_result = [Mock(name="山田太郎")]
            mock_usecase.execute = AsyncMock(return_value=mock_result)

            mock_container.use_cases.scrape_politicians_usecase.return_value = (
                mock_usecase
            )
            mock_create.return_value = mock_container

            # Execute
            result = runner.invoke(
                scrape_politicians_with_di,
                ["--party-id", "1", "--dry-run"],
            )

            # Assert
            assert result.exit_code == 0
            assert "✅ Party 1: 1 politicians processed" in result.output

    def test_scrape_politicians_with_di_no_arguments(self, runner):
        """Test scraping without required arguments"""
        result = runner.invoke(scrape_politicians_with_di, [])

        # Assert
        assert result.exit_code == 1
        assert "Specify either --party-id or --all-parties" in result.output

    def test_scrape_politicians_with_di_exception(self, runner):
        """Test exception handling in scrape_politicians_with_di"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.ApplicationContainer.create_for_environment"
        ) as mock_create:
            # Setup mock to raise exception
            mock_create.side_effect = Exception("Container creation failed")

            # Execute
            result = runner.invoke(
                scrape_politicians_with_di,
                ["--party-id", "1"],
            )

            # Assert
            assert result.exit_code == 1
            assert "Error: Container creation failed" in result.output

    def test_show_container_info_success(self, runner, mock_container):
        """Test showing container information"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            # Mock repositories
            mock_container.repositories.politician_repository = Mock()
            mock_container.repositories.meeting_repository = Mock()

            # Mock services
            mock_container.services.llm_service = Mock()
            mock_container.services.storage_service = Mock()

            # Mock use cases
            mock_container.use_cases.process_minutes_usecase = Mock()
            mock_container.use_cases.scrape_politicians_usecase = Mock()

            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(show_container_info, [])

            # Assert
            assert result.exit_code == 0
            assert "DI Container Information" in result.output
            assert "📋 Configuration:" in result.output
            assert "Database URL" in result.output
            assert "LLM Model" in result.output
            assert "🔧 Available Providers:" in result.output
            assert "Repositories" in result.output
            assert "Services" in result.output
            assert "Use Cases" in result.output
            assert "✅ Container initialized successfully" in result.output

    def test_show_container_info_exception(self, runner):
        """Test exception handling in show_container_info"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock to raise exception
            mock_init.side_effect = Exception("Initialization failed")

            # Execute
            result = runner.invoke(show_container_info, [])

            # Assert
            assert result.exit_code == 1
            assert "❌ Error initializing container" in result.output

    def test_health_check_with_di_all_healthy(self, runner, mock_container):
        """Test health check when all systems are healthy"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            mock_session = Mock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)

            mock_container.get_session_context.return_value = mock_session
            mock_container.services.llm_service.return_value = Mock()
            mock_container.services.storage_service.return_value = Mock()

            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(health_check_with_di, [])

            # Assert
            assert result.exit_code == 0
            assert "🏥 Health Check Results" in result.output
            assert "✅ Database: Healthy" in result.output
            assert "✅ LLM Service: Configured" in result.output
            assert "✅ Storage Service: Configured" in result.output
            assert "✅ All systems operational" in result.output

    def test_health_check_with_di_check_db_only(self, runner, mock_container):
        """Test health check for database only"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            mock_session = Mock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)

            mock_container.get_session_context.return_value = mock_session
            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(health_check_with_di, ["--check-db"])

            # Assert
            assert result.exit_code == 0
            assert "✅ Database: Healthy" in result.output

    def test_health_check_with_di_database_unhealthy(self, runner, mock_container):
        """Test health check when database is unhealthy"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Connection failed")
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)

            mock_container.get_session_context.return_value = mock_session
            mock_container.services.llm_service.return_value = Mock()
            mock_container.services.storage_service.return_value = Mock()

            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(health_check_with_di, [])

            # Assert
            assert result.exit_code == 1
            assert "❌ Database: Unhealthy" in result.output
            assert "⚠️ Some systems need attention" in result.output

    def test_health_check_with_di_llm_unconfigured(self, runner, mock_container):
        """Test health check when LLM service is not configured"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock
            mock_session = Mock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            mock_session.__enter__ = Mock(return_value=mock_session)
            mock_session.__exit__ = Mock(return_value=None)

            mock_container.get_session_context.return_value = mock_session
            mock_container.services.llm_service.side_effect = Exception(
                "Not configured"
            )
            mock_container.services.storage_service.return_value = Mock()

            mock_init.return_value = mock_container

            # Execute
            result = runner.invoke(health_check_with_di, [])

            # Assert
            assert result.exit_code == 1
            assert "❌ LLM Service: Not configured" in result.output
            assert "⚠️ Some systems need attention" in result.output

    def test_health_check_with_di_exception(self, runner):
        """Test exception handling in health_check_with_di"""
        with patch(
            "src.interfaces.cli.commands.di_example_commands.init_container"
        ) as mock_init:
            # Setup mock to raise exception
            mock_init.side_effect = Exception("Health check failed")

            # Execute
            result = runner.invoke(health_check_with_di, [])

            # Assert
            assert result.exit_code == 1
            assert "❌ Health check failed" in result.output
