"""サーキットブレーカーの実装

障害の連鎖を防ぐためのサーキットブレーカーパターン
"""

import asyncio
import functools
import logging

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """サーキットブレーカーの状態"""

    CLOSED = "closed"  # 正常状態（リクエスト通過）
    OPEN = "open"  # 遮断状態（リクエスト拒否）
    HALF_OPEN = "half_open"  # 半開状態（限定的にリクエスト通過）


@dataclass
class CircuitBreakerConfig:
    """サーキットブレーカーの設定"""

    # 失敗閾値（この回数失敗したらOPENになる）
    failure_threshold: int = 5

    # 成功閾値（HALF_OPENでこの回数成功したらCLOSEDになる）
    success_threshold: int = 2

    # タイムアウト（OPEN状態の継続時間、秒）
    timeout: float = 60

    # 失敗率閾値（この割合を超えたらOPENになる、0.0〜1.0）
    failure_rate_threshold: float = 0.5

    # 最小リクエスト数（この数以下の場合は失敗率を計算しない）
    minimum_requests: int = 10

    # ウィンドウサイズ（失敗率計算のための時間窓、秒）
    window_size: float = 60


@dataclass
class CircuitBreakerStats:
    """サーキットブレーカーの統計情報"""

    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    state_changed_at: datetime = field(default_factory=datetime.now)
    recent_requests: list[tuple[datetime, bool]] = field(
        default_factory=list
    )  # (timestamp, is_success)


class CircuitBreakerError(Exception):
    """サーキットブレーカーが開いている場合の例外"""

    def __init__(self, message: str = "Circuit breaker is OPEN"):
        super().__init__(message)


