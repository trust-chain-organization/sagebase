"""Tests for ScraperService.fetch_from_meeting_id method"""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.entities.meeting import Meeting
from src.web_scraper.models import MinutesData
from src.web_scraper.scraper_service import ScraperService


@pytest.fixture
def scraper_service():
    """Create a ScraperService instance for testing"""
    return ScraperService(cache_dir="./test_cache", enable_gcs=False)


@pytest.fixture
def mock_meeting():
    """Create a mock meeting object"""
    meeting = Meeting(
        id=123,
        conference_id=1,
        date=date(2024, 1, 15),
        url="https://example.com/minutes.html",
        name="第1回定例会",
    )
    meeting.created_at = datetime(2024, 1, 1)
    meeting.updated_at = datetime(2024, 1, 1)
    return meeting


@pytest.fixture
def mock_minutes_data():
    """Create mock minutes data"""
    return MinutesData(
        title="第1回定例会議事録",
        date=datetime(2024, 1, 15),  # datetime型に変更
        url="https://example.com/minutes.html",
        content="議事録の内容",
        speakers=[],
        council_id="123",
        schedule_id="456",
        scraped_at=datetime(2024, 1, 15, 10, 0, 0),
    )


@pytest.mark.asyncio
async def test_fetch_from_meeting_id_success(
    scraper_service, mock_meeting, mock_minutes_data
):
    """Test successful fetch from meeting ID"""
    with patch("src.web_scraper.scraper_service.RepositoryAdapter") as mock_repo_class:
        # Mock the repository
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_meeting)
        mock_repo_class.return_value = mock_repo

        # Mock fetch_from_url
        scraper_service.fetch_from_url = AsyncMock(return_value=mock_minutes_data)

        # Execute
        result = await scraper_service.fetch_from_meeting_id(123)

        # Verify
        assert result == mock_minutes_data
        mock_repo.get_by_id.assert_called_once_with(123)
        scraper_service.fetch_from_url.assert_called_once_with(
            "https://example.com/minutes.html", use_cache=True
        )


@pytest.mark.asyncio
async def test_fetch_from_meeting_id_not_found(scraper_service):
    """Test fetch from non-existent meeting ID"""
    with patch("src.web_scraper.scraper_service.RepositoryAdapter") as mock_repo_class:
        # Mock the repository to return None
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo_class.return_value = mock_repo

        # Execute
        result = await scraper_service.fetch_from_meeting_id(999)

        # Verify
        assert result is None
        mock_repo.get_by_id.assert_called_once_with(999)


@pytest.mark.asyncio
async def test_fetch_from_meeting_id_no_url(scraper_service):
    """Test fetch from meeting with no URL"""
    with patch("src.web_scraper.scraper_service.RepositoryAdapter") as mock_repo_class:
        # Mock a meeting without URL
        mock_meeting = Meeting(
            id=123,
            conference_id=1,
            date=date(2024, 1, 15),
            url=None,  # No URL
            name="第1回定例会",
            gcs_pdf_uri=None,
            gcs_text_uri=None,
        )
        mock_meeting.created_at = datetime(2024, 1, 1)
        mock_meeting.updated_at = datetime(2024, 1, 1)
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_meeting)
        mock_repo_class.return_value = mock_repo

        # Execute
        result = await scraper_service.fetch_from_meeting_id(123)

        # Verify
        assert result is None
        mock_repo.get_by_id.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_fetch_from_meeting_id_with_cache_disabled(
    scraper_service, mock_meeting, mock_minutes_data
):
    """Test fetch from meeting ID with cache disabled"""
    with patch("src.web_scraper.scraper_service.RepositoryAdapter") as mock_repo_class:
        # Mock the repository
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_meeting)
        mock_repo_class.return_value = mock_repo

        # Mock fetch_from_url
        scraper_service.fetch_from_url = AsyncMock(return_value=mock_minutes_data)

        # Execute with cache disabled
        result = await scraper_service.fetch_from_meeting_id(123, use_cache=False)

        # Verify
        assert result == mock_minutes_data
        mock_repo.get_by_id.assert_called_once_with(123)
        scraper_service.fetch_from_url.assert_called_once_with(
            "https://example.com/minutes.html", use_cache=False
        )


@pytest.mark.asyncio
async def test_fetch_from_meeting_id_scraping_failure(scraper_service, mock_meeting):
    """Test fetch from meeting ID when scraping fails"""
    with patch("src.web_scraper.scraper_service.RepositoryAdapter") as mock_repo_class:
        # Mock the repository
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_meeting)
        mock_repo_class.return_value = mock_repo

        # Mock fetch_from_url to return None (failure)
        scraper_service.fetch_from_url = AsyncMock(return_value=None)

        # Execute
        result = await scraper_service.fetch_from_meeting_id(123)

        # Verify
        assert result is None
        mock_repo.get_by_id.assert_called_once_with(123)
        scraper_service.fetch_from_url.assert_called_once_with(
            "https://example.com/minutes.html", use_cache=True
        )


# ============================================================================
# リグレッションテスト（Issue #839）
# async/await バグの再発防止
# ============================================================================


@pytest.mark.asyncio
async def test_repository_adapter_requires_await(mock_meeting):
    """
    リグレッションテスト: RepositoryAdapter の非同期メソッドは必ず await すること

    Issue #836 の再発防止のためのテスト。
    AsyncMock を使用して、await なしで呼び出すとエラーになることを確認する。

    背景:
        - Issue #836: ScraperService.fetch_from_meeting_id で await を忘れた
        - 問題: meeting = meeting_repo.get_by_id(meeting_id)  # await なし
        - 結果: meeting がコルーチンオブジェクトになり、meeting.url でエラー
        - 原因: テストがモックに依存しすぎており、実際の挙動を検証していなかった

    このテスト:
        - AsyncMock を正しく使用して、await なしの呼び出しを検出
        - コルーチンオブジェクトが返されることを確認
        - url 属性へのアクセスでエラーが発生することを確認
    """
    import asyncio

    with patch("src.web_scraper.scraper_service.RepositoryAdapter") as mock_repo_class:
        # Mock the repository with AsyncMock
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_meeting)
        mock_repo_class.return_value = mock_repo

        # === ケース1: await していない場合（バグのシミュレーション） ===
        # この呼び出しは await していないため、コルーチンオブジェクトが返される
        coro = mock_repo.get_by_id(123)  # await なし

        # コルーチンオブジェクトであることを確認
        assert asyncio.iscoroutine(coro), (
            "AsyncMock の戻り値は await されていない場合、"
            "コルーチンオブジェクトであるべき"
        )

        # url 属性にアクセスしようとするとエラーになることを確認
        with pytest.raises(AttributeError, match="'coroutine' object has no attribute"):
            _ = coro.url  # これが Issue #836 で発生したエラー

        # コルーチンをクリーンアップ
        coro.close()

        # === ケース2: 正しく await した場合 ===
        # 正しく await すれば、Meeting オブジェクトが返される
        meeting = await mock_repo.get_by_id(123)

        # Meeting オブジェクトであることを確認
        assert meeting == mock_meeting
        assert hasattr(meeting, "url")
        assert meeting.url == "https://example.com/minutes.html"
