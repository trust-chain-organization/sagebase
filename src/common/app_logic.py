"""
アプリケーション共通ロジック

Provides common application logic with proper error handling and type safety.
"""

import logging
import os

from collections.abc import Callable
from typing import Any, TypeVar

import src.infrastructure.config.config as config

from src.application.exceptions import (
    ConfigurationError,
    PDFProcessingError,
    ProcessingError,
)
from src.infrastructure.config.database import test_connection
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.exceptions import (
    FileNotFoundException as PolibaseFileNotFoundError,
)
from src.infrastructure.utilities.text_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar("T")
R = TypeVar("R")


def setup_environment() -> None:
    """環境変数を設定する

    Raises:
        ConfigurationError: If configuration validation fails
    """
    try:
        config.set_env()
        config.validate_config()
        logger.info("Environment setup completed")
    except Exception as e:
        logger.error(f"Failed to setup environment: {e}")
        raise ConfigurationError(
            "Failed to setup application environment", {"error": str(e)}
        ) from e


def load_pdf_text(file_path: str = "data/minutes.pdf") -> str:
    """
    PDFファイルからテキストを読み込む

    Args:
        file_path: PDFファイルのパス

    Returns:
        str: 抽出されたテキスト

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        PDFProcessingError: PDF処理が失敗した場合
    """
    if not os.path.exists(file_path):
        logger.error(f"PDF file not found: {file_path}")
        raise PolibaseFileNotFoundError(file_path)

    try:
        logger.info(f"Loading PDF from: {file_path}")
        with open(file_path, "rb") as f:
            file_content = f.read()

        if not file_content:
            raise PDFProcessingError(
                "PDF file is empty", {"file_path": file_path, "size": 0}
            )

        text = extract_text_from_pdf(file_content)
        logger.info(f"Extracted {len(text)} characters from PDF")

        return text

    except (PolibaseFileNotFoundError, PDFProcessingError):
        raise
    except Exception as e:
        logger.error(f"Failed to load PDF: {e}")
        raise PDFProcessingError(
            f"Failed to process PDF file: {file_path}",
            {"file_path": file_path, "error": str(e)},
        ) from e


def validate_database_connection() -> bool:
    """
    データベース接続をテストする

    Returns:
        bool: 接続が成功した場合True

    Raises:
        DatabaseError: If connection test fails with unexpected error
    """
    print("🔍 データベース接続テストを開始...")

    try:
        if not test_connection():
            print(
                "❌ データベースに接続できません。"
                + "docker compose でPostgreSQLが起動していることを確認してください。"
            )
            logger.warning("Database connection test failed")
            return False
        return True
    except Exception as e:
        logger.error(f"Database connection test error: {e}")
        raise DatabaseError(
            "Failed to test database connection", {"error": str(e)}
        ) from e


def run_main_process(
    process_func: Callable[..., T],
    process_name: str,
    display_status_func: Callable[[], None],
    save_func: Callable[[T], list[int]],
    *args: Any,
    **kwargs: Any,
) -> T | None:
    """
    メイン処理の共通フロー

    Args:
        process_func: 実行する処理関数
        process_name: 処理名（ログ用）
        display_status_func: データベース状態表示関数
        save_func: データベース保存関数
        *args: process_funcに渡す引数
        **kwargs: process_funcに渡すキーワード引数

    Returns:
        処理結果またはNone

    Raises:
        DatabaseError: If database operation fails
        ProcessingError: If processing fails
    """
    try:
        # データベース接続テスト
        if not validate_database_connection():
            logger.error("Database connection validation failed")
            return None

        print("📊 処理前のデータベース状態:")
        display_status_func()

        # メイン処理の実行
        logger.info(f"Starting {process_name} processing")
        result = process_func(*args, **kwargs)

        if result is None:
            logger.warning(f"{process_name} returned no results")
            print(f"⚠️ {process_name}の結果がありません")
            return None

        # データベースに保存
        saved_ids = save_func(result)

        if saved_ids:
            print(
                "💾 データベース保存完了: "
                + f"{len(saved_ids)}件の{process_name}レコードを保存しました"
            )
            print(
                f"{process_name}の抽出が完了しました。"
                + f"{len(saved_ids)}件のレコードをデータベースに保存しました。"
            )
            logger.info(f"Saved {len(saved_ids)} {process_name} records")
        else:
            print(f"⚠️ 保存する{process_name}データがありませんでした")

        print("\n📊 処理後のデータベース状態:")
        display_status_func()

        return result

    except (DatabaseError, ProcessingError):
        # These are already properly formatted, re-raise as-is
        raise
    except Exception as e:
        logger.error(f"{process_name} processing error: {e}", exc_info=True)
        print(f"❌ {process_name}処理エラー: {e}")
        raise ProcessingError(
            f"{process_name} processing failed",
            {"process_name": process_name, "error": str(e)},
        ) from e


def print_completion_message(
    result_data: list[Any] | Any | None, process_name: str = "処理"
) -> None:
    """
    処理完了メッセージを表示する

    Args:
        result_data: 処理結果データ
        process_name: 処理名
    """
    if result_data is not None:
        print("--------結果出力--------")
        if isinstance(result_data, list):
            # 型の絞り込みを明示的に行う
            result_list: list[Any] = result_data  # type: ignore[assignment]
            print(f"結果数: {len(result_list)}件")
            if len(result_list) > 0 and len(result_list) <= 5:
                # Show all items if 5 or fewer
                for i, item in enumerate(result_list, 1):
                    print(f"{i}. {item}")
            elif len(result_list) > 5:
                # Show first 3 items if more than 5
                for i, item in enumerate(result_list[:3], 1):
                    print(f"{i}. {item}")
                print(f"... 他 {len(result_list) - 3} 件")
        else:
            print(result_data)

    print(f"\n✅ {process_name}が全部終わったよ")
    logger.info(f"{process_name} completed successfully")
