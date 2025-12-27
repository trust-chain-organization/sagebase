#!/usr/bin/env python
"""OpenTelemetryメトリクスの動作確認スクリプト.

このスクリプトは、実装したメトリクス機能が正しく動作することを確認します。
"""

import asyncio
import random
import sys
import time

from pathlib import Path


# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.instrumentation import (  # noqa: E402
    MetricsContext,
    count_calls,
    measure_time,
)
from src.common.logging import get_logger, setup_logging  # noqa: E402
from src.common.metrics import (  # noqa: E402
    CommonMetrics,
    create_counter,
    setup_metrics,
)

# from src.database.instrumented_repository import InstrumentedRepository  # noqa: E402
# Removed after migration
from src.services.instrumented_llm_service import InstrumentedLLMService  # noqa: E402


# ロギングとメトリクスの設定
setup_logging()
setup_metrics(
    service_name="polibase-verify",
    service_version="0.1.0",
    prometheus_port=9093,
    enable_prometheus=True,
)

logger = get_logger(__name__)


# デモ用の関数
@measure_time(
    metric_name="demo_function",
    labels={"function": "calculate_fibonacci"},
    log_slow_operations=0.1,
)
def calculate_fibonacci(n: int) -> int:
    """フィボナッチ数を計算（デモ用）."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


@count_calls(metric_name="demo_calls")
def process_item(item_id: int) -> str:
    """アイテムを処理（デモ用）."""
    time.sleep(random.uniform(0.01, 0.05))
    return f"Processed item {item_id}"


@measure_time(metric_name="async_demo")
async def async_process(delay: float) -> str:
    """非同期処理のデモ."""
    await asyncio.sleep(delay)
    return f"Completed after {delay}s"


def test_basic_metrics():
    """基本的なメトリクスのテスト."""
    print("\n=== 基本的なメトリクスのテスト ===")

    # カウンターの作成と使用
    request_counter = create_counter(
        "verify_requests_total",
        "Total verification requests",
        "1",
    )

    for i in range(5):
        request_counter.add(1, attributes={"endpoint": "/verify", "method": "GET"})
        logger.info(f"Request {i + 1} counted")

    print("✅ カウンターメトリクスが作成されました")


def test_instrumentation_decorators():
    """計測デコレーターのテスト."""
    print("\n=== 計測デコレーターのテスト ===")

    # 実行時間計測
    logger.info("フィボナッチ数を計算中...")
    result = calculate_fibonacci(10)
    print(f"✅ Fibonacci(10) = {result} (実行時間が計測されました)")

    # 呼び出し回数カウント
    logger.info("アイテムを処理中...")
    for i in range(3):
        result = process_item(i)
        logger.info(result)
    print("✅ 呼び出し回数がカウントされました")


def test_context_manager():
    """コンテキストマネージャーのテスト."""
    print("\n=== コンテキストマネージャーのテスト ===")

    with MetricsContext(
        operation="batch_processing",
        labels={"batch_size": "100"},
        record_duration=True,
        record_errors=True,
    ) as ctx:
        logger.info("バッチ処理開始")
        time.sleep(0.1)

        # 処理中の追加情報
        ctx.add_metric("items_processed", 100)
        ctx.add_metric("items_failed", 2)

        logger.info("バッチ処理完了")

    print("✅ メトリクスコンテキストが正常に動作しました")


async def test_async_instrumentation():
    """非同期関数の計測テスト."""
    print("\n=== 非同期関数の計測テスト ===")

    tasks = [
        async_process(0.1),
        async_process(0.2),
        async_process(0.15),
    ]

    results = await asyncio.gather(*tasks)
    for result in results:
        logger.info(result)

    print("✅ 非同期関数の計測が完了しました")


def test_common_metrics():
    """共通メトリクスのテスト."""
    print("\n=== 共通メトリクスのテスト ===")

    # HTTPメトリクス
    http_requests = CommonMetrics.http_requests_total()
    http_duration = CommonMetrics.http_request_duration()

    for endpoint in ["/api/minutes", "/api/speakers", "/api/politicians"]:
        http_requests.add(
            1,
            attributes={
                "method": "GET",
                "endpoint": endpoint,
                "status": "200",
            },
        )
        http_duration.record(
            random.uniform(10, 100),
            attributes={
                "method": "GET",
                "endpoint": endpoint,
            },
        )

    # データベースメトリクス
    db_ops = CommonMetrics.db_operations_total()
    db_duration = CommonMetrics.db_operation_duration()

    for op in ["select", "insert", "update"]:
        db_ops.add(
            1,
            attributes={
                "operation": op,
                "table": "conversations",
            },
        )
        db_duration.record(
            random.uniform(1, 10),
            attributes={
                "operation": op,
                "table": "conversations",
            },
        )

    print("✅ 共通メトリクスが正常に動作しました")


def test_llm_instrumentation():
    """LLMサービスの計測テスト."""
    print("\n=== LLMサービスの計測テスト ===")

    try:
        # モックLLMサービスを作成
        from unittest.mock import MagicMock

        from langchain.schema import HumanMessage

        mock_llm = MagicMock()
        mock_llm.model_name = "gemini-test"
        mock_llm.temperature = 0.1
        mock_llm.invoke.return_value = "This is a test response"

        # 計測ラッパーでラップ
        instrumented_llm = InstrumentedLLMService(mock_llm)

        # API呼び出しのシミュレーション
        messages = [HumanMessage(content="Test prompt")]
        result = instrumented_llm.invoke(messages)

        logger.info(f"LLM response: {result[:50]}...")
        print("✅ LLMサービスの計測が正常に動作しました")

    except Exception as e:
        logger.warning(f"LLMテストをスキップ: {e}")
        print("⚠️  LLMサービスのテストはスキップされました（モック環境）")


def test_database_instrumentation():
    """データベースリポジトリの計測テスト."""
    print("\n=== データベースリポジトリの計測テスト ===")
    # InstrumentedRepository was removed during Clean Architecture migration
    print("⚠️  InstrumentedRepositoryは移行により削除されました")


def show_metrics_summary():
    """メトリクスのサマリーを表示."""
    print("\n=== メトリクスサマリー ===")
    print("📊 収集されたメトリクス:")
    print("  - verify_requests_total: リクエスト数")
    print("  - demo_function_duration: 関数実行時間")
    print("  - demo_calls_total: 関数呼び出し回数")
    print("  - http_requests_total: HTTPリクエスト数")
    print("  - db_operations_total: DB操作数")
    print("  - llm_api_calls_total: LLM API呼び出し数")
    print("")
    print("🔗 Prometheusメトリクスエンドポイント:")
    print("   http://localhost:9093/metrics")
    print("")
    print("💡 ヒント: curlでメトリクスを確認できます:")
    print(
        "   curl http://localhost:9093/metrics | grep -E 'verify_|demo_|http_|db_|llm_'"
    )


async def main():
    """メイン実行関数."""
    print("🚀 OpenTelemetryメトリクス動作確認を開始します...")
    print("=" * 60)

    # 各種テストを実行
    test_basic_metrics()
    test_instrumentation_decorators()
    test_context_manager()
    await test_async_instrumentation()
    test_common_metrics()
    test_llm_instrumentation()
    test_database_instrumentation()

    # サマリー表示
    show_metrics_summary()

    print("\n✅ すべてのテストが完了しました！")
    print("⏱️  Prometheusサーバーは引き続き実行中です...")
    print("   Ctrl+C で終了してください")

    # Prometheusサーバーを維持
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 終了します...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n終了しました")