class CircuitBreaker:
    """サーキットブレーカーの実装"""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        """初期化

        Args:
            name: サーキットブレーカーの名前
            config: 設定（Noneの場合はデフォルト）
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = Lock()
        self._half_open_lock = Lock()
        self._state_change_callbacks: list[
            Callable[[CircuitState, CircuitState], None]
        ] = []

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """関数を実行（サーキットブレーカー経由）

        Args:
            func: 実行する関数
            *args: 関数の引数
            **kwargs: 関数のキーワード引数

        Returns:
            関数の戻り値

        Raises:
            CircuitBreakerError: サーキットが開いている場合
        """
        with self._lock:
            if self._should_attempt_reset():
                self._transition_to_half_open()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")

        # HALF_OPENの場合、同時実行を制限
        if self.state == CircuitState.HALF_OPEN:
            if not self._half_open_lock.acquire(blocking=False):
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN and busy"
                )
            try:
                return self._execute(func, *args, **kwargs)
            finally:
                self._half_open_lock.release()
        else:
            return self._execute(func, *args, **kwargs)

    async def async_call(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """非同期関数を実行（サーキットブレーカー経由）

        Args:
            func: 実行する非同期関数
            *args: 関数の引数
            **kwargs: 関数のキーワード引数

        Returns:
            関数の戻り値

        Raises:
            CircuitBreakerError: サーキットが開いている場合
        """
        with self._lock:
            if self._should_attempt_reset():
                self._transition_to_half_open()

            if self.state == CircuitState.OPEN:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")

        # HALF_OPENの場合、同時実行を制限
        if self.state == CircuitState.HALF_OPEN:
            if not self._half_open_lock.acquire(blocking=False):
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN and busy"
                )
            try:
                return await self._async_execute(func, *args, **kwargs)
            finally:
                self._half_open_lock.release()
        else:
            return await self._async_execute(func, *args, **kwargs)

    def _execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """関数を実行して結果を記録"""
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

    async def _async_execute(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """非同期関数を実行して結果を記録"""
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

    def _record_success(self) -> None:
        """成功を記録"""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.total_successes += 1
            self.stats.consecutive_successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = datetime.now()

            # 最近のリクエストを記録
            self._record_recent_request(True)

            # HALF_OPENの場合、閾値チェック
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()

            logger.debug(
                f"Circuit breaker '{self.name}': Success recorded "
                f"(consecutive: {self.stats.consecutive_successes})"
            )

    def _record_failure(self) -> None:
        """失敗を記録"""
        with self._lock:
            self.stats.total_requests += 1
            self.stats.total_failures += 1
            self.stats.consecutive_failures += 1
            self.stats.consecutive_successes = 0
            self.stats.last_failure_time = datetime.now()

            # 最近のリクエストを記録
            self._record_recent_request(False)

            # 失敗閾値チェック
            if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self._should_open():
                    self._transition_to_open()

            logger.debug(
                f"Circuit breaker '{self.name}': Failure recorded "
                f"(consecutive: {self.stats.consecutive_failures})"
            )

    def _record_recent_request(self, is_success: bool) -> None:
        """最近のリクエストを記録"""
        now = datetime.now()
        self.stats.recent_requests.append((now, is_success))

        # 古いエントリを削除
        from datetime import timedelta

        cutoff = now - timedelta(seconds=self.config.window_size)
        self.stats.recent_requests = [
            (ts, success) for ts, success in self.stats.recent_requests if ts > cutoff
        ]

    def _should_open(self) -> bool:
        """サーキットを開くべきか判定"""
        # 連続失敗数チェック
        if self.stats.consecutive_failures >= self.config.failure_threshold:
            return True

        # 失敗率チェック
        if len(self.stats.recent_requests) >= self.config.minimum_requests:
            failures = sum(
                1 for _, success in self.stats.recent_requests if not success
            )
            failure_rate = failures / len(self.stats.recent_requests)
            if failure_rate >= self.config.failure_rate_threshold:
                return True

        return False

    def _should_attempt_reset(self) -> bool:
        """リセットを試みるべきか判定"""
        if self.state != CircuitState.OPEN:
            return False

        elapsed = (datetime.now() - self.stats.state_changed_at).total_seconds()
        return elapsed >= self.config.timeout

    def _transition_to_open(self) -> None:
        """OPEN状態に遷移"""
        self.state = CircuitState.OPEN
        self.stats.state_changed_at = datetime.now()
        self.stats.consecutive_failures = 0
        self.stats.consecutive_successes = 0

        logger.warning(
            f"Circuit breaker '{self.name}': Transitioned to OPEN "
            f"(failures: {self.stats.total_failures}, "
            f"success_rate: {self._get_success_rate():.2%})"
        )

        self._notify_state_change(CircuitState.OPEN)

    def _transition_to_closed(self) -> None:
        """CLOSED状態に遷移"""
        self.state = CircuitState.CLOSED
        self.stats.state_changed_at = datetime.now()
        self.stats.consecutive_failures = 0
        self.stats.consecutive_successes = 0

        logger.info(
            f"Circuit breaker '{self.name}': Transitioned to CLOSED "
            f"(success_rate: {self._get_success_rate():.2%})"
        )

        self._notify_state_change(CircuitState.CLOSED)

    def _transition_to_half_open(self) -> None:
        """HALF_OPEN状態に遷移"""
        self.state = CircuitState.HALF_OPEN
        self.stats.state_changed_at = datetime.now()
        self.stats.consecutive_failures = 0
        self.stats.consecutive_successes = 0

        logger.info(f"Circuit breaker '{self.name}': Transitioned to HALF_OPEN")

        self._notify_state_change(CircuitState.HALF_OPEN)

    def _get_success_rate(self) -> float:
        """成功率を取得"""
        if self.stats.total_requests == 0:
            return 1.0
        return self.stats.total_successes / self.stats.total_requests

    def _notify_state_change(self, new_state: CircuitState) -> None:
        """状態変更を通知"""
        old_state = self.state
        for callback in self._state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}", exc_info=True)

    def add_state_change_callback(
        self, callback: Callable[[CircuitState, CircuitState], None]
    ) -> None:
        """状態変更コールバックを追加"""
        self._state_change_callbacks.append(callback)

    def reset(self) -> None:
        """サーキットブレーカーをリセット"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.stats = CircuitBreakerStats()
            logger.info(f"Circuit breaker '{self.name}': Reset to CLOSED")

    def get_status(self) -> dict[str, Any]:
        """現在のステータスを取得"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "total_requests": self.stats.total_requests,
                "total_failures": self.stats.total_failures,
                "total_successes": self.stats.total_successes,
                "success_rate": self._get_success_rate(),
                "consecutive_failures": self.stats.consecutive_failures,
                "consecutive_successes": self.stats.consecutive_successes,
                "last_failure_time": self.stats.last_failure_time.isoformat()
                if self.stats.last_failure_time
                else None,
                "last_success_time": self.stats.last_success_time.isoformat()
                if self.stats.last_success_time
                else None,
                "state_changed_at": self.stats.state_changed_at.isoformat(),
            }


def circuit_breaker(
    name: str | None = None, config: CircuitBreakerConfig | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """サーキットブレーカーデコレータ

    Args:
        name: サーキットブレーカーの名前
        config: 設定

    Examples:
        @circuit_breaker(name="external_api")
        def call_api():
            return requests.get("https://api.example.com")

        @circuit_breaker(config=CircuitBreakerConfig(failure_threshold=3))
        async def async_call():
            async with aiohttp.ClientSession() as session:
                return await session.get("https://api.example.com")
    """
    breakers: dict[str, CircuitBreaker] = {}

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        breaker_name = name or f"{func.__module__}.{func.__name__}"

        if breaker_name not in breakers:
            breakers[breaker_name] = CircuitBreaker(breaker_name, config)

        breaker = breakers[breaker_name]

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await breaker.async_call(func, *args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return breaker.call(func, *args, **kwargs)

            return sync_wrapper

    return decorator
