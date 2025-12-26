"""Slow query detection and logging for database operations."""

import logging
import time

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SlowQueryRecord:
    """Record of a slow database query."""

    query: str
    duration_ms: float
    timestamp: datetime
    parameters: dict[str, Any] | None = None
    stack_trace: str | None = None


class SlowQueryDetector:
    """Detector for slow database queries."""

    def __init__(
        self,
        threshold_ms: float = 1000,
        log_queries: bool = True,
        store_history: bool = True,
        max_history: int = 100,
    ):
        """Initialize slow query detector.

        Args:
            threshold_ms: Threshold for slow query in milliseconds
            log_queries: Whether to log slow queries
            store_history: Whether to store query history
            max_history: Maximum number of queries to store
        """
        self.threshold_ms = threshold_ms
        self.log_queries = log_queries
        self.store_history = store_history
        self.max_history = max_history
        self._history: list[SlowQueryRecord] = []
        self._active_queries: dict[str, float] = {}

    def start_query(self, query_id: str) -> None:
        """Start tracking a query."""
        self._active_queries[query_id] = time.perf_counter()

    def end_query(
        self,
        query_id: str,
        query_text: str,
        parameters: dict[str, Any] | None = None,
    ) -> float | None:
        """End tracking a query and check if it's slow.

        Returns:
            Duration in milliseconds if slow, None otherwise
        """
        if query_id not in self._active_queries:
            return None

        start_time = self._active_queries.pop(query_id)
        duration = (time.perf_counter() - start_time) * 1000  # Convert to ms

        if duration >= self.threshold_ms:
            self.handle_slow_query(query_text, duration, parameters)
            return duration

        return None

    def handle_slow_query(
        self,
        query: str,
        duration_ms: float,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Handle a detected slow query."""
        # Create record
        record = SlowQueryRecord(
            query=query[:1000],  # Truncate very long queries
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            parameters=parameters,
        )

        # Log if enabled
        if self.log_queries:
            logger.warning(
                f"Slow query detected ({duration_ms:.2f}ms > {self.threshold_ms}ms):\n"
                f"Query: {query[:200]}{'...' if len(query) > 200 else ''}"
            )
            if parameters:
                logger.debug(f"Parameters: {parameters}")

        # Store in history if enabled
        if self.store_history:
            self._history.append(record)
            # Maintain max history size
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history :]

    def get_history(self, limit: int | None = None) -> list[SlowQueryRecord]:
        """Get slow query history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of slow query records
        """
        if limit:
            return self._history[-limit:]
        return self._history.copy()

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about slow queries."""
        if not self._history:
            return {"total_slow_queries": 0}

        durations = [r.duration_ms for r in self._history]

        return {
            "total_slow_queries": len(self._history),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "threshold_ms": self.threshold_ms,
            "latest_query_time": self._history[-1].timestamp.isoformat()
            if self._history
            else None,
        }

    def clear_history(self) -> None:
        """Clear slow query history."""
        self._history.clear()

    @contextmanager
    def track_query(self, query_text: str, parameters: dict[str, Any] | None = None):
        """Context manager for tracking query execution.

        Usage:
            with detector.track_query("SELECT * FROM users"):
                # Execute query
                pass
        """
        query_id = str(id(query_text))
        self.start_query(query_id)
        try:
            yield
        finally:
            self.end_query(query_id, query_text, parameters)


def install_sqlalchemy_listener(
    engine: Engine,
    detector: SlowQueryDetector | None = None,
    threshold_ms: float = 1000,
) -> SlowQueryDetector:
    """Install SQLAlchemy event listeners for slow query detection.

    Args:
        engine: SQLAlchemy engine
        detector: Existing detector or None to create new
        threshold_ms: Threshold for slow queries in milliseconds

    Returns:
        The slow query detector instance
    """
    if detector is None:
        detector = SlowQueryDetector(threshold_ms=threshold_ms)

    query_start_times: dict[Any, float] = {}

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Track query start time."""
        query_start_times[cursor] = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Check query duration and detect slow queries."""
        if cursor in query_start_times:
            start_time = query_start_times.pop(cursor)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if duration_ms >= detector.threshold_ms:
                # Convert parameters to dict if needed
                param_dict = None
                if parameters:
                    if isinstance(parameters, dict):
                        param_dict = parameters
                    elif isinstance(parameters, list | tuple):
                        param_dict = {f"param_{i}": v for i, v in enumerate(parameters)}

                detector.handle_slow_query(statement, duration_ms, param_dict)

    logger.info(f"Slow query detector installed with threshold {threshold_ms}ms")
    return detector


class QueryProfiler:
    """Query profiler for detailed analysis."""

    def __init__(self, session: Session):
        """Initialize query profiler.

        Args:
            session: SQLAlchemy session to profile
        """
        self.session = session
        self._profiles: list[dict[str, Any]] = []

    @contextmanager
    def profile(self, description: str = ""):
        """Profile a block of database operations.

        Usage:
            with profiler.profile("Loading user data"):
                users = session.query(User).all()
        """
        start_time = time.perf_counter()
        initial_query_count = self._get_query_count()

        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            query_count = self._get_query_count() - initial_query_count

            profile = {
                "description": description,
                "duration_ms": duration * 1000,
                "query_count": query_count,
                "queries_per_second": query_count / duration if duration > 0 else 0,
                "timestamp": datetime.now(),
            }

            self._profiles.append(profile)

            # Log if many queries detected (potential N+1)
            if query_count > 10:
                logger.warning(
                    f"High query count detected in '{description}': "
                    f"{query_count} queries in {duration * 1000:.2f}ms"
                )

    def _get_query_count(self) -> int:
        """Get the current query count from session statistics."""
        # This is a simplified version - actual implementation would
        # need to track queries more carefully
        return 0  # Placeholder

    def get_profiles(self) -> list[dict[str, Any]]:
        """Get all collected profiles."""
        return self._profiles.copy()

    def get_summary(self) -> dict[str, Any]:
        """Get profiling summary."""
        if not self._profiles:
            return {"message": "No profiles collected"}

        total_duration = sum(p["duration_ms"] for p in self._profiles)
        total_queries = sum(p["query_count"] for p in self._profiles)

        return {
            "total_profiles": len(self._profiles),
            "total_duration_ms": total_duration,
            "total_queries": total_queries,
            "avg_queries_per_profile": total_queries / len(self._profiles)
            if self._profiles
            else 0,
            "profiles_with_high_query_count": len(
                [p for p in self._profiles if p["query_count"] > 10]
            ),
        }
