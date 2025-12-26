"""Tests for performance optimization features."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.pagination import PaginatedResult, PaginationParams
from src.infrastructure.external.cached_llm_service import CachedLLMService, LLMCache
from src.infrastructure.external.concurrent_llm_service import (
    ConcurrentLLMService,
    RateLimiter,
)
from src.infrastructure.monitoring.performance_metrics import PerformanceMonitor
from src.infrastructure.monitoring.slow_query_detector import SlowQueryDetector


class TestPagination:
    """Tests for pagination utilities."""

    def test_pagination_params_offset_calculation(self):
        """Test offset calculation for pagination."""
        params = PaginationParams(page=1, per_page=10)
        assert params.offset == 0
        assert params.limit == 10

        params = PaginationParams(page=3, per_page=20)
        assert params.offset == 40
        assert params.limit == 20

    def test_pagination_params_validation(self):
        """Test pagination parameter validation."""
        # Valid params
        params = PaginationParams(page=1, per_page=50)
        params.validate()  # Should not raise

        # Invalid page
        params = PaginationParams(page=0, per_page=10)
        with pytest.raises(ValueError, match="Page must be >= 1"):
            params.validate()

        # Invalid per_page (too small)
        params = PaginationParams(page=1, per_page=0)
        with pytest.raises(ValueError, match="Per page must be >= 1"):
            params.validate()

        # Invalid per_page (too large)
        params = PaginationParams(page=1, per_page=101)
        with pytest.raises(ValueError, match="Per page must be <= 100"):
            params.validate()

    def test_paginated_result_properties(self):
        """Test paginated result properties."""
        # Empty result
        result = PaginatedResult(
            items=[],
            total_count=0,
            page=1,
            per_page=10,
        )
        assert result.total_pages == 0
        assert not result.has_next
        assert not result.has_previous
        assert result.next_page is None
        assert result.previous_page is None

        # Result with multiple pages
        result = PaginatedResult(
            items=["item1", "item2", "item3"],
            total_count=25,
            page=2,
            per_page=10,
        )
        assert result.total_pages == 3
        assert result.has_next
        assert result.has_previous
        assert result.next_page == 3
        assert result.previous_page == 1

        # Last page
        result = PaginatedResult(
            items=["item1", "item2"],
            total_count=12,
            page=2,
            per_page=10,
        )
        assert result.total_pages == 2
        assert not result.has_next
        assert result.has_previous
        assert result.next_page is None
        assert result.previous_page == 1


class TestLLMCache:
    """Tests for LLM caching."""

    def test_cache_key_generation(self):
        """Test cache key generation."""
        cache = LLMCache(ttl_minutes=60)

        # Same prompt should generate same key
        key1 = cache._generate_key("test prompt", {"context": "value"})
        key2 = cache._generate_key("test prompt", {"context": "value"})
        assert key1 == key2

        # Different prompts should generate different keys
        key3 = cache._generate_key("different prompt", {"context": "value"})
        assert key1 != key3

        # Different context should generate different keys
        key4 = cache._generate_key("test prompt", {"context": "different"})
        assert key1 != key4

    def test_cache_get_set(self):
        """Test cache get and set operations."""
        cache = LLMCache(ttl_minutes=60)

        # Cache miss
        assert cache.get("prompt1") is None

        # Cache set and hit
        cache.set("prompt1", None, {"result": "value1"})
        assert cache.get("prompt1") == {"result": "value1"}

        # Different prompt should miss
        assert cache.get("prompt2") is None

    def test_cache_expiration(self):
        """Test cache expiration."""
        cache = LLMCache(ttl_minutes=0)  # Immediate expiration

        cache.set("prompt", None, {"result": "value"})
        # Should be expired immediately
        import time

        time.sleep(0.01)
        assert cache.get("prompt") is None

    @pytest.mark.asyncio
    async def test_cached_llm_service(self):
        """Test cached LLM service."""
        # Mock base service
        base_service = MagicMock()
        base_service.match_speaker_to_politician = AsyncMock(
            return_value={"matched_id": 123, "confidence": 0.9}
        )

        # Create cached service
        cached_service = CachedLLMService(base_service)

        # First call should hit base service
        context = MagicMock()
        result1 = await cached_service.match_speaker_to_politician(context)
        assert result1 == {"matched_id": 123, "confidence": 0.9}
        base_service.match_speaker_to_politician.assert_called_once()

        # Second call with same context should use cache
        result2 = await cached_service.match_speaker_to_politician(context)
        assert result2 == result1
        # Base service should still have been called only once
        assert base_service.match_speaker_to_politician.call_count == 1


class TestConcurrentLLMService:
    """Tests for concurrent LLM service."""

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """Test rate limiter functionality."""
        limiter = RateLimiter(max_per_second=2, max_concurrent=2)

        # Should allow first two requests immediately
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.1  # Should be nearly instant

        # Third request should be delayed
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed >= 0.5  # Should wait for rate limit

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test concurrent processing with limits."""
        # Mock base service
        base_service = MagicMock()

        async def mock_match(*args, **kwargs):
            await asyncio.sleep(0.01)  # Simulate processing time
            return {"matched_id": 1}

        base_service.match_speaker_to_politician = mock_match

        # Create concurrent service
        concurrent_service = ConcurrentLLMService(
            base_service,
            max_concurrent=2,
            max_per_second=10,
        )

        # Process multiple items
        items = [1, 2, 3, 4, 5]

        async def process_item(item):
            return await concurrent_service.match_speaker_to_politician(MagicMock())

        results = await concurrent_service.process_with_concurrency_limit(
            items,
            process_item,
            max_concurrent=2,
        )

        assert len(results) == 5
        assert all(r == {"matched_id": 1} for r in results)


