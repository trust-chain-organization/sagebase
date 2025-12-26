"""エラーロガーの実装

統一的なエラーログ記録機能を提供
"""

import logging
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from src.domain.exceptions import PolibaseException


class ErrorLogger:
    """エラーログを記録するクラス"""

    def __init__(self, logger_name: str = __name__):
        """初期化

        Args:
            logger_name: ロガー名
        """
        self.logger = logging.getLogger(logger_name)
        self._context: dict[str, Any] = {}

    def log_error(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
        level: int = logging.ERROR,
        include_traceback: bool = True,
        user_message: str | None = None,
    ) -> None:
        """エラーをログに記録

        Args:
            exception: 記録する例外
            context: 追加のコンテキスト情報
            level: ログレベル
            include_traceback: トレースバックを含めるか
            user_message: ユーザー向けメッセージ
        """
        log_data = self._build_log_data(
            exception, context, include_traceback, user_message
        )

        # ログレベルに応じて出力
        self.logger.log(level, log_data["message"], extra=log_data)

    def log_warning(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
        user_message: str | None = None,
    ) -> None:
        """警告レベルでエラーをログに記録

        Args:
            exception: 記録する例外
            context: 追加のコンテキスト情報
            user_message: ユーザー向けメッセージ
        """
        self.log_error(
            exception,
            context,
            level=logging.WARNING,
            include_traceback=False,
            user_message=user_message,
        )

    def log_critical(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
        user_message: str | None = None,
    ) -> None:
        """重大エラーをログに記録

        Args:
            exception: 記録する例外
            context: 追加のコンテキスト情報
            user_message: ユーザー向けメッセージ
        """
        self.log_error(
            exception,
            context,
            level=logging.CRITICAL,
            include_traceback=True,
            user_message=user_message,
        )

    def log_with_retry_info(
        self,
        exception: Exception,
        retry_count: int,
        max_retries: int,
        context: dict[str, Any] | None = None,
    ) -> None:
        """リトライ情報付きでエラーをログに記録

        Args:
            exception: 記録する例外
            retry_count: 現在のリトライ回数
            max_retries: 最大リトライ回数
            context: 追加のコンテキスト情報
        """
        retry_context = {
            "retry_count": retry_count,
            "max_retries": max_retries,
            "is_final_attempt": retry_count >= max_retries,
        }

        if context:
            retry_context.update(context)

        level = logging.ERROR if retry_count >= max_retries else logging.WARNING
        self.log_error(exception, retry_context, level=level)

    def log_performance_issue(
        self,
        operation: str,
        duration_seconds: float,
        threshold_seconds: float,
        context: dict[str, Any] | None = None,
    ) -> None:
        """パフォーマンス問題をログに記録

        Args:
            operation: 実行した操作
            duration_seconds: 実行時間（秒）
            threshold_seconds: 閾値（秒）
            context: 追加のコンテキスト情報
        """
        perf_data = {
            "operation": operation,
            "duration_seconds": duration_seconds,
            "threshold_seconds": threshold_seconds,
            "exceeded_by": duration_seconds - threshold_seconds,
            **(context or {}),
        }

        message = (
            f"Performance issue detected: Operation '{operation}' "
            f"took {duration_seconds:.2f}s (threshold: {threshold_seconds:.2f}s)"
        )

        self.logger.warning(message, extra=perf_data)

    def _build_log_data(
        self,
        exception: Exception,
        context: dict[str, Any] | None,
        include_traceback: bool,
        user_message: str | None,
    ) -> dict[str, Any]:
        """ログデータを構築

        Args:
            exception: 例外
            context: コンテキスト
            include_traceback: トレースバックを含めるか
            user_message: ユーザー向けメッセージ

        Returns:
            ログデータの辞書
        """
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "exception_type": exception.__class__.__name__,
            "exception_module": exception.__class__.__module__,
            "message": str(exception),
            "user_message": user_message,
        }

        # Polibase例外の場合は追加情報を含める
        if isinstance(exception, PolibaseException):
            log_data["error_code"] = exception.error_code
            log_data["error_details"] = exception.details

        # トレースバックを含める
        if include_traceback:
            log_data["traceback"] = traceback.format_exc()
            log_data["stack_info"] = self._extract_stack_info()

        # コンテキスト情報を追加
        if context:
            log_data["context"] = context

        # グローバルコンテキストを追加
        if self._context:
            log_data["global_context"] = self._context

        return log_data

    def _extract_stack_info(self) -> list[dict[str, Any]]:
        """スタック情報を抽出

        Returns:
            スタックフレーム情報のリスト
        """
        stack_info: list[dict[str, Any]] = []
        for frame_info in traceback.extract_stack()[:-2]:  # 現在のフレームを除外
            stack_info.append(
                {
                    "filename": frame_info.filename,
                    "line_number": frame_info.lineno,
                    "function": frame_info.name,
                    "code": frame_info.line,
                }
            )
        return stack_info[-10:]  # 最後の10フレームのみ

    def set_context(self, **kwargs: Any) -> None:
        """グローバルコンテキストを設定

        Args:
            **kwargs: コンテキスト情報
        """
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """グローバルコンテキストをクリア"""
        self._context.clear()

    @contextmanager
    def context(self, **kwargs: Any):
        """一時的なコンテキストを設定

        Args:
            **kwargs: コンテキスト情報

        Examples:
            with error_logger.context(request_id="123", user_id="456"):
                # このブロック内でのログにコンテキストが追加される
                error_logger.log_error(exception)
        """
        old_context = self._context.copy()
        self._context.update(kwargs)
        try:
            yield
        finally:
            self._context = old_context

    def create_child(self, name: str, **context: Any) -> "ErrorLogger":
        """子ロガーを作成

        Args:
            name: 子ロガーの名前
            **context: 追加のコンテキスト

        Returns:
            子ロガー
        """
        child_logger = ErrorLogger(f"{self.logger.name}.{name}")
        child_logger._context = {**self._context, **context}
        return child_logger


# グローバルエラーロガーのインスタンス
_error_logger: ErrorLogger | None = None


def get_error_logger(name: str | None = None) -> ErrorLogger:
    """エラーロガーを取得

    Args:
        name: ロガー名（Noneの場合はグローバルロガー）

    Returns:
        エラーロガーのインスタンス
    """
    global _error_logger

    if name:
        return ErrorLogger(name)

    if _error_logger is None:
        _error_logger = ErrorLogger("sagebase.error")

    return _error_logger


def log_exception(
    exception: Exception,
    context: dict[str, Any] | None = None,
    logger_name: str | None = None,
) -> None:
    """例外をログに記録するショートカット関数

    Args:
        exception: 記録する例外
        context: 追加のコンテキスト情報
        logger_name: ロガー名
    """
    logger = get_error_logger(logger_name)
    logger.log_error(exception, context)
