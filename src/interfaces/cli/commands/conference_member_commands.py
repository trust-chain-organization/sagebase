"""Commands for managing conference member extraction and matching"""

import asyncio
import logging
from datetime import date, datetime
from typing import Any

import click

from src.conference_member_extractor.matching_service import (
    ConferenceMemberMatchingService,
)
from src.infrastructure.exceptions import DatabaseError, ScrapingError
from src.infrastructure.external.conference_member_extractor.extractor import (
    ConferenceMemberExtractor,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.cli.base import BaseCommand
from src.interfaces.cli.progress import ProgressTracker

logger = logging.getLogger(__name__)


class ConferenceMemberCommands(BaseCommand):
    """Commands for conference member extraction and matching"""

    @staticmethod
    def echo_info(message: str):
        """Show an info message"""
        click.echo(message)

    @staticmethod
    def echo_success(message: str):
        """Show a success message"""
        click.echo(click.style(f"✓ {message}", fg="green"))

    @staticmethod
    def echo_warning(message: str):
        """Show a warning message"""
        click.echo(click.style(f"⚠️  {message}", fg="yellow"))

    @staticmethod
    def echo_error(message: str):
        """Show an error message"""
        click.echo(click.style(f"✗ {message}", fg="red"), err=True)

    def get_commands(self) -> list[click.Command]:
        """Get list of conference member commands"""
        return [
            ConferenceMemberCommands.extract_conference_members,
            ConferenceMemberCommands.match_conference_members,
            ConferenceMemberCommands.create_affiliations,
            ConferenceMemberCommands.member_status,
        ]

    @staticmethod
    @click.command("extract-conference-members")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合はURLが設定されている全会議体を処理）",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="既存の抽出データを削除して再抽出",
    )
    def extract_conference_members(
        conference_id: int | None = None, force: bool = False
    ):
        """会議体の議員紹介URLから議員情報を抽出（ステップ1）"""

        click.echo("📋 会議体メンバー情報の抽出を開始します（ステップ1/3）")

        # 対象の会議体を取得
        conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

        if conference_id:
            # 特定の会議体のみ
            conference = conf_repo.get_conference_by_id(conference_id)
            if not conference:
                ConferenceMemberCommands.echo_error(
                    f"会議体ID {conference_id} が見つかりません"
                )
                conf_repo.close()
                return
            conferences = [conference]
        else:
            # URLが設定されている全会議体
            all_conferences = conf_repo.get_all_conferences()
            conferences = [
                conf for conf in all_conferences if conf.get("members_introduction_url")
            ]

            if not conferences:
                ConferenceMemberCommands.echo_warning(
                    "議員紹介URLが設定されている会議体がありません"
                )
                conf_repo.close()
                return

        ConferenceMemberCommands.echo_info(f"処理対象: {len(conferences)}件の会議体")

        # 抽出器を初期化
        extractor = ConferenceMemberExtractor()
        extracted_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)

        # 各会議体を処理
        total_extracted = 0
        total_saved = 0

        with ProgressTracker(
            total_steps=len(conferences), description="抽出中"
        ) as progress:
            for conf in conferences:
                progress.set_description(f"抽出中: {conf['name']}")

                # 既存データの処理
                if force:
                    deleted = extracted_repo.delete_extracted_members(conf["id"])
                    if deleted > 0:
                        ConferenceMemberCommands.echo_warning(
                            f"  既存の抽出データ{deleted}件を削除しました"
                        )

                try:
                    # 抽出実行
                    result: dict[str, Any] = asyncio.run(
                        extractor.extract_and_save_members(
                            conference_id=conf["id"],
                            conference_name=conf["name"],
                            url=conf["members_introduction_url"],
                        )
                    )

                    if result.get("error"):
                        ConferenceMemberCommands.echo_error(
                            f"  ❌ エラー: {conf['name']} - {result['error']}"
                        )
                    else:
                        total_extracted += int(result["extracted_count"])
                        total_saved += int(result["saved_count"])

                        ConferenceMemberCommands.echo_success(
                            f"  ✓ {conf['name']}: {result['extracted_count']}人を抽出、"
                            f"{result['saved_count']}人を保存"
                        )

                except (ScrapingError, DatabaseError) as e:
                    ConferenceMemberCommands.echo_error(
                        f"  ❌ エラー: {conf['name']} - {str(e)}"
                    )
                    logger.error(f"Error processing conference {conf['id']}: {e}")
                except Exception as e:
                    ConferenceMemberCommands.echo_error(
                        f"  ❌ 予期しないエラー: {conf['name']} - {str(e)}"
                    )
                    logger.exception(
                        f"Unexpected error processing conference {conf['id']}"
                    )
                    # Wrap in ScrapingError for proper handling
                    raise ScrapingError(
                        f"Failed to extract members from conference {conf['id']}",
                        {"conference_id": conf["id"], "error": str(e)},
                    ) from e

                progress.update(1)

        # 最終結果
        ConferenceMemberCommands.echo_info("\n=== 抽出完了 ===")
        ConferenceMemberCommands.echo_success(f"✅ 抽出総数: {total_extracted}人")
        ConferenceMemberCommands.echo_success(f"✅ 保存総数: {total_saved}人")

        # サマリー表示
        summary = extracted_repo.get_extraction_summary()
        ConferenceMemberCommands.echo_info("\n📊 ステータス別件数:")
        ConferenceMemberCommands.echo_info(f"  未処理: {summary['pending']}件")
        ConferenceMemberCommands.echo_info(f"  マッチ済: {summary['matched']}件")
        ConferenceMemberCommands.echo_info(f"  該当なし: {summary['no_match']}件")
        ConferenceMemberCommands.echo_info(f"  要確認: {summary['needs_review']}件")

        conf_repo.close()
        extractor.close()
        extracted_repo.close()

    @staticmethod
    @click.command("match-conference-members")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全ての未処理データを処理）",
    )
    def match_conference_members(conference_id: int | None = None):
        """抽出した議員情報を既存の政治家データとマッチング（ステップ2）"""

        ConferenceMemberCommands.echo_info(
            "🔍 議員情報のマッチングを開始します（ステップ2/3）"
        )

        # マッチングサービスを初期化
        matching_service = ConferenceMemberMatchingService()

        # 処理実行
        ConferenceMemberCommands.echo_info(
            "LLMを使用して政治家データとマッチングします..."
        )

        with ProgressTracker(
            total_steps=1, description="マッチング処理中..."
        ) as progress:
            results: dict[str, Any] = matching_service.process_pending_members(
                conference_id
            )

            progress.update(1)

        # 結果表示
        ConferenceMemberCommands.echo_info("\n=== マッチング完了 ===")
        ConferenceMemberCommands.echo_info(f"処理総数: {results['total']}件")
        ConferenceMemberCommands.echo_success(f"✅ マッチ成功: {results['matched']}件")
        ConferenceMemberCommands.echo_warning(f"⚠️  要確認: {results['needs_review']}件")
        ConferenceMemberCommands.echo_error(f"❌ 該当なし: {results['no_match']}件")

        if results["error"] > 0:
            ConferenceMemberCommands.echo_error(f"❌ エラー: {results['error']}件")

        matching_service.close()

    @staticmethod
    @click.command("create-affiliations")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全てのマッチ済データを処理）",
    )
    @click.option(
        "--start-date",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="所属開始日（デフォルト: 今日）",
    )
    def create_affiliations(
        conference_id: int | None = None, start_date: datetime | None = None
    ):
        """マッチング済みデータから政治家所属情報を作成（ステップ3）"""

        ConferenceMemberCommands.echo_info(
            "🏛️ 政治家所属情報の作成を開始します（ステップ3/3）"
        )

        # 開始日の処理
        start_date_obj: date
        if start_date:
            start_date_obj = start_date.date()
        else:
            start_date_obj = date.today()

        ConferenceMemberCommands.echo_info(f"所属開始日: {start_date_obj}")

        # マッチングサービスを初期化
        matching_service = ConferenceMemberMatchingService()

        # 処理実行
        with ProgressTracker(
            total_steps=1, description="所属情報作成中..."
        ) as progress:
            results: dict[str, Any] = matching_service.create_affiliations_from_matched(
                conference_id, start_date_obj
            )

            progress.update(1)

        # 結果表示
        ConferenceMemberCommands.echo_info("\n=== 所属情報作成完了 ===")
        ConferenceMemberCommands.echo_info(f"処理総数: {results['total']}件")
        ConferenceMemberCommands.echo_success(f"✅ 作成/更新: {results['created']}件")

        if results["failed"] > 0:
            ConferenceMemberCommands.echo_error(f"❌ 失敗: {results['failed']}件")

        matching_service.close()

    @staticmethod
    @click.command("member-status")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全体のステータスを表示）",
    )
    def member_status(conference_id: int | None = None):
        """抽出・マッチング状況を表示"""

        ConferenceMemberCommands.echo_info("📊 会議体メンバー抽出・マッチング状況")

        extracted_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)

        # 全体サマリー
        summary = extracted_repo.get_extraction_summary()

        ConferenceMemberCommands.echo_info("\n=== 全体ステータス ===")
        ConferenceMemberCommands.echo_info(f"総件数: {summary['total']}件")
        ConferenceMemberCommands.echo_info(f"  📋 未処理: {summary['pending']}件")
        ConferenceMemberCommands.echo_success(f"  ✅ マッチ済: {summary['matched']}件")
        ConferenceMemberCommands.echo_warning(
            f"  ⚠️  要確認: {summary['needs_review']}件"
        )
        ConferenceMemberCommands.echo_error(f"  ❌ 該当なし: {summary['no_match']}件")

        # 会議体別の詳細
        if conference_id:
            ConferenceMemberCommands.echo_info(
                f"\n=== 会議体ID {conference_id} の詳細 ==="
            )

            # 未処理メンバー
            pending = extracted_repo.get_pending_members(conference_id)
            if pending:
                ConferenceMemberCommands.echo_info(
                    f"\n📋 未処理メンバー ({len(pending)}人):"
                )
                for member in pending[:10]:  # 最初の10件
                    role = (
                        f" ({member['extracted_role']})"
                        if member.get("extracted_role")
                        else ""
                    )
                    party = (
                        f" - {member['extracted_party_name']}"
                        if member.get("extracted_party_name")
                        else ""
                    )
                    ConferenceMemberCommands.echo_info(
                        f"  • {member['extracted_name']}{role}{party}"
                    )
                if len(pending) > 10:
                    ConferenceMemberCommands.echo_info(
                        f"  ... 他 {len(pending) - 10}人"
                    )

            # マッチ済みメンバー
            matched = extracted_repo.get_matched_members(conference_id)
            if matched:
                ConferenceMemberCommands.echo_success(
                    f"\n✅ マッチ済みメンバー ({len(matched)}人):"
                )
                for member in matched[:10]:  # 最初の10件
                    role = (
                        f" ({member['extracted_role']})"
                        if member.get("extracted_role")
                        else ""
                    )
                    ConferenceMemberCommands.echo_success(
                        f"  • {member['extracted_name']}{role} → "
                        f"{member['politician_name']} "
                        f"(信頼度: {member['matching_confidence']:.2f})"
                    )
                if len(matched) > 10:
                    ConferenceMemberCommands.echo_success(
                        f"  ... 他 {len(matched) - 10}人"
                    )

        extracted_repo.close()


def get_conference_member_commands():
    """Get conference member command group"""
    return ConferenceMemberCommands().get_commands()