class TestPerformanceMonitor:
    """Tests for performance monitoring."""

    def test_timer_operations(self):
        """Test timer start and stop."""
        monitor = PerformanceMonitor()

        # Start timer
        monitor.start_timer("test_operation")

        # Simulate some work
        import time

        time.sleep(0.01)

        # Stop timer
        duration = monitor.stop_timer("test_operation")
        assert duration >= 0.01

        # Stopping non-existent timer returns 0
        duration = monitor.stop_timer("non_existent")
        assert duration == 0.0

    def test_metric_recording(self):
        """Test metric recording."""
        monitor = PerformanceMonitor()

        # Record some metrics
        monitor.record_metric("api_latency", 100.5, tags={"endpoint": "/users"})
        monitor.record_metric("api_latency", 150.2, tags={"endpoint": "/posts"})
        monitor.record_metric("cache_hit_rate", 0.85)

        # Get summary
        summary = monitor.get_summary()
        assert summary["total_metrics"] == 3
        assert "api_latency" in summary["metrics"]
        assert summary["metrics"]["api_latency"]["count"] == 2
        assert summary["metrics"]["api_latency"]["average"] == 125.35

    def test_query_metrics(self):
        """Test database query metrics."""
        monitor = PerformanceMonitor(slow_query_threshold_ms=100)

        # Record fast query
        monitor.record_query("SELECT", 50, 10, "users")

        # Record slow query
        monitor.record_query("SELECT", 150, 100, "posts", "SELECT * FROM posts")

        # Get summary
        summary = monitor.get_summary()
        assert summary["total_queries"] == 2
        assert summary["queries"]["slow_queries_count"] == 1
        assert summary["queries"]["by_type"]["SELECT"]["count"] == 2
        assert summary["queries"]["by_type"]["SELECT"]["slow_count"] == 1

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager for measuring."""
        monitor = PerformanceMonitor()

        async with monitor.measure_async("test_operation"):
            await asyncio.sleep(0.01)

        summary = monitor.get_summary()
        assert "test_operation_duration_seconds" in summary["metrics"]
        assert summary["metrics"]["test_operation_duration_seconds"]["count"] == 1


class TestSlowQueryDetector:
    """Tests for slow query detection."""

    def test_slow_query_detection(self):
        """Test slow query detection."""
        detector = SlowQueryDetector(threshold_ms=100)

        # Track fast query
        query_id = "query1"
        detector.start_query(query_id)
        import time

        time.sleep(0.01)  # 10ms
        duration = detector.end_query(query_id, "SELECT * FROM users")
        assert duration is None  # Not slow

        # Track slow query
        query_id = "query2"
        detector.start_query(query_id)
        time.sleep(0.11)  # 110ms
        duration = detector.end_query(query_id, "SELECT * FROM posts")
        assert duration is not None
        assert duration >= 100

        # Check history
        history = detector.get_history()
        assert len(history) == 1
        assert "posts" in history[0].query

    def test_query_statistics(self):
        """Test slow query statistics."""
        detector = SlowQueryDetector(threshold_ms=50)

        # Add some slow queries
        for i in range(3):
            query_id = f"query{i}"
            detector.start_query(query_id)
            import time

            time.sleep(0.06 + i * 0.01)  # 60ms, 70ms, 80ms
            detector.end_query(query_id, f"SELECT * FROM table{i}")

        # Get statistics
        stats = detector.get_statistics()
        assert stats["total_slow_queries"] == 3
        assert (
            60 <= stats["avg_duration_ms"] <= 90
        )  # More tolerant range for timing variations
        assert stats["min_duration_ms"] >= 55  # Allow some variance
        assert stats["max_duration_ms"] >= 75

    def test_context_manager(self):
        """Test context manager for tracking."""
        detector = SlowQueryDetector(threshold_ms=50)

        with detector.track_query("SELECT * FROM users"):
            import time

            time.sleep(0.06)  # 60ms

        # Should have recorded slow query
        history = detector.get_history()
        assert len(history) == 1
        assert history[0].duration_ms >= 60
