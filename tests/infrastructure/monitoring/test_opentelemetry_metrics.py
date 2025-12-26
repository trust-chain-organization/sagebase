"""OpenTelemetryメトリクスの単体テスト."""

import time

from unittest.mock import patch

import pytest

from opentelemetry.metrics import get_meter_provider

from src.common.instrumentation import MetricsContext, count_calls, measure_time
from src.common.metrics import (
    CommonMetrics,
    create_counter,
    create_histogram,
    create_up_down_counter,
    setup_metrics,
)


class TestMetricsSetup:
    """メトリクス設定のテスト."""

    def test_setup_metrics_with_prometheus(self):
        """Prometheusエクスポーター付きでメトリクスを設定."""
        with patch("src.common.metrics.start_http_server") as mock_server:
            setup_metrics(
                service_name="test-service",
                service_version="0.1.0",
                prometheus_port=9091,
                enable_prometheus=True,
            )

            # HTTPサーバーが起動されたことを確認
            mock_server.assert_called_once_with(port=9091, addr="0.0.0.0")

            # MeterProviderが設定されたことを確認
            meter_provider = get_meter_provider()
            assert meter_provider is not None

    def test_setup_metrics_without_prometheus(self):
        """Prometheusエクスポーターなしでメトリクスを設定."""
        with patch("src.common.metrics.start_http_server") as mock_server:
            setup_metrics(
                service_name="test-service",
                service_version="0.1.0",
                enable_prometheus=False,
            )

            # HTTPサーバーが起動されていないことを確認
            mock_server.assert_not_called()


class TestMetricCreation:
    """メトリクス作成のテスト."""

    def setup_method(self):
        """各テストメソッドの前処理."""
        setup_metrics(enable_prometheus=False)

    def test_create_counter(self):
        """カウンターメトリクスの作成."""
        counter = create_counter(
            "test_counter",
            "Test counter metric",
            "1",
        )

        # カウンターが作成されたことを確認
        assert counter is not None

        # 同じ名前で再度作成してもキャッシュから返される
        counter2 = create_counter("test_counter")
        assert counter is counter2

    def test_create_histogram(self):
        """ヒストグラムメトリクスの作成."""
        histogram = create_histogram(
            "test_histogram",
            "Test histogram metric",
            "ms",
        )

        # ヒストグラムが作成されたことを確認
        assert histogram is not None

    def test_create_up_down_counter(self):
        """アップダウンカウンターメトリクスの作成."""
        up_down_counter = create_up_down_counter(
            "test_up_down_counter",
            "Test up-down counter metric",
            "1",
        )

        # アップダウンカウンターが作成されたことを確認
        assert up_down_counter is not None


class TestInstrumentation:
    """計測機能のテスト."""

    def setup_method(self):
        """各テストメソッドの前処理."""
        setup_metrics(enable_prometheus=False)

    def test_measure_time_decorator(self):
        """実行時間計測デコレーターのテスト."""
        call_count = 0

        @measure_time(
            metric_name="test_function",
            labels={"test": "true"},
            log_slow_operations=0.1,
        )
        def test_function(delay: float = 0.01):
            nonlocal call_count
            call_count += 1
            time.sleep(delay)
            return "success"

        # 関数を実行
        result = test_function()
        assert result == "success"
        assert call_count == 1

        # メトリクスが記録されたことを確認
        # （実際の値の確認は統合テストで行う）

    def test_measure_time_decorator_with_error(self):
        """エラー時の計測デコレーターのテスト."""

        @measure_time(
            metric_name="test_error_function",
            record_errors=True,
        )
        def test_error_function():
            raise ValueError("Test error")

        # エラーが発生することを確認
        with pytest.raises(ValueError):
            test_error_function()

    def test_count_calls_decorator(self):
        """呼び出し回数カウントデコレーターのテスト."""
        call_count = 0

        @count_calls(metric_name="test_counted_function")
        def test_counted_function():
            nonlocal call_count
            call_count += 1
            return call_count

        # 複数回呼び出し
        assert test_counted_function() == 1
        assert test_counted_function() == 2
        assert test_counted_function() == 3

    def test_metrics_context_manager(self):
        """メトリクスコンテキストマネージャーのテスト."""
        with MetricsContext(
            operation="test_operation",
            labels={"env": "test"},
            record_duration=True,
            record_errors=True,
        ) as ctx:
            # コンテキスト内で処理
            time.sleep(0.01)
            assert ctx.operation == "test_operation"
            assert ctx.labels == {"env": "test"}

    def test_metrics_context_manager_with_error(self):
        """エラー時のコンテキストマネージャーのテスト."""
        with pytest.raises(RuntimeError):
            with MetricsContext(
                operation="test_error_operation",
                record_errors=True,
            ):
                raise RuntimeError("Test error in context")


class TestAsyncInstrumentation:
    """非同期関数の計測テスト."""

    def setup_method(self):
        """各テストメソッドの前処理."""
        setup_metrics(enable_prometheus=False)

    @pytest.mark.asyncio
    async def test_async_measure_time_decorator(self):
        """非同期関数の実行時間計測デコレーターのテスト."""

        @measure_time(metric_name="test_async_function")
        async def test_async_function():
            import asyncio

            await asyncio.sleep(0.01)
            return "async success"

        result = await test_async_function()
        assert result == "async success"

    @pytest.mark.asyncio
    async def test_async_count_calls_decorator(self):
        """非同期関数の呼び出し回数カウントデコレーターのテスト."""

        @count_calls(metric_name="test_async_counted")
        async def test_async_counted():
            import asyncio

            await asyncio.sleep(0.01)
            return "counted"

        result = await test_async_counted()
        assert result == "counted"


class TestCommonMetrics:
    """共通メトリクスのテスト."""

    def setup_method(self):
        """各テストメソッドの前処理."""
        setup_metrics(enable_prometheus=False)

    def test_http_metrics(self):
        """HTTPメトリクスの作成."""
        requests_total = CommonMetrics.http_requests_total()
        request_duration = CommonMetrics.http_request_duration()
        requests_in_progress = CommonMetrics.http_requests_in_progress()

        assert requests_total is not None
        assert request_duration is not None
        assert requests_in_progress is not None

    def test_db_metrics(self):
        """データベースメトリクスの作成."""
        db_operations = CommonMetrics.db_operations_total()
        db_duration = CommonMetrics.db_operation_duration()
        db_connections = CommonMetrics.db_connections_active()

        assert db_operations is not None
        assert db_duration is not None
        assert db_connections is not None

    def test_minutes_processing_metrics(self):
        """議事録処理メトリクスの作成."""
        minutes_processed = CommonMetrics.minutes_processed_total()
        processing_duration = CommonMetrics.minutes_processing_duration()
        processing_errors = CommonMetrics.minutes_processing_errors()

        assert minutes_processed is not None
        assert processing_duration is not None
        assert processing_errors is not None

    def test_llm_metrics(self):
        """LLMメトリクスの作成."""
        api_calls = CommonMetrics.llm_api_calls_total()
        api_duration = CommonMetrics.llm_api_duration()
        tokens_used = CommonMetrics.llm_tokens_used()

        assert api_calls is not None
        assert api_duration is not None
        assert tokens_used is not None
