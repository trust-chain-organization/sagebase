"""ヘルスチェックエンドポイント for Cloud Run.

Cloud Runのヘルスチェック要件を満たすシンプルなHTTPサーバー。
Streamlitアプリと別スレッドで動作し、/healthと/readinessエンドポイントを提供する。
"""

import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread


logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """ヘルスチェックリクエストを処理するハンドラー."""

    def do_GET(self) -> None:  # noqa: N802
        """GETリクエストを処理."""
        if self.path == "/health":
            # 基本的なヘルスチェック - 常に200を返す
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')

        elif self.path == "/readiness":
            # レディネスチェック - データベース接続を確認
            try:
                from src.infrastructure.config.database import test_connection

                if test_connection():
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status": "ready", "database": "connected"}')
                else:
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        b'{"status": "not ready", "database": "disconnected"}'
                    )
            except Exception as e:
                logger.error(f"Readiness check failed: {e}")
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                error_msg = f'{{"status": "error", "message": "{str(e)}"}}'
                self.wfile.write(error_msg.encode())

        else:
            # 未知のパスには404を返す
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

    def log_message(self, format: str, *args: object) -> None:
        """ログメッセージを標準ログに出力（アクセスログを抑制）."""
        # ヘルスチェックのアクセスログは大量になるため、エラーのみログに記録
        if args[1] not in ("200", "304"):
            logger.info(f"{self.address_string()} - {format % args}")


def start_health_check_server(port: int = 8081) -> None:
    """ヘルスチェックサーバーを別スレッドで起動.

    Args:
        port: ヘルスチェックサーバーのポート番号（デフォルト: 8081）
    """
    server = HTTPServer(("", port), HealthCheckHandler)
    logger.info(f"Health check server starting on port {port}")

    # デーモンスレッドで起動（メインプロセス終了時に自動終了）
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server running on http://0.0.0.0:{port}")
    logger.info(f"  - Health endpoint: http://0.0.0.0:{port}/health")
    logger.info(f"  - Readiness endpoint: http://0.0.0.0:{port}/readiness")


if __name__ == "__main__":
    # スタンドアロンテスト用
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("HEALTH_CHECK_PORT", "8081"))
    start_health_check_server(port)

    # サーバーを実行し続ける
    import time

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down health check server...")
