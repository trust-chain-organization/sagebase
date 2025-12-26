"""本番環境デプロイの統合テスト.

このテストは本番環境にデプロイされたサービスの動作を確認します。
外部サービス（Cloud SQL, GCS, Vertex AI）は実際のサービスを使用します。

注意:
- CI環境では pytest -m "not production" でスキップ可能
- 本番環境のテストはコストが発生するため、必要な時のみ実行
- 環境変数で本番環境の設定が必要
"""

import os

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from google.cloud import storage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


# 本番環境テストのマーカー
pytestmark = pytest.mark.production


@pytest.fixture(scope="session")
def is_production_env() -> bool:
    """本番環境かどうかを判定."""
    return (
        os.getenv("ENVIRONMENT") == "production"
        or os.getenv("RUN_PRODUCTION_TESTS") == "true"
    )


@pytest.fixture(scope="session")
def skip_if_not_production(is_production_env: bool) -> None:
    """本番環境でない場合はテストをスキップ."""
    if not is_production_env:
        pytest.skip(
            "本番環境テストはスキップされました"
            "（ENVIRONMENT=production または RUN_PRODUCTION_TESTS=true が必要）"
        )


@pytest.fixture(scope="session")
def project_id() -> str:
    """GCPプロジェクトID."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
    if not project_id:
        pytest.skip(
            "GCPプロジェクトIDが設定されていません"
            "（GOOGLE_CLOUD_PROJECT または PROJECT_ID が必要）"
        )
    return project_id


@pytest.fixture(scope="session")
def database_url() -> str:
    """データベース接続URL.

    本番環境ではCloud SQL Proxy経由で接続します。
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Cloud SQL Proxy経由の接続URLを構築
        use_cloud_sql_proxy = (
            os.getenv("USE_CLOUD_SQL_PROXY", "false").lower() == "true"
        )
        if use_cloud_sql_proxy:
            connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME")
            db_user = os.getenv("DB_USER", "sagebase_user")
            db_password = os.getenv("DB_PASSWORD")
            db_name = os.getenv("DB_NAME", "sagebase_db")
            socket_dir = os.getenv("CLOUD_SQL_UNIX_SOCKET_DIR", "/cloudsql")

            if not all([connection_name, db_password]):
                pytest.skip("Cloud SQL接続情報が不足しています")

            db_url = f"postgresql+asyncpg://{db_user}:{db_password}@/{db_name}?host={socket_dir}/{connection_name}"
        else:
            pytest.skip("DATABASE_URLが設定されていません")

    return db_url


@pytest_asyncio.fixture
async def db_session(
    database_url: str, skip_if_not_production: None
) -> AsyncGenerator[AsyncSession]:
    """データベースセッション."""
    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()

    await engine.dispose()


@pytest.fixture(scope="session")
def gcs_client(project_id: str, skip_if_not_production: None) -> storage.Client:
    """GCSクライアント."""
    return storage.Client(project=project_id)


@pytest.fixture(scope="session")
def minutes_bucket_name(project_id: str) -> str:
    """議事録用GCSバケット名."""
    environment = os.getenv("ENVIRONMENT", "production")
    return f"{project_id}-sagebase-minutes-{environment}"


class TestDatabaseConnectivity:
    """データベース接続性のテスト."""

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session: AsyncSession) -> None:
        """データベースに接続できることを確認."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_database_version(self, db_session: AsyncSession) -> None:
        """PostgreSQLバージョンを確認."""
        result = await db_session.execute(text("SELECT version()"))
        version = result.scalar()
        assert version is not None
        assert "PostgreSQL 15" in version

    @pytest.mark.asyncio
    async def test_governing_bodies_table_exists(
        self, db_session: AsyncSession
    ) -> None:
        """governing_bodiesテーブルが存在することを確認."""
        result = await db_session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'governing_bodies'
                )
                """
            )
        )
        assert result.scalar() is True

    @pytest.mark.asyncio
    async def test_master_data_loaded(
        self, db_session: AsyncSession, skip_if_not_production: None
    ) -> None:
        """マスターデータ（governing_bodies）がロードされていることを確認."""
        result = await db_session.execute(text("SELECT COUNT(*) FROM governing_bodies"))
        count = result.scalar()
        assert count is not None, "governing_bodiesのカウントが取得できません"
        assert count > 0, "governing_bodiesテーブルにデータが存在しません"


class TestGCSConnectivity:
    """GCS接続性のテスト."""

    def test_gcs_client_authentication(
        self, gcs_client: storage.Client, project_id: str
    ) -> None:
        """GCSクライアントが認証されていることを確認."""
        # プロジェクト情報を取得できることで認証を確認
        assert gcs_client.project == project_id

    def test_minutes_bucket_exists(
        self, gcs_client: storage.Client, minutes_bucket_name: str
    ) -> None:
        """議事録用バケットが存在することを確認."""
        bucket = gcs_client.bucket(minutes_bucket_name)
        assert bucket.exists(), f"バケット {minutes_bucket_name} が存在しません"

    def test_minutes_bucket_accessible(
        self, gcs_client: storage.Client, minutes_bucket_name: str
    ) -> None:
        """議事録用バケットにアクセスできることを確認."""
        bucket = gcs_client.bucket(minutes_bucket_name)
        # バケットのメタデータを取得できることでアクセス権限を確認
        bucket.reload()
        assert bucket.storage_class in ["STANDARD", "NEARLINE", "COLDLINE"]


