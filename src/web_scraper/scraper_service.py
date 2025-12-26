"""議事録スクレーパーサービス"""

import asyncio
import json
from pathlib import Path

from src.infrastructure.config import config

from ..common.logging import get_logger
from ..infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from ..infrastructure.persistence.repository_adapter import RepositoryAdapter
from ..utils.gcs_storage import GCSStorage
from .base_scraper import BaseScraper
from .kaigiroku_net_scraper import KaigirokuNetScraper
from .kokkai_scraper import KokkaiScraper
from .models import MinutesData


class ScraperService:
    """議事録スクレーパーの統合サービス"""

    def __init__(
        self, cache_dir: str = "./cache/minutes", enable_gcs: bool | None = None
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__)

        # GCS設定
        self.enable_gcs = (
            enable_gcs if enable_gcs is not None else config.GCS_UPLOAD_ENABLED
        )
        self.gcs_storage = None
        if self.enable_gcs:
            try:
                self.gcs_storage = GCSStorage(
                    bucket_name=config.GCS_BUCKET_NAME, project_id=config.GCS_PROJECT_ID
                )
                self.logger.info("GCS storage enabled", bucket=config.GCS_BUCKET_NAME)
            except Exception as e:
                self.logger.error(
                    "Failed to initialize GCS storage", error=str(e), exc_info=True
                )
                self.enable_gcs = False

    async def fetch_from_url(
        self, url: str, use_cache: bool = True
    ) -> MinutesData | None:
        """URLから議事録を取得"""
        # キャッシュチェック
        if use_cache:
            cached = self._get_from_cache(url)
            if cached:
                self.logger.info(f"Using cached data for {url}")
                return cached

        # URLから適切なスクレーパーを選択
        scraper = self._get_scraper_for_url(url)
        if not scraper:
            self.logger.error(f"No scraper available for URL: {url}")
            return None

        # スクレープ実行
        self.logger.info(f"Fetching minutes from {url}")
        try:
            minutes = await scraper.fetch_minutes(url)
            if minutes:
                # キャッシュに保存
                self._save_to_cache(url, minutes)
                return minutes
        except Exception as e:
            self.logger.error(f"Error fetching minutes: {e}")

        return None

    async def fetch_from_meeting_id(
        self, meeting_id: int, use_cache: bool = True
    ) -> MinutesData | None:
        """会議IDから議事録を取得

        Args:
            meeting_id: 会議ID
            use_cache: キャッシュを使用するかどうか

        Returns:
            MinutesData or None
        """
        # 会議情報を取得
        meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
        meeting = meeting_repo.get_by_id(meeting_id)

        if not meeting:
            self.logger.error(f"Meeting not found with ID: {meeting_id}")
            return None

        if not meeting.url:
            self.logger.error(f"Meeting ID {meeting_id} has no URL")
            return None

        self.logger.info(
            f"Fetching minutes for meeting ID {meeting_id} from URL: {meeting.url}"
        )

        # URLから議事録を取得
        return await self.fetch_from_url(meeting.url, use_cache=use_cache)

    async def fetch_multiple(
        self, urls: list[str], max_concurrent: int = 3
    ) -> list[MinutesData | None]:
        """複数のURLから並列で議事録を取得"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_limit(url: str) -> MinutesData | None:
            async with semaphore:
                return await self.fetch_from_url(url)

        tasks = [fetch_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)

    def _get_scraper_for_url(self, url: str) -> BaseScraper | None:
        """URLに基づいて適切なスクレーパーを選択"""
        # 直接PDF URLの場合
        if url.lower().endswith(".pdf"):
            from .pdf_scraper import PDFScraper

            return PDFScraper()

        # kaigiroku.netシステムの場合
        if "kaigiroku.net/tenant/" in url:
            return KaigirokuNetScraper()

        # 国会会議録検索システムの場合
        if "kokkai.ndl.go.jp" in url:
            return KokkaiScraper()

        # 今後、他の議事録システムのスクレーパーをここに追加
        # 例: 独自システムを使う自治体など

        return None

    def _get_cache_key(self, url: str) -> str:
        """URLからキャッシュキーを生成"""
        import hashlib

        return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()

    def _get_from_cache(self, url: str) -> MinutesData | None:
        """キャッシュから取得"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)

                # MinutesDataオブジェクトに変換
                return MinutesData.from_dict(data)
            except Exception as e:
                self.logger.warning(f"Failed to load cache for {url}: {e}")

        return None

    def _save_to_cache(self, url: str, minutes: MinutesData):
        """キャッシュに保存"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(minutes.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache for {url}: {e}")

    def export_to_pdf(self, minutes: MinutesData, output_path: str) -> bool:
        """議事録をPDFにエクスポート"""
        # TODO: PDFエクスポート機能の実装
        # reportlabやweasyprint等を使用
        return False

    def export_to_text(
        self, minutes: MinutesData, output_path: str, upload_to_gcs: bool = True
    ) -> tuple[bool, str | None]:
        """議事録をテキストファイルにエクスポート

        Args:
            minutes: 議事録データ
            output_path: 出力ファイルパス
            upload_to_gcs: GCSにアップロードするかどうか

        Returns:
            (成功フラグ, GCS URL or None)
        """
        gcs_url = None
        try:
            # テキスト内容を作成
            content = self._format_minutes_as_text(minutes)

            # ローカルに保存
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            # GCSにアップロード
            if upload_to_gcs and self.enable_gcs and self.gcs_storage:
                try:
                    gcs_path = self._generate_gcs_path(minutes, "txt")
                    gcs_url = self.gcs_storage.upload_content(
                        content=content,
                        gcs_path=gcs_path,
                        content_type="text/plain; charset=utf-8",
                    )
                    self.logger.info(f"Uploaded to GCS: {gcs_url}")
                except Exception as e:
                    self.logger.error(f"Failed to upload to GCS: {e}")

            return True, gcs_url
        except Exception as e:
            self.logger.error(f"Failed to export to text: {e}")
            return False, None

    def _format_minutes_as_text(self, minutes: MinutesData) -> str:
        """議事録をテキスト形式にフォーマット"""
        lines: list[str] = []
        lines.append(f"タイトル: {minutes.title}")
        lines.append(
            f"日付: {minutes.date.strftime('%Y年%m月%d日') if minutes.date else '不明'}"
        )
        lines.append(f"URL: {minutes.url}")
        lines.append("\n" + "=" * 50 + "\n")
        lines.append(minutes.content)

        if minutes.speakers:
            lines.append("\n" + "=" * 50)
            lines.append("発言者一覧:\n")
            for speaker in minutes.speakers:
                speaker_name = speaker.name
                if speaker.role:
                    speaker_name = f"{speaker.name}{speaker.role}"
                lines.append(f"【{speaker_name}】")
                lines.append(f"{speaker.content}\n")

        return "\n".join(lines)

    def _generate_gcs_path(self, minutes: MinutesData, extension: str) -> str:
        """GCSのパスを生成"""
        # MinutesDataからcouncil_idとschedule_idを使用
        council_id = minutes.council_id if minutes.council_id else "unknown"
        schedule_id = minutes.schedule_id if minutes.schedule_id else "unknown"

        # 日付ベースのディレクトリ構造
        date_str = minutes.date.strftime("%Y/%m/%d") if minutes.date else "unknown_date"

        return f"scraped/{date_str}/{council_id}_{schedule_id}.{extension}"

    def export_to_json(
        self, minutes: MinutesData, output_path: str, upload_to_gcs: bool = True
    ) -> tuple[bool, str | None]:
        """議事録をJSONファイルにエクスポート

        Args:
            minutes: 議事録データ
            output_path: 出力ファイルパス
            upload_to_gcs: GCSにアップロードするかどうか

        Returns:
            (成功フラグ, GCS URL or None)
        """
        gcs_url = None
        try:
            # JSON内容を作成
            content = json.dumps(minutes.to_dict(), ensure_ascii=False, indent=2)

            # ローカルに保存
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            # GCSにアップロード
            if upload_to_gcs and self.enable_gcs and self.gcs_storage:
                try:
                    gcs_path = self._generate_gcs_path(minutes, "json")
                    gcs_url = self.gcs_storage.upload_content(
                        content=content,
                        gcs_path=gcs_path,
                        content_type="application/json",
                    )
                    self.logger.info(f"Uploaded to GCS: {gcs_url}")
                except Exception as e:
                    self.logger.error(f"Failed to upload to GCS: {e}")

            return True, gcs_url
        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")
            return False, None

    def upload_pdf_to_gcs(self, pdf_path: str, minutes: MinutesData) -> str | None:
        """PDFファイルをGCSにアップロード

        Args:
            pdf_path: PDFファイルのローカルパス
            minutes: 議事録データ（メタデータ用）

        Returns:
            GCS URL or None
        """
        if not self.enable_gcs or not self.gcs_storage:
            return None

        try:
            gcs_path = self._generate_gcs_path(minutes, "pdf")
            gcs_url = self.gcs_storage.upload_file(
                local_path=pdf_path, gcs_path=gcs_path, content_type="application/pdf"
            )
            self.logger.info(f"Uploaded PDF to GCS: {gcs_url}")
            return gcs_url
        except Exception as e:
            self.logger.error(f"Failed to upload PDF to GCS: {e}")
            return None
