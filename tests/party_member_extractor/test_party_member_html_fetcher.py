"""Tests for Party Member HTML Fetcher"""

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher


# Suppress the specific coroutine warning
warnings.filterwarnings(
    "ignore", message="coroutine.*was never awaited", category=RuntimeWarning
)


class TestPartyMemberPageFetcher:
    """PartyMemberPageFetcherのテストクラス"""

    @pytest_asyncio.fixture
    async def mock_playwright(self):
        """Playwrightのモック"""
        with patch("src.party_member_extractor.html_fetcher.async_playwright") as mock:
            # async_playwright()の戻り値をモック
            mock_async_playwright = MagicMock()
            mock.return_value = mock_async_playwright

            # startメソッドを非同期にする
            mock_playwright_instance = AsyncMock()
            mock_async_playwright.start = AsyncMock(
                return_value=mock_playwright_instance
            )

            # ブラウザのモック
            mock_browser = AsyncMock()
            mock_playwright_instance.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            # コンテキストのモック
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            yield {
                "playwright": mock_playwright_instance,
                "browser": mock_browser,
                "context": mock_context,
            }

    @pytest_asyncio.fixture
    async def fetcher(self, mock_playwright):
        """フェッチャーのフィクスチャ"""
        fetcher = PartyMemberPageFetcher()
        await fetcher.__aenter__()
        fetcher.browser = mock_playwright["browser"]
        fetcher.context = mock_playwright["context"]
        yield fetcher
        await fetcher.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_fetch_all_pages_single_page(self, fetcher):
        """単一ページ取得のテスト"""
        # ページのモック
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/members"
        mock_page.content.return_value = "<html><body>Members list</body></html>"
        fetcher.context.new_page.return_value = mock_page

        # 次ページリンクなし
        with patch.object(fetcher, "_find_next_page_link", return_value=None):
            # テスト実行
            result = await fetcher.fetch_all_pages(
                "https://example.com/members", max_pages=5
            )

        # アサーション
        assert len(result) == 1
        assert result[0].url == "https://example.com/members"
        assert result[0].page_number == 1
        assert "Members list" in result[0].html_content

        # ページ遷移の確認
        mock_page.goto.assert_called_once_with(
            "https://example.com/members", wait_until="domcontentloaded", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_fetch_all_pages_multiple_pages(self, fetcher):
        """複数ページ取得のテスト"""
        # ページのモック
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/members"
        mock_page.content.side_effect = [
            "<html><body>Page 1</body></html>",
            "<html><body>Page 2</body></html>",
            "<html><body>Page 3</body></html>",
        ]
        fetcher.context.new_page.return_value = mock_page

        # 次ページリンクのモック
        mock_next_link = AsyncMock()
        call_count = 0

        def side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                mock_page.url = f"https://example.com/members?page={call_count + 1}"
                return mock_next_link
            return None

        with patch.object(fetcher, "_find_next_page_link", side_effect=side_effect):
            # テスト実行
            result = await fetcher.fetch_all_pages(
                "https://example.com/members", max_pages=5
            )

        # アサーション
        assert len(result) == 3
        assert "Page 1" in result[0].html_content
        assert "Page 2" in result[1].html_content
        assert "Page 3" in result[2].html_content
        assert mock_next_link.click.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_all_pages_max_limit(self, fetcher):
        """最大ページ数制限のテスト"""
        # ページのモック
        mock_page = AsyncMock()
        # URLを変化させる
        urls = [
            "https://example.com/members",
            "https://example.com/members?page=2",
            "https://example.com/members?page=3",
        ]
        url_index = 0

        def get_url():
            nonlocal url_index
            return urls[min(url_index, len(urls) - 1)]

        # URLプロパティをモック
        type(mock_page).url = property(lambda self: get_url())
        mock_page.content.return_value = "<html><body>Page</body></html>"
        mock_page.wait_for_load_state = AsyncMock()
        fetcher.context.new_page.return_value = mock_page

        # 常に次ページがある
        mock_next_link = AsyncMock()

        async def click_effect():
            nonlocal url_index
            url_index += 1

        mock_next_link.click.side_effect = click_effect

        # 最初は次ページリンクあり、2回目はなし
        find_next_calls = [0]

        async def find_next_side_effect(page):
            find_next_calls[0] += 1
            if find_next_calls[0] == 1:
                return mock_next_link  # 最初の呼び出しではリンクを返す
            else:
                return None  # 2回目以降はNoneを返す

        with patch.object(
            fetcher, "_find_next_page_link", side_effect=find_next_side_effect
        ):
            # テスト実行（最大2ページ）
            result = await fetcher.fetch_all_pages(
                "https://example.com/members", max_pages=2
            )

        # アサーション
        assert len(result) == 2  # 最大ページ数で制限
        # max_pages=2の場合、ページ1を取得してクリック、
        # ページ2を取得して終了なので1回のクリック
        assert mock_next_link.click.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_all_pages_with_error(self, fetcher):
        """エラー処理のテスト"""
        # ページのモック
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Network error")
        fetcher.context.new_page.return_value = mock_page

        # テスト実行
        result = await fetcher.fetch_all_pages("https://example.com/members")

        # アサーション
        assert len(result) == 0  # エラー時は空のリスト
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_next_page_link(self, fetcher):
        """次ページリンク検出のテスト"""
        # ページのモック
        mock_page = AsyncMock()

        # リンク要素のモック
        mock_element = AsyncMock()
        mock_element.is_visible.return_value = True
        mock_element.get_attribute.side_effect = lambda attr: None

        # セレクタごとの結果
        def query_selector_side_effect(selector):
            if selector == 'a:has-text("次へ")':
                return mock_element
            return None

        mock_page.query_selector.side_effect = query_selector_side_effect

        # テスト実行
        result = await fetcher._find_next_page_link(mock_page)

        # アサーション
        assert result == mock_element

    @pytest.mark.asyncio
    async def test_find_next_page_link_disabled(self, fetcher):
        """無効化されたリンクのテスト"""
        # ページのモック
        mock_page = AsyncMock()

        # 無効化されたリンク要素
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)

        async def get_attribute_side_effect(attr):
            return "true" if attr == "aria-disabled" else None

        mock_element.get_attribute = AsyncMock(side_effect=get_attribute_side_effect)

        mock_page.query_selector = AsyncMock(return_value=mock_element)

        # テスト実行
        result = await fetcher._find_next_page_link(mock_page)

        # アサーション
        assert result is None  # 無効化されたリンクは返さない

    @pytest.mark.asyncio
    async def test_find_next_page_link_numeric(self, fetcher):
        """数字ベースのページネーションテスト"""
        # ページのモック
        mock_page = AsyncMock()

        # 現在のページ番号要素
        mock_current = AsyncMock()
        mock_current.text_content = AsyncMock(return_value="2")

        # 次のページ番号リンク
        mock_next = AsyncMock()
        mock_next.is_visible = AsyncMock(return_value=True)

        # query_selectorの動作を定義
        async def query_selector_side_effect(selector):
            # パターンベースのセレクタは全てNoneを返す
            if selector in [
                'a:has-text("次へ")',
                'a:has-text("次")',
                'a:has-text("Next")',
                'a:has-text(">")',
                'a:has-text("»")',
                'a[rel="next"]',
                ".pagination a.next",
                ".pager a.next",
                "a.page-next",
                "li.next a",
            ]:
                return None
            # 現在のページ番号を探すセレクタ
            elif ".pagination .active, .pager .current, .page-current" in selector:
                return mock_current
            # 次のページ番号のリンクを探すセレクタ
            elif selector == 'a:has-text("3")':
                return mock_next
            return None

        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)

        # テスト実行
        result = await fetcher._find_next_page_link(mock_page)

        # アサーション
        assert result == mock_next

    @pytest.mark.asyncio
    async def test_fetch_single_page(self, fetcher):
        """単一ページ取得のテスト"""
        # ページのモック
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body>Single page content</body></html>"
        fetcher.context.new_page.return_value = mock_page

        # テスト実行
        result = await fetcher.fetch_single_page("https://example.com/page")

        # アサーション
        assert result is not None
        assert result.url == "https://example.com/page"
        assert result.page_number == 1
        assert "Single page content" in result.html_content
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """コンテキストマネージャのテスト"""
        with patch(
            "src.party_member_extractor.html_fetcher.async_playwright"
        ) as mock_playwright:
            # async_playwright()の戻り値をモック
            mock_async_playwright = MagicMock()
            mock_playwright.return_value = mock_async_playwright

            # startメソッドを非同期にする
            mock_playwright_instance = AsyncMock()
            mock_async_playwright.start = AsyncMock(
                return_value=mock_playwright_instance
            )

            mock_browser = AsyncMock()
            mock_playwright_instance.chromium.launch = AsyncMock(
                return_value=mock_browser
            )

            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            # テスト実行
            async with PartyMemberPageFetcher() as fetcher:
                assert fetcher.browser is not None
                assert fetcher.context is not None

            # クリーンアップの確認
            mock_context.close.assert_called_once()
            mock_browser.close.assert_called_once()
