"""エラーハンドラー実装

例外を適切なエラーレスポンスに変換するハンドラー
"""

import logging
import traceback

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from src.application.exceptions import (
    AuthorizationException,
    ConcurrencyException,
    ConfigurationException,
    DataProcessingException,
    ResourceNotFoundException,
    ValidationException,
    WorkflowException,
)
from src.domain.exceptions import (
    BusinessRuleViolationException,
    DataIntegrityException,
    DuplicateEntityException,
    EntityNotFoundException,
    InvalidDomainOperationException,
    InvalidEntityStateException,
    PolibaseException,
)
from src.infrastructure.exceptions import (
    ConnectionException,
    DatabaseException,
    ExternalServiceException,
    FileSystemException,
    NetworkException,
    RateLimitException,
    StorageException,
    TimeoutException,
)

from .models import ErrorResponse

logger = logging.getLogger(__name__)


class ErrorHandler:
    """個別の例外をエラーレスポンスに変換するハンドラー"""

    def __init__(self):
        """初期化"""
        self._handlers: dict[type[Exception], Callable[[Any], ErrorResponse]] = {
            # Domain exceptions
            EntityNotFoundException: self._handle_entity_not_found,
            BusinessRuleViolationException: self._handle_business_rule_violation,
            InvalidEntityStateException: self._handle_invalid_entity_state,
            DuplicateEntityException: self._handle_duplicate_entity,
            InvalidDomainOperationException: self._handle_invalid_domain_operation,
            DataIntegrityException: self._handle_data_integrity,
            # Application exceptions
            ValidationException: self._handle_validation,
            AuthorizationException: self._handle_authorization,
            ResourceNotFoundException: self._handle_resource_not_found,
            WorkflowException: self._handle_workflow,
            ConcurrencyException: self._handle_concurrency,
            ConfigurationException: self._handle_configuration,
            DataProcessingException: self._handle_data_processing,
            # Infrastructure exceptions
            DatabaseException: self._handle_database,
            ConnectionException: self._handle_connection,
            ExternalServiceException: self._handle_external_service,
            FileSystemException: self._handle_file_system,
            StorageException: self._handle_storage,
            NetworkException: self._handle_network,
            TimeoutException: self._handle_timeout,
            RateLimitException: self._handle_rate_limit,
        }

    def handle(
        self, exception: Exception, request_id: str | None = None
    ) -> ErrorResponse:
        """例外をエラーレスポンスに変換

        Args:
            exception: 処理する例外
            request_id: リクエストID（トレーシング用）

        Returns:
            ErrorResponse: エラーレスポンス
        """
        if request_id is None:
            request_id = str(uuid4())

        # 特定のハンドラーを探す
        handler = self._get_handler(exception)
        if handler:
            response = handler(exception)
            response.request_id = request_id
            return response

        # Sagebase例外の汎用処理
        if isinstance(exception, PolibaseException):
            return self._handle_sagebase_exception(exception, request_id)

        # その他の例外
        return self._handle_unknown_exception(exception, request_id)

    def _get_handler(
        self, exception: Exception
    ) -> Callable[[Any], ErrorResponse] | None:
        """例外に対応するハンドラーを取得"""
        for exc_type, handler in self._handlers.items():
            if isinstance(exception, exc_type):
                return handler
        return None

    # Domain exception handlers
    def _handle_entity_not_found(
        self, exception: EntityNotFoundException
    ) -> ErrorResponse:
        """エンティティ未検出エラーの処理"""
        return ErrorResponse(
            status_code=404,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_business_rule_violation(
        self, exception: BusinessRuleViolationException
    ) -> ErrorResponse:
        """ビジネスルール違反エラーの処理"""
        return ErrorResponse(
            status_code=400,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_invalid_entity_state(
        self, exception: InvalidEntityStateException
    ) -> ErrorResponse:
        """エンティティ状態不正エラーの処理"""
        return ErrorResponse(
            status_code=409,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_duplicate_entity(
        self, exception: DuplicateEntityException
    ) -> ErrorResponse:
        """重複エンティティエラーの処理"""
        return ErrorResponse(
            status_code=409,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_invalid_domain_operation(
        self, exception: InvalidDomainOperationException
    ) -> ErrorResponse:
        """ドメイン操作無効エラーの処理"""
        return ErrorResponse(
            status_code=400,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_data_integrity(
        self, exception: DataIntegrityException
    ) -> ErrorResponse:
        """データ整合性エラーの処理"""
        return ErrorResponse(
            status_code=409,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    # Application exception handlers
    def _handle_validation(self, exception: ValidationException) -> ErrorResponse:
        """バリデーションエラーの処理"""
        response = ErrorResponse(
            status_code=400,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )
        # フィールドエラーを追加
        if "field" in exception.details:
            response.add_error(
                field=exception.details["field"],
                message=exception.message,
                code=exception.error_code,
            )
        return response

    def _handle_authorization(self, exception: AuthorizationException) -> ErrorResponse:
        """認可エラーの処理"""
        return ErrorResponse(
            status_code=403,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_resource_not_found(
        self, exception: ResourceNotFoundException
    ) -> ErrorResponse:
        """リソース未検出エラーの処理"""
        return ErrorResponse(
            status_code=404,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_workflow(self, exception: WorkflowException) -> ErrorResponse:
        """ワークフローエラーの処理"""
        return ErrorResponse(
            status_code=500 if not exception.details.get("can_retry") else 503,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_concurrency(self, exception: ConcurrencyException) -> ErrorResponse:
        """並行実行エラーの処理"""
        return ErrorResponse(
            status_code=409,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_configuration(self, exception: ConfigurationException) -> ErrorResponse:
        """設定エラーの処理"""
        return ErrorResponse(
            status_code=500,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_data_processing(
        self, exception: DataProcessingException
    ) -> ErrorResponse:
        """データ処理エラーの処理"""
        return ErrorResponse(
            status_code=422,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    # Infrastructure exception handlers
    def _handle_database(self, exception: DatabaseException) -> ErrorResponse:
        """データベースエラーの処理"""
        return ErrorResponse(
            status_code=503,
            message="データベースエラーが発生しました",
            error_code=exception.error_code,
            details=self._sanitize_details(exception.details),
        )

    def _handle_connection(self, exception: ConnectionException) -> ErrorResponse:
        """接続エラーの処理"""
        return ErrorResponse(
            status_code=503,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_external_service(
        self, exception: ExternalServiceException
    ) -> ErrorResponse:
        """外部サービスエラーの処理"""
        status_code = exception.details.get("status_code")
        if status_code is None or not isinstance(status_code, int):
            status_code = 502
        elif not (400 <= status_code < 600):
            status_code = 502

        return ErrorResponse(
            status_code=status_code,
            message=exception.message,
            error_code=exception.error_code,
            details=self._sanitize_details(exception.details),
        )

    def _handle_file_system(self, exception: FileSystemException) -> ErrorResponse:
        """ファイルシステムエラーの処理"""
        return ErrorResponse(
            status_code=500,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_storage(self, exception: StorageException) -> ErrorResponse:
        """ストレージエラーの処理"""
        return ErrorResponse(
            status_code=503,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_network(self, exception: NetworkException) -> ErrorResponse:
        """ネットワークエラーの処理"""
        return ErrorResponse(
            status_code=503,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_timeout(self, exception: TimeoutException) -> ErrorResponse:
        """タイムアウトエラーの処理"""
        return ErrorResponse(
            status_code=504,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    def _handle_rate_limit(self, exception: RateLimitException) -> ErrorResponse:
        """レート制限エラーの処理"""
        return ErrorResponse(
            status_code=429,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
        )

    # Generic handlers
    def _handle_sagebase_exception(
        self, exception: PolibaseException, request_id: str
    ) -> ErrorResponse:
        """Sagebase例外の汎用処理"""
        return ErrorResponse(
            status_code=500,
            message=exception.message,
            error_code=exception.error_code,
            details=exception.details,
            request_id=request_id,
        )

    def _handle_unknown_exception(
        self, exception: Exception, request_id: str
    ) -> ErrorResponse:
        """未知の例外の処理"""
        logger.error(
            f"Unhandled exception: {exception.__class__.__name__}",
            exc_info=exception,
            extra={"request_id": request_id},
        )

        return ErrorResponse(
            status_code=500,
            message="予期しないエラーが発生しました",
            error_code="UNKNOWN",
            details={"exception_type": exception.__class__.__name__},
            request_id=request_id,
        )

    def _sanitize_details(self, details: dict[str, Any]) -> dict[str, Any]:
        """機密情報を除去した詳細を返す"""
        # SQLクエリやレスポンスボディなどの機密情報を除去
        sanitized = details.copy()
        sensitive_keys = ["query", "response_body", "original_error"]
        for key in sensitive_keys:
            if key in sanitized:
                sanitized[key] = "***"
        return sanitized


class GlobalErrorHandler:
    """グローバルエラーハンドラー

    アプリケーション全体のエラー処理を統括
    """

    def __init__(self, error_handler: ErrorHandler | None = None):
        """初期化

        Args:
            error_handler: 使用するエラーハンドラー
        """
        self.error_handler = error_handler or ErrorHandler()

    def handle_exception(
        self,
        exception: Exception,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> ErrorResponse:
        """例外を処理してエラーレスポンスを返す

        Args:
            exception: 処理する例外
            context: エラーコンテキスト情報
            request_id: リクエストID

        Returns:
            ErrorResponse: エラーレスポンス
        """
        # リクエストIDの生成
        if request_id is None:
            request_id = str(uuid4())

        # エラーログ出力
        self._log_error(exception, context, request_id)

        # エラーレスポンスの生成
        response = self.error_handler.handle(exception, request_id)

        # コンテキスト情報の追加
        if context:
            if response.details is None:
                response.details = {}
            response.details["context"] = context

        return response

    def _log_error(
        self, exception: Exception, context: dict[str, Any] | None, request_id: str
    ) -> None:
        """エラーログを出力"""
        log_data = {
            "request_id": request_id,
            "exception_type": exception.__class__.__name__,
            "exception_message": str(exception),
            "context": context,
            "traceback": traceback.format_exc(),
        }

        # Sagebase例外の場合は詳細情報も記録
        if isinstance(exception, PolibaseException):
            log_data["error_code"] = exception.error_code
            log_data["error_details"] = exception.details

        # エラーレベルに応じてログ出力
        if isinstance(exception, ValidationException | BusinessRuleViolationException):
            logger.warning("Business logic error", extra=log_data)
        elif isinstance(
            exception, ConnectionException | NetworkException | TimeoutException
        ):
            logger.error("Infrastructure error", extra=log_data)
        else:
            logger.error("Application error", extra=log_data)
