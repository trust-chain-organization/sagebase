"""Performance metrics collection and monitoring."""

import functools
import logging
import time

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])

logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Container for metric data."""

    name: str
    value: float
    timestamp: datetime
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryMetrics:
    """Database query performance metrics."""

    query_type: str
    duration_ms: float
    row_count: int
    table_name: str
    timestamp: datetime
    slow_query: bool = False
    query_text: str = ""


class PerformanceMonitor:
    """Central performance monitoring system."""

    def __init__(self, slow_query_threshold_ms: float = 1000):
        """Initialize performance monitor.

        Args:
            slow_query_threshold_ms: Threshold for slow query detection in milliseconds
        """
        self._slow_query_threshold = (
            slow_query_threshold_ms / 1000
        )  # Convert to seconds
        self._metrics: list[MetricData] = []
        self._query_metrics: list[QueryMetrics] = []
        self._active_timers: dict[str, float] = {}

    def start_timer(self, name: str) -> None:
        """Start a named timer."""
        self._active_timers[name] = time.perf_counter()

    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return duration in seconds."""
        if name not in self._active_timers:
            logger.warning(f"Timer '{name}' was not started")
            return 0.0

        start_time = self._active_timers.pop(name)
        duration = time.perf_counter() - start_time
        return duration

    def record_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a performance metric.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for categorization
            metadata: Optional metadata
        """
        metric = MetricData(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata=metadata or {},
        )
        self._metrics.append(metric)

        # Log if debug mode
        logger.debug(f"Metric recorded: {name}={value} tags={tags}")

    def record_query(
        self,
        query_type: str,
        duration_ms: float,
        row_count: int,
        table_name: str,
        query_text: str = "",
    ) -> None:
        """Record database query metrics.

        Args:
            query_type: Type of query (SELECT, INSERT, etc.)
            duration_ms: Query duration in milliseconds
            row_count: Number of rows affected/returned
            table_name: Primary table name
            query_text: Optional query text
        """
        slow_query = duration_ms / 1000 > self._slow_query_threshold

        metric = QueryMetrics(
            query_type=query_type,
            duration_ms=duration_ms,
            row_count=row_count,
            table_name=table_name,
            timestamp=datetime.now(),
            slow_query=slow_query,
            query_text=query_text[:500] if query_text else "",  # Truncate long queries
        )
        self._query_metrics.append(metric)

        if slow_query:
            logger.warning(
                f"Slow query detected: {query_type} on {table_name} "
                f"took {duration_ms:.2f}ms (threshold: "
                f"{self._slow_query_threshold * 1000:.0f}ms)"
            )
            if query_text:
                logger.debug(f"Query: {query_text[:200]}...")

    @asynccontextmanager
    async def measure_async(
        self,
        name: str,
        tags: dict[str, str] | None = None,
    ):
        """Async context manager for measuring operation duration.

        Usage:
            async with monitor.measure_async("operation_name"):
                await some_operation()
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.record_metric(
                f"{name}_duration_seconds",
                duration,
                tags=tags,
                metadata={"duration_ms": duration * 1000},
            )

    def measure_sync(
        self, name: str, tags: dict[str, str] | None = None
    ) -> Callable[[F], F]:
        """Decorator for measuring sync function duration.

        Usage:
            @monitor.measure_sync("function_name")
            def my_function():
                pass
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    self.record_metric(
                        f"{name}_duration_seconds",
                        duration,
                        tags=tags,
                        metadata={"duration_ms": duration * 1000},
                    )

            return wrapper  # type: ignore

        return decorator

    def measure_async_func(
        self, name: str, tags: dict[str, str] | None = None
    ) -> Callable[[AF], AF]:
        """Decorator for measuring async function duration.

        Usage:
            @monitor.measure_async_func("function_name")
            async def my_async_function():
                pass
        """

        def decorator(func: AF) -> AF:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                async with self.measure_async(name, tags):
                    return await func(*args, **kwargs)

            return wrapper  # type: ignore

        return decorator

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary statistics."""
        if not self._metrics and not self._query_metrics:
            return {"message": "No metrics collected"}

        summary: dict[str, Any] = {
            "total_metrics": len(self._metrics),
            "total_queries": len(self._query_metrics),
        }

        # Aggregate metrics by name
        if self._metrics:
            metric_stats = {}
            for metric in self._metrics:
                if metric.name not in metric_stats:
                    metric_stats[metric.name] = {
                        "count": 0,
                        "sum": 0,
                        "min": float("inf"),
                        "max": float("-inf"),
                        "values": [],
                    }

                stats = metric_stats[metric.name]
                stats["count"] += 1
                stats["sum"] += metric.value
                stats["min"] = min(stats["min"], metric.value)
                stats["max"] = max(stats["max"], metric.value)
                stats["values"].append(metric.value)

            # Calculate averages and percentiles
            for _name, stats in metric_stats.items():
                stats["average"] = stats["sum"] / stats["count"]
                values = sorted(stats["values"])
                stats["p50"] = values[len(values) // 2]
                stats["p95"] = (
                    values[int(len(values) * 0.95)]
                    if len(values) > 20
                    else stats["max"]
                )
                del stats["values"]  # Remove raw values from summary

            summary["metrics"] = metric_stats

        # Query statistics
        if self._query_metrics:
            slow_queries = [q for q in self._query_metrics if q.slow_query]
            query_by_type = {}

            for query in self._query_metrics:
                if query.query_type not in query_by_type:
                    query_by_type[query.query_type] = {
                        "count": 0,
                        "total_duration_ms": 0,
                        "slow_count": 0,
                    }

                stats = query_by_type[query.query_type]
                stats["count"] += 1
                stats["total_duration_ms"] += query.duration_ms
                if query.slow_query:
                    stats["slow_count"] += 1

            # Calculate averages
            for _query_type, stats in query_by_type.items():
                stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["count"]

            summary["queries"] = {
                "by_type": query_by_type,
                "slow_queries_count": len(slow_queries),
                "slow_query_threshold_ms": self._slow_query_threshold * 1000,
            }

        return summary

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._metrics.clear()
        self._query_metrics.clear()
        self._active_timers.clear()


# Global monitor instance
_global_monitor: PerformanceMonitor | None = None


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def reset_monitor() -> None:
    """Reset the global performance monitor."""
    monitor = get_monitor()
    monitor.reset()
