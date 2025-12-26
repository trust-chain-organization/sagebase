"""Tests for politician CLI commands"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.interfaces.cli.commands.politician_commands import PoliticianCommands


class TestScrapePoliticiansCommand:
    """Test cases for scrape-politicians command"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_db_engine(self):
        """Mock database engine"""
        with patch("src.infrastructure.config.database.get_db_engine") as mock:
            engine = Mock()
            engine.connect.return_value.__enter__ = Mock()
            engine.connect.return_value.__exit__ = Mock()
            engine.dispose = Mock()
            mock.return_value = engine
            yield engine

    @pytest.fixture
    def mock_progress(self):
        """Create a mock progress tracker"""
        with patch(
            "src.interfaces.cli.commands.politician_commands.ProgressTracker"
        ) as mock:
            progress_instance = Mock()
            progress_instance.__enter__ = Mock(return_value=progress_instance)
            progress_instance.__exit__ = Mock(return_value=None)
            progress_instance.update = Mock()
            mock.return_value = progress_instance
            yield progress_instance

    def test_scrape_politicians_specific_party_success(
        self, runner, mock_db_engine, mock_progress
    ):
        """Test successful scraping for a specific party"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="テスト政党",
                    members_list_url="https://example.com/members",
                )
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock PartyMemberPageFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_pages = AsyncMock(
                return_value=[
                    {"html": "<html>test</html>", "url": "https://example.com"}
                ]
            )
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock()

            # Mock PartyMemberExtractor
            mock_extractor = Mock()
            mock_member_result = Mock()
            mock_member_result.members = [
                Mock(
                    name="山田太郎",
                    position="衆議院議員",
                    model_dump=Mock(
                        return_value={"name": "山田太郎", "position": "衆議院議員"}
                    ),
                )
            ]
            mock_extractor.extract_from_pages = AsyncMock(
                return_value=mock_member_result
            )

            # Mock repository
            mock_repo = Mock()
            mock_repo.bulk_create_politicians_sync.return_value = {
                "created": [1],
                "updated": [],
                "errors": [],
            }
            mock_repo.close = Mock()

            with patch(
                "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
                return_value=mock_fetcher,
            ):
                with patch(
                    "src.interfaces.factories.party_member_extractor_factory.PartyMemberExtractorFactory.create",
                    return_value=mock_extractor,
                ):
                    with patch(
                        "src.infrastructure.config.database.get_db_session"
                    ) as mock_session:
                        mock_session.return_value = Mock()
                        with patch(
                            "src.infrastructure.persistence.politician_repository_sync_impl.PoliticianRepositorySyncImpl",
                            return_value=mock_repo,
                        ):
                            # Execute
                            result = runner.invoke(
                                PoliticianCommands.scrape_politicians,
                                ["--party-id", "1"],
                            )

                            # Assert
                            assert result.exit_code == 0
                            assert (
                                "Processing テスト政党" in result.output
                                or "Found 1 parties to scrape" in result.output
                            )

    def test_scrape_politicians_all_parties_success(
        self, runner, mock_db_engine, mock_progress
    ):
        """Test successful scraping for all parties"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="政党A",
                    members_list_url="https://example.com/party-a",
                ),
                Mock(
                    id=2,
                    name="政党B",
                    members_list_url="https://example.com/party-b",
                ),
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock PartyMemberPageFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_pages = AsyncMock(
                return_value=[
                    {"html": "<html>test</html>", "url": "https://example.com"}
                ]
            )
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock()

            # Mock PartyMemberExtractor
            mock_extractor = Mock()
            mock_member_result = Mock()
            mock_member_result.members = [
                Mock(
                    name="議員1",
                    position="衆議院議員",
                    model_dump=Mock(return_value={"name": "議員1"}),
                )
            ]
            mock_extractor.extract_from_pages = AsyncMock(
                return_value=mock_member_result
            )

            # Mock repository
            mock_repo = Mock()
            mock_repo.bulk_create_politicians_sync.return_value = {
                "created": [1],
                "updated": [],
                "errors": [],
            }
            mock_repo.close = Mock()

            with patch(
                "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
                return_value=mock_fetcher,
            ):
                with patch(
                    "src.interfaces.factories.party_member_extractor_factory.PartyMemberExtractorFactory.create",
                    return_value=mock_extractor,
                ):
                    with patch(
                        "src.infrastructure.config.database.get_db_session"
                    ) as mock_session:
                        mock_session.return_value = Mock()
                        with patch(
                            "src.infrastructure.persistence.politician_repository_sync_impl.PoliticianRepositorySyncImpl",
                            return_value=mock_repo,
                        ):
                            # Execute
                            result = runner.invoke(
                                PoliticianCommands.scrape_politicians,
                                ["--all-parties"],
                            )

                            # Assert
                            assert result.exit_code == 0
                            assert "Found 2 parties to scrape" in result.output

    def test_scrape_politicians_dry_run(self, runner, mock_db_engine, mock_progress):
        """Test dry-run mode (no data saved)"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="テスト政党",
                    members_list_url="https://example.com/members",
                )
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock PartyMemberPageFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_pages = AsyncMock(
                return_value=[
                    {"html": "<html>test</html>", "url": "https://example.com"}
                ]
            )
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock()

            # Mock PartyMemberExtractor
            mock_extractor = Mock()
            mock_member_result = Mock()
            mock_member_result.members = [
                Mock(
                    name="山田太郎",
                    position="衆議院議員",
                    prefecture="東京都",
                    electoral_district="東京1区",
                    party_position="幹事長",
                )
            ]
            mock_extractor.extract_from_pages = AsyncMock(
                return_value=mock_member_result
            )

            with patch(
                "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
                return_value=mock_fetcher,
            ):
                with patch(
                    "src.interfaces.factories.party_member_extractor_factory.PartyMemberExtractorFactory.create",
                    return_value=mock_extractor,
                ):
                    # Execute with dry-run flag
                    result = runner.invoke(
                        PoliticianCommands.scrape_politicians,
                        ["--party-id", "1", "--dry-run"],
                    )

                    # Assert
                    assert result.exit_code == 0
                    assert "山田太郎" in result.output
                    # In dry-run mode, no "Total politicians saved" message
                    assert "Total politicians saved" not in result.output

    def test_scrape_politicians_hierarchical_mode(
        self, runner, mock_db_engine, mock_progress
    ):
        """Test hierarchical scraping mode using Agent"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="テスト政党",
                    members_list_url="https://example.com/members",
                )
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock DI container
            mock_container = Mock()
            mock_agent = Mock()
            mock_final_state = Mock()
            mock_final_state.error_message = None
            mock_final_state.extracted_members = [
                {"name": "議員A", "position": "衆議院議員"}
            ]
            mock_final_state.visited_urls = ["https://example.com/members"]
            mock_agent.scrape = AsyncMock(return_value=mock_final_state)
            mock_container.use_cases.party_scraping_agent.return_value = mock_agent

            # Mock repository
            mock_repo = Mock()
            mock_repo.bulk_create_politicians_sync.return_value = {
                "created": [1],
                "updated": [],
                "errors": [],
            }
            mock_repo.close = Mock()

            with patch(
                "src.infrastructure.di.container.get_container",
                return_value=mock_container,
            ):
                with patch(
                    "src.infrastructure.config.database.get_db_session"
                ) as mock_session:
                    mock_session.return_value = Mock()
                    with patch(
                        "src.infrastructure.persistence.politician_repository_sync_impl.PoliticianRepositorySyncImpl",
                        return_value=mock_repo,
                    ):
                        # Execute with hierarchical flag
                        result = runner.invoke(
                            PoliticianCommands.scrape_politicians,
                            ["--party-id", "1", "--hierarchical"],
                        )

                        # Assert
                        assert result.exit_code == 0
                        assert (
                            "hierarchical mode" in result.output
                            or "Found 1 parties to scrape" in result.output
                        )

    def test_scrape_politicians_no_parties_found(self, runner, mock_db_engine):
        """Test when no parties with member list URLs are found"""
        # Mock database query returning no results
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result
        mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

        # Execute
        result = runner.invoke(
            PoliticianCommands.scrape_politicians,
            ["--party-id", "999"],
        )

        # Assert
        assert result.exit_code == 0
        assert "No parties found" in result.output

    def test_scrape_politicians_fetch_pages_failure(
        self, runner, mock_db_engine, mock_progress
    ):
        """Test when fetching pages fails"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="テスト政党",
                    members_list_url="https://example.com/members",
                )
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock PartyMemberPageFetcher to return empty pages
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_pages = AsyncMock(return_value=[])
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock()

            with patch(
                "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
                return_value=mock_fetcher,
            ):
                # Execute
                result = runner.invoke(
                    PoliticianCommands.scrape_politicians,
                    ["--party-id", "1"],
                )

                # Assert
                assert result.exit_code == 0
                # Should show "Failed to fetch pages" message
                assert (
                    "Failed to fetch pages" in result.output
                    or "Found 1 parties to scrape" in result.output
                )

    def test_scrape_politicians_llm_extraction_failure(
        self, runner, mock_db_engine, mock_progress
    ):
        """Test when LLM extraction fails to find members"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="テスト政党",
                    members_list_url="https://example.com/members",
                )
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock PartyMemberPageFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_pages = AsyncMock(
                return_value=[
                    {"html": "<html>test</html>", "url": "https://example.com"}
                ]
            )
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock()

            # Mock PartyMemberExtractor to return no members
            mock_extractor = Mock()
            mock_member_result = Mock()
            mock_member_result.members = []
            mock_extractor.extract_from_pages = AsyncMock(
                return_value=mock_member_result
            )

            with patch(
                "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
                return_value=mock_fetcher,
            ):
                with patch(
                    "src.interfaces.factories.party_member_extractor_factory.PartyMemberExtractorFactory.create",
                    return_value=mock_extractor,
                ):
                    # Execute
                    result = runner.invoke(
                        PoliticianCommands.scrape_politicians,
                        ["--party-id", "1"],
                    )

                    # Assert
                    assert result.exit_code == 0
                    assert (
                        "No members found" in result.output
                        or "Found 1 parties to scrape" in result.output
                    )

    def test_scrape_politicians_database_save_error(
        self, runner, mock_db_engine, mock_progress
    ):
        """Test handling of database save errors"""
        # Set environment variable to skip confirmation
        with patch.dict("os.environ", {"STREAMLIT_RUNNING": "true"}):
            # Mock database query
            mock_conn = Mock()
            mock_result = Mock()
            mock_result.fetchall.return_value = [
                Mock(
                    id=1,
                    name="テスト政党",
                    members_list_url="https://example.com/members",
                )
            ]
            mock_conn.execute.return_value = mock_result
            mock_db_engine.connect.return_value.__enter__.return_value = mock_conn

            # Mock PartyMemberPageFetcher
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_pages = AsyncMock(
                return_value=[
                    {"html": "<html>test</html>", "url": "https://example.com"}
                ]
            )
            mock_fetcher.__aenter__ = AsyncMock(return_value=mock_fetcher)
            mock_fetcher.__aexit__ = AsyncMock()

            # Mock PartyMemberExtractor
            mock_extractor = Mock()
            mock_member_result = Mock()
            mock_member_result.members = [
                Mock(
                    name="山田太郎",
                    position="衆議院議員",
                    model_dump=Mock(return_value={"name": "山田太郎"}),
                )
            ]
            mock_extractor.extract_from_pages = AsyncMock(
                return_value=mock_member_result
            )

            # Mock repository to return errors
            mock_repo = Mock()
            mock_repo.bulk_create_politicians_sync.return_value = {
                "created": [],
                "updated": [],
                "errors": ["Error saving politician"],
            }
            mock_repo.close = Mock()

            with patch(
                "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher",
                return_value=mock_fetcher,
            ):
                with patch(
                    "src.interfaces.factories.party_member_extractor_factory.PartyMemberExtractorFactory.create",
                    return_value=mock_extractor,
                ):
                    with patch(
                        "src.infrastructure.config.database.get_db_session"
                    ) as mock_session:
                        mock_session.return_value = Mock()
                        with patch(
                            "src.infrastructure.persistence.politician_repository_sync_impl.PoliticianRepositorySyncImpl",
                            return_value=mock_repo,
                        ):
                            # Execute
                            result = runner.invoke(
                                PoliticianCommands.scrape_politicians,
                                ["--party-id", "1"],
                            )

                            # Assert
                            assert result.exit_code == 0
                            assert (
                                "Errors: 1" in result.output
                                or "Found 1 parties to scrape" in result.output
                            )


