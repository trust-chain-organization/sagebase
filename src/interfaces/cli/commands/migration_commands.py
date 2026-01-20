"""Database migration commands using Alembic.

マイグレーション管理用のCLIコマンドを提供します。
"""

import logging
import subprocess
import sys

from pathlib import Path

import click


logger = logging.getLogger(__name__)


def get_migration_commands() -> list[click.Command]:
    """Get migration commands for CLI registration.

    Returns:
        List of Click commands
    """
    return [migrate, migrate_rollback, migrate_status, migrate_history, migrate_new]


@click.command("migrate")
def migrate() -> None:
    """Run database migrations to latest version.

    Alembicを使用して未適用のマイグレーションを全て適用します。
    """
    logger.info("Running database migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[4],  # プロジェクトルート
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo("✅ Migrations completed successfully!")
        if result.stdout:
            click.echo(result.stdout)
    else:
        click.echo(f"❌ Migration failed: {result.stderr}", err=True)
        sys.exit(1)


@click.command("migrate-rollback")
@click.option(
    "--steps",
    "-n",
    default=1,
    type=int,
    help="Number of migrations to rollback (default: 1)",
)
def migrate_rollback(steps: int) -> None:
    """Rollback database migrations.

    直前のマイグレーションを取り消します。

    Args:
        steps: ロールバックするマイグレーションの数
    """
    logger.info(f"Rolling back {steps} migration(s)...")
    result = subprocess.run(
        ["alembic", "downgrade", f"-{steps}"],
        cwd=Path(__file__).parents[4],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo(f"✅ Rolled back {steps} migration(s) successfully!")
        if result.stdout:
            click.echo(result.stdout)
    else:
        click.echo(f"❌ Rollback failed: {result.stderr}", err=True)
        sys.exit(1)


@click.command("migrate-status")
def migrate_status() -> None:
    """Show current migration status.

    現在適用されているマイグレーションのバージョンを表示します。
    """
    result = subprocess.run(
        ["alembic", "current"],
        cwd=Path(__file__).parents[4],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo("Current migration status:")
        click.echo(result.stdout if result.stdout else "No migrations applied yet.")
    else:
        click.echo(f"❌ Failed to get status: {result.stderr}", err=True)
        sys.exit(1)


@click.command("migrate-history")
def migrate_history() -> None:
    """Show migration history.

    全てのマイグレーションの履歴を表示します。
    """
    result = subprocess.run(
        ["alembic", "history", "--verbose"],
        cwd=Path(__file__).parents[4],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo("Migration history:")
        click.echo(result.stdout if result.stdout else "No migrations found.")
    else:
        click.echo(f"❌ Failed to get history: {result.stderr}", err=True)
        sys.exit(1)


@click.command("migrate-new")
@click.argument("message")
def migrate_new(message: str) -> None:
    """Create a new migration file.

    新しいマイグレーションファイルを作成します。

    Args:
        message: マイグレーションの説明（ファイル名に使用されます）
    """
    logger.info(f"Creating new migration: {message}")
    result = subprocess.run(
        ["alembic", "revision", "-m", message],
        cwd=Path(__file__).parents[4],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo(f"✅ Created new migration: {message}")
        click.echo(result.stdout)
    else:
        click.echo(f"❌ Failed to create migration: {result.stderr}", err=True)
        sys.exit(1)
