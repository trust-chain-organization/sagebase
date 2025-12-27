"""ログコンテキスト管理

ログにコンテキスト情報を追加するためのユーティリティ
"""

import contextvars
import functools
import logging

from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, TypeVar
from uuid import uuid4


# コンテキスト変数（スレッドセーフ・非同期セーフ）
_log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "log_context"
)


class LogContext:
    """ログコンテキストを管理するクラス"""

    @staticmethod
    def set(**kwargs: Any) -> None:
        """コンテキストを設定

        Args:
            **kwargs: 設定するコンテキスト情報
        """
        current = _log_context.get({}).copy()
        current.update(kwargs)
        _log_context.set(current)

    @staticmethod
    def get() -> dict[str, Any]:
        """現在のコンテキストを取得

        Returns:
            コンテキスト情報の辞書
        """
        return _log_context.get({}).copy()

    @staticmethod
    def clear() -> None:
        """コンテキストをクリア"""
        _log_context.set({})

    @staticmethod
    def set_request_id(request_id: str | None = None) -> str:
        """リクエストIDを設定

        Args:
            request_id: リクエストID（Noneの場合は自動生成）

        Returns:
            設定されたリクエストID
        """
        if request_id is None:
            request_id = str(uuid4())
        LogContext.set(request_id=request_id)
        return request_id

    @staticmethod
    def set_user_id(user_id: str) -> None:
        """ユーザーIDを設定

        Args:
            user_id: ユーザーID
        """
        LogContext.set(user_id=user_id)

    @staticmethod
    def set_operation(operation: str) -> None:
        """操作名を設定

        Args:
            operation: 操作名
        """
        LogContext.set(operation=operation)

    @staticmethod
    @contextmanager
    def context(**kwargs: Any):
        """一時的なコンテキストを設定

        Args:
            **kwargs: コンテキスト情報

        Examples:
            with LogContext.context(request_id="123"):
                # このブロック内でのログにrequest_idが追加される
                logger.info("Processing request")
        """
        old_context = _log_context.get({})
        new_context = old_context.copy()
        new_context.update(kwargs)
        token = _log_context.set(new_context)

        try:
            yield
        finally:
            _log_context.reset(token)


T = TypeVar("T", bound=Callable[..., Any])


def with_log_context(**default_context: Any) -> Callable[[T], T]:
    """関数にログコンテキストを追加するデコレータ

    Args:
        **default_context: デフォルトのコンテキスト情報

    Examples:
        @with_log_context(operation="fetch_user")
        def fetch_user(user_id: str):
            LogContext.set(user_id=user_id)
            logger.info("Fetching user")
            return user
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with LogContext.context(**default_context):
                # 関数名を自動的に追加
                LogContext.set(function=func.__name__)
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with LogContext.context(**default_context):
                # 関数名を自動的に追加
                LogContext.set(function=func.__name__)
                return await func(*args, **kwargs)

        # 非同期関数か同期関数かで適切なラッパーを返す
        import asyncio

        from typing import cast

        if asyncio.iscoroutinefunction(func):
            return cast(T, async_wrapper)
        else:
            return cast(T, sync_wrapper)

    return decorator


class ContextualLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """コンテキスト情報を自動的に追加するログアダプター"""

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        """ログメッセージにコンテキスト情報を追加

        Args:
            msg: ログメッセージ
            kwargs: ログのキーワード引数

        Returns:
            処理後のメッセージとキーワード引数
        """
        # コンテキスト情報を取得
        context = LogContext.get()

        # extraフィールドにコンテキストを追加
        if context:
            extra = kwargs.get("extra", {})
            extra["context"] = context
            kwargs["extra"] = extra

        return msg, kwargs


def get_contextual_logger(name: str) -> ContextualLoggerAdapter:
    """コンテキスト付きロガーを取得

    Args:
        name: ロガー名

    Returns:
        コンテキスト付きロガー

    Examples:
        logger = get_contextual_logger(__name__)

        with LogContext.context(request_id="123"):
            logger.info("Processing")  # request_idが自動的に含まれる
    """
    base_logger = logging.getLogger(name)
    return ContextualLoggerAdapter(base_logger, {})
