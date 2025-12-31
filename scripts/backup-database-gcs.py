#!/usr/bin/env python3
"""Database backup and restore script with Google Cloud Storage integration

This script provides functionality to:
- Backup PostgreSQL database to local files and GCS
- Restore database from local files or GCS
- List available backups (both local and GCS)
"""

import argparse
import logging
import os
import subprocess
import sys

from datetime import datetime
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.config.settings import get_settings
from src.infrastructure.storage.gcs_client import HAS_GCS, GCSStorage


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DatabaseBackupManager:
    """Manage database backups with optional GCS integration"""

    def __init__(self, use_gcs: bool = False):
        """Initialize backup manager

        Args:
            use_gcs: Whether to use Google Cloud Storage
        """
        self.backup_dir = Path("./database/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.settings = get_settings()
        self.use_gcs = use_gcs and HAS_GCS and self.settings.gcs_upload_enabled

        if self.use_gcs:
            try:
                self.gcs_storage = GCSStorage(
                    bucket_name=self.settings.gcs_bucket_name,
                    project_id=self.settings.gcs_project_id,
                )
                bucket_name = self.settings.gcs_bucket_name
                logger.info(f"GCS storage initialized with bucket: {bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS storage: {e}")
                self.use_gcs = False
                self.gcs_storage = None
        else:
            self.gcs_storage = None

    def create_backup(self, upload_to_gcs: bool = True) -> str | None:
        """Create database backup

        Args:
            upload_to_gcs: Whether to upload backup to GCS

        Returns:
            Backup file path if successful, None otherwise
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"polibase_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename

        logger.info("💾 データベースをバックアップ中...")

        # Determine if running inside Docker container
        in_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER")

        # Create backup
        try:
            with open(backup_path, "w") as f:
                if in_docker:
                    # Running inside container - connect directly
                    result = subprocess.run(
                        [
                            "pg_dump",
                            "-h",
                            "postgres",
                            "-U",
                            "sagebase_user",
                            "sagebase_db",
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        env={**os.environ, "PGPASSWORD": "sagebase_password"},
                    )
                else:
                    # Running on host - use docker compose
                    # Check if PostgreSQL container is running
                    check_result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            "docker/docker-compose.yml",
                            "ps",
                            "postgres",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if "Up" not in check_result.stdout:
                        logger.error("❌ PostgreSQLコンテナが起動していません")
                        print("以下のコマンドでDockerサービスを起動してください：")
                        print("docker compose -f docker/docker-compose.yml up -d")
                        return None

                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            "docker/docker-compose.yml",
                            "exec",
                            "-T",
                            "postgres",
                            "pg_dump",
                            "-U",
                            "sagebase_user",
                            "sagebase_db",
                        ],
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

            if result.returncode != 0:
                logger.error(f"❌ バックアップに失敗しました: {result.stderr}")
                backup_path.unlink(missing_ok=True)
                return None

            file_size = backup_path.stat().st_size / (1024 * 1024)  # MB
            logger.info(f"✅ バックアップ完了: {backup_path} ({file_size:.2f} MB)")

            # Upload to GCS if enabled
            if upload_to_gcs and self.use_gcs and self.gcs_storage:
                try:
                    gcs_path = f"database-backups/{backup_filename}"
                    gcs_uri = self.gcs_storage.upload_file(
                        local_path=backup_path,
                        gcs_path=gcs_path,
                        content_type="application/sql",
                    )
                    logger.info(f"☁️  GCSへのアップロード完了: {gcs_uri}")
                except Exception as e:
                    logger.error(f"⚠️  GCSへのアップロードに失敗しました: {e}")
                    # Continue even if GCS upload fails

            return str(backup_path)

        except Exception as e:
            logger.error(f"❌ バックアップ中にエラーが発生しました: {e}")
            backup_path.unlink(missing_ok=True)
            return None

    def restore_backup(self, backup_source: str) -> bool:
        """Restore database from backup

        Args:
            backup_source: Local file path or GCS URI (gs://...)

        Returns:
            True if successful, False otherwise
        """
        # Determine if source is GCS or local
        if backup_source.startswith("gs://"):
            if not self.use_gcs or not self.gcs_storage:
                logger.error("❌ GCS機能が有効になっていません")
                return False

            # Download from GCS to temporary file
            temp_path = (
                self.backup_dir / f"temp_restore_{datetime.now().timestamp()}.sql"
            )
            logger.info(f"📥 GCSからバックアップをダウンロード中: {backup_source}")

            if not self.gcs_storage.download_file_from_uri(backup_source, temp_path):
                logger.error("❌ GCSからのダウンロードに失敗しました")
                return False

            backup_path = temp_path
            is_temp = True
        else:
            backup_path = Path(backup_source)
            is_temp = False

        # Check if backup file exists
        if not backup_path.exists():
            logger.error(f"❌ バックアップファイルが見つかりません: {backup_path}")
            return False

        logger.info("📥 データベースをリストア中...")

        # Determine if running inside Docker container
        in_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER")

        try:
            if in_docker:
                # Running inside container - connect directly
                env = {**os.environ, "PGPASSWORD": "sagebase_password"}

                # Drop and recreate database
                subprocess.run(
                    [
                        "psql",
                        "-h",
                        "postgres",
                        "-U",
                        "sagebase_user",
                        "-d",
                        "postgres",
                        "-c",
                        "DROP DATABASE IF EXISTS sagebase_db;",
                    ],
                    check=True,
                    env=env,
                )

                subprocess.run(
                    [
                        "psql",
                        "-h",
                        "postgres",
                        "-U",
                        "sagebase_user",
                        "-d",
                        "postgres",
                        "-c",
                        "CREATE DATABASE sagebase_db;",
                    ],
                    check=True,
                    env=env,
                )

                # Restore from backup
                with open(backup_path) as f:
                    result = subprocess.run(
                        [
                            "psql",
                            "-h",
                            "postgres",
                            "-U",
                            "sagebase_user",
                            "-d",
                            "sagebase_db",
                        ],
                        stdin=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env,
                    )
            else:
                # Running on host - use docker compose
                # Check if PostgreSQL container is running
                check_result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        "docker/docker-compose.yml",
                        "ps",
                        "postgres",
                    ],
                    capture_output=True,
                    text=True,
                )
                if "Up" not in check_result.stdout:
                    logger.error("❌ PostgreSQLコンテナが起動していません")
                    print("以下のコマンドでDockerサービスを起動してください：")
                    print("docker compose -f docker/docker-compose.yml up -d")
                    return False

                # Drop and recreate database
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        "docker/docker-compose.yml",
                        "exec",
                        "-T",
                        "postgres",
                        "psql",
                        "-U",
                        "sagebase_user",
                        "-d",
                        "postgres",
                        "-c",
                        "DROP DATABASE IF EXISTS sagebase_db;",
                    ],
                    check=True,
                )

                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        "docker/docker-compose.yml",
                        "exec",
                        "-T",
                        "postgres",
                        "psql",
                        "-U",
                        "sagebase_user",
                        "-d",
                        "postgres",
                        "-c",
                        "CREATE DATABASE sagebase_db;",
                    ],
                    check=True,
                )

                # Restore from backup
                with open(backup_path) as f:
                    result = subprocess.run(
                        [
                            "docker",
                            "compose",
                            "-f",
                            "docker/docker-compose.yml",
                            "exec",
                            "-T",
                            "postgres",
                            "psql",
                            "-U",
                            "sagebase_user",
                            "-d",
                            "sagebase_db",
                        ],
                        stdin=f,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

            if result.returncode != 0:
                logger.error(f"❌ リストアに失敗しました: {result.stderr}")
                return False

            logger.info("✅ リストア完了")

            # Verify restoration
            if in_docker:
                result = subprocess.run(
                    [
                        "psql",
                        "-h",
                        "postgres",
                        "-U",
                        "sagebase_user",
                        "-d",
                        "sagebase_db",
                        "-c",
                        r"\dt",
                    ],
                    capture_output=True,
                    text=True,
                    env={**os.environ, "PGPASSWORD": "sagebase_password"},
                )
            else:
                result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        "docker/docker-compose.yml",
                        "exec",
                        "-T",
                        "postgres",
                        "psql",
                        "-U",
                        "sagebase_user",
                        "-d",
                        "sagebase_db",
                        "-c",
                        r"\dt",
                    ],
                    capture_output=True,
                    text=True,
                )

            if result.returncode == 0:
                logger.info("🔍 データベース状態:")
                print(result.stdout)

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ リストア中にエラーが発生しました: {e}")
            return False
        finally:
            # Clean up temporary file
            if is_temp and backup_path.exists():
                backup_path.unlink()

    def list_backups(self, include_gcs: bool = True) -> None:
        """List available backups

        Args:
            include_gcs: Whether to include GCS backups
        """
        print("📋 利用可能なバックアップ")
        print("=" * 50)

        # List local backups
        print("\n🗂️  ローカルバックアップ:")
        local_backups = list(self.backup_dir.glob("polibase_backup_*.sql"))

        if local_backups:
            for backup in sorted(local_backups, reverse=True):
                size_mb = backup.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                time_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  - {backup.name} ({size_mb:.2f} MB) - {time_str}")
        else:
            print("  バックアップファイルが見つかりません")

        # List GCS backups
        if include_gcs and self.use_gcs and self.gcs_storage:
            print("\n☁️  Cloud Storageバックアップ:")
            try:
                gcs_files = self.gcs_storage.list_files(prefix="database-backups/")
                backup_files = [f for f in gcs_files if f.endswith(".sql")]

                if backup_files:
                    for file_path in sorted(backup_files, reverse=True):
                        gcs_uri = f"gs://{self.settings.gcs_bucket_name}/{file_path}"
                        print(f"  - {gcs_uri}")
                else:
                    print("  Cloud Storageにバックアップが見つかりません")
            except Exception as e:
                logger.error(f"  GCSバックアップの一覧取得に失敗しました: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PostgreSQLデータベース バックアップ/リストア (GCS対応)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  %(prog)s backup                              # ローカルとGCSにバックアップ
  %(prog)s backup --no-gcs                     # ローカルのみにバックアップ
  %(prog)s restore database/backups/xxx.sql    # ローカルファイルからリストア
  %(prog)s restore gs://bucket/xxx.sql         # GCSからリストア
  %(prog)s list                                # すべてのバックアップを表示
  %(prog)s list --no-gcs                       # ローカルバックアップのみ表示
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="データベースをバックアップ")
    backup_parser.add_argument(
        "--no-gcs",
        action="store_true",
        help="GCSへのアップロードをスキップ",
    )

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="バックアップからリストア")
    restore_parser.add_argument(
        "backup_file",
        help="バックアップファイルパスまたはGCS URI (gs://...)",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="バックアップ一覧を表示")
    list_parser.add_argument(
        "--no-gcs",
        action="store_true",
        help="GCSバックアップを含めない",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize backup manager
    manager = DatabaseBackupManager(use_gcs=True)

    # Execute command
    if args.command == "backup":
        backup_path = manager.create_backup(upload_to_gcs=not args.no_gcs)
        sys.exit(0 if backup_path else 1)

    elif args.command == "restore":
        # Confirm before restore
        print("⚠️  警告: この操作は現在のデータベースを上書きします")
        print(f"リストアファイル: {args.backup_file}")
        response = input("本当に実行しますか？ (y/N): ")

        if response.lower() != "y":
            print("❌ 操作をキャンセルしました")
            sys.exit(0)

        success = manager.restore_backup(args.backup_file)
        sys.exit(0 if success else 1)

    elif args.command == "list":
        manager.list_backups(include_gcs=not args.no_gcs)
        sys.exit(0)


if __name__ == "__main__":
    main()
