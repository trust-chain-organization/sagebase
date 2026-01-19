"""HTML fetcher for web pages with pagination support

Playwright を使用してWebページをフェッチし、ページネーションを処理します。
元々は政党メンバーページ用でしたが、汎用的なHTMLフェッチャーとして使用できます。
"""

import asyncio
import logging

from types import TracebackType
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.application.dtos.web_page_content_dto import WebPageContentDTO
from src.infrastructure.config.settings import get_settings


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class HtmlPageFetcher:
    """Webページを取得（ページネーション対応）

    Playwright を使用してJavaScriptをレンダリングした後のHTMLを取得します。
    ページネーションに対応し、複数ページを順番に取得できます。
    """

    def __init__(self, proc_logger: Any = None):
        """初期化

        Args:
            proc_logger: 処理ログ出力用のオプションロガー（Streamlit等で使用）
        """
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.settings = get_settings()
        self.proc_logger = proc_logger

    async def __aenter__(self):
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            self.context = await self.browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            return self
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception:
            pass

    async def fetch_all_pages(
        self, start_url: str, max_pages: int = 20
    ) -> list[WebPageContentDTO]:
        """
        ページを取得（ページネーション対応）

        Args:
            start_url: 開始URL
            max_pages: 最大ページ数

        Returns:
            List[WebPageContentDTO]: 取得したページコンテンツのリスト
        """
        pages_content: list[WebPageContentDTO] = []
        visited_urls: set[str] = set()

        if not self.context:
            raise RuntimeError("Browser context not initialized")

        page = await self.context.new_page()
        try:
            logger.info(f"Fetching initial page: {start_url}")
            try:
                await page.goto(
                    start_url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.page_load_timeout * 1000,
                )
                try:
                    await page.wait_for_load_state(
                        "networkidle",
                        timeout=5000,
                    )
                except Exception:
                    logger.debug("Network idle timeout, but continuing")
            except Exception as e:
                logger.warning(f"Initial page load with domcontentloaded failed: {e}")
                await page.goto(
                    start_url,
                    wait_until="load",
                    timeout=self.settings.page_load_timeout * 1000,
                )

            await asyncio.sleep(2)

            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            current_page_num = 1

            while current_page_num <= max_pages:
                current_url = page.url
                if current_url in visited_urls:
                    logger.info("Already visited this URL, stopping pagination")
                    break

                visited_urls.add(current_url)
                content = await page.content()

                pages_content.append(
                    WebPageContentDTO(
                        url=current_url,
                        html_content=content,
                        page_number=current_page_num,
                    )
                )

                logger.info(f"Fetched page {current_page_num}: {current_url}")

                next_link = await self._find_next_page_link(page)

                if not next_link:
                    logger.info("No more pages found")
                    break

                try:
                    logger.info("Attempting to click next page link")
                    await next_link.click()
                    await page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=self.settings.page_load_timeout * 1000,
                    )
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        logger.debug("Network idle timeout on pagination, continuing")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Failed to navigate to next page: {e}")
                    break

                current_page_num += 1

            return pages_content

        except Exception as e:
            logger.error(f"Error during page fetching from {start_url}: {e}")
            import traceback

            traceback_str = traceback.format_exc()
            logger.error(f"Traceback: {traceback_str}")
            return pages_content if pages_content else []
        finally:
            await page.close()

    async def _find_next_page_link(self, page: Page):
        """次のページへのリンクを探す"""
        next_patterns = [
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
        ]

        for pattern in next_patterns:
            try:
                element = await page.query_selector(pattern)
                if element and await element.is_visible():
                    is_disabled = (
                        await element.get_attribute("disabled")
                        or await element.get_attribute("aria-disabled") == "true"
                        or "disabled" in (await element.get_attribute("class") or "")
                    )

                    if not is_disabled:
                        return element
            except Exception:
                continue

        try:
            current_page_elem = await page.query_selector(
                ".pagination .active, .pager .current, .page-current"
            )
            if current_page_elem:
                current_text = await current_page_elem.text_content()
                if current_text and current_text.strip().isdigit():
                    current_num = int(current_text.strip())
                    next_num = current_num + 1

                    next_link = await page.query_selector(f'a:has-text("{next_num}")')
                    if next_link and await next_link.is_visible():
                        return next_link
        except Exception:
            pass

        return None

    async def fetch_single_page(self, url: str) -> WebPageContentDTO | None:
        """単一ページを取得"""
        if not self.context:
            raise RuntimeError("Browser context not initialized")

        page = await self.context.new_page()
        try:
            logger.info(f"Fetching page: {url}")
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.page_load_timeout * 1000,
                )
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    logger.debug("Network idle timeout, but continuing")
            except Exception as e:
                logger.warning(f"Page load with domcontentloaded failed: {e}")
                await page.goto(
                    url,
                    wait_until="load",
                    timeout=self.settings.page_load_timeout * 1000,
                )
            await asyncio.sleep(2)

            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            content = await page.content()
            return WebPageContentDTO(url=url, html_content=content, page_number=1)

        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None
        finally:
            await page.close()
