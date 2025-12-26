"""エラーハンドラーのテスト"""

from unittest.mock import Mock, patch

from src.application.exceptions import AuthorizationException, ValidationException
from src.domain.exceptions import (
    BusinessRuleViolationException,
    EntityNotFoundException,
)
from src.infrastructure.error_handling.handlers import ErrorHandler, GlobalErrorHandler
from src.infrastructure.error_handling.models import ErrorResponse
from src.infrastructure.exceptions import DatabaseException, ExternalServiceException


class TestErrorHandler:
    """ErrorHandlerのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.handler = ErrorHandler()

    def test_handle_entity_not_found(self):
        """エンティティ未検出例外の処理テスト"""
        exception = EntityNotFoundException("Politician", entity_id=123)
        response = self.handler.handle(exception, "test-request-id")

        assert response.status_code == 404
        assert response.error_code == "DOM-001"
        assert response.request_id == "test-request-id"
        assert "見つかりません" in response.message

    def test_handle_business_rule_violation(self):
        """ビジネスルール違反例外の処理テスト"""
        exception = BusinessRuleViolationException(
            "date_validation", "会議日が無効です"
        )
        response = self.handler.handle(exception)

        assert response.status_code == 400
        assert response.error_code == "DOM-002"
        assert "ビジネスルール違反" in response.message
        assert response.details["rule"] == "date_validation"

    def test_handle_validation_exception(self):
        """バリデーション例外の処理テスト"""
        exception = ValidationException(
            "email",
            "invalid-email",
            "email_format",
            "有効なメールアドレスではありません",
        )
        response = self.handler.handle(exception)

        assert response.status_code == 400
        assert response.error_code == "APP-002"
        assert len(response.errors) == 1
        assert response.errors[0].field == "email"
        assert response.errors[0].message == "有効なメールアドレスではありません"

    def test_handle_authorization_exception(self):
        """認可例外の処理テスト"""
        exception = AuthorizationException("meeting/123", "delete", "admin")
        response = self.handler.handle(exception)

        assert response.status_code == 403
        assert response.error_code == "APP-003"
        assert "権限がありません" in response.message

    def test_handle_database_exception(self):
        """データベース例外の処理テスト"""
        exception = DatabaseException(
            "SELECT",
            "接続タイムアウト",
            table="politicians",
            query="SELECT * FROM sensitive_data",
        )
        response = self.handler.handle(exception)

        assert response.status_code == 503
        assert response.error_code == "INF-001"
        assert "データベースエラー" in response.message
        # 機密情報（クエリ）がサニタイズされることを確認
        assert response.details["query"] == "***"

    def test_handle_external_service_exception_with_status_code(self):
        """ステータスコード付き外部サービス例外の処理テスト"""
        exception = ExternalServiceException(
            "Gemini API", "generate_content", status_code=429, reason="レート制限"
        )
        response = self.handler.handle(exception)

        assert response.status_code == 429
        assert response.error_code == "INF-003"

    def test_handle_external_service_exception_without_status_code(self):
        """ステータスコードなし外部サービス例外の処理テスト"""
        exception = ExternalServiceException(
            "Unknown API", "request", reason="不明なエラー"
        )
        response = self.handler.handle(exception)

        assert response.status_code == 502  # デフォルト
        assert response.error_code == "INF-003"

    def test_handle_unknown_exception(self):
        """未知の例外の処理テスト"""
        exception = ValueError("予期しないエラー")

        with patch("src.infrastructure.error_handling.handlers.logger") as mock_logger:
            response = self.handler.handle(exception)

        assert response.status_code == 500
        assert response.error_code == "UNKNOWN"
        assert "予期しないエラーが発生しました" in response.message
        assert response.details["exception_type"] == "ValueError"

        # エラーログが出力されることを確認
        mock_logger.error.assert_called_once()

    def test_handle_generates_request_id_when_none(self):
        """リクエストIDが自動生成されることのテスト"""
        exception = EntityNotFoundException("Test", entity_id=1)
        response = self.handler.handle(exception)

        assert response.request_id is not None
        assert len(response.request_id) > 0


class TestGlobalErrorHandler:
    """GlobalErrorHandlerのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.error_handler = Mock(spec=ErrorHandler)
        self.global_handler = GlobalErrorHandler(self.error_handler)

    def test_handle_exception_with_context(self):
        """コンテキスト付き例外処理のテスト"""
        exception = EntityNotFoundException("Test", entity_id=1)
        context = {"user_id": "123", "operation": "fetch_politician"}

        # モックの設定
        mock_response = ErrorResponse(
            status_code=404, message="Test not found", error_code="DOM-001"
        )
        self.error_handler.handle.return_value = mock_response

        result = self.global_handler.handle_exception(
            exception, context=context, request_id="test-request"
        )

        # エラーハンドラーが呼ばれることを確認
        self.error_handler.handle.assert_called_once_with(exception, "test-request")

        # コンテキストが追加されることを確認
        assert result.details["context"] == context

    def test_handle_exception_generates_request_id(self):
        """リクエストIDが自動生成されることのテスト"""
        exception = ValueError("test error")

        # モックの設定
        mock_response = ErrorResponse(
            status_code=500, message="Error", error_code="UNKNOWN"
        )
        self.error_handler.handle.return_value = mock_response

        with patch("src.infrastructure.error_handling.handlers.logger"):
            self.global_handler.handle_exception(exception)

        # リクエストIDが設定されることを確認
        call_args = self.error_handler.handle.call_args[0]
        # handleメソッドは(exception, request_id)の形で呼ばれる
        assert len(call_args) == 2
        request_id = call_args[1]  # 2番目の引数がrequest_id
        assert request_id is not None
        assert isinstance(request_id, str)

    @patch("src.infrastructure.error_handling.handlers.logger")
    def test_log_error_validation_exception(self, mock_logger):
        """バリデーション例外のログレベルテスト"""
        exception = ValidationException("field", "value", "error")

        mock_response = ErrorResponse(
            status_code=400, message="Validation error", error_code="APP-002"
        )
        self.error_handler.handle.return_value = mock_response

        self.global_handler.handle_exception(exception)

        # 警告レベルでログが出力されることを確認
        mock_logger.warning.assert_called_once()

    @patch("src.infrastructure.error_handling.handlers.logger")
    def test_log_error_infrastructure_exception(self, mock_logger):
        """インフラ例外のログレベルテスト"""
        exception = DatabaseException("SELECT", "error")

        mock_response = ErrorResponse(
            status_code=503, message="Database error", error_code="INF-001"
        )
        self.error_handler.handle.return_value = mock_response

        self.global_handler.handle_exception(exception)

        # エラーレベルでログが出力されることを確認
        mock_logger.error.assert_called_once()

    @patch("src.infrastructure.error_handling.handlers.logger")
    def test_log_error_unknown_exception(self, mock_logger):
        """未知の例外のログレベルテスト"""
        exception = RuntimeError("unknown error")

        mock_response = ErrorResponse(
            status_code=500, message="Unknown error", error_code="UNKNOWN"
        )
        self.error_handler.handle.return_value = mock_response

        self.global_handler.handle_exception(exception)

        # エラーレベルでログが出力されることを確認
        mock_logger.error.assert_called_once()


