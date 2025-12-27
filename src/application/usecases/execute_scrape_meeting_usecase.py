"""会議スクレイピング実行ユースケース

このモジュールは、会議一覧画面からWebスクレイピング処理を実行するユースケースを提供します。
会議URLから議事録をスクレイピングし、GCSにアップロードしてMeetingエンティティを更新します。
"""

import logging

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.domain.repositories.meeting_repository import MeetingRepository
from src.web_scraper.scraper_service import ScraperService


logger = logging.getLogger(__name__)


@dataclass
class ExecuteScrapeMeetingDTO:
    """会議スクレイピング実行リクエストDTO"""

    meeting_id: int
    force_rescrape: bool = False
    upload_to_gcs: bool = True


@dataclass
class ScrapeMeetingResultDTO:
    """会議スクレイピング結果DTO"""

    meeting_id: int
    title: str
    speakers_count: int
    content_length: int
    gcs_text_uri: str | None
    gcs_pdf_uri: str | None
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


class ExecuteScrapeMeetingUseCase:
    """会議スクレイピング実行ユースケース

    会議URLから議事録をスクレイピングし、GCSにアップロードします。
    """

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        enable_gcs: bool = True,
    ):
        """ユースケースを初期化する

        Args:
            meeting_repository: 会議リポジトリ
            enable_gcs: GCS機能を有効にするか
        """
        self.meeting_repo = meeting_repository
        self.enable_gcs = enable_gcs

    async def execute(self, request: ExecuteScrapeMeetingDTO) -> ScrapeMeetingResultDTO:
        """会議スクレイピング処理を実行する

        Args:
            request: 処理リクエストDTO

        Returns:
            ScrapeMeetingResultDTO: 処理結果

        Raises:
            ValueError: 会議が見つからない、URLが設定されていない場合
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            # 会議情報を取得
            meeting = await self.meeting_repo.get_by_id(request.meeting_id)
            if not meeting:
                raise ValueError(f"Meeting {request.meeting_id} not found")

            if not meeting.url:
                raise ValueError(
                    f"Meeting {request.meeting_id} does not have a URL set"
                )

            # 強制再スクレイピングでない場合、既存のGCS URIをチェック
            if not request.force_rescrape:
                if meeting.gcs_text_uri or meeting.gcs_pdf_uri:
                    raise ValueError(
                        f"Meeting {request.meeting_id} already has scraped data "
                        "in GCS. Use force_rescrape=True to re-scrape."
                    )

            logger.info(
                f"Starting scraping for meeting {request.meeting_id}, "
                f"URL: {meeting.url}"
            )

            # ScraperServiceを初期化
            service = ScraperService(enable_gcs=request.upload_to_gcs)

            # スクレイピング実行
            minutes = await service.fetch_from_meeting_id(
                request.meeting_id, use_cache=not request.force_rescrape
            )

            if not minutes:
                raise ValueError(f"Failed to scrape minutes for meeting {meeting.url}")

            logger.info(
                f"Successfully scraped minutes: {minutes.title}, "
                f"{len(minutes.speakers)} speakers, "
                f"{len(minutes.content)} characters"
            )

            # 一時ディレクトリに保存してGCSにアップロード
            output_dir = Path("tmp/scraped")
            output_dir.mkdir(parents=True, exist_ok=True)

            base_name = f"{minutes.council_id}_{minutes.schedule_id}"
            txt_path = output_dir / f"{base_name}.txt"

            # テキスト形式で保存 + GCSアップロード
            txt_success, txt_gcs_url = service.export_to_text(
                minutes, str(txt_path), upload_to_gcs=request.upload_to_gcs
            )

            if not txt_success:
                errors.append("Failed to save scraped minutes to text file")

            gcs_text_uri = txt_gcs_url if request.upload_to_gcs else None
            gcs_pdf_uri = None  # PDFは現在サポートしていない

            # Meetingエンティティを更新
            if gcs_text_uri or gcs_pdf_uri:
                meeting.gcs_text_uri = gcs_text_uri
                meeting.gcs_pdf_uri = gcs_pdf_uri
                updated_meeting = await self.meeting_repo.update(meeting)

                if updated_meeting:
                    logger.info(
                        f"Updated meeting {request.meeting_id} with GCS URIs: "
                        f"text={gcs_text_uri}, pdf={gcs_pdf_uri}"
                    )
                else:
                    errors.append("Failed to update meeting with GCS URIs")

            # ローカルファイルをクリーンアップ
            if txt_path.exists():
                txt_path.unlink()
                logger.debug(f"Cleaned up temporary file: {txt_path}")

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            return ScrapeMeetingResultDTO(
                meeting_id=request.meeting_id,
                title=minutes.title,
                speakers_count=len(minutes.speakers),
                content_length=len(minutes.content),
                gcs_text_uri=gcs_text_uri,
                gcs_pdf_uri=gcs_pdf_uri,
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Meeting scraping failed: {e}", exc_info=True)
            raise
