"""
データベース操作に関する共通処理

Provides common database operations with type safety and error handling.
"""

import logging
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from src.infrastructure.exceptions import DatabaseError, RepositoryException


logger = logging.getLogger(__name__)

# Type variable for generic repository operations
T = TypeVar("T")


class DatabaseRepository(Protocol):
    """データベースリポジトリの共通インターフェース"""

    def get_count(self) -> int:
        """レコード数を取得する"""
        ...

    def get_all(self) -> list[dict[str, Any]]:
        """全レコードを取得する"""
        ...


def display_repository_status(
    repo: DatabaseRepository,
    table_name: str,
    additional_stats: dict[str, Any] | None = None,
) -> None:
    """
    データベースリポジトリの状態を表示する共通処理

    Args:
        repo: データベースリポジトリ
        table_name: テーブル名
        additional_stats: 追加統計情報

    Raises:
        RepositoryException: If repository operation fails
    """
    try:
        count = repo.get_count()
        print(f"📊 現在の{table_name}テーブルレコード数: {count}件")
        logger.info(f"{table_name} table has {count} records")

        # 追加統計情報の表示
        if additional_stats:
            for key, value in additional_stats.items():
                print(f"   - {key}: {value}件")

        # サンプルレコードの表示
        if count > 0:
            print("\n📋 最新の5件のレコード:")
            records = repo.get_all()[:5]
            for i, record in enumerate(records, 1):
                _display_record_summary(record, i)

    except AttributeError as e:
        logger.error(f"Repository does not implement required method: {e}")
        raise RepositoryException(
            operation="display_status",
            entity_type=table_name,
            reason=f"Repository does not implement required method: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Failed to display repository status: {e}")
        print(f"❌ データベース状態確認エラー: {e}")
        raise RepositoryException(
            operation="display_status",
            entity_type=table_name,
            reason=str(e),
        ) from e


def _display_record_summary(record: dict[str, Any], index: int) -> None:
    """レコードのサマリーを表示する（内部使用）"""
    print(f"  {index}. ID: {record.get('id', 'N/A')}")
    for key, value in record.items():
        if key != "id" and value is not None:
            if isinstance(value, str) and len(value) > 50:
                print(f"      {key}: {value[:50]}...")
            else:
                print(f"      {key}: {value}")


def save_data_with_logging(
    save_func: Callable[[Any], list[int]], data: Any, data_type: str
) -> list[int]:
    """
    データ保存処理の共通ラッパー

    Args:
        save_func: 保存処理を行う関数
        data: 保存するデータ
        data_type: データの種類（ログメッセージ用）

    Returns:
        List[int]: 保存されたレコードのIDリスト

    Raises:
        DatabaseError: If save operation fails
    """
    if not data:
        logger.warning(f"No {data_type} data to save")
        return []

    try:
        saved_ids = save_func(data)

        if not isinstance(saved_ids, list):
            raise TypeError(f"save_func must return List[int], got {type(saved_ids)}")

        print(
            f"💾 データベース保存完了: {len(saved_ids)}件の"
            + f"{data_type}レコードを保存しました"
        )
        logger.info(f"Saved {len(saved_ids)} {data_type} records")

        return saved_ids

    except DatabaseError:
        # Re-raise database errors as-is
        raise
    except Exception as e:
        logger.error(f"Failed to save {data_type} data: {e}")
        print(f"❌ データベース保存エラー: {e}")
        raise DatabaseError(
            f"Failed to save {data_type} data",
            {"data_type": data_type, "error": str(e)},
        ) from e


def batch_save_with_logging(
    save_func: Callable[[list[T]], list[int]],
    items: list[T],
    batch_size: int,
    data_type: str,
) -> list[int]:
    """
    バッチ処理でデータを保存する共通ラッパー

    Args:
        save_func: 保存処理を行う関数
        items: 保存するアイテムのリスト
        batch_size: バッチサイズ
        data_type: データの種類（ログメッセージ用）

    Returns:
        List[int]: 保存されたレコードのIDリスト

    Raises:
        DatabaseError: If save operation fails
    """
    if not items:
        logger.warning(f"No {data_type} items to save")
        return []

    all_saved_ids: list[int] = []
    total_items = len(items)

    try:
        for i in range(0, total_items, batch_size):
            batch = items[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_items + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)"
            )

            saved_ids = save_func(batch)
            all_saved_ids.extend(saved_ids)

            print(
                f"  ✓ バッチ {batch_num}/{total_batches} 完了: {len(saved_ids)}件保存"
            )

        print(
            f"\n💾 バッチ処理完了: 合計 {len(all_saved_ids)}件の"
            + f"{data_type}レコードを保存しました"
        )
        logger.info(
            f"Batch save completed: {len(all_saved_ids)} {data_type} records saved"
        )

        return all_saved_ids

    except Exception as e:
        logger.error(f"Batch save failed at item {len(all_saved_ids)}: {e}")
        print(
            f"\n❌ バッチ保存エラー: {len(all_saved_ids)}件保存後にエラーが発生しました"
        )
        raise DatabaseError(
            f"Batch save failed after saving {len(all_saved_ids)} items",
            {
                "data_type": data_type,
                "saved_count": len(all_saved_ids),
                "error": str(e),
            },
        ) from e
