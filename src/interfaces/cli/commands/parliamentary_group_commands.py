"""議員団関連のCLIコマンド"""

import asyncio
from datetime import date, datetime
from typing import Any

import click

from src.infrastructure.di.container import get_container, init_container
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.interfaces.cli.progress import ProgressTracker
from src.parliamentary_group_member_extractor import (
    ParliamentaryGroupMembershipService,
)


@click.command("extract-group-members")
@click.option(
    "--group-id",
    type=int,
    help="処理する議員団ID",
)
@click.option(
    "--all-groups",
    is_flag=True,
    help="URLが設定されている全議員団を処理",
)
@click.option(
    "--conference-id",
    type=int,
    help="特定の会議体の議員団のみ処理",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="実際にはメンバーシップを作成せず、結果のみ表示",
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.7,
    help="メンバーシップ作成の最低信頼度（デフォルト: 0.7）",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="所属開始日（デフォルト: 今日）",
)
def extract_group_members(
    group_id: int | None,
    all_groups: bool,
    conference_id: int | None,
    dry_run: bool,
    confidence_threshold: float,
    start_date: datetime | None,
):
    """議員団メンバーをURLから抽出してメンバーシップを作成"""
    # Initialize and get dependencies from DI container
    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    session = container.database.session()

    # Import repository implementations
    from src.infrastructure.persistence.parliamentary_group_repository_impl import (
        ParliamentaryGroupRepositoryImpl,
    )
    from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

    group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl, session)

    # 処理対象の議員団を取得
    groups_to_process = []

    if group_id:
        group = group_repo.get_parliamentary_group_by_id(group_id)
        if not group:
            click.echo(
                click.style(f"議員団ID {group_id} が見つかりません", fg="red"), err=True
            )
            return
        if not group.get("url"):
            click.echo(
                click.style(
                    f"議員団 '{group['name']}' にURLが設定されていません", fg="yellow"
                )
            )
            return
        groups_to_process = [group]
    elif all_groups or conference_id:
        # 全議員団または特定会議体の議員団を取得（URLが設定されているもののみ）
        groups_to_process = group_repo.get_all_with_details(
            conference_id=conference_id, active_only=True, with_url_only=True
        )

        if not groups_to_process:
            click.echo(
                click.style("URLが設定されている議員団がありません", fg="yellow")
            )
            return
    else:
        click.echo(
            click.style(
                (
                    "--group-id, --all-groups, --conference-id の"
                    "いずれかを指定してください"
                ),
                fg="red",
            ),
            err=True,
        )
        return

    # ドライランモードの表示
    if dry_run:
        click.echo(
            "\n"
            + click.style(
                "ドライランモード: 実際にはメンバーシップを作成しません",
                fg="yellow",
                bold=True,
            )
            + "\n"
        )

    # 抽出器とサービスの初期化
    extractor = ParliamentaryGroupMemberExtractorFactory.create()
    service = ParliamentaryGroupMembershipService()

    # 開始日の設定
    membership_start_date: date = start_date.date() if start_date else date.today()

    # 処理の実行
    total_results: dict[str, Any] = {
        "total_groups": len(groups_to_process),
        "processed": 0,
        "total_extracted": 0,
        "total_matched": 0,
        "total_created": 0,
        "errors": [],
    }

    with ProgressTracker(
        total_steps=len(groups_to_process), description="議員団を処理中..."
    ) as progress:
        for group in groups_to_process:
            try:
                # メンバー情報を抽出
                extraction_result = extractor.extract_members_sync(
                    group["id"], group["url"]
                )

                if extraction_result.error:
                    total_results["errors"].append(
                        f"{group['name']}: {extraction_result.error}"
                    )
                    progress.update(1)
                    continue

                if not extraction_result.extracted_members:
                    click.echo(
                        click.style(
                            f"{group['name']}: メンバーが抽出されませんでした",
                            fg="yellow",
                        )
                    )
                    progress.update(1)
                    continue

                # 政治家とマッチング
                matching_results = asyncio.run(
                    service.match_politicians(
                        extraction_result.extracted_members,
                        conference_id=group["conference_id"],
                    )
                )

                # メンバーシップを作成
                creation_result = service.create_memberships(
                    parliamentary_group_id=group["id"],
                    matching_results=matching_results,
                    start_date=membership_start_date,
                    confidence_threshold=confidence_threshold,
                    dry_run=dry_run,
                )

                # 結果を集計
                total_results["processed"] += 1
                total_results["total_extracted"] += creation_result.total_extracted
                total_results["total_matched"] += creation_result.matched_count
                total_results["total_created"] += creation_result.created_count

                # グループごとの結果を表示
                click.echo(
                    f"\n{click.style(group['name'], fg='green')} "
                    f"(会議体: {group.get('conference_name', 'N/A')})"
                )
                click.echo(f"  抽出: {creation_result.total_extracted}名")
                click.echo(f"  マッチング: {creation_result.matched_count}名")
                click.echo(f"  作成: {creation_result.created_count}名")
                click.echo(f"  スキップ: {creation_result.skipped_count}名")

                if creation_result.errors:
                    click.echo(f"  {click.style('エラー:', fg='red')}")
                    for error in creation_result.errors[:5]:  # 最初の5件のみ表示
                        click.echo(f"    - {error}")
                    if len(creation_result.errors) > 5:
                        click.echo(f"    ... 他 {len(creation_result.errors) - 5} 件")

            except Exception as e:
                total_results["errors"].append(f"{group['name']}: {str(e)}")
                click.echo(click.style(f"エラー: {group['name']} - {str(e)}", fg="red"))

            progress.update(1)

    # 全体の結果を表示
    click.echo(f"\n{click.style('処理結果サマリー:', bold=True)}")
    click.echo(f"処理対象議員団数: {total_results['total_groups']}")
    click.echo(f"処理完了: {total_results['processed']}")
    click.echo(f"総抽出数: {total_results['total_extracted']}")
    click.echo(f"総マッチング数: {total_results['total_matched']}")
    click.echo(f"総作成数: {total_results['total_created']}")

    if total_results["errors"]:
        click.echo(
            f"\n{click.style(f'エラー ({len(total_results["errors"])}件):', fg='red')}"
        )
        for error in total_results["errors"]:
            click.echo(f"  - {error}")


