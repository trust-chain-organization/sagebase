"""Commands for managing proposal judge extraction and matching"""

import asyncio
import logging

import click

from sqlalchemy import text

from src.application.dtos.proposal_judge_dto import (
    CreateProposalJudgesInputDTO,
    ExtractProposalJudgesInputDTO,
    MatchProposalJudgesInputDTO,
)
from src.infrastructure.di.container import get_container, init_container
from src.interfaces.cli.base import BaseCommand


logger = logging.getLogger(__name__)


class ProposalCommands(BaseCommand):
    """Commands for proposal judge extraction and matching"""

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
        """Get list of proposal commands"""
        return [
            ProposalCommands.extract_proposal_judges,
            ProposalCommands.match_proposal_judges,
            ProposalCommands.create_proposal_judges,
            ProposalCommands.proposal_judge_status,
        ]

    @staticmethod
    @click.command("extract-proposal-judges")
    @click.option(
        "--url",
        required=True,
        help="議案投票結果ページのURL",
    )
    @click.option(
        "--proposal-id",
        type=int,
        help="議案ID（既存議案と紐付ける場合）",
    )
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（会議体を指定する場合）",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="既存の抽出データを削除して再抽出",
    )
    def extract_proposal_judges(
        url: str,
        proposal_id: int | None = None,
        conference_id: int | None = None,
        force: bool = False,
    ):
        """議案ページから賛否情報を抽出（ステップ1/3）

        議案の投票結果ページから賛成者・反対者のリストを抽出し、
        ステージングテーブルに保存します。
        """
        click.echo("📋 議案賛否情報の抽出を開始します（ステップ1/3）")

        async def run_extract():
            # Initialize and get dependencies from DI container
            try:
                container = get_container()
            except RuntimeError:
                container = init_container()

            use_case = container.use_cases.extract_proposal_judges_usecase()

            # Execute extraction
            input_dto = ExtractProposalJudgesInputDTO(
                url=url,
                proposal_id=proposal_id,
                conference_id=conference_id,
                force=force,
            )

            result = await use_case.extract_judges(input_dto)

            ProposalCommands.echo_success(
                f"抽出完了: {result.extracted_count}件の賛否情報を抽出しました"
            )

            # Show extracted judges
            for judge in result.judges[:5]:  # Show first 5
                party = judge.extracted_party_name or "無所属"
                ProposalCommands.echo_info(
                    f"  - {judge.extracted_name} ({party}): {judge.extracted_judgment}"
                )

            if result.extracted_count > 5:
                ProposalCommands.echo_info(f"  ... 他 {result.extracted_count - 5}件")

        # Run async function
        asyncio.run(run_extract())

    @staticmethod
    @click.command("match-proposal-judges")
    @click.option(
        "--proposal-id",
        type=int,
        help="議案ID（特定の議案のみ処理）",
    )
    @click.option(
        "--judge-ids",
        multiple=True,
        type=int,
        help="特定の賛否情報IDを指定（複数指定可）",
    )
    def match_proposal_judges(
        proposal_id: int | None = None,
        judge_ids: tuple[int, ...] | None = None,
    ):
        """抽出した賛否情報と政治家をマッチング（ステップ2/3）

        LLMを使用して抽出した名前と既存の政治家データをマッチングします。
        信頼度スコアに基づいて、matched/needs_review/no_matchに分類されます。
        """
        click.echo("🔍 議案賛否情報と政治家のマッチングを開始します（ステップ2/3）")

        async def run_match():
            # Initialize and get dependencies from DI container
            try:
                container = get_container()
            except RuntimeError:
                container = init_container()

            use_case = container.use_cases.extract_proposal_judges_usecase()

            # Execute matching
            input_dto = MatchProposalJudgesInputDTO(
                proposal_id=proposal_id,
                judge_ids=list(judge_ids) if judge_ids else None,
            )

            result = await use_case.match_judges(input_dto)

            ProposalCommands.echo_success(
                f"マッチング完了: "
                f"matched={result.matched_count}, "
                f"needs_review={result.needs_review_count}, "
                f"no_match={result.no_match_count}"
            )

            # Show results
            if result.matched_count > 0:
                ProposalCommands.echo_info("\n✅ マッチ成功:")
                matched = [r for r in result.results if r.matching_status == "matched"]
                for r in matched[:5]:
                    ProposalCommands.echo_info(
                        f"  {r.judge_name} → {r.matched_politician_name} "
                        f"(信頼度: {r.confidence_score:.2f})"
                    )

            if result.needs_review_count > 0:
                ProposalCommands.echo_warning("\n⚠️ 要確認:")
                needs_review = [
                    r for r in result.results if r.matching_status == "needs_review"
                ]
                for r in needs_review[:5]:
                    politician = r.matched_politician_name or "候補なし"
                    ProposalCommands.echo_warning(
                        f"  {r.judge_name} → {politician} "
                        f"(信頼度: {r.confidence_score:.2f})"
                    )

            if result.no_match_count > 0:
                ProposalCommands.echo_error("\n❌ マッチなし:")
                no_match = [
                    r for r in result.results if r.matching_status == "no_match"
                ]
                for r in no_match[:5]:
                    ProposalCommands.echo_error(f"  {r.judge_name}")

        # Run async function
        asyncio.run(run_match())

    @staticmethod
    @click.command("create-proposal-judges")
    @click.option(
        "--proposal-id",
        type=int,
        help="議案ID（特定の議案のみ処理）",
    )
    @click.option(
        "--judge-ids",
        multiple=True,
        type=int,
        help="特定の賛否情報IDを指定（複数指定可）",
    )
    def create_proposal_judges(
        proposal_id: int | None = None,
        judge_ids: tuple[int, ...] | None = None,
    ):
        """マッチング結果から議案賛否レコードを作成（ステップ3/3）

        'matched'ステータスの賛否情報から正式なProposalJudgeレコードを作成します。
        """
        click.echo("✍️ 議案賛否レコードの作成を開始します（ステップ3/3）")

        async def run_create():
            # Initialize and get dependencies from DI container
            try:
                container = get_container()
            except RuntimeError:
                container = init_container()

            use_case = container.use_cases.extract_proposal_judges_usecase()

            # Execute creation
            input_dto = CreateProposalJudgesInputDTO(
                proposal_id=proposal_id,
                judge_ids=list(judge_ids) if judge_ids else None,
            )

            result = await use_case.create_judges(input_dto)

            ProposalCommands.echo_success(
                f"作成完了: "
                f"{result.created_count}件の賛否レコードを作成、"
                f"{result.skipped_count}件をスキップ"
            )

            # Show created judges
            for judge in result.judges[:10]:
                ProposalCommands.echo_info(
                    f"  ✓ {judge.politician_name}: {judge.judgment}"
                )

            if len(result.judges) > 10:
                ProposalCommands.echo_info(f"  ... 他 {len(result.judges) - 10}件")

        # Run async function
        asyncio.run(run_create())

    @staticmethod
    @click.command("proposal-judge-status")
    @click.option(
        "--proposal-id",
        type=int,
        help="議案ID（特定の議案の状況を確認）",
    )
    def proposal_judge_status(proposal_id: int | None = None):
        """議案賛否情報の抽出・マッチング状況を確認

        各ステップの処理状況と統計情報を表示します。
        """
        click.echo("📊 議案賛否情報の処理状況")

        # Initialize and get dependencies from DI container
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        session = container.database.session()

        try:
            # Get statistics from database
            if proposal_id:
                # Query for specific proposal
                extracted_query = text("""
                    SELECT
                        matching_status,
                        COUNT(*) as count
                    FROM extracted_proposal_judges
                    WHERE proposal_id = :proposal_id
                    GROUP BY matching_status
                """)
                extracted_result = session.execute(
                    extracted_query, {"proposal_id": proposal_id}
                )
            else:
                # Query for all proposals
                extracted_query = text("""
                    SELECT
                        matching_status,
                        COUNT(*) as count
                    FROM extracted_proposal_judges
                    GROUP BY matching_status
                """)
                extracted_result = session.execute(extracted_query)

            # Process results
            status_counts = {
                "pending": 0,
                "matched": 0,
                "needs_review": 0,
                "no_match": 0,
            }
            for row in extracted_result:
                status_counts[row[0]] = row[1]

            total_extracted = sum(status_counts.values())

            # Display statistics
            ProposalCommands.echo_info("\n📥 抽出済み賛否情報:")
            ProposalCommands.echo_info(f"  合計: {total_extracted}件")
            ProposalCommands.echo_info(f"  - 未処理: {status_counts['pending']}件")
            ProposalCommands.echo_info(f"  - マッチ済み: {status_counts['matched']}件")
            ProposalCommands.echo_info(f"  - 要確認: {status_counts['needs_review']}件")
            ProposalCommands.echo_info(f"  - マッチなし: {status_counts['no_match']}件")

            # Get created judges count
            if proposal_id:
                judges_query = text("""
                    SELECT COUNT(*) FROM proposal_judges
                    WHERE proposal_id = :proposal_id
                """)
                judges_result = session.execute(
                    judges_query, {"proposal_id": proposal_id}
                )
            else:
                judges_query = text("SELECT COUNT(*) FROM proposal_judges")
                judges_result = session.execute(judges_query)

            row = judges_result.fetchone()
            judges_count = row[0] if row else 0

            ProposalCommands.echo_info(f"\n✅ 作成済み賛否レコード: {judges_count}件")

            # Show next steps
            if status_counts["pending"] > 0:
                ProposalCommands.echo_warning(
                    f"\n💡 未処理の賛否情報が{status_counts['pending']}件あります。"
                    "'match-proposal-judges'コマンドでマッチングを実行してください。"
                )
            elif status_counts["matched"] > judges_count:
                ProposalCommands.echo_warning(
                    "\n💡 マッチ済みで未作成の賛否情報があります。"
                    "'create-proposal-judges'コマンドでレコードを作成してください。"
                )
            elif status_counts["needs_review"] > 0:
                ProposalCommands.echo_warning(
                    f"\n⚠️ {status_counts['needs_review']}件の"
                    "賛否情報が手動確認待ちです。"
                )
            else:
                ProposalCommands.echo_success("\n✨ すべての賛否情報が処理済みです！")

        finally:
            session.close()


def get_proposal_commands() -> list[click.Command]:
    """Get list of proposal-related commands for registration"""
    commands = ProposalCommands()
    return commands.get_commands()
