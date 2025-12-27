"""Prometheusメトリクスエンドポイント用のFastAPIアプリケーション."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.common.instrumentation import MetricsContext, measure_time
from src.common.logging import get_logger
from src.common.metrics import CommonMetrics, setup_metrics


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """アプリケーションのライフサイクル管理."""
    # 起動時の処理
    logger.info("Starting metrics server")

    # メトリクスの初期化（Prometheusサーバーは別ポートで起動）
    setup_metrics(
        service_name="sagebase",
        service_version="1.0.0",
        prometheus_port=9090,
        enable_prometheus=True,
    )

    yield

    # 終了時の処理
    logger.info("Shutting down metrics server")


# FastAPIアプリケーションの作成
app = FastAPI(
    title="Polibase Metrics API",
    description="Prometheus metrics endpoint for Polibase",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Any]
) -> Response:
    """HTTPリクエストのメトリクスを記録するミドルウェア."""
    # リクエストカウンターとアクティブリクエスト数の更新
    http_requests = CommonMetrics.http_requests_total()
    requests_in_progress = CommonMetrics.http_requests_in_progress()

    # ラベルの設定
    labels = {
        "method": request.method,
        "endpoint": request.url.path,
    }

    # メトリクスの記録
    http_requests.add(1, attributes=labels)
    requests_in_progress.add(1, attributes=labels)

    try:
        # リクエスト処理時間の計測
        with MetricsContext(
            operation="http_request",
            labels=labels,
            record_duration=True,
            record_errors=True,
        ):
            response = await call_next(request)

            # ステータスコードをラベルに追加
            labels["status"] = str(response.status_code)

            return response
    finally:
        # アクティブリクエスト数を減らす
        requests_in_progress.add(-1, attributes=labels)


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント."""
    return {"status": "healthy", "service": "sagebase-metrics"}


@app.get("/metrics", response_class=PlainTextResponse)
@measure_time(metric_name="metrics_endpoint", log_slow_operations=0.1)
async def metrics():
    """Prometheusメトリクスエンドポイント.

    注意: このエンドポイントは別のポート（9090）で
    PrometheusMetricReaderによって自動的に提供されるため、
    通常はこのエンドポイントは使用されません。
    これは追加のメトリクス確認用です。
    """
    try:
        # Prometheusメトリクスの生成
        metrics_data = generate_latest()

        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
        )
    except Exception as e:
        logger.error(
            "Failed to generate metrics",
            error=str(e),
            exc_info=True,
        )
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain",
            status_code=500,
        )


@app.get("/")
async def root() -> dict[str, Any]:
    """ルートエンドポイント."""
    return {
        "service": "sagebase-metrics",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "prometheus": "http://localhost:9090/metrics",
        },
        "description": "Metrics service for Sagebase application",
    }


# カスタムメトリクスのデモエンドポイント
@app.post("/demo/process-minutes")
@measure_time(
    metric_name="demo_process_minutes",
    labels={"demo": "true"},
    log_slow_operations=0.5,
)
async def demo_process_minutes(minutes_count: int = 1) -> dict[str, Any]:
    """議事録処理のデモ（メトリクス記録のテスト用）."""
    import asyncio
    import random

    # 処理時間のシミュレーション
    processing_time = random.uniform(0.1, 0.5)
    await asyncio.sleep(processing_time)

    # メトリクスの記録
    minutes_counter = CommonMetrics.minutes_processed_total()
    minutes_counter.add(minutes_count, attributes={"demo": "true"})

    # ランダムにエラーを発生させる（10%の確率）
    if random.random() < 0.1:
        error_counter = CommonMetrics.minutes_processing_errors()
        error_counter.add(1, attributes={"demo": "true", "error_type": "demo_error"})
        raise Exception("Demo error for testing")

    return {
        "processed": minutes_count,
        "processing_time": processing_time,
        "status": "success",
    }


if __name__ == "__main__":
    import uvicorn

    # メトリクスAPIサーバーの起動
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
