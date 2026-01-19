"""例外クラスのテスト"""

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
    DataValidationException,
    DuplicateEntityException,
    EntityNotFoundException,
    InvalidDomainOperationException,
    InvalidEntityStateException,
    PolibaseException,
    RateLimitExceededException,
    RetryableException,
    TemporaryServiceException,
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


class TestPolibaseException:
    """PolibaseException（基底例外）のテスト"""

    def test_init_with_message_only(self):
        """メッセージのみでの初期化テスト"""
        exception = PolibaseException("エラーが発生しました")
        assert str(exception) == "エラーが発生しました"
        assert exception.message == "エラーが発生しました"
        assert exception.error_code is None
        assert exception.details == {}

    def test_init_with_error_code(self):
        """エラーコード付きの初期化テスト"""
        exception = PolibaseException("エラーが発生しました", "TEST-001")
        assert str(exception) == "[TEST-001] エラーが発生しました"
        assert exception.error_code == "TEST-001"

    def test_init_with_details(self):
        """詳細情報付きの初期化テスト"""
        details = {"user_id": 123, "operation": "test"}
        exception = PolibaseException("エラーが発生しました", "TEST-001", details)
        assert exception.details == details


class TestDomainExceptions:
    """ドメイン例外のテスト"""

    def test_entity_not_found_with_id(self):
        """ID付きエンティティ未検出例外のテスト"""
        exception = EntityNotFoundException("Politician", entity_id=123)
        assert "Politicianが見つかりません (ID: 123)" in str(exception)
        assert exception.error_code == "DOM-001"
        assert exception.details["entity_type"] == "Politician"
        assert exception.details["entity_id"] == 123

    def test_entity_not_found_with_criteria(self):
        """検索条件付きエンティティ未検出例外のテスト"""
        criteria = {"name": "田中太郎", "party": "自民党"}
        exception = EntityNotFoundException("Politician", search_criteria=criteria)
        assert "Politicianが見つかりません" in str(exception)
        assert exception.details["search_criteria"] == criteria

    def test_business_rule_violation(self):
        """ビジネスルール違反例外のテスト"""
        exception = BusinessRuleViolationException(
            "meeting_date_validation", "会議日が未来の日付です"
        )
        assert "ビジネスルール違反: 会議日が未来の日付です" in str(exception)
        assert exception.error_code == "DOM-002"
        assert exception.details["rule"] == "meeting_date_validation"

    def test_invalid_entity_state(self):
        """エンティティ状態不正例外のテスト"""
        exception = InvalidEntityStateException(
            "Meeting", "archived", "active", entity_id=456
        )
        assert "Meetingの状態が不正です (現在: archived, 期待: active)" in str(
            exception
        )
        assert exception.error_code == "DOM-003"
        assert exception.details["current_state"] == "archived"
        assert exception.details["expected_state"] == "active"

    def test_duplicate_entity(self):
        """重複エンティティ例外のテスト"""
        criteria = {"name": "田中太郎", "party": "自民党"}
        exception = DuplicateEntityException("Politician", criteria, existing_id=789)
        assert "Politicianが既に存在します" in str(exception)
        assert exception.error_code == "DOM-004"
        assert exception.details["duplicate_criteria"] == criteria
        assert exception.details["existing_id"] == 789

    def test_invalid_domain_operation(self):
        """ドメイン操作無効例外のテスト"""
        exception = InvalidDomainOperationException(
            "delete_speaker", "関連する発言が存在します"
        )
        assert (
            "操作 'delete_speaker' を実行できません: 関連する発言が存在します"
            in str(exception)
        )
        assert exception.error_code == "DOM-005"

    def test_data_integrity(self):
        """データ整合性例外のテスト"""
        exception = DataIntegrityException(
            "foreign_key_constraint", "参照されているレコードを削除できません"
        )
        assert "データ整合性エラー: 参照されているレコードを削除できません" in str(
            exception
        )
        assert exception.error_code == "DOM-006"


