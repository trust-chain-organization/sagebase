#!/usr/bin/env python
"""OpenTelemetryメトリクスの簡易動作確認スクリプト."""

import sys
import time

from pathlib import Path


# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.logging import get_logger, setup_logging  # noqa: E402
from src.common.metrics import (  # noqa: E402
    CommonMetrics,
    create_counter,
    setup_metrics,
)


# ロギングとメトリクスの設定
setup_logging()
setup_metrics(
    service_name="polibase-verify",
    service_version="0.1.0",
    prometheus_port=9092,
    enable_prometheus=True,
)

logger = get_logger(__name__)


def main():
    """メイン実行関数."""
    print("🚀 OpenTelemetryメトリクス動作確認を開始します...")
    print("=" * 60)

    # 基本的なカウンターのテスト
    print("\n✅ カウンターメトリクスのテスト")
    counter = create_counter("test_counter", "Test counter", "1")
    for _ in range(5):
        counter.add(1, attributes={"test": "true"})
    print("   カウンターに5回カウントしました")

    # 共通メトリクスのテスト
    print("\n✅ 共通メトリクスのテスト")
    http_requests = CommonMetrics.http_requests_total()
    http_requests.add(
        1, attributes={"method": "GET", "endpoint": "/test", "status": "200"}
    )
    print("   HTTPリクエストメトリクスを記録しました")

    db_ops = CommonMetrics.db_operations_total()
    db_ops.add(1, attributes={"operation": "select", "table": "test"})
    print("   データベース操作メトリクスを記録しました")

    # Prometheusエンドポイントの確認
    print("\n📊 Prometheusメトリクス:")
    print("   http://localhost:9092/metrics で確認できます")
    print("\n✅ 動作確認完了！")
    print("   Ctrl+C で終了してください")

    # サーバーを維持
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n終了します...")


if __name__ == "__main__":
    main()
