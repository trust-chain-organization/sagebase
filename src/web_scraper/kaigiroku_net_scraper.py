"""kaigiroku.net議事録システムスクレーパー"""

import asyncio
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from src.infrastructure.config.settings import get_settings

from .base_scraper import BaseScraper
from .extractors import ContentExtractor, SpeakerExtractor
from .handlers import FileHandler, PDFHandler
from .models import MinutesData, SpeakerData


class KaigirokuNetScraper(BaseScraper):
    """kaigiroku.net議事録システム汎用スクレーパー

    対応URL例:
    - https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1
    - https://ssp.kaigiroku.net/tenant/osaka/MinuteView.html?council_id=1234&schedule_id=1
    - https://ssp.kaigiroku.net/tenant/kobe/MinuteView.html?council_id=5678&schedule_id=1

    kaigiroku.netは多くの地方議会で使用されている統一システムのため、
    tenant名が異なっても同じ構造で議事録を取得可能です。
    """

    def __init__(self, headless: bool = True, download_dir: str = "data/scraped"):
        super().__init__()
        self.headless = headless
        self.settings = get_settings()

        # コンポーネントの初期化
        self.content_extractor = ContentExtractor(logger=self.logger)
        self.speaker_extractor = SpeakerExtractor(logger=self.logger)
        self.pdf_handler = PDFHandler(download_dir=download_dir, logger=self.logger)
        self.file_handler = FileHandler(base_dir=download_dir, logger=self.logger)

    async def fetch_minutes(self, url: str) -> MinutesData | None:
        """指定されたURLから議事録を取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()

                self.logger.info(f"Loading URL: {url}")

                # ページを読み込み
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.web_scraper_timeout * 1000,
                )
                if not response:
                    self.logger.error("No response from server")
                    return None

                self.logger.info(f"Response status: {response.status}")

                # JavaScriptの実行を待つ
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5)  # 追加の待機時間

                # URLパラメータを抽出
                council_id, schedule_id = self._extract_url_params(url)

                # まずPDFのダウンロードボタンを探す
                pdf_url = await self._find_pdf_download_url(page)
                if pdf_url:
                    self.logger.info(f"Found PDF URL: {pdf_url}")
                    # PDFをダウンロードして内容を返す
                    return await self._download_pdf_as_minutes(
                        pdf_url, url, council_id, schedule_id
                    )

                # JavaScriptレンダリング待機
                await self._wait_for_content(page)

                # iframeコンテンツの処理
                iframe_content = await self._extract_iframe_content(page)

                # HTML取得（iframeコンテンツまたはメインページ）
                if iframe_content:
                    html = iframe_content
                    self.logger.info("Using iframe content")
                else:
                    html = await page.content()
                    self.logger.info("Using main page content")

                # BeautifulSoupオブジェクトを作成
                soup = BeautifulSoup(html, "html.parser")

                # データ抽出
                title = self.content_extractor.extract_title(soup)
                date = await self._extract_date(page)
                content = self.content_extractor.extract_content(html)
                speakers = self.speaker_extractor.extract_speakers_with_context(soup)

                # コンテンツが空の場合は、ページ全体のテキストを取得
                if not content or len(content.strip()) < 100:
                    self.logger.warning(
                        "Content is too short, trying to extract all text"
                    )
                    content = await page.evaluate('document.body.innerText || ""')

                # それでも空の場合は、テキスト表示用のURLを試す
                text_view_url = None
                if not content or len(content.strip()) < 100:
                    text_view_url = await self._find_text_view_url(page)
                    if text_view_url:
                        self.logger.info(f"Trying text view URL: {text_view_url}")
                        await page.goto(text_view_url, wait_until="networkidle")
                        await asyncio.sleep(3)
                        content = await page.evaluate('document.body.innerText || ""')

                # メタデータを抽出
                metadata = self.content_extractor.extract_metadata(soup)

                return MinutesData(
                    council_id=council_id,
                    schedule_id=schedule_id,
                    title=title,
                    date=date,
                    content=content,
                    speakers=speakers,
                    url=url,
                    scraped_at=datetime.now(),
                    pdf_url=pdf_url,
                    text_view_url=text_view_url,
                    metadata=metadata,
                )

            except Exception as e:
                self.logger.error(f"Error fetching minutes from {url}: {e}")
                import traceback

                self.logger.error(traceback.format_exc())
                return None
            finally:
                await browser.close()

    def _extract_url_params(self, url: str) -> tuple[str, str]:
        """URLからパラメータを抽出"""
        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        council_id = params.get("council_id", [""])[0]
        schedule_id = params.get("schedule_id", [""])[0]
        return council_id, schedule_id

    async def _wait_for_content(self, page: Page):
        """議事録コンテンツの読み込みを待機"""
        # kaigiroku.netの動的コンテンツ読み込みを待機
        self.logger.info("Waiting for content to load...")

        # まず基本的なページ読み込みを待つ
        await asyncio.sleep(3)

        # 複数の可能なセレクタを試す
        content_selectors = [
            "#minuteFrame",  # iframe要素
            'iframe[name="minuteFrame"]',
            "#plain-minute",
            ".minute-content",
            ".meeting-content",
            "#meeting-text",
            'div[id*="minute"]',
            'div[class*="minute"]',
        ]

        content_found = False
        for selector in content_selectors:
            try:
                await page.wait_for_selector(
                    selector, timeout=self.settings.selector_wait_timeout * 1000
                )
                self.logger.info(f"Found content selector: {selector}")
                content_found = True
                break
            except Exception:
                continue

        if not content_found:
            self.logger.warning(
                "No standard content selectors found, checking for iframes..."
            )

            # iframeをチェック
            iframes = await page.query_selector_all("iframe")
            if iframes:
                self.logger.info(
                    f"Found {len(iframes)} iframes, may need to handle iframe content"
                )

        # 最終的な待機時間
        await asyncio.sleep(2)

    async def _extract_iframe_content(self, page: Page) -> str | None:
        """iframeからコンテンツを抽出"""
        try:
            # まずminuteFrameというiframeを探す
            iframe_element = await page.query_selector(
                'iframe#minuteFrame, iframe[name="minuteFrame"]'
            )
            if iframe_element:
                frame = await iframe_element.content_frame()
                if frame:
                    self.logger.info("Found minuteFrame iframe, extracting content...")
                    # iframe内のコンテンツを待つ
                    await asyncio.sleep(2)
                    return await frame.content()

            # 他のiframeも試す
            all_frames = page.frames
            for frame in all_frames:
                if frame != page.main_frame:
                    try:
                        frame_url = frame.url
                        self.logger.info(f"Checking frame: {frame_url}")
                        if (
                            "minute" in frame_url.lower()
                            or "content" in frame_url.lower()
                        ):
                            await asyncio.sleep(1)
                            return await frame.content()
                    except Exception:
                        continue

            return None
        except Exception as e:
            self.logger.warning(f"Error extracting iframe content: {e}")
            return None

    async def _extract_date(self, page: Page) -> datetime | None:
        """ページから日付を抽出"""
        try:
            # 日付要素のセレクタを試行
            selectors = [".date-info", ".minute-date", ".meeting-date"]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    date_text = await element.text_content()
                    if date_text:
                        parsed_date = self.date_parser.parse(date_text.strip())
                        if parsed_date:
                            return parsed_date

            # ページ全体から日付を検索
            content = await page.content()
            return self.date_parser.extract_from_text(content)

        except Exception as e:
            self.logger.warning(f"Error extracting date: {e}")
            return None

    async def _find_pdf_download_url(self, page: Page) -> str | None:
        """PDFダウンロードURLを見つける"""
        try:
            # ダウンロードボタンを探す
            selectors = [
                'a:has-text("PDF")',
                'a:has-text("ダウンロード")',
                'button:has-text("PDF")',
                'button:has-text("ダウンロード")',
                'a[href*=".pdf"]',
                'a[onclick*="download"]',
                'button[onclick*="download"]',
            ]

            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    # href属性をチェック
                    href = await element.get_attribute("href")
                    if href and ".pdf" in href:
                        if not href.startswith("http"):
                            base_url = page.url.split("?")[0]
                            base_url = "/".join(base_url.split("/")[:-1])
                            href = f"{base_url}/{href}".replace("//", "/")
                        return href

                    # onclick属性をチェック
                    onclick = await element.get_attribute("onclick")
                    if onclick:
                        # JavaScript関数からURLを抽出
                        import re

                        pdf_match = re.search(
                            r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick
                        )
                        if pdf_match:
                            pdf_url = pdf_match.group(1)
                            if not pdf_url.startswith("http"):
                                base_url = page.url.split("?")[0]
                                base_url = "/".join(base_url.split("/")[:-1])
                                pdf_url = f"{base_url}/{pdf_url}".replace("//", "/")
                            return pdf_url

            return None
        except Exception as e:
            self.logger.warning(f"Error finding PDF URL: {e}")
            return None

    async def _find_text_view_url(self, page: Page) -> str | None:
        """テキスト表示用のURLを見つける"""
        try:
            # テキスト表示リンクを探す
            selectors = [
                'a:has-text("テキスト表示")',
                'a:has-text("本文表示")',
                'a:has-text("議事録表示")',
                'a[href*="TextView"]',
                'a[href*="text_view"]',
            ]

            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    href = await element.get_attribute("href")
                    if href:
                        if not href.startswith("http"):
                            base_url = page.url.split("?")[0]
                            base_url = "/".join(base_url.split("/")[:-1])
                            href = f"{base_url}/{href}".replace("//", "/")
                        return href

            return None
        except Exception as e:
            self.logger.warning(f"Error finding text view URL: {e}")
            return None

    async def _download_pdf_as_minutes(
        self, pdf_url: str, original_url: str, council_id: str, schedule_id: str
    ) -> MinutesData | None:
        """PDFをダウンロードして議事録データとして返す"""
        try:
            # PDFをダウンロードしてテキストを抽出
            pdf_path, text_content = await self.pdf_handler.download_and_extract(
                pdf_url,
                self.file_handler.generate_filename(council_id, schedule_id, "pdf"),
            )

            if not pdf_path:
                return None

            self.logger.info(f"PDF saved to: {pdf_path}")

            return MinutesData(
                council_id=council_id,
                schedule_id=schedule_id,
                title=f"議事録 {council_id}_{schedule_id}",
                date=None,
                content=text_content,
                speakers=[],  # PDFからの発言者抽出は別途実装が必要
                url=original_url,
                scraped_at=datetime.now(),
                pdf_url=pdf_url,
                metadata={"pdf_path": pdf_path},
            )

        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return None

    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出"""
        return self.content_extractor.extract_content(html_content)

    async def extract_speakers(self, html_content: str) -> list[SpeakerData]:
        """HTMLから発言者情報を抽出"""
        soup = BeautifulSoup(html_content, "html.parser")
        return self.speaker_extractor.extract_speakers_with_context(soup)
