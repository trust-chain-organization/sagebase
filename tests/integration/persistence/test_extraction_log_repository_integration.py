"""ExtractionLogRepository 統合テスト

このテストでは、ExtractionLogRepositoryImplの実際のデータベース操作を検証します：
1. CRUD操作の正しい動作
2. 複数エンティティタイプの同時操作
3. 検索・フィルタリング機能
4. パフォーマンス特性の確認

重要: このテストでは実際のデータベースを使用しますが、LLMは使用しません。
"""

# pyright: reportUnknownParameterType=false, reportUnknownArgumentType=false
# pyright: reportMissingParameterType=false, reportArgumentType=false

import os

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


# Skip all tests in this module if NOT running in CI environment
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

    extraction_logsテーブルは外部キー制約がないため、マスターデータ不要。
    各テスト後にクリーンアップを実行。
    """
    engine = create_engine(DATABASE_URL)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    yield session

    # Cleanup: テスト用のデータを削除
    try:
        session.execute(
            text("DELETE FROM extraction_logs WHERE pipeline_version LIKE 'test-%'")
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def repository(test_db_session):
    """テスト用のリポジトリを作成"""
    adapter = RepositoryAdapter(test_db_session)
    return ExtractionLogRepositoryImpl(adapter)


@pytest.fixture
def sample_log() -> ExtractionLog:
    """テスト用のExtractionLogエンティティを作成"""
    return ExtractionLog(
        entity_type=EntityType.SPEAKER,
        entity_id=1,
        pipeline_version="test-v1",
        extracted_data={"name": "テスト太郎", "role": "議員"},
        confidence_score=0.95,
        extraction_metadata={
            "model_name": "gemini-2.0-flash",
            "token_count_input": 100,
            "token_count_output": 50,
            "processing_time_ms": 500,
        },
    )


# ============================================================================
# CRUD操作テスト
# ============================================================================


@pytest.mark.asyncio
async def test_create_and_get_by_id(
    repository: ExtractionLogRepositoryImpl,
    sample_log: ExtractionLog,
):
    """Create操作とGet by ID操作のテスト"""
    # Create
    created_log = await repository.create(sample_log)

    assert created_log.id is not None
    assert created_log.entity_type == sample_log.entity_type
    assert created_log.entity_id == sample_log.entity_id
    assert created_log.pipeline_version == sample_log.pipeline_version
    assert created_log.extracted_data == sample_log.extracted_data
    assert created_log.confidence_score == sample_log.confidence_score
    assert created_log.extraction_metadata == sample_log.extraction_metadata

    # Get by ID
    retrieved_log = await repository.get_by_id(created_log.id)

    assert retrieved_log is not None
    assert retrieved_log.id == created_log.id
    assert retrieved_log.entity_type == created_log.entity_type
    assert retrieved_log.entity_id == created_log.entity_id
    assert retrieved_log.pipeline_version == created_log.pipeline_version


@pytest.mark.asyncio
async def test_get_by_entity(
    repository: ExtractionLogRepositoryImpl,
    sample_log: ExtractionLog,
):
    """特定エンティティのログ取得テスト"""
    # 3つのログを作成
    await repository.create(sample_log)
    log2 = ExtractionLog(
        entity_type=EntityType.SPEAKER,
        entity_id=1,
        pipeline_version="test-v2",
        extracted_data={"name": "テスト太郎", "role": "議員", "updated": True},
        confidence_score=0.98,
        extraction_metadata={},
    )
    await repository.create(log2)

    # 別のエンティティIDのログ
    log3 = ExtractionLog(
        entity_type=EntityType.SPEAKER,
        entity_id=2,
        pipeline_version="test-v1",
        extracted_data={"name": "テスト花子", "role": "議員"},
        confidence_score=0.90,
        extraction_metadata={},
    )
    await repository.create(log3)

    # entity_id=1のログを取得
    logs = await repository.get_by_entity(EntityType.SPEAKER, 1)

    assert len(logs) == 2
    assert all(log.entity_id == 1 for log in logs)
    assert all(log.entity_type == EntityType.SPEAKER for log in logs)
    # 降順でソートされていることを確認
    assert logs[0].created_at is not None and logs[1].created_at is not None
    assert logs[0].created_at >= logs[1].created_at


@pytest.mark.asyncio
async def test_get_latest_by_entity(
    repository: ExtractionLogRepositoryImpl,
    sample_log: ExtractionLog,
):
    """最新ログの取得テスト"""
    # 2つのログを作成（時間差をつける）
    await repository.create(sample_log)

    # 少し待ってから2つ目を作成
    import asyncio

    await asyncio.sleep(0.1)

    log2 = ExtractionLog(
        entity_type=EntityType.SPEAKER,
        entity_id=1,
        pipeline_version="test-v2",
        extracted_data={"name": "テスト太郎", "role": "議員", "updated": True},
        confidence_score=0.98,
        extraction_metadata={},
    )
    latest_created = await repository.create(log2)

    # 最新のログを取得
    latest_log = await repository.get_latest_by_entity(EntityType.SPEAKER, 1)

    assert latest_log is not None
    assert latest_log.id == latest_created.id
    assert latest_log.pipeline_version == "test-v2"


@pytest.mark.asyncio
async def test_get_latest_by_entity_not_found(
    repository: ExtractionLogRepositoryImpl,
):
    """存在しないエンティティの最新ログ取得テスト"""
    latest_log = await repository.get_latest_by_entity(EntityType.SPEAKER, 99999)

    assert latest_log is None


# ============================================================================
# 検索・フィルタリングテスト
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_entity_type(
    repository: ExtractionLogRepositoryImpl,
    sample_log: ExtractionLog,
):
    """エンティティタイプでのフィルタリングテスト"""
    # SPEAKERタイプのログを作成
    await repository.create(sample_log)

    # POLITICIANタイプのログを作成
    politician_log = ExtractionLog(
        entity_type=EntityType.POLITICIAN,
        entity_id=1,
        pipeline_version="test-v1",
        extracted_data={"name": "政治家太郎"},
        confidence_score=0.90,
        extraction_metadata={},
    )
    await repository.create(politician_log)

    # SPEAKERタイプのログを取得
    speaker_logs = await repository.get_by_entity_type(EntityType.SPEAKER)

    assert len(speaker_logs) >= 1
    assert all(log.entity_type == EntityType.SPEAKER for log in speaker_logs)


@pytest.mark.asyncio
async def test_get_by_pipeline_version(
    repository: ExtractionLogRepositoryImpl,
    sample_log: ExtractionLog,
):
    """パイプラインバージョンでのフィルタリングテスト"""
    # test-v1のログを作成
    await repository.create(sample_log)

    # test-v2のログを作成
    log_v2 = ExtractionLog(
        entity_type=EntityType.SPEAKER,
        entity_id=2,
        pipeline_version="test-v2",
        extracted_data={"name": "テスト花子"},
        confidence_score=0.85,
        extraction_metadata={},
    )
    await repository.create(log_v2)

    # test-v1のログを取得
    logs_v1 = await repository.get_by_pipeline_version("test-v1")

    assert len(logs_v1) >= 1
    assert all(log.pipeline_version == "test-v1" for log in logs_v1)


@pytest.mark.asyncio
async def test_search_with_multiple_filters(
    repository: ExtractionLogRepositoryImpl,
):
    """複数条件での検索テスト"""
    # 異なる条件のログを作成
    logs_to_create = [
        ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=1,
            pipeline_version="test-search-v1",
            extracted_data={"name": "高信頼度"},
            confidence_score=0.95,
            extraction_metadata={},
        ),
        ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=2,
            pipeline_version="test-search-v1",
            extracted_data={"name": "低信頼度"},
            confidence_score=0.70,
            extraction_metadata={},
        ),
        ExtractionLog(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            pipeline_version="test-search-v1",
            extracted_data={"name": "政治家"},
            confidence_score=0.90,
            extraction_metadata={},
        ),
    ]

    for log in logs_to_create:
        await repository.create(log)

    # 検索: SPEAKER + min_confidence_score=0.9
    results = await repository.search(
        entity_type=EntityType.SPEAKER,
        pipeline_version="test-search-v1",
        min_confidence_score=0.9,
    )

    assert len(results) == 1
    assert results[0].confidence_score is not None
    assert results[0].confidence_score >= 0.9
    assert results[0].entity_type == EntityType.SPEAKER


# ============================================================================
# カウントテスト
# ============================================================================


@pytest.mark.asyncio
async def test_count_by_entity_type(
    repository: ExtractionLogRepositoryImpl,
):
    """エンティティタイプ別カウントテスト"""
    # SPEAKERタイプのログを2つ作成
    for i in range(2):
        log = ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=i,
            pipeline_version="test-count",
            extracted_data={"index": i},
            confidence_score=0.9,
            extraction_metadata={},
        )
        await repository.create(log)

    count = await repository.count_by_entity_type(EntityType.SPEAKER)

    assert count >= 2


@pytest.mark.asyncio
async def test_count_by_pipeline_version(
    repository: ExtractionLogRepositoryImpl,
):
    """パイプラインバージョン別カウントテスト"""
    # test-count-v1のログを3つ作成
    for i in range(3):
        log = ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=i,
            pipeline_version="test-count-v1",
            extracted_data={"index": i},
            confidence_score=0.9,
            extraction_metadata={},
        )
        await repository.create(log)

    count = await repository.count_by_pipeline_version("test-count-v1")

    assert count == 3


# ============================================================================
# 全エンティティタイプテスト
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entity_type",
    [
        EntityType.STATEMENT,
        EntityType.POLITICIAN,
        EntityType.SPEAKER,
        EntityType.CONFERENCE_MEMBER,
        EntityType.PARLIAMENTARY_GROUP_MEMBER,
    ],
)
async def test_all_entity_types(
    repository: ExtractionLogRepositoryImpl,
    entity_type: EntityType,
):
    """全エンティティタイプでの動作確認"""
    log = ExtractionLog(
        entity_type=entity_type,
        entity_id=1,
        pipeline_version=f"test-{entity_type.value}",
        extracted_data={"test": "data"},
        confidence_score=0.9,
        extraction_metadata={},
    )

    created_log = await repository.create(log)

    assert created_log.id is not None
    assert created_log.entity_type == entity_type

    # 取得確認
    retrieved_log = await repository.get_by_id(created_log.id)
    assert retrieved_log is not None
    assert retrieved_log.entity_type == entity_type


# ============================================================================
# ページネーションテスト
# ============================================================================


@pytest.mark.asyncio
async def test_pagination(
    repository: ExtractionLogRepositoryImpl,
):
    """ページネーション機能のテスト"""
    # 10個のログを作成
    for i in range(10):
        log = ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=i,
            pipeline_version="test-pagination",
            extracted_data={"index": i},
            confidence_score=0.9,
            extraction_metadata={},
        )
        await repository.create(log)

    # 1ページ目（5件）
    page1 = await repository.get_by_pipeline_version(
        "test-pagination", limit=5, offset=0
    )

    # 2ページ目（5件）
    page2 = await repository.get_by_pipeline_version(
        "test-pagination", limit=5, offset=5
    )

    assert len(page1) == 5
    assert len(page2) == 5
    # ページ間で重複がないことを確認
    page1_ids = {log.id for log in page1}
    page2_ids = {log.id for log in page2}
    assert len(page1_ids & page2_ids) == 0
