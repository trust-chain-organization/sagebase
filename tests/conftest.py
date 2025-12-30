"""Shared pytest fixtures."""

import os
import sys

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


# Add project root to Python path to ensure baml_client can be imported
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Debug: Print sys.path during pytest startup
if os.getenv("CI"):
    print("\n" + "=" * 60)
    print("DEBUG: pytest startup - sys.path contents:")
    print("=" * 60)
    for i, path in enumerate(sys.path):
        print(f"{i}: {path}")
    print("=" * 60)
    print(f"DEBUG: project_root = {project_root}")
    baml_client_path = os.path.join(project_root, "baml_client")
    print(f"DEBUG: baml_client directory exists: {os.path.exists(baml_client_path)}")

    # Try importing baml_client
    try:
        from baml_client.async_client import b  # noqa: F401

        print("DEBUG: ✅ baml_client import SUCCESSFUL in conftest.py")
    except Exception as e:
        print(f"DEBUG: ❌ baml_client import FAILED in conftest.py: {e}")
    print("=" * 60 + "\n")

from tests.fixtures.dto_factories import (  # noqa: E402
    create_extracted_speech_dto,
    create_politician_dto,
    create_process_minutes_dto,
    create_speaker_dto,
)
from tests.fixtures.entity_factories import (  # noqa: E402
    create_conference,
    create_conversation,
    create_governing_body,
    create_meeting,
    create_minutes,
    create_parliamentary_group,
    create_political_party,
    create_politician,
    create_speaker,
)

from src.common.metrics import setup_metrics  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_test_metrics():
    """Setup metrics for all test sessions.

    This fixture runs automatically for all tests to ensure metrics
    are initialized before any LLM services are created.
    """
    setup_metrics(
        service_name="sagebase-test",
        service_version="0.1.0",
        enable_prometheus=False,  # Don't start Prometheus server in tests
    )
    yield


# Entity fixtures
@pytest.fixture
def sample_governing_body():
    """Create a sample governing body."""
    return create_governing_body()


@pytest.fixture
def sample_conference():
    """Create a sample conference."""
    return create_conference()


@pytest.fixture
def sample_meeting():
    """Create a sample meeting."""
    return create_meeting()


@pytest.fixture
def sample_minutes():
    """Create a sample minutes."""
    return create_minutes()


@pytest.fixture
def sample_speaker():
    """Create a sample speaker."""
    return create_speaker()


@pytest.fixture
def sample_politician():
    """Create a sample politician."""
    return create_politician()


@pytest.fixture
def sample_political_party():
    """Create a sample political party."""
    return create_political_party()


@pytest.fixture
def sample_conversation():
    """Create a sample conversation."""
    return create_conversation()


@pytest.fixture
def sample_parliamentary_group():
    """Create a sample parliamentary group."""
    return create_parliamentary_group()


# DTO fixtures
@pytest.fixture
def sample_process_minutes_dto():
    """Create a sample ProcessMinutesDTO."""
    return create_process_minutes_dto()


@pytest.fixture
def sample_extracted_speech_dto():
    """Create a sample ExtractedSpeechDTO."""
    return create_extracted_speech_dto()


@pytest.fixture
def sample_speaker_dto():
    """Create a sample SpeakerDTO."""
    return create_speaker_dto()


@pytest.fixture
def sample_politician_dto():
    """Create a sample PoliticianDTO."""
    return create_politician_dto()


