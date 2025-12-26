"""計測用デコレーターとユーティリティ."""

import asyncio
import functools
import time

from collections.abc import Callable
from typing import Any, TypeVar, cast

from src.common.logging import LogContext, get_logger
from src.common.metrics import create_counter, create_histogram, record_error


logger = get_logger(__name__)

T = TypeVar("T")


def measure_time(
    metric_name: str | None = None,
    labels: dict[str, str] | None = None,
    record_errors: bool = True,
    log_slow_operations: float = 1.0,  # 秒
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """関数の実行時間を計測するデコレーター.

    Args:
        metric_name: メトリクス名（指定しない場合は関数名から生成）
        labels: 追加のラベル
        record_errors: エラーを記録するか
        log_slow_operations: この時間（秒）を超えた処理をログに記録

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # メトリクス名の決定
        actual_metric_name = metric_name or f"{func.__module__}.{func.__name__}"

        # 遅延初期化用の変数
        duration_metric = None
        call_counter = None

        def get_metrics():
            """メトリクスを遅延初期化."""
            nonlocal duration_metric, call_counter
            if duration_metric is None:
                duration_metric = create_histogram(
                    f"{actual_metric_name}_duration_seconds",
                    f"Duration of {actual_metric_name}",
                    "s",
                )
            if call_counter is None:
                call_counter = create_counter(
                    f"{actual_metric_name}_calls_total",
                    f"Total calls to {actual_metric_name}",
                    "1",
                )
            return duration_metric, call_counter

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            attributes = labels or {}

            # メトリクスを事前に初期化
            duration_metric, call_counter = get_metrics()

            try:
                call_counter.add(1, attributes=attributes)

                # ログコンテキストの設定
                with LogContext(operation=actual_metric_name):
                    result = func(*args, **kwargs)

                # 成功時の処理
                elapsed = time.time() - start_time
                duration_metric.record(elapsed, attributes=attributes)

                # 遅い処理のログ
                if elapsed > log_slow_operations:
                    logger.warning(
                        "Slow operation detected",
                        operation=actual_metric_name,
                        duration_seconds=elapsed,
                        threshold_seconds=log_slow_operations,
                    )

                return cast(T, result)

            except Exception as e:
                # エラー時の処理
                elapsed = time.time() - start_time
                error_attributes = {**attributes, "error": type(e).__name__}
                duration_metric.record(elapsed, attributes=error_attributes)

                if record_errors:
                    record_error(type(e).__name__, actual_metric_name)
                    logger.error(
                        "Operation failed",
                        operation=actual_metric_name,
                        duration_seconds=elapsed,
                        error=str(e),
                        exc_info=True,
                    )

                raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.time()
            attributes = labels or {}

            # メトリクスを事前に初期化
            duration_metric, call_counter = get_metrics()

            try:
                call_counter.add(1, attributes=attributes)

                # ログコンテキストの設定
                with LogContext(operation=actual_metric_name):
                    result: T = await func(*args, **kwargs)  # type: ignore[misc]

                # 成功時の処理
                elapsed = time.time() - start_time
                duration_metric.record(elapsed, attributes=attributes)

                # 遅い処理のログ
                if elapsed > log_slow_operations:
                    logger.warning(
                        "Slow operation detected",
                        operation=actual_metric_name,
                        duration_seconds=elapsed,
                        threshold_seconds=log_slow_operations,
                    )

                return cast(T, result)

            except Exception as e:
                # エラー時の処理
                elapsed = time.time() - start_time
                error_attributes = {**attributes, "error": type(e).__name__}
                duration_metric.record(elapsed, attributes=error_attributes)

                if record_errors:
                    record_error(type(e).__name__, actual_metric_name)
                    logger.error(
                        "Operation failed",
                        operation=actual_metric_name,
                        duration_seconds=elapsed,
                        error=str(e),
                        exc_info=True,
                    )

                raise

        # 非同期関数かどうかで適切なラッパーを返す
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper

    return decorator


def count_calls(
    metric_name: str | None = None,
    labels: dict[str, str] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """関数の呼び出し回数をカウントするデコレーター.

    Args:
        metric_name: メトリクス名（指定しない場合は関数名から生成）
        labels: 追加のラベル

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # メトリクス名の決定
        actual_metric_name = metric_name or f"{func.__module__}.{func.__name__}"

        # 遅延初期化用の変数
        counter = None

        def get_counter():
            """カウンターを遅延初期化."""
            nonlocal counter
            if counter is None:
                counter = create_counter(
                    f"{actual_metric_name}_total",
                    f"Total calls to {actual_metric_name}",
                    "1",
                )
            return counter

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            attributes = labels or {}
            get_counter().add(1, attributes=attributes)
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            attributes = labels or {}
            get_counter().add(1, attributes=attributes)
            result: T = await func(*args, **kwargs)  # type: ignore[misc]
            return result  # type: ignore[return-value]

        # 非同期関数かどうかで適切なラッパーを返す
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper

    return decorator


class MetricsContext:
    """メトリクス記録用のコンテキストマネージャー."""

    def __init__(
        self,
        operation: str,
        labels: dict[str, str] | None = None,
        record_duration: bool = True,
        record_errors: bool = True,
    ):
        """コンテキストマネージャーの初期化.

        Args:
            operation: 操作名
            labels: 追加のラベル
            record_duration: 実行時間を記録するか
            record_errors: エラーを記録するか
        """
        self.operation = operation
        self.labels = labels or {}
        self.record_duration = record_duration
        self.record_errors = record_errors
        self.start_time: float | None = None

        # メトリクスの遅延初期化
        self.duration_metric = None
        self.additional_metrics: dict[str, Any] = {}

    def __enter__(self) -> "MetricsContext":
        """コンテキストに入る際の処理."""
        self.start_time = time.time()
        logger.debug(
            "Operation started",
            operation=self.operation,
            labels=self.labels,
        )

        # 初回利用時にメトリクスを作成
        if self.record_duration and self.duration_metric is None:
            self.duration_metric = create_histogram(
                f"{self.operation}_duration_seconds",
                f"Duration of {self.operation}",
                "s",
            )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """コンテキストから出る際の処理."""
        if (
            self.record_duration
            and self.start_time is not None
            and self.duration_metric is not None
        ):
            elapsed = time.time() - self.start_time

            # エラーの有無で属性を変更
            attributes = self.labels.copy()
            if exc_type is not None:
                attributes["error"] = exc_type.__name__
                if self.record_errors:
                    record_error(exc_type.__name__, self.operation)

            self.duration_metric.record(elapsed, attributes=attributes)

            logger.debug(
                "Operation completed",
                operation=self.operation,
                duration_seconds=elapsed,
                error=exc_type.__name__ if exc_type else None,
            )

    def add_metric(self, name: str, value: int | float) -> None:
        """追加のメトリクスを記録.

        Args:
            name: メトリクス名
            value: 値
        """
        self.additional_metrics[name] = value


# 共通の計測デコレーター関数
def measure_http_request():
    """HTTPリクエスト用の計測デコレーター."""
    return measure_time(
        metric_name="http_request",
        log_slow_operations=2.0,
    )


def measure_db_operation():
    """DB操作用の計測デコレーター."""
    return measure_time(
        metric_name="db_operation",
        log_slow_operations=0.5,
    )


def measure_llm_call():
    """LLM API呼び出し用の計測デコレーター."""
    return measure_time(
        metric_name="llm_api_call",
        log_slow_operations=5.0,
    )
