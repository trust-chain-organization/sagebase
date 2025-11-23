"""Tests for CLI scraping commands with meeting ID support"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.interfaces.cli.commands.scraping_commands import ScrapingCommands
from src.web_scraper.models import MinutesData


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def mock_minutes_data():
    """Create mock minutes data"""
    from datetime import datetime

    return MinutesData(
        title="議事録タイトル",
        date=datetime(2024, 1, 15),  # datetime型に変更
        url="https://example.com/minutes.html",
        content="議事録の内容",
        speakers=[],
        council_id="123",
        schedule_id="456",
        scraped_at=datetime(2024, 1, 15, 10, 0, 0),
    )


def test_scrape_minutes_with_url(cli_runner, mock_minutes_data):
    """Test scrape-minutes command with URL"""
    with patch("src.interfaces.cli.commands.scraping_commands.asyncio.run") as mock_run:
        # Mock the async function to return success
        mock_run.return_value = True

        result = cli_runner.invoke(
            ScrapingCommands.scrape_minutes,
            ["https://example.com/minutes.html"],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_scrape_minutes_with_meeting_id(cli_runner, mock_minutes_data):
    """Test scrape-minutes command with meeting ID"""
    with patch("src.interfaces.cli.commands.scraping_commands.asyncio.run") as mock_run:
        # Mock the async function to return success
        mock_run.return_value = True

        result = cli_runner.invoke(
            ScrapingCommands.scrape_minutes,
            ["--meeting-id", "123"],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_scrape_minutes_with_both_url_and_meeting_id(cli_runner):
    """Test scrape-minutes command with both URL and meeting ID (should fail)"""
    result = cli_runner.invoke(
        ScrapingCommands.scrape_minutes,
        ["https://example.com/minutes.html", "--meeting-id", "123"],
    )

    assert result.exit_code == 1
    assert "Specify either URL or --meeting-id, but not both" in result.output


def test_scrape_minutes_without_url_or_meeting_id(cli_runner):
    """Test scrape-minutes command without URL or meeting ID (should fail)"""
    result = cli_runner.invoke(
        ScrapingCommands.scrape_minutes,
        [],
    )

    assert result.exit_code == 1
    assert "Specify either URL or --meeting-id, but not both" in result.output


@pytest.mark.asyncio
async def test_async_scrape_minutes_with_url(mock_minutes_data):
    """Test async scrape minutes function with URL"""
    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service
        mock_service = Mock()
        mock_service.fetch_from_url = AsyncMock(return_value=mock_minutes_data)
        mock_service.export_to_text = Mock(return_value=(True, "gs://bucket/file.txt"))
        mock_service.export_to_json = Mock(return_value=(True, "gs://bucket/file.json"))
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            # Execute
            result = await ScrapingCommands._async_scrape_minutes(
                url="https://example.com/minutes.html",
                meeting_id=None,
                output_dir="data/scraped",
                format="both",
                no_cache=False,
                upload_to_gcs=True,
                gcs_bucket=None,
            )

            # Verify
            assert result is True
            mock_service.fetch_from_url.assert_called_once_with(
                "https://example.com/minutes.html", use_cache=True
            )


@pytest.mark.asyncio
async def test_async_scrape_minutes_with_meeting_id(mock_minutes_data):
    """Test async scrape minutes function with meeting ID"""
    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service
        mock_service = Mock()
        mock_service.fetch_from_meeting_id = AsyncMock(return_value=mock_minutes_data)
        mock_service.export_to_text = Mock(return_value=(True, "gs://bucket/file.txt"))
        mock_service.export_to_json = Mock(return_value=(True, "gs://bucket/file.json"))
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            # Execute
            result = await ScrapingCommands._async_scrape_minutes(
                url=None,
                meeting_id=123,
                output_dir="data/scraped",
                format="both",
                no_cache=False,
                upload_to_gcs=True,
                gcs_bucket=None,
            )

            # Verify
            assert result is True
            mock_service.fetch_from_meeting_id.assert_called_once_with(
                123, use_cache=True
            )


@pytest.mark.asyncio
async def test_async_scrape_minutes_failure(mock_minutes_data):
    """Test async scrape minutes function when scraping fails"""
    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service to return None (failure)
        mock_service = Mock()
        mock_service.fetch_from_url = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            # Execute
            result = await ScrapingCommands._async_scrape_minutes(
                url="https://example.com/minutes.html",
                meeting_id=None,
                output_dir="data/scraped",
                format="both",
                no_cache=False,
                upload_to_gcs=False,
                gcs_bucket=None,
            )

            # Verify
            assert result is False
            mock_service.fetch_from_url.assert_called_once()


@pytest.mark.asyncio
async def test_async_scrape_minutes_with_gcs_uri_update_meeting_id(mock_minutes_data):
    """Test GCS URI update when using meeting ID"""
    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service
        mock_service = Mock()
        mock_service.fetch_from_meeting_id = AsyncMock(return_value=mock_minutes_data)
        mock_service.export_to_text = Mock(return_value=(True, "gs://bucket/file.txt"))
        mock_service.export_to_json = Mock(return_value=(True, "gs://bucket/file.json"))
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_adapter_class:
            mock_repo = Mock()
            mock_repo.update_meeting_gcs_uris = Mock(return_value=Mock())
            mock_repo.close = Mock()
            mock_adapter_class.return_value = mock_repo

            # Execute
            result = await ScrapingCommands._async_scrape_minutes(
                url=None,
                meeting_id=123,
                output_dir="data/scraped",
                format="both",
                no_cache=False,
                upload_to_gcs=True,
                gcs_bucket=None,
            )

            # Verify
            assert result is True
            mock_repo.update_meeting_gcs_uris.assert_called_once_with(
                123, None, "gs://bucket/file.txt"
            )


@pytest.mark.asyncio
async def test_async_scrape_minutes_with_gcs_uri_update_url(mock_minutes_data):
    """Test GCS URI update when using URL"""
    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service
        mock_service = Mock()
        mock_service.fetch_from_url = AsyncMock(return_value=mock_minutes_data)
        mock_service.export_to_text = Mock(return_value=(True, "gs://bucket/file.txt"))
        mock_service.export_to_json = Mock(return_value=(True, "gs://bucket/file.json"))
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.fetch_as_dict = Mock(return_value=[{"id": 456}])
            mock_repo.update_meeting_gcs_uris = Mock(return_value=Mock())
            mock_repo.close = Mock()
            mock_repo_class.return_value = mock_repo

            # Execute
            result = await ScrapingCommands._async_scrape_minutes(
                url="https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=123&schedule_id=456",
                meeting_id=None,
                output_dir="data/scraped",
                format="both",
                no_cache=False,
                upload_to_gcs=True,
                gcs_bucket=None,
            )

            # Verify
            assert result is True
            mock_repo.update_meeting_gcs_uris.assert_called_once_with(
                456, None, "gs://bucket/file.txt"
            )


@pytest.mark.asyncio
async def test_async_scrape_minutes_with_gcs_uri_update_url_not_found(
    mock_minutes_data,
):
    """Test GCS URI update when URL is not found in database"""
    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service
        mock_service = Mock()
        mock_service.fetch_from_url = AsyncMock(return_value=mock_minutes_data)
        mock_service.export_to_text = Mock(return_value=(True, "gs://bucket/file.txt"))
        mock_service.export_to_json = Mock(return_value=(True, "gs://bucket/file.json"))
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.fetch_as_dict = Mock(return_value=[])
            mock_repo.update_meeting_gcs_uris = Mock()
            mock_repo.close = Mock()
            mock_repo_class.return_value = mock_repo

            # Execute
            result = await ScrapingCommands._async_scrape_minutes(
                url="https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=123&schedule_id=456",
                meeting_id=None,
                output_dir="data/scraped",
                format="both",
                no_cache=False,
                upload_to_gcs=True,
                gcs_bucket=None,
            )

            # Verify
            assert result is True
            # update_meeting_gcs_uris should not be called if meeting is not found
            mock_repo.update_meeting_gcs_uris.assert_not_called()


@pytest.mark.asyncio
async def test_async_batch_scrape_with_gcs_uri_update():
    """Test batch scrape with GCS URI update"""
    from datetime import datetime

    mock_minutes1 = MinutesData(
        title="議事録1",
        date=datetime(2024, 1, 15),
        url="https://example.com/minutes1.html",
        content="議事録1の内容",
        speakers=[],
        council_id="123",
        schedule_id="1",
        scraped_at=datetime(2024, 1, 15, 10, 0, 0),
    )

    mock_minutes2 = MinutesData(
        title="議事録2",
        date=datetime(2024, 1, 16),
        url="https://example.com/minutes2.html",
        content="議事録2の内容",
        speakers=[],
        council_id="123",
        schedule_id="2",
        scraped_at=datetime(2024, 1, 16, 10, 0, 0),
    )

    with patch("src.web_scraper.scraper_service.ScraperService") as mock_service_class:
        # Mock the scraper service
        mock_service = Mock()
        mock_service.fetch_multiple = AsyncMock(
            return_value=[mock_minutes1, mock_minutes2]
        )
        mock_service.export_to_text = Mock(
            side_effect=[
                (True, "gs://bucket/123_1.txt"),
                (True, "gs://bucket/123_2.txt"),
            ]
        )
        mock_service.export_to_json = Mock(
            side_effect=[
                (True, "gs://bucket/123_1.json"),
                (True, "gs://bucket/123_2.json"),
            ]
        )
        mock_service_class.return_value = mock_service

        # Mock meeting repository
        with patch(
            "src.infrastructure.persistence.repository_adapter.RepositoryAdapter"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.fetch_as_dict = Mock(
                side_effect=[
                    [{"id": 1}],  # First URL found
                    [{"id": 2}],  # Second URL found
                ]
            )
            mock_repo.update_meeting_gcs_uris = Mock(
                side_effect=[
                    Mock(),  # First update successful
                    Mock(),  # Second update successful
                ]
            )
            mock_repo.close = Mock()
            mock_repo_class.return_value = mock_repo

            # Execute
            urls = [
                "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=123&schedule_id=1",
                "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=123&schedule_id=2",
            ]

            result = await ScrapingCommands._async_batch_scrape(
                urls=urls,
                output_dir="data/scraped/batch",
                concurrent=2,
                upload_to_gcs=True,
                gcs_bucket=None,
            )

            # Verify
            assert result == 2
            assert mock_repo.update_meeting_gcs_uris.call_count == 2
            mock_repo.update_meeting_gcs_uris.assert_any_call(
                1, None, "gs://bucket/123_1.txt"
            )
            mock_repo.update_meeting_gcs_uris.assert_any_call(
                2, None, "gs://bucket/123_2.txt"
            )
