"""File management utilities"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class FileHandler:
    """ファイル管理ユーティリティ"""

    def __init__(
        self, base_dir: str = "data/scraped", logger: logging.Logger | None = None
    ):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)

    def save_json(
        self, data: dict[str, Any], filename: str, subdirs: list[str] | None = None
    ) -> str:
        """JSONデータを保存

        Args:
            data: 保存するデータ
            filename: ファイル名
            subdirs: サブディレクトリのリスト（例: ['2024', '12', '25']）

        Returns:
            保存したファイルのパス
        """
        # 保存先ディレクトリを作成
        save_dir = self.base_dir
        if subdirs:
            for subdir in subdirs:
                save_dir = save_dir / subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        # ファイルパスを決定
        file_path = save_dir / filename

        # JSONを保存
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"JSON saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error saving JSON: {e}")
            raise

    def save_text(
        self, content: str, filename: str, subdirs: list[str] | None = None
    ) -> str:
        """テキストデータを保存

        Args:
            content: 保存するテキスト
            filename: ファイル名
            subdirs: サブディレクトリのリスト

        Returns:
            保存したファイルのパス
        """
        # 保存先ディレクトリを作成
        save_dir = self.base_dir
        if subdirs:
            for subdir in subdirs:
                save_dir = save_dir / subdir
        save_dir.mkdir(parents=True, exist_ok=True)

        # ファイルパスを決定
        file_path = save_dir / filename

        # テキストを保存
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.info(f"Text saved to: {file_path}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error saving text: {e}")
            raise

    def load_json(self, filepath: str) -> dict[str, Any] | None:
        """JSONファイルを読み込み

        Args:
            filepath: ファイルパス

        Returns:
            読み込んだデータ or None
        """
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"File not found: {filepath}")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            self.logger.error(f"Error loading JSON: {e}")

        return None

    def load_text(self, filepath: str) -> str | None:
        """テキストファイルを読み込み

        Args:
            filepath: ファイルパス

        Returns:
            読み込んだテキスト or None
        """
        try:
            with open(filepath, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            self.logger.warning(f"File not found: {filepath}")
        except Exception as e:
            self.logger.error(f"Error loading text: {e}")

        return None

    def create_date_subdirs(self, date: datetime | None = None) -> list[str]:
        """日付ベースのサブディレクトリリストを作成

        Args:
            date: 日付（省略時は現在日時）

        Returns:
            サブディレクトリのリスト ['2024', '12', '25']
        """
        if date is None:
            date = datetime.now()

        return [str(date.year), f"{date.month:02d}", f"{date.day:02d}"]

    def generate_filename(
        self, council_id: str, schedule_id: str, extension: str
    ) -> str:
        """標準的なファイル名を生成

        Args:
            council_id: 議会ID
            schedule_id: スケジュールID
            extension: ファイル拡張子（'json', 'txt', 'pdf'など）

        Returns:
            生成されたファイル名
        """
        return f"{council_id}_{schedule_id}.{extension}"

    def list_files(
        self, pattern: str = "*", subdirs: list[str] | None = None
    ) -> list[Path]:
        """ファイルを一覧表示

        Args:
            pattern: ファイル名パターン（例: "*.json"）
            subdirs: サブディレクトリのリスト

        Returns:
            マッチしたファイルのパスリスト
        """
        search_dir = self.base_dir
        if subdirs:
            for subdir in subdirs:
                search_dir = search_dir / subdir

        if not search_dir.exists():
            return []

        return list(search_dir.glob(pattern))

    def cleanup_old_files(self, days: int = 30, pattern: str = "*"):
        """古いファイルを削除

        Args:
            days: この日数より古いファイルを削除
            pattern: 削除対象のファイルパターン
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)

        deleted_count = 0
        for file_path in self.base_dir.rglob(pattern):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    self.logger.error(f"Error deleting {file_path}: {e}")

        self.logger.info(f"Cleanup complete. Deleted {deleted_count} files.")

    def get_file_info(self, filepath: str) -> dict[str, Any] | None:
        """ファイル情報を取得

        Args:
            filepath: ファイルパス

        Returns:
            ファイル情報の辞書
        """
        path = Path(filepath)

        if not path.exists():
            return None

        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }

    def ensure_directory(self, path: str) -> Path:
        """ディレクトリが存在することを保証

        Args:
            path: ディレクトリパス

        Returns:
            作成されたPathオブジェクト
        """
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
