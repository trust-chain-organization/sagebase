"""ログフォーマッターの実装

構造化ログとJSON形式のログフォーマッター
"""

import json
import logging
from datetime import datetime
from typing import Any


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター

    ログを構造化された形式で出力
    """

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_location: bool = True,
    ):
        """初期化

        Args:
            include_timestamp: タイムスタンプを含めるか
            include_level: ログレベルを含めるか
            include_location: ファイル名と行番号を含めるか
        """
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_location = include_location

    def format(self, record: logging.LogRecord) -> str:
        """レコードをフォーマット

        Args:
            record: ログレコード

        Returns:
            フォーマットされたログ文字列
        """
        # 基本情報
        parts = []

        if self.include_timestamp:
            timestamp = datetime.fromtimestamp(record.created).isoformat()
            parts.append(f"[{timestamp}]")

        if self.include_level:
            parts.append(f"[{record.levelname}]")

        if self.include_location:
            parts.append(f"[{record.filename}:{record.lineno}]")

        # メッセージ
        parts.append(record.getMessage())

        # 追加情報（extra フィールド）
        extra_data = self._extract_extra(record)
        if extra_data:
            parts.append(f"| {self._format_extra(extra_data)}")

        # 例外情報
        if record.exc_info:
            parts.append(f"\n{self.formatException(record.exc_info)}")

        return " ".join(parts)

    def _extract_extra(self, record: logging.LogRecord) -> dict[str, Any]:
        """extraフィールドを抽出

        Args:
            record: ログレコード

        Returns:
            追加データの辞書
        """
        # デフォルトのフィールドを除外
        default_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in default_fields:
                extra[key] = value

        return extra

    def _format_extra(self, extra: dict[str, Any]) -> str:
        """追加データをフォーマット

        Args:
            extra: 追加データ

        Returns:
            フォーマットされた文字列
        """
        items = []
        for key, value in extra.items():
            if isinstance(value, dict | list):
                value = json.dumps(value, ensure_ascii=False, default=str)
            items.append(f"{key}={value}")
        return ", ".join(items)


class JSONFormatter(logging.Formatter):
    """JSONフォーマッター

    ログをJSON形式で出力（構造化ログ分析ツール用）
    """

    def __init__(self, indent: int | None = None, ensure_ascii: bool = False):
        """初期化

        Args:
            indent: インデント（Noneで1行）
            ensure_ascii: ASCII文字のみ使用するか
        """
        super().__init__()
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def format(self, record: logging.LogRecord) -> str:
        """レコードをJSON形式でフォーマット

        Args:
            record: ログレコード

        Returns:
            JSON形式のログ文字列
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "process_name": record.processName,
        }

        # 追加情報を含める
        extra = self._extract_extra(record)
        if extra:
            log_data["extra"] = extra

        # 例外情報を含める
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__
                if record.exc_info[0]
                else "Unknown",
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # スタック情報を含める
        if record.stack_info:
            log_data["stack_info"] = record.stack_info

        return json.dumps(
            log_data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=self._json_default,
        )

    def _extract_extra(self, record: logging.LogRecord) -> dict[str, Any]:
        """extraフィールドを抽出

        Args:
            record: ログレコード

        Returns:
            追加データの辞書
        """
        # デフォルトのフィールドを除外
        default_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "message",  # formatMessageで生成される
        }

        extra = {}
        for key, value in record.__dict__.items():
            if key not in default_fields:
                extra[key] = value

        return extra

    def _json_default(self, obj: Any) -> str:
        """JSONシリアライズできないオブジェクトの処理

        Args:
            obj: シリアライズするオブジェクト

        Returns:
            文字列表現
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return str(obj)
        else:
            return repr(obj)
