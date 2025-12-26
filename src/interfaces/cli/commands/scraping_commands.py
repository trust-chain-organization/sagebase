"""CLI commands for web scraping operations"""

import asyncio
import sys
from pathlib import Path

import click

from ..base import BaseCommand, with_error_handling
from ..progress import ProgressTracker, spinner


class ScrapingCommands(BaseCommand):
    """Commands for scraping meeting minutes and related data"""

    @staticmethod
    @click.command()
    @click.argument("url", required=False)
    @click.option(
        "--meeting-id",
        type=int,
        help="Meeting ID to scrape (alternative to URL)",
    )
    @click.option(
        "--output-dir",
        default="data/scraped",
        help="Output directory for scraped content",
    )
    @click.option(
        "--format",
        type=click.Choice(["txt", "json", "both"]),
        default="both",
        help="Output format",
    )
    @click.option("--no-cache", is_flag=True, help="Ignore cache and force re-scraping")
    @click.option(
        "--upload-to-gcs",
        is_flag=True,
        help="Upload scraped files to Google Cloud Storage",
    )
    @click.option(
        "--gcs-bucket", help="GCS bucket name (overrides environment variable)"
    )
    @with_error_handling
    def scrape_minutes(
        url: str | None,
        meeting_id: int | None,
        output_dir: str,
        format: str,
        no_cache: bool,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Scrape meeting minutes from council website (議事録Web取得)

        This command fetches meeting minutes from supported council websites
        and saves them as text or JSON files.

        You can specify either a URL or a meeting ID:

        Example with URL:
            sagebase scrape-minutes "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"

        Example with meeting ID:
            sagebase scrape-minutes --meeting-id 123
        """
        # URLとmeeting-idの両方が指定されていない、
        # または両方が指定されている場合はエラー
        if (url is None and meeting_id is None) or (
            url is not None and meeting_id is not None
        ):
            click.echo(
                "Error: Specify either URL or --meeting-id, but not both", err=True
            )
            sys.exit(1)

        if url:
            ScrapingCommands.show_progress(f"Scraping minutes from: {url}")
        else:
            ScrapingCommands.show_progress(
                f"Scraping minutes for meeting ID: {meeting_id}"
            )

        # Run the async scraping operation
        success = asyncio.run(
            ScrapingCommands._async_scrape_minutes(
                url, meeting_id, output_dir, format, no_cache, upload_to_gcs, gcs_bucket
            )
        )

        sys.exit(0 if success else 1)

    @staticmethod
    async def _async_scrape_minutes(
        url: str | None,
        meeting_id: int | None,
        output_dir: str,
        format: str,
        no_cache: bool,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Async implementation of scrape_minutes"""
        import os

        from src.infrastructure.persistence.meeting_repository_impl import (
            MeetingRepositoryImpl,
        )
        from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
        from src.web_scraper.scraper_service import ScraperService

        # GCS設定の上書き
        if gcs_bucket:
            os.environ["GCS_BUCKET_NAME"] = gcs_bucket

        # サービス初期化
        with spinner("Initializing scraper service"):
            service = ScraperService(enable_gcs=upload_to_gcs)

        # スクレイピング実行
        if url:
            with spinner(f"Fetching minutes from: {url}") as spin:
                minutes = await service.fetch_from_url(url, use_cache=not no_cache)
                spin.stop(
                    "✓ Minutes fetched successfully"
                    if minutes
                    else "✗ Failed to fetch minutes"
                )
        else:  # meeting_id が指定されている場合
            assert meeting_id is not None  # Type narrowing for pyright
            with spinner(f"Fetching minutes for meeting ID: {meeting_id}") as spin:
                minutes = await service.fetch_from_meeting_id(
                    meeting_id, use_cache=not no_cache
                )
                spin.stop(
                    "✓ Minutes fetched successfully"
                    if minutes
                    else "✗ Failed to fetch minutes"
                )

        if not minutes:
            ScrapingCommands.error("Failed to scrape minutes", exit_code=0)
            return False

        # 出力ディレクトリ作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイル名生成
        base_name = f"{minutes.council_id}_{minutes.schedule_id}"

        # GCS URIを保存するための変数
        gcs_text_uri = None
        gcs_pdf_uri = None

        # テキスト形式で保存
        if format in ["txt", "both"]:
            txt_path = output_path / f"{base_name}.txt"
            success, gcs_url = service.export_to_text(
                minutes, str(txt_path), upload_to_gcs=upload_to_gcs
            )
            if success:
                ScrapingCommands.show_progress(f"Saved text to: {txt_path}")
                if gcs_url:
                    ScrapingCommands.show_progress(f"Uploaded to GCS: {gcs_url}")
                    gcs_text_uri = gcs_url
            else:
                ScrapingCommands.error("Failed to save text file", exit_code=0)

        # JSON形式で保存
        if format in ["json", "both"]:
            json_path = output_path / f"{base_name}.json"
            success, gcs_url = service.export_to_json(
                minutes, str(json_path), upload_to_gcs=upload_to_gcs
            )
            if success:
                ScrapingCommands.show_progress(f"Saved JSON to: {json_path}")
                if gcs_url:
                    ScrapingCommands.show_progress(f"Uploaded to GCS: {gcs_url}")
            else:
                ScrapingCommands.error("Failed to save JSON file", exit_code=0)

        # PDFをGCSにアップロード（PDFがローカルに保存されている場合）
        if upload_to_gcs and minutes.pdf_url:
            pdf_path = output_path / f"{base_name}.pdf"
            if pdf_path.exists():
                gcs_url = service.upload_pdf_to_gcs(str(pdf_path), minutes)
                if gcs_url:
                    ScrapingCommands.show_progress(f"Uploaded PDF to GCS: {gcs_url}")
                    gcs_pdf_uri = gcs_url

        # meetingsテーブルのGCS URIを更新
        if gcs_text_uri or gcs_pdf_uri:
            try:
                with spinner("Updating meeting record with GCS URIs"):
                    repo = RepositoryAdapter(MeetingRepositoryImpl)
                    meeting_id_to_update: int | None = None

                    # meeting IDベースの場合
                    if meeting_id is not None:
                        meeting_id_to_update = meeting_id
                        ScrapingCommands.show_progress(
                            f"Updating meeting ID {meeting_id} with GCS URIs"
                        )
                    # URLベースの場合
                    elif url:
                        # URLでmeetingを検索（パラメータの順序が異なる場合も考慮）
                        # 完全一致で検索
                        meetings = repo.fetch_as_dict(
                            "SELECT id FROM meetings WHERE url = :url", {"url": url}
                        )

                        # 完全一致で見つからない場合、LIKE検索を試す
                        if not meetings:
                            # minIdがURLに含まれている場合の処理
                            if "minId=" in url:
                                min_id = url.split("minId=")[1].split("&")[0]
                                meetings = repo.fetch_as_dict(
                                    "SELECT id FROM meetings WHERE url LIKE :pattern",
                                    {"pattern": f"%minId={min_id}%"},
                                )
                            # kaigiroku.netのURLパターンの場合
                            elif "council_id=" in url and "schedule_id=" in url:
                                # council_idとschedule_idを抽出
                                council_id_match = url.split("council_id=")[1].split(
                                    "&"
                                )[0]
                                schedule_id_match = url.split("schedule_id=")[1].split(
                                    "&"
                                )[0]
                                meetings = repo.fetch_as_dict(
                                    "SELECT id FROM meetings WHERE url LIKE :pattern",
                                    {
                                        "pattern": (
                                            f"%council_id={council_id_match}%"
                                            f"schedule_id={schedule_id_match}%"
                                        )
                                    },
                                )

                        if meetings:
                            meeting_id_to_update = meetings[0]["id"]
                            ScrapingCommands.show_progress(
                                f"Found meeting ID {meeting_id_to_update} for URL"
                            )
                        else:
                            ScrapingCommands.show_progress(
                                f"Warning: Could not find meeting record for URL: {url}"
                            )

                    # GCS URIを更新
                    if meeting_id_to_update:
                        updated_meeting = repo.update_meeting_gcs_uris(
                            meeting_id_to_update, gcs_pdf_uri, gcs_text_uri
                        )
                        if updated_meeting:
                            msg = (
                                f"✓ Updated meeting {meeting_id_to_update} "
                                "with GCS URIs"
                            )
                            ScrapingCommands.show_progress(msg)
                            if gcs_pdf_uri:
                                ScrapingCommands.show_progress(
                                    f"  PDF URI: {gcs_pdf_uri}"
                                )
                            if gcs_text_uri:
                                ScrapingCommands.show_progress(
                                    f"  Text URI: {gcs_text_uri}"
                                )
                        else:
                            ScrapingCommands.show_progress(
                                f"✗ Failed to update meeting {meeting_id_to_update} "
                                "with GCS URIs"
                            )
                    repo.close()
            except Exception as e:
                ScrapingCommands.show_progress(f"✗ Error updating meeting record: {e}")

        # 基本情報を表示
        ScrapingCommands.show_progress("\n--- Minutes Summary ---")
        ScrapingCommands.show_progress(f"Title: {minutes.title}")
        date_str = minutes.date.strftime("%Y年%m月%d日") if minutes.date else "Unknown"
        ScrapingCommands.show_progress(f"Date: {date_str}")
        ScrapingCommands.show_progress(f"Speakers found: {len(minutes.speakers)}")
        ScrapingCommands.show_progress(
            f"Content length: {len(minutes.content)} characters"
        )
        if minutes.pdf_url:
            ScrapingCommands.show_progress(f"PDF URL: {minutes.pdf_url}")

        return True

    @staticmethod
    @click.command()
    @click.option(
        "--tenant",
        required=True,
        help="Tenant name in kaigiroku.net (e.g., kyoto, osaka, kobe)",
    )
    @click.option("--start-id", default=6000, help="Start council ID")
    @click.option("--end-id", default=6100, help="End council ID")
    @click.option("--max-schedule", default=10, help="Maximum schedule ID to try")
    @click.option("--output-dir", default="data/scraped/batch", help="Output directory")
    @click.option("--concurrent", default=3, help="Number of concurrent requests")
    @click.option(
        "--upload-to-gcs",
        is_flag=True,
        help="Upload scraped files to Google Cloud Storage",
    )
    @click.option(
        "--gcs-bucket", help="GCS bucket name (overrides environment variable)"
    )
    @with_error_handling
    def batch_scrape(
        tenant: str,
        start_id: int,
        end_id: int,
        max_schedule: int,
        output_dir: str,
        concurrent: int,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Batch scrape multiple meeting minutes from kaigiroku.net (議事録一括取得)

        This command tries to scrape multiple meeting minutes from kaigiroku.net
        by iterating through council and schedule IDs.

        Examples:
            sagebase batch-scrape --tenant kyoto --start-id 6000 --end-id 6010
            sagebase batch-scrape --tenant osaka --start-id 1000 --end-id 1100
        """
        ScrapingCommands.show_progress(
            f"Batch scraping from kaigiroku.net tenant: {tenant}"
        )
        ScrapingCommands.show_progress(f"Council IDs: {start_id} to {end_id}")
        ScrapingCommands.show_progress(f"Schedule IDs: 1 to {max_schedule}")

        # URL生成
        base_url = f"https://ssp.kaigiroku.net/tenant/{tenant}/MinuteView.html"
        urls: list[str] = []
        for council_id in range(start_id, end_id + 1):
            for schedule_id in range(1, max_schedule + 1):
                url = f"{base_url}?council_id={council_id}&schedule_id={schedule_id}"
                urls.append(url)

        ScrapingCommands.show_progress(f"Total URLs to try: {len(urls)}")

        if not ScrapingCommands.confirm("Do you want to continue?"):
            return

        # Run the async batch processing
        success_count = asyncio.run(
            ScrapingCommands._async_batch_scrape(
                urls, output_dir, concurrent, upload_to_gcs, gcs_bucket
            )
        )

        ScrapingCommands.success(
            f"Saved {success_count} meeting minutes to {output_dir}"
        )

    @staticmethod
    async def _async_batch_scrape(
        urls: list[str],
        output_dir: str,
        concurrent: int,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Async implementation of batch_scrape"""
        import os

        from src.infrastructure.persistence.meeting_repository_impl import (
            MeetingRepositoryImpl,
        )
        from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
        from src.web_scraper.scraper_service import ScraperService

        # GCS設定の上書き
        if gcs_bucket:
            os.environ["GCS_BUCKET_NAME"] = gcs_bucket

        # サービス初期化
        service = ScraperService(enable_gcs=upload_to_gcs)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # バッチ処理実行
        success_count = 0
        gcs_update_count = 0

        with ProgressTracker(len(urls), "Scraping minutes") as tracker:
            results = await service.fetch_multiple(urls, max_concurrent=concurrent)

            for i, (url, minutes) in enumerate(zip(urls, results, strict=False)):
                tracker.update(1, f"Processing {i + 1}/{len(urls)}")
                if minutes:
                    # テキストとJSONで保存
                    base_name = f"{minutes.council_id}_{minutes.schedule_id}"
                    txt_path = output_path / f"{base_name}.txt"
                    json_path = output_path / f"{base_name}.json"

                    # テキスト形式で保存（GCS対応）
                    txt_success, txt_gcs_url = service.export_to_text(
                        minutes, str(txt_path), upload_to_gcs=upload_to_gcs
                    )

                    # JSON形式で保存（GCS対応）
                    json_success, json_gcs_url = service.export_to_json(
                        minutes, str(json_path), upload_to_gcs=upload_to_gcs
                    )

                    if txt_success and json_success:
                        success_count += 1
                        if txt_gcs_url or json_gcs_url:
                            ScrapingCommands.show_progress(
                                f"Scraped and uploaded: {base_name}"
                            )

                            # meetingsテーブルのGCS URIを更新
                            try:
                                repo = RepositoryAdapter(MeetingRepositoryImpl)

                                # kaigiroku.netのURLパターンから会議を検索
                                if "council_id=" in url and "schedule_id=" in url:
                                    council_id_match = url.split("council_id=")[
                                        1
                                    ].split("&")[0]
                                    schedule_id_match = url.split("schedule_id=")[
                                        1
                                    ].split("&")[0]
                                    query = (
                                        "SELECT id FROM meetings "
                                        "WHERE url LIKE :pattern"
                                    )
                                    meetings = repo.fetch_as_dict(
                                        query,
                                        {
                                            "pattern": (
                                                f"%council_id={council_id_match}%"
                                                f"schedule_id={schedule_id_match}%"
                                            )
                                        },
                                    )

                                    if meetings:
                                        meeting_id = meetings[0]["id"]
                                        updated = repo.update_meeting_gcs_uris(
                                            meeting_id,
                                            None,  # PDFは現在対応していない
                                            txt_gcs_url,
                                        )
                                        if updated:
                                            gcs_update_count += 1
                                            msg = (
                                                f"  ✓ Updated meeting {meeting_id} "
                                                "with GCS URIs"
                                            )
                                            ScrapingCommands.show_progress(msg)
                                repo.close()
                            except Exception as e:
                                ScrapingCommands.show_progress(
                                    f"  Note: Could not update meeting record: {e}"
                                )

        ScrapingCommands.show_progress(
            f"\nCompleted: {success_count}/{len(urls)} URLs successfully scraped"
        )
        if gcs_update_count > 0:
            ScrapingCommands.show_progress(
                f"Updated {gcs_update_count} meeting records with GCS URIs"
            )
        return success_count


def get_scraping_commands():
    """Get all scraping-related commands"""
    return [ScrapingCommands.scrape_minutes, ScrapingCommands.batch_scrape]
