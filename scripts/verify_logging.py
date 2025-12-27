#!/usr/bin/env python3
"""構造化ログの動作確認スクリプト.

このスクリプトは、構造化ログが正しく動作することを確認するために、
様々なログ出力パターンをテストします。
"""

import sys
import time

from pathlib import Path


# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logging import (
    LogContext,
    add_context,
    clear_context,
    get_logger,
    setup_logging,
)


def test_json_logging():
    """JSON形式のログ出力をテスト."""
    print("\n=== JSON形式のログ出力テスト ===")
    setup_logging(log_level="DEBUG", json_format=True)
    logger = get_logger("verify_logging")

    logger.debug("デバッグメッセージ", debug_info="詳細情報")
    logger.info("情報メッセージ", user_id=123, action="login")
    logger.warning("警告メッセージ", threshold=80, current=85)
    logger.error("エラーメッセージ", error_code="E001", details="接続失敗")

    # 例外情報を含むログ
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.error("ゼロ除算エラーが発生しました", exc_info=True)


def test_console_logging():
    """コンソール形式のログ出力をテスト."""
    print("\n=== コンソール形式のログ出力テスト ===")
    setup_logging(log_level="INFO", json_format=False)
    logger = get_logger("verify_logging")

    logger.info("読みやすいコンソール形式", key1="value1", key2="value2")
    logger.warning("警告もカラフルに表示されます", level="high")


def test_context_management():
    """コンテキスト管理機能をテスト."""
    print("\n=== コンテキスト管理テスト ===")
    setup_logging(log_level="INFO", json_format=True)
    logger = get_logger("context_test")

    # グローバルコンテキストを設定
    add_context(request_id="req-123", environment="production")
    logger.info("グローバルコンテキスト付きログ")

    # with文でローカルコンテキストを追加
    with LogContext(operation="データ処理", step=1):
        logger.info("処理開始")
        time.sleep(0.1)  # 処理をシミュレート
        logger.info("処理完了", duration_ms=100)

    # コンテキストをクリア
    clear_context()
    logger.info("コンテキストなしのログ")


def test_module_integration():
    """実際のモジュールとの統合テスト."""
    print("\n=== モジュール統合テスト ===")
    setup_logging(log_level="INFO", json_format=True)

    # process_minutesモジュールのログ出力
    from src.process_minutes import logger as process_logger

    with LogContext(test_mode=True, test_id="integration-001"):
        process_logger.info(
            "議事録処理テスト", minutes_id=999, pdf_size_bytes=1024000, status="testing"
        )

    # web_scraperモジュールのログ出力
    from src.web_scraper.scraper_service import ScraperService

    print("\n--- ScraperServiceの初期化ログ ---")
    _ = ScraperService(enable_gcs=False)


def test_performance_logging():
    """パフォーマンス計測を含むログ出力をテスト."""
    print("\n=== パフォーマンスログテスト ===")
    setup_logging(log_level="INFO", json_format=True)
    logger = get_logger("performance")

    # 処理時間の計測例
    start_time = time.time()
    logger.info("重い処理を開始", process_type="data_analysis")

    # 処理をシミュレート
    time.sleep(0.5)

    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(
        "処理完了",
        process_type="data_analysis",
        elapsed_ms=elapsed_ms,
        records_processed=1000,
        throughput_per_sec=1000 / (elapsed_ms / 1000),
    )


def test_error_scenarios():
    """エラーシナリオのログ出力をテスト."""
    print("\n=== エラーシナリオテスト ===")
    setup_logging(log_level="INFO", json_format=True)
    logger = get_logger("error_test")

    # 様々なエラーレベル
    logger.warning("リトライ可能なエラー", retry_count=1, max_retries=3)
    logger.error("リトライ上限に達しました", retry_count=3, max_retries=3)
    logger.critical(
        "システムクリティカルエラー", component="database", action="shutdown"
    )


def main():
    """メイン実行関数."""
    print("構造化ログ動作確認スクリプト")
    print("=" * 50)

    # 各種テストを実行
    test_json_logging()
    print("\n" + "-" * 50)

    test_console_logging()
    print("\n" + "-" * 50)

    test_context_management()
    print("\n" + "-" * 50)

    test_module_integration()
    print("\n" + "-" * 50)

    test_performance_logging()
    print("\n" + "-" * 50)

    test_error_scenarios()

    print("\n" + "=" * 50)
    print("✅ すべてのログ出力テストが完了しました")
    print("\n使用方法:")
    print("  - JSON形式で見やすく表示: python scripts/verify_logging.py | jq")
    print(
        "  - 特定のフィールドで絞り込み: "
        "python scripts/verify_logging.py | jq 'select(.level==\"error\")'"
    )
    print(
        "  - ログレベルで絞り込み: "
        'python scripts/verify_logging.py | grep \'"level":"error"\''
    )


if __name__ == "__main__":
    main()
