"""PDF download and processing handler"""

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import aiohttp


try:
    import pypdfium2 as pdfium

    HAS_PDFIUM = True
except ImportError:
    pdfium = None
    HAS_PDFIUM = False

from src.infrastructure.config.settings import get_settings


class PDFHandler:
    """PDFファイルのダウンロードと処理を行うハンドラー"""

    def __init__(
        self, download_dir: str = "data/scraped", logger: logging.Logger | None = None
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self.settings = get_settings()

        if not HAS_PDFIUM:
            self.logger.warning(
                "pypdfium2 is not installed. PDF text extraction will not be available."
            )

    async def download_pdf(
        self, pdf_url: str, filename: str | None = None
    ) -> str | None:
        """PDFをダウンロード

        Args:
            pdf_url: PDFのURL
            filename: 保存するファイル名（省略時は自動生成）

        Returns:
            保存したファイルのパス or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    pdf_url,
                    timeout=aiohttp.ClientTimeout(
                        total=self.settings.pdf_download_timeout
                    ),
                ) as response:
                    if response.status != 200:
                        self.logger.error(
                            f"Failed to download PDF: HTTP {response.status}"
                        )
                        return None

                    # ファイル名を決定
                    if not filename:
                        filename = self._generate_filename(pdf_url)

                    # PDFを保存
                    pdf_path = self.download_dir / filename
                    pdf_content = await response.read()

                    with open(pdf_path, "wb") as f:
                        f.write(pdf_content)

                    self.logger.info(f"PDF saved to: {pdf_path}")
                    return str(pdf_path)

        except TimeoutError:
            self.logger.error(f"Timeout downloading PDF from {pdf_url}")
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")

        return None

    def _generate_filename(self, pdf_url: str) -> str:
        """URLからファイル名を生成"""
        # URLからファイル名を抽出
        parsed = urlparse(pdf_url)
        path_parts = parsed.path.split("/")

        if path_parts and path_parts[-1].endswith(".pdf"):
            return path_parts[-1]

        # デフォルトのファイル名を生成
        import hashlib

        url_hash = hashlib.md5(pdf_url.encode(), usedforsecurity=False).hexdigest()[:8]
        return f"document_{url_hash}.pdf"

    async def download_with_metadata(
        self, pdf_url: str, council_id: str, schedule_id: str
    ) -> str | None:
        """メタデータ付きでPDFをダウンロード

        Args:
            pdf_url: PDFのURL
            council_id: 議会ID
            schedule_id: スケジュールID

        Returns:
            保存したファイルのパス or None
        """
        filename = f"{council_id}_{schedule_id}.pdf"
        return await self.download_pdf(pdf_url, filename)

    def extract_text(self, pdf_path: str) -> str:
        """PDFからテキストを抽出

        Args:
            pdf_path: PDFファイルのパス

        Returns:
            抽出されたテキスト
        """
        if not HAS_PDFIUM:
            return (
                f"PDF text extraction not available. Please install pypdfium2. "
                f"PDF saved at: {pdf_path}"
            )

        try:
            assert pdfium is not None
            pdf = pdfium.PdfDocument(pdf_path)
            text_content: list[str] = []

            for page_num in range(len(pdf)):
                page = pdf[page_num]
                textpage = page.get_textpage()
                text: str = textpage.get_text_bounded()  # type: ignore
                if text:
                    text_content.append(f"--- Page {page_num + 1} ---")
                    text_content.append(text)

            pdf.close()
            return "\n".join(text_content)

        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
            return f"Error extracting text from PDF. File saved at: {pdf_path}"

    async def download_and_extract(
        self, pdf_url: str, filename: str | None = None
    ) -> tuple[str | None, str]:
        """PDFをダウンロードしてテキストを抽出

        Args:
            pdf_url: PDFのURL
            filename: 保存するファイル名（省略時は自動生成）

        Returns:
            (PDFのパス, 抽出されたテキスト)
        """
        pdf_path = await self.download_pdf(pdf_url, filename)

        if not pdf_path:
            return None, ""

        text_content = self.extract_text(pdf_path)
        return pdf_path, text_content

    def cleanup_old_files(self, days: int = 30):
        """古いPDFファイルを削除

        Args:
            days: この日数より古いファイルを削除
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)

        for pdf_file in self.download_dir.glob("*.pdf"):
            if pdf_file.stat().st_mtime < cutoff_time:
                try:
                    pdf_file.unlink()
                    self.logger.info(f"Deleted old PDF: {pdf_file}")
                except Exception as e:
                    self.logger.error(f"Error deleting {pdf_file}: {e}")

    def get_pdf_info(self, pdf_path: str) -> dict[str, int | str | bool]:
        """PDFの情報を取得

        Args:
            pdf_path: PDFファイルのパス

        Returns:
            PDFの情報（ページ数、ファイルサイズなど）
        """
        info: dict[str, int | str | bool] = {
            "path": pdf_path,
            "exists": os.path.exists(pdf_path),
            "size": 0,
            "pages": 0,
        }

        if info["exists"]:
            info["size"] = os.path.getsize(pdf_path)

            if HAS_PDFIUM:
                try:
                    assert pdfium is not None
                    pdf = pdfium.PdfDocument(pdf_path)
                    info["pages"] = len(pdf)
                    pdf.close()
                except Exception as e:
                    self.logger.error(f"Error getting PDF info: {e}")

        return info
