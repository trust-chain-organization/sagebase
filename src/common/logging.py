"""構造化ログの設定と共通ユーティリティ."""

import logging
import sys
from typing import Any, cast

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


try:
    import sentry_sdk

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

# ログレベルの定義
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class SentryProcessor:
    """Sentry統合用のstructlogプロセッサー.

    ERROR以上のログをSentryに送信します。
    """

    def __call__(
        self, logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """ログイベントを処理し、必要に応じてSentryに送信.

        Args:
            logger: ロガーインスタンス
            method_name: ログメソッド名 (error, warning, info等)
            event_dict: ログイベントの辞書

        Returns:
            変更されていないイベント辞書
        """
        if not SENTRY_AVAILABLE:
            return event_dict

        # ログレベルを取得
        level = event_dict.get("level", method_name).upper()

        # ERROR以上のレベルをSentryに送信
        if level in ["ERROR", "CRITICAL", "FATAL"]:
            # イベントからメッセージを取得
            message = event_dict.get("event", "Unknown error")

            # 例外情報があれば送信
            exc_info = event_dict.get("exc_info")
            if exc_info:
                # exc_info が True の場合は sys.exc_info() から取得
                if exc_info is True:
                    import sys

                    exc_info = sys.exc_info()
                # exc_info がタプルの場合は最初の要素（例外インスタンス）を使用
                if (
                    isinstance(exc_info, tuple)
                    and len(cast(tuple[Any, ...], exc_info)) >= 2
                ):
                    sentry_sdk.capture_exception(exc_info[1])  # type: ignore
                elif isinstance(exc_info, BaseException):
                    sentry_sdk.capture_exception(exc_info)  # type: ignore
            else:
                # 例外がない場合はメッセージとして送信
                extra = {
                    k: v
                    for k, v in event_dict.items()
                    if k not in ["event", "level", "timestamp", "logger", "exc_info"]
                }
                sentry_sdk.capture_message(message, level=level.lower(), extras=extra)  # type: ignore

        return event_dict


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    add_timestamp: bool = True,
    enable_sentry: bool = True,
) -> None:
    """構造化ログの初期設定.

    Args:
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: JSON形式で出力するか
        add_timestamp: タイムスタンプを追加するか
        enable_sentry: Sentry統合を有効にするか
    """
    # タイムスタンプ追加のプロセッサー
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    # 共通のプロセッサー
    shared_processors_raw = [  # type: ignore[var-annotated]
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper if add_timestamp else None,
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.UnicodeDecoder(),
        SentryProcessor() if enable_sentry and SENTRY_AVAILABLE else None,
    ]

    # Noneを除外
    shared_processors: list[Any] = [p for p in shared_processors_raw if p is not None]  # type: ignore[misc]

    # レンダラーの選択
    if json_format:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # structlogの設定
    structlog.configure(
        processors=cast(list[Any], shared_processors)
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 標準ログのフォーマッター
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=cast(list[Any], shared_processors),
    )

    # ハンドラーの設定
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(LOG_LEVELS.get(log_level, logging.INFO))

    # structlogロガーも同じレベルに設定
    logging.getLogger("structlog").setLevel(LOG_LEVELS.get(log_level, logging.INFO))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """構造化ログのロガーインスタンスを取得.

    Args:
        name: ロガー名（通常は__name__を渡す）

    Returns:
        構造化ログのロガーインスタンス
    """
    return structlog.get_logger(name)


def add_context(**kwargs: Any) -> None:
    """現在のコンテキストにキー・バリューペアを追加.

    Args:
        **kwargs: コンテキストに追加するキー・バリューペア
    """
    bind_contextvars(**kwargs)


def clear_context() -> None:
    """現在のコンテキストをクリア."""
    clear_contextvars()


class LogContext:
    """with文で使用できるログコンテキストマネージャー."""

    def __init__(self, **kwargs: Any):
        """コンテキストマネージャーの初期化.

        Args:
            **kwargs: コンテキストに追加するキー・バリューペア
        """
        self.context = kwargs

    def __enter__(self) -> "LogContext":
        """コンテキストに入る際の処理."""
        add_context(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """コンテキストから出る際の処理."""
        # 注: clear_context()を呼ぶと他のコンテキストも消えるため、
        # 実装では個別のコンテキスト管理が必要な場合は要検討
        pass


# デフォルトログ設定の適用は呼び出し側で行う
# setup_logging()
