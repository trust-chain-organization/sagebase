"""OpenTelemetryメトリクスの設定と共通ユーティリティ."""

import os

from typing import Any

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import Counter, Histogram, Meter, UpDownCounter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import start_http_server

from src.common.logging import get_logger

logger = get_logger(__name__)

# グローバルなメーターインスタンス
_meter: Meter | None = None
_meter_provider: MeterProvider | None = None

# メトリクスインスタンスのキャッシュ
_metrics_cache: dict[str, Any] = {}


def setup_metrics(
    service_name: str = "sagebase",
    service_version: str = "1.0.0",
    prometheus_port: int = 9090,
    enable_prometheus: bool = True,
) -> None:
    """OpenTelemetryメトリクスの初期設定.

    Args:
        service_name: サービス名
        service_version: サービスバージョン
        prometheus_port: Prometheusメトリクスのポート番号
        enable_prometheus: Prometheusエクスポーターを有効にするか
    """
    global _meter, _meter_provider

    # リソース情報の設定
    resource = Resource(
        attributes={
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Prometheusエクスポーターの設定
    if enable_prometheus:
        # PrometheusMetricReaderの作成
        prometheus_reader = PrometheusMetricReader()

        # HTTPサーバーの起動
        start_http_server(port=prometheus_port, addr="0.0.0.0")
        logger.info(
            "Prometheus metrics server started",
            port=prometheus_port,
            endpoint=f"http://0.0.0.0:{prometheus_port}/metrics",
        )

        # MeterProviderの設定
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader],
        )
    else:
        # Prometheusなしの設定
        _meter_provider = MeterProvider(resource=resource)

    # グローバルMeterProviderの設定
    metrics.set_meter_provider(_meter_provider)

    # メーターの取得
    _meter = metrics.get_meter(
        name=__name__,
        version=service_version,
    )

    logger.info(
        "Metrics setup completed",
        service_name=service_name,
        service_version=service_version,
        prometheus_enabled=enable_prometheus,
    )


def get_meter() -> Meter:
    """メーターインスタンスを取得.

    Returns:
        Meter: OpenTelemetryメーター

    Raises:
        RuntimeError: メトリクスが初期化されていない場合
    """
    if _meter is None:
        raise RuntimeError("Metrics not initialized. Call setup_metrics() first.")
    return _meter


def create_counter(
    name: str,
    description: str = "",
    unit: str = "1",
) -> Counter:
    """カウンターメトリクスを作成.

    Args:
        name: メトリクス名
        description: メトリクスの説明
        unit: 単位

    Returns:
        Counter: カウンターインスタンス
    """
    if name in _metrics_cache:
        return _metrics_cache[name]

    meter = get_meter()
    counter = meter.create_counter(
        name=name,
        description=description,
        unit=unit,
    )
    _metrics_cache[name] = counter
    return counter


def create_histogram(
    name: str,
    description: str = "",
    unit: str = "ms",
) -> Histogram:
    """ヒストグラムメトリクスを作成.

    Args:
        name: メトリクス名
        description: メトリクスの説明
        unit: 単位

    Returns:
        Histogram: ヒストグラムインスタンス
    """
    if name in _metrics_cache:
        return _metrics_cache[name]

    meter = get_meter()
    histogram = meter.create_histogram(
        name=name,
        description=description,
        unit=unit,
    )
    _metrics_cache[name] = histogram
    return histogram


def create_up_down_counter(
    name: str,
    description: str = "",
    unit: str = "1",
) -> UpDownCounter:
    """アップダウンカウンターメトリクスを作成.

    Args:
        name: メトリクス名
        description: メトリクスの説明
        unit: 単位

    Returns:
        UpDownCounter: アップダウンカウンターインスタンス
    """
    if name in _metrics_cache:
        return _metrics_cache[name]

    meter = get_meter()
    up_down_counter = meter.create_up_down_counter(
        name=name,
        description=description,
        unit=unit,
    )
    _metrics_cache[name] = up_down_counter
    return up_down_counter


# 共通メトリクスの定義
class CommonMetrics:
    """共通で使用されるメトリクス."""

    # HTTPリクエスト関連
    @staticmethod
    def http_requests_total():
        return create_counter(
            "http_requests_total",
            "Total number of HTTP requests",
            "1",
        )

    @staticmethod
    def http_request_duration():
        return create_histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            "s",
        )

    @staticmethod
    def http_requests_in_progress():
        return create_up_down_counter(
            "http_requests_in_progress",
            "Number of HTTP requests in progress",
            "1",
        )

    # データベース関連
    @staticmethod
    def db_operations_total():
        return create_counter(
            "db_operations_total",
            "Total number of database operations",
            "1",
        )

    @staticmethod
    def db_operation_duration():
        return create_histogram(
            "db_operation_duration_milliseconds",
            "Database operation latency",
            "ms",
        )

    @staticmethod
    def db_connections_active():
        return create_up_down_counter(
            "db_connections_active",
            "Number of active database connections",
            "1",
        )

    # 処理関連
    @staticmethod
    def minutes_processed_total():
        return create_counter(
            "minutes_processed_total",
            "Total number of minutes processed",
            "1",
        )

    @staticmethod
    def minutes_processing_duration():
        return create_histogram(
            "minutes_processing_duration_seconds",
            "Minutes processing duration",
            "s",
        )

    @staticmethod
    def minutes_processing_errors():
        return create_counter(
            "minutes_processing_errors_total",
            "Total number of minutes processing errors",
            "1",
        )

    # LLM API関連
    @staticmethod
    def llm_api_calls_total():
        return create_counter(
            "llm_api_calls_total",
            "Total number of LLM API calls",
            "1",
        )

    @staticmethod
    def llm_api_duration():
        return create_histogram(
            "llm_api_duration_milliseconds",
            "LLM API call duration",
            "ms",
        )

    @staticmethod
    def llm_tokens_used():
        return create_counter(
            "llm_tokens_used_total",
            "Total number of tokens used",
            "1",
        )


def record_error(error_type: str, operation: str) -> None:
    """エラーを記録する共通関数.

    Args:
        error_type: エラーの種類
        operation: 操作名
    """
    error_counter = create_counter(
        "errors_total",
        "Total number of errors",
        "1",
    )
    error_counter.add(
        1,
        attributes={
            "error_type": error_type,
            "operation": operation,
        },
    )