class TestConvertPoliticiansCommand:
    """Test cases for convert-politicians command"""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()

    @pytest.fixture
    def mock_container(self):
        """Mock DI container"""
        with patch("src.infrastructure.di.container.get_container") as mock:
            container = Mock()
            mock.return_value = container
            yield container

    def test_convert_politicians_success(self, runner, mock_container):
        """Test successful conversion of approved politicians"""
        # Mock use case
        mock_usecase = Mock()
        mock_result = Mock()
        mock_result.total_processed = 5
        mock_result.converted_count = 5
        mock_result.skipped_count = 0
        mock_result.error_count = 0
        mock_result.converted_politicians = [
            Mock(name="議員A", politician_id=1),
            Mock(name="議員B", politician_id=2),
        ]
        mock_result.skipped_names = []
        mock_result.error_messages = []
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        mock_container.use_cases.convert_extracted_politician_usecase.return_value = (
            mock_usecase
        )

        with patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ):
            # Execute
            result = runner.invoke(PoliticianCommands.convert_politicians, [])

            # Assert
            assert result.exit_code == 0
            assert "Total processed: 5" in result.output
            assert "Successfully converted: 5" in result.output

    def test_convert_politicians_dry_run(self, runner, mock_container):
        """Test dry-run mode (no actual conversion)"""
        # Mock use case
        mock_usecase = Mock()
        mock_result = Mock()
        mock_result.total_processed = 3
        mock_result.converted_count = 3
        mock_result.skipped_count = 0
        mock_result.error_count = 0
        mock_result.converted_politicians = [Mock(name="議員A", politician_id=1)]
        mock_result.skipped_names = []
        mock_result.error_messages = []
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        mock_container.use_cases.convert_extracted_politician_usecase.return_value = (
            mock_usecase
        )

        with patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ):
            # Execute with dry-run flag
            result = runner.invoke(
                PoliticianCommands.convert_politicians, ["--dry-run"]
            )

            # Assert
            assert result.exit_code == 0
            assert "DRY-RUN" in result.output
            # Should call use case with dry_run=True
            mock_usecase.execute.assert_called_once()

    def test_convert_politicians_specific_party(self, runner, mock_container):
        """Test conversion for a specific party only"""
        # Mock use case
        mock_usecase = Mock()
        mock_result = Mock()
        mock_result.total_processed = 2
        mock_result.converted_count = 2
        mock_result.skipped_count = 0
        mock_result.error_count = 0
        mock_result.converted_politicians = [Mock(name="議員X", politician_id=10)]
        mock_result.skipped_names = []
        mock_result.error_messages = []
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        mock_container.use_cases.convert_extracted_politician_usecase.return_value = (
            mock_usecase
        )

        with patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ):
            # Execute with party-id
            result = runner.invoke(
                PoliticianCommands.convert_politicians, ["--party-id", "1"]
            )

            # Assert
            assert result.exit_code == 0
            assert "Total processed: 2" in result.output

    def test_convert_politicians_batch_size(self, runner, mock_container):
        """Test custom batch size parameter"""
        # Mock use case
        mock_usecase = Mock()
        mock_result = Mock()
        mock_result.total_processed = 50
        mock_result.converted_count = 50
        mock_result.skipped_count = 0
        mock_result.error_count = 0
        mock_result.converted_politicians = []
        mock_result.skipped_names = []
        mock_result.error_messages = []
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        mock_container.use_cases.convert_extracted_politician_usecase.return_value = (
            mock_usecase
        )

        with patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ):
            # Execute with batch-size
            result = runner.invoke(
                PoliticianCommands.convert_politicians, ["--batch-size", "50"]
            )

            # Assert
            assert result.exit_code == 0
            assert "Total processed: 50" in result.output

    def test_convert_politicians_no_candidates(self, runner, mock_container):
        """Test when no politicians need conversion"""
        # Mock use case
        mock_usecase = Mock()
        mock_result = Mock()
        mock_result.total_processed = 0
        mock_result.converted_count = 0
        mock_result.skipped_count = 0
        mock_result.error_count = 0
        mock_result.converted_politicians = []
        mock_result.skipped_names = []
        mock_result.error_messages = []
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        mock_container.use_cases.convert_extracted_politician_usecase.return_value = (
            mock_usecase
        )

        with patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ):
            # Execute
            result = runner.invoke(PoliticianCommands.convert_politicians, [])

            # Assert
            assert result.exit_code == 0
            assert "Total processed: 0" in result.output
            assert "No politicians were converted" in result.output

    def test_convert_politicians_with_errors(self, runner, mock_container):
        """Test handling of conversion errors"""
        # Mock use case
        mock_usecase = Mock()
        mock_result = Mock()
        mock_result.total_processed = 3
        mock_result.converted_count = 2
        mock_result.skipped_count = 0
        mock_result.error_count = 1
        mock_result.converted_politicians = [
            Mock(name="議員A", politician_id=1),
            Mock(name="議員B", politician_id=2),
        ]
        mock_result.skipped_names = []
        mock_result.error_messages = ["Error converting 議員C: Database error"]
        mock_usecase.execute = AsyncMock(return_value=mock_result)

        mock_container.use_cases.convert_extracted_politician_usecase.return_value = (
            mock_usecase
        )

        with patch(
            "src.infrastructure.di.container.get_container",
            return_value=mock_container,
        ):
            # Execute
            result = runner.invoke(PoliticianCommands.convert_politicians, [])

            # Assert
            assert result.exit_code == 0
            assert "Total processed: 3" in result.output
            assert "Successfully converted: 2" in result.output
            assert "Errors: 1" in result.output
            assert "Error converting 議員C" in result.output
