"""Direct PDF scraper for downloading and extracting text from PDF URLs"""

import logging
from datetime import datetime
from urllib.parse import urlparse

from .base_scraper import BaseScraper
from .handlers.pdf_handler import PDFHandler
from .models.scraped_data import MinutesData, SpeakerData


class PDFScraper(BaseScraper):
    """PDFファイルを直接ダウンロードして処理するスクレイパー"""

    def __init__(self, logger: logging.Logger | None = None):
        super().__init__(logger)
        self.pdf_handler = PDFHandler(logger=self.logger)

    async def fetch_minutes(self, url: str) -> MinutesData | None:
        """PDFのURLから議事録を取得

        Args:
            url: PDFファイルのURL

        Returns:
            MinutesData or None
        """
        self.logger.info(f"Fetching PDF from: {url}")

        # PDFをダウンロードしてテキストを抽出
        pdf_path, text_content = await self.pdf_handler.download_and_extract(url)

        if not pdf_path or not text_content:
            self.logger.error("Failed to download or extract PDF")
            return None

        # URLからcouncil_idとschedule_idを生成
        council_id, schedule_id = self._generate_ids_from_url(url)

        # PDFファイル名からタイトルを生成
        title = self._extract_title_from_url(url)

        # MinutesDataオブジェクトを作成
        minutes = MinutesData(
            council_id=council_id,
            schedule_id=schedule_id,
            title=title,
            date=None,  # PDFから日付を抽出できない場合はNone
            content=text_content,
            speakers=[],  # PDFからは発言者を抽出しない
            url=url,
            scraped_at=datetime.now(),
            pdf_url=url,
            metadata={"source_type": "direct_pdf", "pdf_path": pdf_path},
        )

        self.logger.info(f"Successfully extracted PDF: {len(text_content)} characters")
        return minutes

    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出（PDFスクレイパーでは使用しない）

        Args:
            html_content: HTML content (not used for PDF scraper)

        Returns:
            Empty string (PDF scraper extracts text directly from PDF)
        """
        return ""

    async def extract_speakers(self, html_content: str) -> list[SpeakerData]:
        """HTMLから発言者情報を抽出（PDFスクレイパーでは使用しない）

        Args:
            html_content: HTML content (not used for PDF scraper)

        Returns:
            Empty list (PDF scraper doesn't extract speakers)
        """
        return []

    def _generate_ids_from_url(self, url: str) -> tuple[str, str]:
        """URLからcouncil_idとschedule_idを生成

        Args:
            url: PDF URL

        Returns:
            (council_id, schedule_id)
        """
        import hashlib

        # URLのハッシュを使用してIDを生成
        url_hash = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

        # council_idとschedule_idを生成
        council_id = f"pdf_{url_hash[:8]}"
        schedule_id = url_hash[8:16]

        return council_id, schedule_id

    def _extract_title_from_url(self, url: str) -> str:
        """URLからタイトルを抽出

        Args:
            url: PDF URL

        Returns:
            Extracted title from URL
        """
        parsed = urlparse(url)
        path_parts = parsed.path.split("/")

        # 最後のパス要素をタイトルとして使用
        if path_parts and path_parts[-1]:
            filename = path_parts[-1]
            # .pdfを削除
            if filename.endswith(".pdf"):
                filename = filename[:-4]
            # アンダースコアやハイフンをスペースに置換
            title = filename.replace("_", " ").replace("-", " ")
            return title

        return "Untitled PDF Document"