class TestErrorHandlerIntegration:
    """エラーハンドラーの統合テスト"""

    def test_end_to_end_error_handling(self):
        """エンドツーエンドのエラー処理テスト"""
        # 実際のエラーハンドラーとグローバルハンドラーを使用
        global_handler = GlobalErrorHandler()

        # 複雑な例外を作成
        exception = DatabaseException(
            "INSERT",
            "一意制約違反",
            table="politicians",
            query="INSERT INTO politicians (name, party) VALUES ('田中太郎', '自民党')",
        )

        # 処理を実行
        response = global_handler.handle_exception(
            exception,
            context={"user_id": "test_user", "operation": "create_politician"},
            request_id="integration-test-123",
        )

        # 結果を検証
        assert response.status_code == 503
        assert response.error_code == "INF-001"
        assert response.request_id == "integration-test-123"
        assert "データベースエラー" in response.message
        assert response.details["context"]["user_id"] == "test_user"

        # 機密情報がサニタイズされていることを確認
        assert response.details["query"] == "***"

        # ユーザー向けメッセージとデベロッパー向けメッセージの違いを確認
        user_msg = response.get_user_message()
        dev_msg = response.get_developer_message()

        assert "システムエラーが発生しました" in user_msg
        assert "データベースエラー" in dev_msg
        assert response.error_code in dev_msg