@click.command("list-parliamentary-groups")
@click.option(
    "--conference-id",
    type=int,
    help="特定の会議体の議員団のみ表示",
)
@click.option(
    "--with-members",
    is_flag=True,
    help="現在のメンバー数も表示",
)
@click.option(
    "--active-only/--all",
    default=True,
    help="活動中の議員団のみ表示するか",
)
def list_parliamentary_groups(
    conference_id: int | None,
    with_members: bool,
    active_only: bool,
):
    """議員団の一覧を表示"""
    # Initialize and get dependencies from DI container
    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    session = container.database.session()

    # Import repository implementations
    from src.infrastructure.persistence.parliamentary_group_repository_impl import (
        ParliamentaryGroupMembershipRepositoryImpl,
        ParliamentaryGroupRepositoryImpl,
    )
    from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

    group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl, session)
    membership_repo = RepositoryAdapter(
        ParliamentaryGroupMembershipRepositoryImpl, session
    )

    # 議員団を取得（会議体・行政機関情報も含む）
    groups = group_repo.get_all_with_details(
        conference_id=conference_id, active_only=active_only
    )

    if not groups:
        click.echo(click.style("議員団が見つかりません", fg="yellow"))
        return

    # 表形式で表示
    click.echo("\n議員団一覧")
    click.echo("-" * 80)

    # ヘッダー
    headers = ["ID", "議員団名", "会議体", "行政機関", "URL", "状態"]
    if with_members:
        headers.append("メンバー数")

    # ヘッダー行を表示
    header_line = " | ".join(h.ljust(15) if h != "ID" else h.ljust(6) for h in headers)
    click.echo(header_line)
    click.echo("-" * len(header_line))

    # 各議員団の情報を表示
    for group in groups:
        row_data: list[str] = [
            str(group["id"]).ljust(6),
            group["name"][:15].ljust(15),
            group.get("conference_name", "N/A")[:15].ljust(15),
            group.get("governing_body_name", "N/A")[:15].ljust(15),
            (group.get("url", "未設定") if group.get("url") else "未設定")[:15].ljust(
                15
            ),
            ("活動中" if group.get("is_active", True) else "非活動").ljust(15),
        ]

        if with_members:
            # 現在のメンバー数を取得
            members = membership_repo.get_current_members(group["id"])
            row_data.append(str(len(members)).ljust(15))

        click.echo(" | ".join(row_data))

    click.echo(f"\n総数: {len(groups)} 議員団")


def get_parliamentary_group_commands():
    """Get all parliamentary group related commands"""
    return [
        extract_group_members,
        list_parliamentary_groups,
    ]
