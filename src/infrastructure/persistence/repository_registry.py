"""リポジトリレジストリ。

このモジュールは、リポジトリ実装クラスへのアクセスを一元化し、
Interface層がInfrastructure層の具体実装に直接依存することを防ぎます。
"""

from typing import Any

from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


# リポジトリ実装クラスのレジストリ
_REPOSITORY_CLASSES: dict[str, type] = {
    "extraction_log": ExtractionLogRepositoryImpl,
}


def get_repository_class(repository_name: str) -> type:
    """リポジトリ実装クラスを取得する。

    Args:
        repository_name: リポジトリ名（例: "extraction_log"）

    Returns:
        リポジトリ実装クラス

    Raises:
        KeyError: 指定された名前のリポジトリが登録されていない場合
    """
    if repository_name not in _REPOSITORY_CLASSES:
        available = ", ".join(_REPOSITORY_CLASSES.keys())
        raise KeyError(
            f"リポジトリ '{repository_name}' は登録されていません。"
            f"利用可能なリポジトリ: {available}"
        )
    return _REPOSITORY_CLASSES[repository_name]


def create_repository_adapter(repository_name: str) -> Any:
    """リポジトリアダプターを作成する。

    Args:
        repository_name: リポジトリ名（例: "extraction_log"）

    Returns:
        RepositoryAdapterインスタンス
    """
    repo_class = get_repository_class(repository_name)
    return RepositoryAdapter(repo_class)


def register_repository(repository_name: str, repository_class: type) -> None:
    """リポジトリ実装クラスを登録する。

    Args:
        repository_name: リポジトリ名
        repository_class: リポジトリ実装クラス
    """
    _REPOSITORY_CLASSES[repository_name] = repository_class