class TestVertexAIAccess:
    """Vertex AI APIアクセスのテスト."""

    def test_vertex_ai_import(self, skip_if_not_production: None) -> None:
        """Vertex AI SDKをインポートできることを確認."""
        try:
            from google.cloud import aiplatform  # noqa: F401

            assert True
        except ImportError:
            pytest.fail("Vertex AI SDKがインポートできません")

    def test_vertex_ai_project_config(
        self, project_id: str, skip_if_not_production: None
    ) -> None:
        """Vertex AIのプロジェクト設定を確認."""
        from google.cloud import aiplatform

        # プロジェクトIDとロケーションの設定
        location = os.getenv("VERTEX_AI_LOCATION", "asia-northeast1")
        aiplatform.init(project=project_id, location=location)

        # 設定が正しく適用されているか確認
        assert aiplatform.initializer.global_config.project == project_id
        assert aiplatform.initializer.global_config.location == location


class TestApplicationEndpoints:
    """アプリケーションエンドポイントのテスト."""

    @pytest.fixture(scope="class")
    def service_url(self) -> str:
        """Cloud RunサービスのURL."""
        service_url = os.getenv("SERVICE_URL")
        if not service_url:
            pytest.skip("SERVICE_URLが設定されていません")
        return service_url.rstrip("/")

    def test_health_endpoint(
        self, service_url: str, skip_if_not_production: None
    ) -> None:
        """ヘルスチェックエンドポイントが応答することを確認."""
        import requests

        response = requests.get(f"{service_url}/_stcore/health", timeout=10)
        assert response.status_code == 200

    def test_root_endpoint(
        self, service_url: str, skip_if_not_production: None
    ) -> None:
        """ルートエンドポイントが応答することを確認."""
        import requests

        response = requests.get(service_url, timeout=30)
        assert response.status_code in [200, 302], (
            f"予期しないステータスコード: {response.status_code}"
        )


class TestPerformance:
    """パフォーマンステスト."""

    @pytest.fixture(scope="class")
    def service_url(self) -> str:
        """Cloud RunサービスのURL."""
        service_url = os.getenv("SERVICE_URL")
        if not service_url:
            pytest.skip("SERVICE_URLが設定されていません")
        return service_url.rstrip("/")

    def test_response_time(
        self, service_url: str, skip_if_not_production: None
    ) -> None:
        """レスポンスタイムが許容範囲内であることを確認.

        初回アクセスはコールドスタートのため遅い可能性があるため、
        2回目のアクセスで確認します。
        """
        import time

        import requests

        # ウォームアップリクエスト
        requests.get(f"{service_url}/_stcore/health", timeout=30)
        time.sleep(1)

        # 実際の測定
        start_time = time.time()
        response = requests.get(f"{service_url}/_stcore/health", timeout=10)
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        # ヘルスチェックエンドポイントは3秒以内に応答すべき
        assert elapsed_time < 3.0, f"レスポンスタイムが遅すぎます: {elapsed_time:.2f}秒"

    @pytest.mark.asyncio
    async def test_database_query_performance(
        self, db_session: AsyncSession, skip_if_not_production: None
    ) -> None:
        """データベースクエリのパフォーマンスを確認."""
        import time

        # シンプルなクエリの実行時間を測定
        start_time = time.time()
        await db_session.execute(text("SELECT COUNT(*) FROM governing_bodies"))
        elapsed_time = time.time() - start_time

        # 単純なCOUNTクエリは1秒以内に完了すべき
        assert elapsed_time < 1.0, (
            f"データベースクエリが遅すぎます: {elapsed_time:.2f}秒"
        )


class TestDataIntegrity:
    """データ整合性のテスト."""

    @pytest.mark.asyncio
    async def test_referential_integrity(
        self, db_session: AsyncSession, skip_if_not_production: None
    ) -> None:
        """外部キー制約が正しく設定されていることを確認."""
        # conferences テーブルは governing_body_id を持つ
        result = await db_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_type = 'FOREIGN KEY'
                AND table_name = 'conferences'
                """
            )
        )
        fk_count = result.scalar()
        assert fk_count is not None, "外部キー制約のカウントが取得できません"
        assert fk_count > 0, "conferencesテーブルに外部キー制約が設定されていません"

    @pytest.mark.asyncio
    async def test_unique_constraints(
        self, db_session: AsyncSession, skip_if_not_production: None
    ) -> None:
        """ユニーク制約が正しく設定されていることを確認."""
        # governing_bodies の organization_code はユニークであるべき
        result = await db_session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_type = 'UNIQUE'
                AND table_name = 'governing_bodies'
                """
            )
        )
        unique_count = result.scalar()
        assert unique_count is not None, "ユニーク制約のカウントが取得できません"
        assert unique_count > 0, (
            "governing_bodiesテーブルにユニーク制約が設定されていません"
        )


if __name__ == "__main__":
    # ローカルでの実行用
    pytest.main([__file__, "-v", "-s", "-m", "production"])
