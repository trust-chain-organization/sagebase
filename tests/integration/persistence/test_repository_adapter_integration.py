"""
Repository Adapter 統合テスト

Issue #839: async/await バグ再発防止のための統合テスト

このテストファイルは、RepositoryAdapter の実際の挙動を検証します：
1. 非同期コンテキストでの正しい動作
2. 同期コンテキストでの正しい動作
3. トランザクション管理の動作

重要: このテストでは実際のデータベースを使用しますが、LLMは使用しません。
"""

import os

from datetime import UTC, date, datetime

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.domain.entities.meeting import Meeting
from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


# Skip all tests in this module if NOT running in CI environment
# CI環境でのみ実行（ローカルではデータベースポート設定が異なるため）
pytestmark = pytest.mark.skipif(
    os.getenv("CI") != "true",
    reason="Integration tests require database connection available in CI only",
)


# ============================================================================
# テストフィクスチャー
# ============================================================================


@pytest.fixture(scope="function")
def test_db_session():
    """テスト用のデータベースセッションを作成

    各テストの前後でデータベースをクリーンアップします。
    """
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    # 既存のテストデータをクリーンアップ（TRUNCATEは重いのでDELETEを使用）
    try:
        session.execute(text("DELETE FROM meetings WHERE id > 0"))
        session.commit()
    except Exception as e:
        print(f"Cleanup failed (setup): {e}")
        session.rollback()

    yield session

    # テストデータを削除（クリーンアップ）
    try:
        session.execute(text("DELETE FROM meetings WHERE id > 0"))
        session.commit()
    except Exception as e:
        print(f"Cleanup failed (teardown): {e}")
        session.rollback()

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def sample_meeting():
    """テスト用のサンプルMeetingエンティティ"""
    meeting = Meeting(
        conference_id=1,
        date=date(2024, 1, 15),
        url="https://example.com/test-meeting.html",
        name="統合テスト用会議",
        gcs_pdf_uri=None,
        gcs_text_uri=None,
    )
    meeting.created_at = datetime.now(UTC)
    meeting.updated_at = datetime.now(UTC)
    return meeting


# ============================================================================
# 非同期コンテキストでの統合テスト
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_adapter_async_create_and_retrieve(
    test_db_session, sample_meeting
):
    """非同期コンテキストで RepositoryAdapter を使用: 作成と取得

    Issue #839: 実際の RepositoryAdapter の挙動を検証。
    モックではなく、実際のデータベースを使用します。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        # 作成 (await 必須)
        created = await repo.create(sample_meeting)

        assert created is not None
        assert created.id is not None
        assert created.name == "統合テスト用会議"
        assert created.url == "https://example.com/test-meeting.html"

        # 取得 (await 必須)
        retrieved = await repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.url == created.url

    finally:
        repo.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_adapter_async_update(test_db_session, sample_meeting):
    """非同期コンテキストで RepositoryAdapter を使用: 更新

    Issue #839: 更新操作でも await が必要であることを確認。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        # 作成
        created = await repo.create(sample_meeting)
        original_name = created.name

        # 更新
        created.name = "更新後の会議名"
        updated = await repo.update(created)

        assert updated.name == "更新後の会議名"
        assert updated.name != original_name

        # 取得して確認
        retrieved = await repo.get_by_id(created.id)
        assert retrieved.name == "更新後の会議名"

    finally:
        repo.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_adapter_async_delete(test_db_session, sample_meeting):
    """非同期コンテキストで RepositoryAdapter を使用: 削除

    Issue #839: 削除操作でも await が必要であることを確認。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        # 作成
        created = await repo.create(sample_meeting)
        meeting_id = created.id

        # 削除
        await repo.delete(meeting_id)

        # 取得して確認（削除されているはず）
        retrieved = await repo.get_by_id(meeting_id)
        assert retrieved is None

    finally:
        repo.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_adapter_async_transaction(test_db_session):
    """非同期コンテキストでトランザクションを使用

    Issue #839: トランザクション内での複数操作を検証。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        async with repo.transaction():
            # トランザクション内で複数の Meeting を作成
            meeting1 = Meeting(
                conference_id=1,
                date=date(2024, 1, 15),
                url="https://example.com/meeting1.html",
                name="会議1",
            )
            meeting1.created_at = datetime.now(UTC)
            meeting1.updated_at = datetime.now(UTC)

            meeting2 = Meeting(
                conference_id=1,
                date=date(2024, 1, 16),
                url="https://example.com/meeting2.html",
                name="会議2",
            )
            meeting2.created_at = datetime.now(UTC)
            meeting2.updated_at = datetime.now(UTC)

            created1 = await repo.create(meeting1)
            created2 = await repo.create(meeting2)

            assert created1.id is not None
            assert created2.id is not None

        # トランザクション外で取得して確認
        retrieved1 = await repo.get_by_id(created1.id)
        retrieved2 = await repo.get_by_id(created2.id)

        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.name == "会議1"
        assert retrieved2.name == "会議2"

    finally:
        repo.close()


# ============================================================================
# 同期コンテキストでの統合テスト
# ============================================================================


@pytest.mark.integration
def test_repository_adapter_sync_create_and_retrieve(test_db_session, sample_meeting):
    """同期コンテキストで RepositoryAdapter を使用: 作成と取得

    Issue #839: RepositoryAdapter は同期コンテキストでも動作する。
    この場合、await は不要で、自動的に同期変換される。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        # 作成 (await なし - 同期コンテキスト)
        created = repo.create(sample_meeting)

        assert created is not None
        assert created.id is not None
        assert created.name == "統合テスト用会議"

        # 取得 (await なし - 同期コンテキスト)
        retrieved = repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    finally:
        repo.close()


@pytest.mark.integration
def test_repository_adapter_sync_with_transaction(test_db_session, sample_meeting):
    """同期コンテキストでトランザクションを使用

    Issue #839: with_transaction メソッドの動作確認。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:

        async def create_meeting():
            """トランザクション内で Meeting を作成する非同期関数"""
            return await repo.create(sample_meeting)

        # with_transaction で非同期関数を実行
        created = repo.with_transaction(create_meeting)

        assert created is not None
        assert created.id is not None

        # 取得して確認
        retrieved = repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id

    finally:
        repo.close()


# ============================================================================
# エラーケースのテスト
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_adapter_async_get_nonexistent(test_db_session):
    """非同期コンテキストで存在しない ID を取得

    Issue #839: エラーケースでも await が正しく動作することを確認。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        # 存在しない ID を取得
        result = await repo.get_by_id(999999)

        # None が返されることを確認
        assert result is None

    finally:
        repo.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_adapter_async_transaction_rollback(test_db_session):
    """トランザクションのロールバック動作を検証

    Issue #839: トランザクション内でエラーが発生した場合、
    ロールバックされることを確認。
    """
    repo = RepositoryAdapter(MeetingRepositoryImpl)

    try:
        with pytest.raises(ValueError):
            async with repo.transaction():
                # Meeting を作成
                meeting = Meeting(
                    conference_id=1,
                    date=date(2024, 1, 15),
                    url="https://example.com/rollback-test.html",
                    name="ロールバックテスト",
                )
                meeting.created_at = datetime.now(UTC)
                meeting.updated_at = datetime.now(UTC)

                await repo.create(meeting)

                # 意図的にエラーを発生させる
                raise ValueError("Test rollback")

        # ロールバックされているため、作成された Meeting は存在しないはず
        # すべての Meeting を取得して確認
        all_meetings = await repo.get_all()
        assert len(all_meetings) == 0, "トランザクションがロールバックされているべき"

    finally:
        repo.close()
