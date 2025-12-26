"""CLI commands for database operations"""

import subprocess

import click

from ..base import BaseCommand, with_error_handling


class DatabaseCommands(BaseCommand):
    """Commands for database management"""

    @staticmethod
    @click.command()
    @with_error_handling
    def test_connection():
        """Test database connection (データベース接続テスト)"""
        from src.infrastructure.config.database import test_connection as test_db

        DatabaseCommands.show_progress("Testing database connection...")
        test_db()
        DatabaseCommands.success("Database connection successful!")

    @staticmethod
    @click.command()
    @click.argument("action", type=click.Choice(["backup", "restore", "list"]))
    @click.argument("filename", required=False)
    @click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
    @with_error_handling
    def database(action: str, filename: str | None, gcs: bool):
        """Database management commands (データベース管理)

        Actions:
        - backup: Create a new backup (local and optionally GCS)
        - restore: Restore from a backup file (local or GCS)
        - list: List available backups (local and GCS)

        Examples:
        - sagebase database backup                     # Backup to local and GCS
        - sagebase database backup --no-gcs            # Backup to local only
        - sagebase database restore backup.sql         # Restore from local file
        - sagebase database restore gs://bucket/x.sql  # Restore from GCS
        - sagebase database list                       # List all backups
        """
        import sys
        from pathlib import Path

        # Use new GCS-enabled backup script
        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts"
            / "backup-database-gcs.py"
        )

        if action == "backup":
            DatabaseCommands.show_progress("Creating database backup...")
            args = [sys.executable, str(script_path), "backup"]
            if not gcs:
                args.append("--no-gcs")
            result = subprocess.run(args)
            if result.returncode == 0:
                DatabaseCommands.success("Backup completed successfully!")
            else:
                DatabaseCommands.error("Backup failed")

        elif action == "restore":
            if not filename:
                DatabaseCommands.error("Error: filename required for restore")
                return
            DatabaseCommands.show_progress(f"Restoring from backup: {filename}")
            result = subprocess.run(
                [sys.executable, str(script_path), "restore", filename]
            )
            if result.returncode == 0:
                DatabaseCommands.success("Restore completed successfully!")
            else:
                DatabaseCommands.error("Restore failed")

        elif action == "list":
            args = [sys.executable, str(script_path), "list"]
            if not gcs:
                args.append("--no-gcs")
            subprocess.run(args)

    @staticmethod
    @click.command()
    @with_error_handling
    def reset_database():
        """Reset database to initial state (データベースリセット)

        WARNING: This will delete all data and restore to initial state!
        """
        if DatabaseCommands.confirm(
            "Are you sure you want to reset the database? This will delete all data!"
        ):
            subprocess.run(["./reset-database.sh"])
            DatabaseCommands.success("Database reset complete.")
        else:
            DatabaseCommands.show_progress("Database reset cancelled.")


def get_database_commands():
    """Get all database-related commands"""
    return [
        DatabaseCommands.test_connection,
        DatabaseCommands.database,
        DatabaseCommands.reset_database,
    ]
