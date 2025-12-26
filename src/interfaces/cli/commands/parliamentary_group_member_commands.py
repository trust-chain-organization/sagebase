"""Commands for managing parliamentary group member extraction and matching"""

import asyncio
import logging

from datetime import date, datetime

import click

from src.application.usecases.create_parliamentary_group_memberships_usecase import (
    CreateParliamentaryGroupMembershipsUseCase,
)
from src.application.usecases.match_parliamentary_group_members_usecase import (
    MatchParliamentaryGroupMembersUseCase,
)
from src.domain.services.parliamentary_group_member_matching_service import (
    ParliamentaryGroupMemberMatchingService as PGMemberMatchingDomainService,
)
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.config.database import get_db_session
from src.infrastructure.exceptions import DatabaseError, ScrapingError
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl
from src.interfaces.cli.base import BaseCommand
from src.interfaces.cli.progress import ProgressTracker

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

    @staticmethod
    def _create_match_members_usecase() -> MatchParliamentaryGroupMembersUseCase:
        """Create MatchParliamentaryGroupMembersUseCase with dependencies

        Note: Uses sync session temporarily. Should be refactored to use async session.
        """
        session = get_db_session()

        # リポジトリの初期化
        # TODO: 型エラーを修正するため、async sessionを使用するようにリファクタリング
        member_repo = ExtractedParliamentaryGroupMemberRepositoryImpl(session)  # type: ignore
        politician_repo = PoliticianRepositoryImpl(session)  # type: ignore
        speaker_repo = SpeakerRepositoryImpl(session)  # type: ignore

        # サービスの初期化
        llm_service = GeminiLLMService()
        speaker_service = SpeakerDomainService(speaker_repo)
        matching_service = PGMemberMatchingDomainService(
            politician_repository=politician_repo,
            llm_service=llm_service,
            speaker_service=speaker_service,
        )

        return MatchParliamentaryGroupMembersUseCase(
            member_repository=member_repo,
            matching_service=matching_service,
        )

    @staticmethod
    def _create_memberships_usecase() -> CreateParliamentaryGroupMembershipsUseCase:
        """Create CreateParliamentaryGroupMembershipsUseCase with dependencies

        Note: Uses sync session temporarily. Should be refactored to use async session.
        """
        session = get_db_session()

        # リポジトリの初期化
        # TODO: 型エラーを修正するため、async sessionを使用するようにリファクタリング
        member_repo = ExtractedParliamentaryGroupMemberRepositoryImpl(session)  # type: ignore
        membership_repo = ParliamentaryGroupMembershipRepositoryImpl(session)  # type: ignore

        return CreateParliamentaryGroupMembershipsUseCase(
            member_repository=member_repo,
            membership_repository=membership_repo,
        )

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

        # UseCaseを初期化
        usecase = ParliamentaryGroupMemberCommands._create_match_members_usecase()

        # 処理実行
        ParliamentaryGroupMemberCommands.echo_info(
            "LLMを使用して政治家データとマッチングします..."
        )

        with ProgressTracker(
            total_steps=1, description="マッチング処理中..."
        ) as progress:
            # 非同期処理を実行
            results = asyncio.run(usecase.execute(parliamentary_group_id))

            progress.update(1)

        # 結果表示
        ParliamentaryGroupMemberCommands.echo_info("\n=== マッチング完了 ===")
        total = len(results)
        matched = sum(1 for r in results if r["status"] == "matched")
        needs_review = sum(1 for r in results if r["status"] == "needs_review")
        no_match = sum(1 for r in results if r["status"] == "no_match")

        ParliamentaryGroupMemberCommands.echo_info(f"処理総数: {total}件")
        ParliamentaryGroupMemberCommands.echo_success(f"✅ マッチ成功: {matched}件")
        ParliamentaryGroupMemberCommands.echo_warning(f"⚠️  要確認: {needs_review}件")
        ParliamentaryGroupMemberCommands.echo_error(f"❌ 該当なし: {no_match}件")

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

        # UseCaseを初期化
        usecase = ParliamentaryGroupMemberCommands._create_memberships_usecase()

        # 処理実行
        with ProgressTracker(
            total_steps=1, description="メンバーシップ作成中..."
        ) as progress:
            # 非同期処理を実行
            results = asyncio.run(
                usecase.execute(
                    parliamentary_group_id=parliamentary_group_id,
                    min_confidence=min_confidence,
                    start_date=start_date_obj,
                )
            )

            progress.update(1)

        # 結果表示
        ParliamentaryGroupMemberCommands.echo_info("\n=== メンバーシップ作成完了 ===")
        # 型アサーション: resultsは dict[str, int | list[...]] だが、
        # これらのキーは int のみを返す
        created_raw = results.get("created_count", 0)
        skipped_raw = results.get("skipped_count", 0)
        created = int(created_raw) if isinstance(created_raw, int) else 0
        skipped = int(skipped_raw) if isinstance(skipped_raw, int) else 0
        total = created + skipped

        ParliamentaryGroupMemberCommands.echo_info(f"処理総数: {total}件")
        ParliamentaryGroupMemberCommands.echo_success(f"✅ 作成/更新: {created}件")

        if skipped > 0:
            ParliamentaryGroupMemberCommands.echo_warning(f"⚠️  スキップ: {skipped}件")

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
