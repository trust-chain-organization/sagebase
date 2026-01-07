"""ドメイン層の例外クラス定義

アプリケーション全体で使用される基底例外クラスと、
ドメイン層で発生する例外を定義
"""

from typing import Any


class PolibaseException(Exception):  # noqa: N818
    """Polibaseアプリケーションの基底例外クラス

    すべての独自例外クラスはこのクラスを継承する。
    エラーコードとメッセージを管理し、トレーサビリティを提供。
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Args:
            message: エラーメッセージ
            error_code: エラーコード（例: DOM-001）
            details: 追加の詳細情報
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """エラーの文字列表現を返す"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


# Backward compatibility wrapper
class PolibaseError(PolibaseException):
    """Backward compatibility wrapper for the old PolibaseError signature"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(message=message, error_code=None, details=details)


class DomainException(PolibaseException):
    """ドメイン層の基底例外クラス

    ドメインロジックに関連するすべての例外の基底クラス
    """

    pass


class EntityNotFoundException(DomainException):
    """エンティティが見つからない場合の例外

    データベースに存在しないエンティティを参照した場合に発生
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: int | None = None,
        search_criteria: dict[str, Any] | None = None,
    ):
        """
        Args:
            entity_type: エンティティの種類（例: "Politician", "Meeting"）
            entity_id: エンティティのID（あれば）
            search_criteria: 検索条件（IDが無い場合）
        """
        if entity_id:
            message = f"{entity_type}が見つかりません (ID: {entity_id})"
            details = {"entity_type": entity_type, "entity_id": entity_id}
        else:
            message = f"{entity_type}が見つかりません"
            details = {"entity_type": entity_type, "search_criteria": search_criteria}

        super().__init__(message=message, error_code="DOM-001", details=details)


class BusinessRuleViolationException(DomainException):
    """ビジネスルール違反の例外

    ドメインのビジネスルールに違反する操作を実行した場合に発生
    """

    def __init__(self, rule: str, violation_details: str):
        """
        Args:
            rule: 違反したビジネスルール
            violation_details: 違反の詳細
        """
        message = f"ビジネスルール違反: {violation_details}"
        super().__init__(
            message=message,
            error_code="DOM-002",
            details={"rule": rule, "violation": violation_details},
        )


class InvalidEntityStateException(DomainException):
    """エンティティの状態が不正な場合の例外

    エンティティが期待される状態でない場合に発生
    """

    def __init__(
        self,
        entity_type: str,
        current_state: str,
        expected_state: str,
        entity_id: int | None = None,
    ):
        """
        Args:
            entity_type: エンティティの種類
            current_state: 現在の状態
            expected_state: 期待される状態
            entity_id: エンティティのID（あれば）
        """
        message = (
            f"{entity_type}の状態が不正です "
            f"(現在: {current_state}, 期待: {expected_state})"
        )
        super().__init__(
            message=message,
            error_code="DOM-003",
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "current_state": current_state,
                "expected_state": expected_state,
            },
        )


class DuplicateEntityException(DomainException):
    """重複エンティティの例外

    既に存在するエンティティを作成しようとした場合に発生
    """

    def __init__(
        self,
        entity_type: str,
        duplicate_criteria: dict[str, Any],
        existing_id: int | None = None,
    ):
        """
        Args:
            entity_type: エンティティの種類
            duplicate_criteria: 重複判定の条件
            existing_id: 既存エンティティのID（あれば）
        """
        message = f"{entity_type}が既に存在します"
        super().__init__(
            message=message,
            error_code="DOM-004",
            details={
                "entity_type": entity_type,
                "duplicate_criteria": duplicate_criteria,
                "existing_id": existing_id,
            },
        )


class InvalidDomainOperationException(DomainException):
    """ドメイン操作が無効な場合の例外

    実行できない操作を試みた場合に発生
    """

    def __init__(self, operation: str, reason: str):
        """
        Args:
            operation: 実行しようとした操作
            reason: 無効な理由
        """
        message = f"操作 '{operation}' を実行できません: {reason}"
        super().__init__(
            message=message,
            error_code="DOM-005",
            details={"operation": operation, "reason": reason},
        )


class DataIntegrityException(DomainException):
    """データ整合性エラーの例外

    データの整合性が保たれない場合に発生
    """

    def __init__(self, constraint: str, violation_details: str):
        """
        Args:
            constraint: 違反した制約
            violation_details: 違反の詳細
        """
        message = f"データ整合性エラー: {violation_details}"
        super().__init__(
            message=message,
            error_code="DOM-006",
            details={"constraint": constraint, "violation": violation_details},
        )


class ExternalServiceException(DomainException):
    """外部サービス操作失敗の例外

    ドメインロジックで必要な外部サービス操作が失敗した場合に発生
    インフラ層の例外をドメイン層で扱うためのラッパー
    """

    def __init__(self, service_name: str, operation: str, reason: str):
        """
        Args:
            service_name: サービス名（例: "LLM", "Storage", "ExternalAPI"）
            operation: 実行しようとした操作
            reason: 失敗理由
        """
        message = f"{service_name}サービス操作が失敗しました ({operation}): {reason}"
        super().__init__(
            message=message,
            error_code="DOM-007",
            details={
                "service_name": service_name,
                "operation": operation,
                "reason": reason,
            },
        )


class RepositoryError(DomainException):
    """リポジトリ操作失敗の例外

    リポジトリ操作（データの取得・保存・更新・削除）が失敗した場合に発生。
    Application層がInfrastructure層の例外に直接依存しないようにするための
    Domain層の例外クラス。
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報
        """
        super().__init__(
            message=message,
            error_code="DOM-008",
            details=details or {},
        )
