"""Cloud Run用のStreamlitエントリーポイント.

ヘルスチェックサーバーとStreamlitアプリを起動する。
Cloud Logging設定も初期化する。
"""

import logging
import os
import subprocess
import sys

# ログ設定を初期化
from src.common.logging import setup_logging


# Cloud Run環境では構造化ログ（JSON形式）を使用
is_cloud_run = os.getenv("CLOUD_RUN", "false").lower() == "true"
log_level = os.getenv("LOG_LEVEL", "INFO")

setup_logging(
    log_level=log_level,
    json_format=is_cloud_run,  # Cloud RunではJSON形式
    add_timestamp=True,
    # SentryはCloud Run環境では無効化（別途設定が必要な場合のみ有効化）
    enable_sentry=False,
)

logger = logging.getLogger(__name__)

logger.info("Starting Streamlit application for Cloud Run")
logger.info(f"Cloud Run mode: {is_cloud_run}")
logger.info(f"Log level: {log_level}")
logger.info("Note: Streamlit provides health check at /_stcore/health endpoint")

# StreamlitのPORTを取得（Cloud Runが自動設定）
port = os.getenv("PORT", "8080")

# Streamlitアプリのパス
app_path = "src/interfaces/web/streamlit/app.py"

# Streamlitコマンドを構築（uv経由で実行）
streamlit_cmd = [
    "uv",
    "run",
    "streamlit",
    "run",
    app_path,
    "--server.port",
    port,
    "--server.address",
    "0.0.0.0",
    "--server.headless",
    "true",
    "--server.enableCORS",
    "false",
    "--server.enableXsrfProtection",
    "true",
    "--browser.gatherUsageStats",
    "false",
]

logger.info(f"Executing: {' '.join(streamlit_cmd)}")

try:
    # Streamlitプロセスを起動
    result = subprocess.run(streamlit_cmd, check=True)
    sys.exit(result.returncode)
except subprocess.CalledProcessError as e:
    logger.error(f"Streamlit process failed: {e}")
    sys.exit(e.returncode)
except KeyboardInterrupt:
    logger.info("Shutting down Streamlit application")
    sys.exit(0)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    sys.exit(1)