class TestNewDomainExceptions:
    """Issue #965で追加された新しいドメイン例外のテスト"""

    def test_data_validation_exception(self):
        """データバリデーション例外のテスト"""
        exception = DataValidationException(
            field="email",
            reason="有効なメールアドレスではありません",
            actual_value="invalid-email",
        )
        assert "データ不正 (email)" in str(exception)
        assert exception.error_code == "DOM-009"
        assert exception.details["field"] == "email"
        assert exception.details["reason"] == "有効なメールアドレスではありません"
        assert exception.details["actual_value"] == "invalid-email"

    def test_data_validation_exception_truncates_long_value(self):
        """長い値が200文字で切り捨てられることを確認"""
        long_value = "a" * 300
        exception = DataValidationException(
            field="content",
            reason="値が長すぎます",
            actual_value=long_value,
        )
        assert len(exception.details["actual_value"]) == 200

    def test_data_validation_exception_without_actual_value(self):
        """actual_valueなしでの初期化テスト"""
        exception = DataValidationException(
            field="name",
            reason="必須項目です",
        )
        assert exception.details["actual_value"] is None

    def test_retryable_exception_with_retry_after(self):
        """再試行可能例外のテスト（retry_after指定あり）"""
        exception = RetryableException(
            message="一時的なエラー",
            retry_after=60,
        )
        assert exception.retry_after == 60
        assert exception.error_code == "DOM-010"
        assert exception.details["retry_after"] == 60

    def test_retryable_exception_without_retry_after(self):
        """再試行可能例外のテスト（retry_after指定なし）"""
        exception = RetryableException(
            message="一時的なエラー",
        )
        assert exception.retry_after is None
        assert exception.error_code == "DOM-010"

    def test_retryable_exception_with_custom_error_code(self):
        """カスタムエラーコード付きの再試行可能例外テスト"""
        exception = RetryableException(
            message="カスタムエラー",
            error_code="CUSTOM-001",
            details={"key": "value"},
        )
        assert exception.error_code == "CUSTOM-001"
        assert exception.details["key"] == "value"

    def test_rate_limit_exceeded_exception(self):
        """レート制限超過例外のテスト"""
        exception = RateLimitExceededException(
            service_name="Gemini API",
            retry_after=30,
        )
        assert "Gemini APIのレート制限に達しました" in str(exception)
        assert "30秒後に再試行可能" in str(exception)
        assert exception.error_code == "DOM-011"
        assert exception.retry_after == 30
        assert exception.details["service_name"] == "Gemini API"

    def test_rate_limit_exceeded_exception_without_retry_after(self):
        """レート制限超過例外のテスト（retry_after指定なし）"""
        exception = RateLimitExceededException(service_name="GCS")
        assert "GCSのレート制限に達しました" in str(exception)
        assert "秒後" not in str(exception)
        assert exception.retry_after is None

    def test_rate_limit_exceeded_is_retryable(self):
        """RateLimitExceededExceptionがRetryableExceptionを継承していることを確認"""
        exception = RateLimitExceededException(service_name="API", retry_after=10)
        assert isinstance(exception, RetryableException)

    def test_temporary_service_exception(self):
        """一時的なサービスエラー例外のテスト"""
        exception = TemporaryServiceException(
            service_name="BAML",
            operation="section_divide",
            reason="サービスが一時的に利用不可",
            retry_after=10,
        )
        assert "BAMLの一時的なエラー (section_divide)" in str(exception)
        assert "サービスが一時的に利用不可" in str(exception)
        assert exception.error_code == "DOM-012"
        assert exception.retry_after == 10
        assert exception.details["service_name"] == "BAML"
        assert exception.details["operation"] == "section_divide"
        assert exception.details["reason"] == "サービスが一時的に利用不可"

    def test_temporary_service_exception_without_retry_after(self):
        """一時的なサービスエラー例外のテスト（retry_after指定なし）"""
        exception = TemporaryServiceException(
            service_name="LLM",
            operation="invoke",
            reason="タイムアウト",
        )
        assert exception.retry_after is None

    def test_temporary_service_exception_is_retryable(self):
        """TemporaryServiceExceptionがRetryableExceptionを継承していることを確認"""
        exception = TemporaryServiceException(
            service_name="API",
            operation="call",
            reason="error",
        )
        assert isinstance(exception, RetryableException)


