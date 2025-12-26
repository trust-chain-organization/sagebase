"""国会会議録検索システム用スクレイパー

国会会議録検索システム（kokkai.ndl.go.jp）から議事録を取得するスクレイパー
"""

import asyncio
import logging
import re

from datetime import datetime
from typing import Any

from playwright.async_api import Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .base_scraper import BaseScraper
from .exceptions import ScraperConnectionError, ScraperParseError
from .models import MinutesData, SpeakerData

from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)


class KokkaiScraper(BaseScraper):
    """国会会議録検索システム用スクレイパー"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://kokkai.ndl.go.jp"

    async def _create_browser(self):
        """Playwrightブラウザを作成"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        return browser

    async def _load_page_with_retry(
        self, page: Page, url: str, retry_count: int = 3
    ) -> None:
        """ページを読み込み（リトライ付き）"""
        for attempt in range(retry_count):
            try:
                logger.info(
                    f"Loading page: {url} (attempt {attempt + 1}/{retry_count})"
                )

                # ページを読み込み
                await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=settings.web_scraper_timeout * 1000,
                )

                # コンテンツが読み込まれるまで待機（SPAのため）
                # Vueアプリがロードされるまで待機
                await page.wait_for_timeout(3000)

                # h2タグ（会議情報）が表示されるまで待機
                await page.wait_for_selector(
                    "h2",
                    timeout=settings.selector_wait_timeout * 1000,
                )

                logger.info("Page loaded successfully")
                return

            except PlaywrightTimeoutError:
                if attempt < retry_count - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    raise ScraperConnectionError(
                        f"Failed to load page after {retry_count} attempts: {url}"
                    ) from None
            except Exception as e:
                logger.error(f"Unexpected error loading page: {e}")
                raise

    async def fetch_minutes(self, url: str) -> MinutesData | None:
        """議事録を取得"""
        browser = None
        try:
            browser = await self._create_browser()
            page = await browser.new_page()

            # ページを読み込み
            await self._load_page_with_retry(page, url)

            # 議事録データを抽出
            minutes_data = await self._extract_minutes_data(page, url)

            if not minutes_data:
                logger.warning(f"No minutes data found for URL: {url}")
                return None

            return minutes_data

        except Exception as e:
            logger.error(f"Error fetching minutes: {e}")
            raise ScraperParseError(
                f"Failed to fetch minutes from kokkai.ndl.go.jp: {url} - {str(e)}"
            ) from e
        finally:
            if browser:
                await browser.close()

    async def _extract_minutes_data(self, page: Page, url: str) -> MinutesData | None:
        """議事録データを抽出"""
        try:
            # 会議情報を取得
            meeting_info = await self._extract_meeting_info(page)

            # タイトルを取得
            title = await self._extract_title(page)
            if not title:
                title = meeting_info.get("title", "国会議事録")

            # 日付を取得
            date = self._parse_date(meeting_info.get("date", ""))

            # 本文を取得
            content = await self._extract_content(page)
            if not content:
                logger.warning("No content found")
                return None

            # 発言者情報を抽出
            speakers = await self._extract_speakers(page)

            # MinId から council_id と schedule_id を生成
            council_id, schedule_id = self._extract_ids_from_url(url)

            return MinutesData(
                url=url,
                title=title,
                date=date,
                content=content,
                speakers=speakers,
                council_id=council_id,
                schedule_id=schedule_id,
                scraped_at=datetime.now(),
                metadata=meeting_info,
            )

        except Exception as e:
            logger.error(f"Error extracting minutes data: {e}")
            raise

    async def _extract_meeting_info(self, page: Page) -> dict[str, Any]:
        """会議情報を抽出"""
        meeting_info: dict[str, Any] = {}

        try:
            # h2タグから会議情報を取得
            h2_element = await page.query_selector("h2")

            if h2_element:
                # h2タグのテキストから会議情報を抽出
                h2_text = await h2_element.inner_text()
                meeting_info["title"] = h2_text.strip()

                # テキストから情報をパース
                # 例: "第217回国会　衆議院　北朝鮮による拉致問題等に関する特別委員会
                # 第3号　令和7年4月23日"
                parts = h2_text.split("　")
                for part in parts:
                    if "国会" in part:
                        meeting_info["国会"] = part
                    elif "院" in part:
                        meeting_info["院"] = part
                    elif "委員会" in part:
                        meeting_info["委員会"] = part
                    elif "第" in part and "号" in part:
                        meeting_info["号数"] = part
                    elif "年" in part and "月" in part and "日" in part:
                        meeting_info["date"] = part

            logger.info(f"Extracted meeting info: {meeting_info}")

        except Exception as e:
            logger.warning(f"Error extracting meeting info: {e}")

        return meeting_info

    async def _extract_title(self, page: Page) -> str:
        """タイトルを抽出"""
        try:
            # h2タグからタイトルを取得
            h2_element = await page.query_selector("h2")
            if h2_element:
                title = await h2_element.inner_text()
                if title and title.strip():
                    return title.strip()

            # ページタイトルから取得
            page_title = await page.title()
            if page_title:
                # " | テキスト表示 | 国会会議録検索システム" を削除
                if " | " in page_title:
                    return page_title.split(" | ")[0].strip()
                return page_title

        except Exception as e:
            logger.warning(f"Error extracting title: {e}")

        return ""

    async def _extract_content(self, page: Page) -> str:
        """本文を抽出"""
        content_parts: list[str] = []

        try:
            # テーブル内の発言データを取得
            tables = await page.query_selector_all("table")

            for table in tables:
                # テーブル内の行を取得
                rows = await table.query_selector_all("tr")
                for row in rows:
                    # 発言者情報と発言内容を含む行を探す
                    cells = await row.query_selector_all("td")
                    if len(cells) >= 2:
                        # 最初のセルが発言者、二番目が内容の可能性
                        content_cell = cells[1] if len(cells) > 1 else None

                        if content_cell:
                            content_text = await content_cell.inner_text()
                            if (
                                content_text
                                and content_text.strip()
                                and len(content_text.strip()) > 20
                            ):
                                content_parts.append(content_text.strip())

            # テーブルからコンテンツが取得できない場合
            if not content_parts:
                logger.warning(
                    "No content found in tables, trying alternative approach"
                )
                # 全体のテキストを取得
                body_text = await page.inner_text("body")
                if body_text:
                    # 不要な部分を除去
                    lines = body_text.split("\n")
                    for line in lines:
                        line = line.strip()
                        # 長いテキストで、ナビゲーションやヘッダーでないもの
                        skip_words = [
                            "シンプル表示",
                            "ヘルプ",
                            "検索",
                            "ダウンロード",
                        ]
                        if len(line) > 50 and not any(
                            skip in line for skip in skip_words
                        ):
                            content_parts.append(line)

        except Exception as e:
            logger.error(f"Error extracting content: {e}")

        return "\n\n".join(content_parts)

    async def _extract_speakers(self, page: Page) -> list[SpeakerData]:
        """発言者情報を抽出"""
        speakers: list[SpeakerData] = []
        seen_speakers: set[str] = set()

        try:
            # div[class*="speaker"] 要素から発言者情報を取得
            speaker_divs = await page.query_selector_all('div[class*="speaker"]')

            if speaker_divs:
                logger.info(f"Found {len(speaker_divs)} speaker divs")
                for div in speaker_divs:
                    # 発言者名を取得
                    text = await div.inner_text()
                    if text and text.strip():
                        # 発言番号と発言者名を分離
                        # 例: "001　牧義夫　発言者情報"
                        parts = text.split()
                        if len(parts) >= 2:
                            # 数字で始まる部分をスキップ
                            name_parts: list[str] = []
                            skip_terms = ["発言者情報", "会議録情報"]
                            for part in parts:
                                if not part[0].isdigit() and part not in skip_terms:
                                    name_parts.append(part)

                            if name_parts:
                                name = " ".join(name_parts)
                                if name not in seen_speakers and name != "会議録情報":
                                    seen_speakers.add(name)
                                    speakers.append(
                                        SpeakerData(
                                            name=self._normalize_speaker_name(name),
                                            role=self._extract_role(name),
                                            content="",
                                        )
                                    )

            logger.info(f"Extracted {len(speakers)} speakers")

        except Exception as e:
            logger.warning(f"Error extracting speakers: {e}")

        return speakers

    def _normalize_speaker_name(self, name: str) -> str:
        """発言者名を正規化"""
        # 役職や記号を除去
        name = re.sub(r"[（(].+?[）)]", "", name)
        name = re.sub(r"○|◯|●|◎|△|▲|□|■", "", name)
        name = name.replace("君", "").replace("議員", "")
        return name.strip()

    def _extract_role(self, name: str) -> str:
        """役職を抽出"""
        # 括弧内の役職を抽出
        match = re.search(r"[（(](.+?)[）)]", name)
        if match:
            return match.group(1)

        # 特定の役職キーワードを探す
        roles = ["委員長", "議長", "大臣", "政務官", "参考人", "公述人"]
        for role in roles:
            if role in name:
                return role

        return ""

    def _parse_date(self, date_str: str) -> datetime | None:
        """日付文字列をパース"""
        if not date_str:
            return None

        # 複数の日付フォーマットを試す
        date_formats = [
            "%Y年%m月%d日",
            "%Y/%m/%d",
            "%Y-%m-%d",
            "%Y.%m.%d",
            "%Y%m%d",
        ]

        # 和暦対応
        date_str = date_str.replace("令和", "R")
        date_str = date_str.replace("平成", "H")
        date_str = date_str.replace("昭和", "S")

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # 和暦をパース
        wareki_match = re.match(r"([RHS])(\d+)年(\d+)月(\d+)日", date_str)
        if wareki_match:
            era, year, month, day = wareki_match.groups()
            year = int(year)

            # 和暦から西暦に変換
            if era == "R":  # 令和
                year += 2018
            elif era == "H":  # 平成
                year += 1988
            elif era == "S":  # 昭和
                year += 1925

            try:
                return datetime(year, int(month), int(day))
            except ValueError:
                pass

        logger.warning(f"Failed to parse date: {date_str}")
        return None

    def _extract_ids_from_url(self, url: str) -> tuple[str, str]:
        """URLからIDを抽出"""
        # minIdパラメータを探す
        match = re.search(r"minId=(\w+)", url)
        if match:
            min_id = match.group(1)
            # minIdを council_id と schedule_id に分割
            # 例: 121705253X00320250423
            # -> council: kokkai_121705253, schedule: X00320250423
            if len(min_id) > 10:
                return f"kokkai_{min_id[:9]}", min_id[9:]
            else:
                return f"kokkai_{min_id}", "1"

        # デフォルト値
        return "kokkai_unknown", "1"

    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出（BaseScraper abstract method）"""
        # この実装はPlaywrightを使用するため、fetch_minutesメソッド内で処理
        return ""

    async def extract_speakers(self, html_content: str) -> list[SpeakerData]:
        """HTMLから発言者情報を抽出（BaseScraper abstract method）"""
        # この実装はPlaywrightを使用するため、fetch_minutesメソッド内で処理
        return []
