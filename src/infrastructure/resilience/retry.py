"""リトライポリシーの実装

外部サービス呼び出しなどのリトライ処理を統一的に管理
"""

import asyncio
import functools
import logging

from collections.abc import Callable
from typing import Any

from tenacity import (
    RetryError,
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_chain,
    wait_exponential,
    wait_fixed,
    wait_random,
)

from src.infrastructure.exceptions import (
    ConnectionException,
    DatabaseException,
    ExternalServiceException,
    NetworkException,
    RateLimitException,
    TimeoutException,
)


logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """リトライ可能なエラーの基底クラス"""

    pass


class RetryPolicy:
    """リトライポリシーを定義するクラス

    様々なシナリオに対応したリトライポリシーを提供
    """

    # リトライ可能な例外のデフォルトリスト
    DEFAULT_RETRYABLE_EXCEPTIONS = (
        ConnectionException,
        NetworkException,
        TimeoutException,
        RetryableError,
    )

    @staticmethod
    def default():
        """デフォルトのリトライポリシー

        - 最大3回リトライ
        - 指数バックオフ（1秒〜10秒）
        """
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=1, max=10),
            retry=retry_if_exception_type(RetryPolicy.DEFAULT_RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )

    @staticmethod
    def external_service():
        """外部サービス用のリトライポリシー

        - 最大5回リトライ
        - 指数バックオフ（2秒〜30秒）
        - レート制限エラーも含む
        """
        retryable_exceptions = RetryPolicy.DEFAULT_RETRYABLE_EXCEPTIONS + (
            RateLimitException,
            ExternalServiceException,
        )

        def should_retry(exception: BaseException) -> bool:
            """リトライすべきか判定"""
            # 外部サービスエラーの場合、ステータスコードを確認
            if isinstance(exception, ExternalServiceException):
                status_code = exception.details.get("status_code")
                # 5xx エラーまたは 429 (Too Many Requests) はリトライ
                if status_code and (500 <= status_code < 600 or status_code == 429):
                    return True
                # 4xxエラーはリトライしない
                return False

            # その他の特定の例外タイプ
            if isinstance(exception, retryable_exceptions):
                return True

            return False

        return retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(min=2, max=30),
            retry=retry_if_exception(should_retry),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )

    @staticmethod
    def database():
        """データベース用のリトライポリシー

        - 最大3回リトライ
        - 固定遅延（1秒）
        - デッドロックやタイムアウトのみ
        """

        def should_retry(exception: BaseException) -> bool:
            """データベースエラーでリトライすべきか判定"""
            if isinstance(exception, DatabaseException):
                # デッドロックやタイムアウトはリトライ
                reason = exception.details.get("reason", "").lower()
                if any(
                    keyword in reason
                    for keyword in ["deadlock", "timeout", "connection"]
                ):
                    return True
            elif isinstance(exception, ConnectionException | TimeoutException):
                return True

            return False

        return retry(
            stop=stop_after_attempt(3),
            wait=wait_fixed(1),
            retry=retry_if_exception(should_retry),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )

    @staticmethod
    def aggressive():
        """アグレッシブなリトライポリシー

        - 最大10回リトライ
        - 指数バックオフ（0.5秒〜60秒）
        - より多くの例外をリトライ
        """
        return retry(
            stop=stop_after_attempt(10),
            wait=wait_exponential(min=0.5, max=60),
            retry=retry_if_exception_type(Exception),  # すべての例外をリトライ
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )

    @staticmethod
    def no_retry():
        """リトライしないポリシー

        リトライを無効化（テスト用など）
        """
        return retry(
            stop=stop_after_attempt(1),
            retry=retry_if_exception_type(()),  # 何もリトライしない
        )

    @staticmethod
    def with_jitter(
        max_attempts: int = 3,
        min_wait: float = 1,
        max_wait: float = 10,
        jitter: float = 1,
    ):
        """ジッター付きリトライポリシー

        複数のクライアントが同時にリトライすることを防ぐ

        Args:
            max_attempts: 最大リトライ回数
            min_wait: 最小待機時間（秒）
            max_wait: 最大待機時間（秒）
            jitter: ジッター量（秒）
        """
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_chain(
                wait_exponential(min=min_wait, max=max_wait), wait_random(0, jitter)
            ),
            retry=retry_if_exception_type(RetryPolicy.DEFAULT_RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )

    @staticmethod
    def rate_limit_aware():
        """レート制限を考慮したリトライポリシー

        レート制限エラーの場合、指定された時間待機
        """

        def wait_for_rate_limit(retry_state: Any) -> float:
            """レート制限の待機時間を計算"""
            exception = retry_state.outcome.exception()

            if isinstance(exception, RateLimitException):
                # retry_after が指定されていればその時間待機
                retry_after = exception.details.get("retry_after")
                if retry_after:
                    return retry_after

            # デフォルトは指数バックオフ
            return wait_exponential(min=5, max=60)(retry_state)

        return retry(
            stop=stop_after_attempt(5),
            wait=wait_for_rate_limit,
            retry=retry_if_exception_type(
                (RateLimitException,) + RetryPolicy.DEFAULT_RETRYABLE_EXCEPTIONS
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )

    @staticmethod
    def custom(
        max_attempts: int = 3,
        wait_strategy: Any = None,
        retryable_exceptions: tuple[type[Exception], ...] | None = None,
        should_retry: Callable[[BaseException], bool] | None = None,
    ):
        """カスタムリトライポリシー

        Args:
            max_attempts: 最大リトライ回数
            wait_strategy: 待機戦略
            retryable_exceptions: リトライ可能な例外のタプル
            should_retry: リトライ判定関数
        """
        if wait_strategy is None:
            wait_strategy = wait_exponential(min=1, max=10)

        if should_retry:
            retry_condition = retry_if_exception(should_retry)
        elif retryable_exceptions:
            retry_condition = retry_if_exception_type(retryable_exceptions)
        else:
            retry_condition = retry_if_exception_type(
                RetryPolicy.DEFAULT_RETRYABLE_EXCEPTIONS
            )

        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_strategy,
            retry=retry_condition,
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO),
        )


def with_retry(
    policy: Callable[..., Any] | None = None, async_func: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """関数にリトライポリシーを適用するデコレータ

    Args:
        policy: 使用するリトライポリシー（Noneの場合はデフォルト）
        async_func: 非同期関数かどうか

    Examples:
        @with_retry()
        def fetch_data():
            return requests.get("https://api.example.com/data")

        @with_retry(policy=RetryPolicy.external_service())
        async def async_fetch():
            async with aiohttp.ClientSession() as session:
                return await session.get("https://api.example.com/data")
    """
    if policy is None:
        policy = RetryPolicy.default()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if async_func or asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # 非同期関数用のラッパー
                @policy
                async def retry_func():
                    return await func(*args, **kwargs)

                try:
                    return await retry_func()
                except RetryError as e:
                    # 最後の例外を再発生
                    last_exception = e.last_attempt.exception()
                    if last_exception is not None:
                        raise last_exception from None
                    raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # 同期関数用のラッパー
                @policy
                def retry_func():
                    return func(*args, **kwargs)

                try:
                    return retry_func()
                except RetryError as e:
                    # 最後の例外を再発生
                    last_exception = e.last_attempt.exception()
                    if last_exception is not None:
                        raise last_exception from None
                    raise

            return sync_wrapper

    return decorator