# Mock repository fixtures
@pytest.fixture
def mock_base_repository():
    """Create a mock base repository."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    repo.get_all.return_value = []
    repo.create.return_value = None
    repo.update.return_value = None
    repo.delete.return_value = True
    return repo


@pytest.fixture
def mock_speaker_repository(mock_base_repository):
    """Create a mock speaker repository."""
    repo = mock_base_repository
    repo.get_by_name_party_position.return_value = None
    repo.get_politicians.return_value = []
    repo.upsert.return_value = create_speaker()
    return repo


@pytest.fixture
def mock_politician_repository(mock_base_repository):
    """Create a mock politician repository."""
    repo = mock_base_repository
    repo.get_by_speaker_id.return_value = None
    repo.get_by_name_and_party.return_value = None
    repo.get_by_party.return_value = []
    repo.search_by_name.return_value = []
    return repo


@pytest.fixture
def mock_meeting_repository(mock_base_repository):
    """Create a mock meeting repository."""
    repo = mock_base_repository
    repo.get_by_conference.return_value = []
    repo.get_recent.return_value = []
    return repo


@pytest.fixture
def mock_minutes_repository(mock_base_repository):
    """Create a mock minutes repository."""
    repo = mock_base_repository
    repo.get_by_meeting.return_value = None
    repo.mark_processed.return_value = None
    return repo


@pytest.fixture
def mock_conversation_repository(mock_base_repository):
    """Create a mock conversation repository."""
    repo = mock_base_repository
    repo.bulk_create.return_value = []
    repo.get_by_minutes.return_value = []
    repo.update_speaker_links.return_value = 0
    return repo


# Mock service fixtures
@pytest.fixture
def mock_speaker_domain_service():
    """Create a mock speaker domain service."""
    service = MagicMock()
    service.normalize_speaker_name.side_effect = lambda x: x.strip()
    service.extract_party_from_name.return_value = ("山田太郎", None)
    service.calculate_name_similarity.return_value = 0.9
    service.is_likely_politician.return_value = True
    return service


@pytest.fixture
def mock_politician_domain_service():
    """Create a mock politician domain service."""
    service = MagicMock()
    service.normalize_politician_name.side_effect = lambda x: x.strip()
    service.is_duplicate_politician.return_value = None
    service.merge_politician_info.side_effect = lambda x, y: x
    service.validate_politician_data.return_value = []
    return service


@pytest.fixture
def mock_minutes_domain_service():
    """Create a mock minutes domain service."""
    service = MagicMock()
    service.is_minutes_processed.return_value = False
    service.calculate_processing_duration.return_value = 10.0
    service.create_conversations_from_speeches.return_value = []
    service.validate_conversation_sequence.return_value = []
    return service


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = AsyncMock()
    service.match_speaker_to_politician.return_value = {"politician_id": None}
    service.extract_conference_members.return_value = []
    service.scrape_party_members.return_value = []
    return service


# Test data fixtures
@pytest.fixture
def current_datetime():
    """Get current datetime with timezone."""
    return datetime.now(UTC)


@pytest.fixture
def test_speeches():
    """Create test speech data."""
    return [
        {"speaker": "山田太郎", "content": "本日の議題について説明します。"},
        {"speaker": "鈴木花子", "content": "質問があります。"},
        {"speaker": "田中次郎", "content": "賛成です。"},
    ]


# ============================================================================
# LLMモックフィクスチャー（統合テスト用）
# Issue #839: 統合テストで実際のLLMを叩かないためのフィクスチャー
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def set_testing_env():
    """テスト環境フラグを自動設定

    統合テストで実際のLLM APIを呼ばないようにする（マスト要件）。
    """
    os.environ["TESTING"] = "true"
    # ダミーAPIキー（実際には使用されない）
    if "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = "test-api-key-not-used"
    yield
    # クリーンアップ
    if os.environ.get("TESTING") == "true":
        del os.environ["TESTING"]


@pytest.fixture
def mock_gemini_llm_service():
    """統合テスト用のモックGemini LLMサービス

    実際のGemini APIを呼ばず、予測可能な結果を返す。
    Issue #839: LLM APIコストゼロ、テスト高速化。
    """

    mock_service = AsyncMock()

    # 基本的なLLM生成メソッド
    mock_service.generate.return_value = {
        "content": "モックされたLLMレスポンス",
        "role": "assistant",
        "model": "gemini-2.0-flash-mock",
    }

    # 構造化出力メソッド
    mock_service.generate_structured.return_value = {
        "members": [
            {"name": "テスト議員1", "role": "議長", "party_name": "テスト党"},
            {"name": "テスト議員2", "role": "議員", "party_name": "テスト党"},
        ]
    }

    # 話者マッチングメソッド
    mock_service.match_speaker_to_politician.return_value = {
        "politician_id": 1,
        "confidence": 0.95,
        "reason": "完全一致",
    }

    return mock_service


@pytest.fixture(scope="session")
def mock_baml_client():
    """BAML クライアントをモック（統合テスト用）

    実際のLLM APIコールを完全に防ぐ。
    必要なテストで明示的に使用する。

    Issue #839: 統合テストでLLMを絶対に叩かない（マスト要件）

    注: autouse=True を削除したため、このフィクスチャーが必要なテストは
    明示的に引数として受け取る必要があります。
    BAML生成コードの構造テスト（シグネチャやasync確認）には影響しません。
    """
    from unittest.mock import AsyncMock, patch

    # BAML関数のモックレスポンス
    mock_responses = {
        "ExtractMembers": [
            {"name": "テスト議員1", "role": "議長", "party_name": "テスト党"},
            {"name": "テスト議員2", "role": "議員", "party_name": "テスト党"},
        ],
        "ExtractSpeeches": [
            {"speaker": "テスト議員1", "content": "テスト発言1"},
            {"speaker": "テスト議員2", "content": "テスト発言2"},
        ],
        "MatchSpeaker": {
            "politician_id": 1,
            "confidence": 0.95,
            "reason": "モックマッチング",
        },
        "DivideMinutes": {
            "sections": [
                {"title": "議事開始", "content": "テスト議事録セクション1"},
                {"title": "質疑応答", "content": "テスト議事録セクション2"},
            ]
        },
    }

    # BAML クライアントをパッチ
    with patch("baml_client.async_client.b") as mock_b:
        # 各BAML関数をモック
        for func_name, response in mock_responses.items():
            mock_func = AsyncMock(return_value=response)
            setattr(mock_b, func_name, mock_func)

        yield mock_b


@pytest.fixture(scope="function", autouse=True)
def assert_no_real_llm_call(monkeypatch, request):
    """実際のLLM APIコールが発生していないことを検証するフィクスチャー

    Issue #839: 統合テストでLLMを絶対に叩かない（マスト要件）

    統合テストで自動的に有効化され、実際のLLM APIコールを検出・ブロックします。
    単体テストでは無効化されます。

    使用例:
        @pytest.mark.integration
        async def test_something():
            # 実際のLLM APIコールがあれば自動的にエラー
            result = await some_function()
    """
    import httpx

    # 単体テストではスキップ（integrationマーカーがある場合のみ有効化）
    if "integration" not in request.keywords:
        yield
        return

    original_post = httpx.AsyncClient.post
    call_count = {"count": 0}

    async def patched_post(self, url, *args, **kwargs):
        # Gemini APIへのコールを検出
        if "generativelanguage.googleapis.com" in str(url):
            call_count["count"] += 1
            raise AssertionError(
                f"実際のLLM APIコールが検出されました！ URL: {url}\n"
                "統合テストでは実際のLLMを叩いてはいけません（マスト要件）。\n"
                "mock_gemini_llm_service または mock_baml_client を使用してください。"
            )
        return await original_post(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "post", patched_post)

    yield

    # テスト終了後、カウントを確認
    assert call_count["count"] == 0, (
        f"統合テスト中に {call_count['count']} 回のLLM APIコールが検出されました！"
    )
