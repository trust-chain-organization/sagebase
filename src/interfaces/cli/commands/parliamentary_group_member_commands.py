"""Commands for managing parliamentary group member extraction and matching"""

import logging
from datetime import date, datetime

import click

from src.infrastructure.exceptions import DatabaseError, ScrapingError
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.cli.base import BaseCommand
from src.interfaces.cli.progress import ProgressTracker
from src.parliamentary_group_member_extractor.matching_service import (
    ParliamentaryGroupMemberMatchingService,
)

logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberCommands(BaseCommand):
    """Commands for parliamentary group member extraction and matching"""

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
        """Get list of parliamentary group member commands"""
        return [
            ParliamentaryGroupMemberCommands.extract_parliamentary_group_members,
            ParliamentaryGroupMemberCommands.match_parliamentary_group_members,
            ParliamentaryGroupMemberCommands.create_parliamentary_group_affiliations,  # noqa: E501
            ParliamentaryGroupMemberCommands.parliamentary_group_member_status,
        ]

    @staticmethod
    @click.command("extract-parliamentary-group-members")
    @click.option(
        "--parliamentary-group-id",
        type=int,
        help="議員団ID（指定しない場合はURLが設定されている全議員団を処理）",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="既存の抽出データを削除して再抽出",
    )
    def extract_parliamentary_group_members(
        parliamentary_group_id: int | None = None, force: bool = False
    ):
        """議員団のURLから議員情報を抽出（ステップ1）"""

        click.echo("📋 議員団メンバー情報の抽出を開始します（ステップ1/3）")

        # リポジトリの初期化
        group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl)
        extracted_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )

        # 対象の議員団を取得
        if parliamentary_group_id:
            # 特定の議員団のみ
            parliamentary_group = group_repo.get_parliamentary_group_by_id(
                parliamentary_group_id
            )
            if not parliamentary_group:
                ParliamentaryGroupMemberCommands.echo_error(
                    f"議員団ID {parliamentary_group_id} が見つかりません"
                )
                group_repo.close()
                extracted_repo.close()
                return

            if not parliamentary_group.get("url"):
                ParliamentaryGroupMemberCommands.echo_warning(
                    f"議員団 '{parliamentary_group['name']}' にURLが設定されていません"
                )
                group_repo.close()
                extracted_repo.close()
                return

            parliamentary_groups = [parliamentary_group]
        else:
            # URLが設定されている全議員団
            all_groups = group_repo.get_all_parliamentary_groups()
            parliamentary_groups = [g for g in all_groups if g.get("url")]

            if not parliamentary_groups:
                ParliamentaryGroupMemberCommands.echo_warning(
                    "URLが設定されている議員団がありません"
                )
                group_repo.close()
                extracted_repo.close()
                return

        ParliamentaryGroupMemberCommands.echo_info(
            f"処理対象: {len(parliamentary_groups)}件の議員団"
        )

        # 抽出器を初期化
        extractor = ParliamentaryGroupMemberExtractorFactory.create()

        # 各議員団を処理
        total_extracted = 0
        total_saved = 0

        with ProgressTracker(
            total_steps=len(parliamentary_groups), description="抽出中"
        ) as progress:
            for group in parliamentary_groups:
                progress.set_description(f"抽出中: {group['name']}")

                # 既存データの処理
                if force:
                    deleted = extracted_repo.delete_extracted_members(group["id"])
                    if deleted > 0:
                        ParliamentaryGroupMemberCommands.echo_warning(
                            f"  既存の抽出データ{deleted}件を削除しました"
                        )

                try:
                    # 抽出実行
                    result = extractor.extract_members_sync(
                        parliamentary_group_id=group["id"], url=group["url"]
                    )

                    if result.error:
                        ParliamentaryGroupMemberCommands.echo_error(
                            f"  ❌ エラー: {group['name']} - {result.error}"
                        )
                    else:
                        # ステージングテーブルに保存
                        save_result = extracted_repo.save_extracted_members(
                            parliamentary_group_id=group["id"],
                            members=result.extracted_members,
                            url=group["url"],
                        )

                        total_extracted += len(result.extracted_members)
                        total_saved += save_result

                        ParliamentaryGroupMemberCommands.echo_success(
                            f"  ✓ {group['name']}: "
                            f"{len(result.extracted_members)}人を抽出、"
                            f"{save_result}人を保存"
                        )

                except (ScrapingError, DatabaseError) as e:
                    ParliamentaryGroupMemberCommands.echo_error(
                        f"  ❌ エラー: {group['name']} - {str(e)}"
                    )
                    logger.error(
                        "Error processing parliamentary group %s: %s", group["id"], e
                    )
                except Exception as e:
                    ParliamentaryGroupMemberCommands.echo_error(
                        f"  ❌ 予期しないエラー: {group['name']} - {str(e)}"
                    )
                    logger.exception(
                        "Unexpected error processing parliamentary group %s",
                        group["id"],
                    )

                progress.update(1)

        # 最終結果
        ParliamentaryGroupMemberCommands.echo_info("\n=== 抽出完了 ===")
        ParliamentaryGroupMemberCommands.echo_success(
            f"✅ 抽出総数: {total_extracted}人"
        )
        ParliamentaryGroupMemberCommands.echo_success(f"✅ 保存総数: {total_saved}人")

        # サマリー表示
        summary = extracted_repo.get_extraction_summary()
        ParliamentaryGroupMemberCommands.echo_info("\n📊 ステータス別件数:")
        ParliamentaryGroupMemberCommands.echo_info(f"  未処理: {summary['pending']}件")
        ParliamentaryGroupMemberCommands.echo_info(
            f"  マッチ済: {summary['matched']}件"
        )
        ParliamentaryGroupMemberCommands.echo_info(
            f"  該当なし: {summary['no_match']}件"
        )
        ParliamentaryGroupMemberCommands.echo_info(
            f"  要確認: {summary['needs_review']}件"
        )

        group_repo.close()
        extracted_repo.close()

    @staticmethod
    @click.command("match-parliamentary-group-members")
    @click.option(
        "--parliamentary-group-id",
        type=int,
        help="議員団ID（指定しない場合は全ての未処理データを処理）",
    )
    def match_parliamentary_group_members(parliamentary_group_id: int | None = None):
        """抽出した議員情報を既存の政治家データとマッチング（ステップ2）"""

        ParliamentaryGroupMemberCommands.echo_info(
            "🔍 議員情報のマッチングを開始します（ステップ2/3）"
        )

        # マッチングサービスを初期化
        matching_service = ParliamentaryGroupMemberMatchingService()

        # 処理実行
        ParliamentaryGroupMemberCommands.echo_info(
            "LLMを使用して政治家データとマッチングします..."
        )

        with ProgressTracker(
            total_steps=1, description="マッチング処理中..."
        ) as progress:
            results = matching_service.process_pending_members(parliamentary_group_id)

            progress.update(1)

        # 結果表示
        ParliamentaryGroupMemberCommands.echo_info("\n=== マッチング完了 ===")
        ParliamentaryGroupMemberCommands.echo_info(f"処理総数: {results['total']}件")
        ParliamentaryGroupMemberCommands.echo_success(
            f"✅ マッチ成功: {results['matched']}件"
        )
        ParliamentaryGroupMemberCommands.echo_warning(
            f"⚠️  要確認: {results['needs_review']}件"
        )
        ParliamentaryGroupMemberCommands.echo_error(
            f"❌ 該当なし: {results['no_match']}件"
        )

        if results["error"] > 0:
            ParliamentaryGroupMemberCommands.echo_error(
                f"❌ エラー: {results['error']}件"
            )

        matching_service.close()

    @staticmethod
    @click.command("create-parliamentary-group-affiliations")
    @click.option(
        "--parliamentary-group-id",
        type=int,
        help="議員団ID（指定しない場合は全てのマッチ済データを処理）",
    )
    @click.option(
        "--start-date",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="所属開始日（デフォルト: 今日）",
    )
    @click.option(
        "--min-confidence",
        type=float,
        default=0.7,
        help="メンバーシップ作成の最低信頼度（デフォルト: 0.7）",
    )
    def create_parliamentary_group_affiliations(
        parliamentary_group_id: int | None = None,
        start_date: datetime | None = None,
        min_confidence: float = 0.7,
    ):
        """マッチング済みデータから議員団メンバーシップを作成（ステップ3）"""

        ParliamentaryGroupMemberCommands.echo_info(
            "🏛️ 議員団メンバーシップの作成を開始します（ステップ3/3）"
        )

        # 開始日の処理
        start_date_obj: date
        if start_date:
            start_date_obj = start_date.date()
        else:
            start_date_obj = date.today()

        ParliamentaryGroupMemberCommands.echo_info(f"所属開始日: {start_date_obj}")
        ParliamentaryGroupMemberCommands.echo_info(f"最低信頼度: {min_confidence}")

        # マッチングサービスを初期化
        matching_service = ParliamentaryGroupMemberMatchingService()

        # 処理実行
        with ProgressTracker(
            total_steps=1, description="メンバーシップ作成中..."
        ) as progress:
            results = matching_service.create_memberships_from_matched(
                parliamentary_group_id, start_date_obj
            )

            progress.update(1)

        # 結果表示
        ParliamentaryGroupMemberCommands.echo_info("\n=== メンバーシップ作成完了 ===")
        ParliamentaryGroupMemberCommands.echo_info(f"処理総数: {results['total']}件")
        ParliamentaryGroupMemberCommands.echo_success(
            f"✅ 作成/更新: {results['created']}件"
        )

        if results["failed"] > 0:
            ParliamentaryGroupMemberCommands.echo_error(
                f"❌ 失敗: {results['failed']}件"
            )

        matching_service.close()

    @staticmethod
    @click.command("parliamentary-group-member-status")
    @click.option(
        "--parliamentary-group-id",
        type=int,
        help="議員団ID（指定しない場合は全体のステータスを表示）",
    )
    def parliamentary_group_member_status(parliamentary_group_id: int | None = None):
        """抽出・マッチング状況を表示"""

        ParliamentaryGroupMemberCommands.echo_info(
            "📊 議員団メンバー抽出・マッチング状況"
        )

        extracted_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )

        # 全体サマリー
        summary = extracted_repo.get_extraction_summary()

        ParliamentaryGroupMemberCommands.echo_info("\n=== 全体ステータス ===")
        ParliamentaryGroupMemberCommands.echo_info(f"総件数: {summary['total']}件")
        ParliamentaryGroupMemberCommands.echo_info(
            f"  📋 未処理: {summary['pending']}件"
        )
        ParliamentaryGroupMemberCommands.echo_success(
            f"  ✅ マッチ済: {summary['matched']}件"
        )
        ParliamentaryGroupMemberCommands.echo_warning(
            f"  ⚠️  要確認: {summary['needs_review']}件"
        )
        ParliamentaryGroupMemberCommands.echo_error(
            f"  ❌ 該当なし: {summary['no_match']}件"
        )

        # 議員団別の詳細
        if parliamentary_group_id:
            ParliamentaryGroupMemberCommands.echo_info(
                f"\n=== 議員団ID {parliamentary_group_id} の詳細 ==="
            )

            # 未処理メンバー
            pending = extracted_repo.get_pending_members(parliamentary_group_id)
            if pending:
                ParliamentaryGroupMemberCommands.echo_info(
                    f"\n📋 未処理メンバー ({len(pending)}人):"
                )
                for member in pending[:10]:  # 最初の10件
                    role = (
                        f" ({member.extracted_role})" if member.extracted_role else ""
                    )
                    party = (
                        f" - {member.extracted_party_name}"
                        if member.extracted_party_name
                        else ""
                    )
                    ParliamentaryGroupMemberCommands.echo_info(
                        f"  • {member.extracted_name}{role}{party}"
                    )
                if len(pending) > 10:
                    ParliamentaryGroupMemberCommands.echo_info(
                        f"  ... 他 {len(pending) - 10}人"
                    )

            # マッチ済みメンバー
            matched = extracted_repo.get_matched_members(parliamentary_group_id)
            if matched:
                ParliamentaryGroupMemberCommands.echo_success(
                    f"\n✅ マッチ済みメンバー ({len(matched)}人):"
                )
                for member in matched[:10]:  # 最初の10件
                    role = (
                        f" ({member.extracted_role})" if member.extracted_role else ""
                    )
                    # politician_nameはエンティティに存在しないため、
                    # matched_politician_idからpolitician名を取得する必要がある
                    politician_name = "N/A"  # 後で実装
                    confidence = member.matching_confidence or 0.0
                    ParliamentaryGroupMemberCommands.echo_success(
                        f"  • {member.extracted_name}{role} → "
                        f"{politician_name} "
                        f"(信頼度: {confidence:.2f})"
                    )
                if len(matched) > 10:
                    ParliamentaryGroupMemberCommands.echo_success(
                        f"  ... 他 {len(matched) - 10}人"
                    )

        extracted_repo.close()


def get_parliamentary_group_member_commands():
    """Get parliamentary group member command group"""
    return ParliamentaryGroupMemberCommands().get_commands()