class TestApplicationExceptions:
    """アプリケーション例外のテスト"""

    def test_validation_exception(self):
        """バリデーション例外のテスト"""
        exception = ValidationException(
            "email", "invalid-email", "有効なメールアドレスではありません"
        )
        assert exception.error_code == "APP-002"
        assert exception.details["field"] == "email"
        assert exception.details["value"] == "invalid-email"

    def test_authorization_exception(self):
        """認可例外のテスト"""
        exception = AuthorizationException("meeting/123", "delete", "admin")
        assert "リソース 'meeting/123' に対する操作 'delete' の権限がありません" in str(
            exception
        )
        assert exception.error_code == "APP-003"

    def test_resource_not_found_exception(self):
        """リソース未検出例外のテスト"""
        exception = ResourceNotFoundException("User", 123, "authentication_context")
        assert "リソース 'User' (ID: 123) が見つかりません" in str(exception)
        assert "コンテキスト: authentication_context" in str(exception)
        assert exception.error_code == "APP-004"

    def test_workflow_exception(self):
        """ワークフロー例外のテスト"""
        exception = WorkflowException(
            "minutes_processing",
            "text_extraction",
            "PDFが破損しています",
            can_retry=True,
        )
        assert (
            "ワークフロー 'minutes_processing' のステップ 'text_extraction' で失敗"
            in str(exception)
        )
        assert exception.error_code == "APP-005"
        assert exception.details["can_retry"] is True

    def test_concurrency_exception(self):
        """並行実行例外のテスト"""
        exception = ConcurrencyException(
            "meeting/123", "update", "同時に更新されました"
        )
        assert "リソース 'meeting/123' への並行アクセスで競合が発生" in str(exception)
        assert exception.error_code == "APP-006"

    def test_configuration_exception(self):
        """設定例外のテスト"""
        exception = ConfigurationException(
            "GOOGLE_API_KEY",
            "環境変数が設定されていません",
            expected_value="string",
            actual_value=None,
        )
        assert "設定 'GOOGLE_API_KEY' のエラー: 環境変数が設定されていません" in str(
            exception
        )
        assert exception.error_code == "APP-007"

    def test_data_processing_exception(self):
        """データ処理例外のテスト"""
        exception = DataProcessingException(
            "pdf_extraction",
            "PDF",
            "テキストの抽出に失敗しました",
            input_data="sample_data",
        )
        assert (
            "データ処理 'pdf_extraction' でエラー (PDF): テキストの抽出に失敗しました"
            in str(exception)
        )
        assert exception.error_code == "APP-008"


class TestInfrastructureExceptions:
    """インフラストラクチャ例外のテスト"""

    def test_database_exception(self):
        """データベース例外のテスト"""
        exception = DatabaseException(
            "SELECT",
            "接続タイムアウト",
            table="politicians",
            query="SELECT * FROM politicians WHERE id = 123",
        )
        assert (
            "データベースエラー (SELECT): 接続タイムアウト - テーブル: politicians"
            in str(exception)
        )
        assert exception.error_code == "INF-001"
        assert exception.details["operation"] == "SELECT"
        assert exception.details["table"] == "politicians"

    def test_connection_exception(self):
        """接続例外のテスト"""
        exception = ConnectionException(
            "PostgreSQL", "localhost:5432", "接続が拒否されました", retry_after=30
        )
        assert (
            "サービス 'PostgreSQL' への接続に失敗しました: 接続が拒否されました"
            in str(exception)
        )
        assert exception.error_code == "INF-002"
        assert exception.details["retry_after"] == 30

    def test_external_service_exception(self):
        """外部サービス例外のテスト"""
        exception = ExternalServiceException(
            "Gemini API",
            "generate_content",
            status_code=429,
            reason="レート制限に達しました",
        )
        assert (
            "外部サービス 'Gemini API' でエラー (generate_content) - ステータス: 429"
            in str(exception)
        )
        assert exception.error_code == "INF-003"
        assert exception.details["status_code"] == 429

    def test_file_system_exception(self):
        """ファイルシステム例外のテスト"""
        exception = FileSystemException(
            "read", "/path/to/file.pdf", "ファイルが見つかりません"
        )
        assert (
            "ファイル操作エラー (read): /path/to/file.pdf - ファイルが見つかりません"
            in str(exception)
        )
        assert exception.error_code == "INF-004"

    def test_storage_exception(self):
        """ストレージ例外のテスト"""
        exception = StorageException(
            "GCS",
            "upload",
            "document.pdf",
            "バケットが見つかりません",
            bucket="sagebase-bucket",
        )
        assert (
            "GCSストレージエラー (upload): document.pdf - バケットが見つかりません"
            in str(exception)
        )
        assert exception.error_code == "INF-005"
        assert exception.details["bucket"] == "sagebase-bucket"

    def test_network_exception(self):
        """ネットワーク例外のテスト"""
        exception = NetworkException(
            "GET",
            "https://api.example.com/data",
            "タイムアウト",
            timeout=30,
            retry_count=3,
        )
        assert (
            "ネットワークエラー (GET): https://api.example.com/data - タイムアウト"
            in str(exception)
        )
        assert exception.error_code == "INF-007"
        assert exception.details["timeout"] == 30
        assert exception.details["retry_count"] == 3

    def test_timeout_exception(self):
        """タイムアウト例外のテスト"""
        exception = TimeoutException("database_query", 30, resource="users_table")
        expected_message = (
            "操作 'database_query' がタイムアウトしました (30秒) - "
            "リソース: users_table"
        )
        assert expected_message in str(exception)
        assert exception.error_code == "INF-009"

    def test_rate_limit_exception(self):
        """レート制限例外のテスト"""
        exception = RateLimitException(
            "Gemini API", 1000, reset_at="2024-01-01T12:00:00Z", retry_after=60
        )
        assert "サービス 'Gemini API' のレート制限に達しました (制限: 1000)" in str(
            exception
        )
        assert exception.error_code == "INF-010"
        assert exception.details["retry_after"] == 60
