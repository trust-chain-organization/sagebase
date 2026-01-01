"""ExecuteMinutesProcessingUseCaseのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
    ExecuteMinutesProcessingUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.infrastructure.exceptions import APIKeyError


@pytest.fixture
def mock_unit_of_work():
    """モックUnit of Workのフィクスチャ"""
    uow = AsyncMock()
    uow.meeting_repository = AsyncMock()
    uow.minutes_repository = AsyncMock()
    uow.conversation_repository = AsyncMock()
    uow.speaker_repository = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.flush = AsyncMock()
    return uow


@pytest.fixture
def mock_services():
    """モックサービスのフィクスチャ"""
    speaker_service = MagicMock()
    # Issue #865: extract_party_from_nameメソッドのモック設定
    speaker_service.extract_party_from_name.return_value = ("テスト太郎", "テスト党")

    return {
        "speaker_service": speaker_service,
        "minutes_processing_service": AsyncMock(),
        "storage_service": AsyncMock(),
    }


@pytest.fixture
def use_case(mock_unit_of_work, mock_services):
    """ユースケースのフィクスチャ"""
    # Issue #865: update_statement_usecaseモックを追加
    mock_update_statement_usecase = AsyncMock()
    mock_update_statement_usecase.execute = AsyncMock()

    return ExecuteMinutesProcessingUseCase(
        speaker_domain_service=mock_services["speaker_service"],
        minutes_processing_service=mock_services["minutes_processing_service"],
        storage_service=mock_services["storage_service"],
        unit_of_work=mock_unit_of_work,
        update_statement_usecase=mock_update_statement_usecase,
    )


@pytest.fixture
def sample_meeting():
    """サンプル会議エンティティ"""
    return Meeting(
        id=1,
        conference_id=1,
        date=datetime(2024, 1, 1),
        url="https://example.com",
        gcs_text_uri="gs://bucket/text.txt",
        gcs_pdf_uri=None,
    )


@pytest.fixture
def sample_minutes():
    """サンプル議事録エンティティ"""
    return Minutes(
        id=1,
        meeting_id=1,
        url="https://example.com",
    )


@pytest.mark.asyncio
async def test_execute_success(
    use_case, mock_unit_of_work, mock_services, sample_meeting, sample_minutes
):
    """正常に議事録処理が実行されることをテスト"""
    # モックの設定
    mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
    mock_unit_of_work.minutes_repository.get_by_meeting.return_value = None
    mock_unit_of_work.minutes_repository.create.return_value = sample_minutes
    mock_unit_of_work.conversation_repository.get_by_minutes.return_value = []

    # Storage serviceをモック - download_file returns bytes
    mock_services[
        "storage_service"
    ].download_file.return_value = "議事録テキスト".encode()

    # MinutesProcessingServiceをモック - ドメイン値オブジェクトを返す
    mock_services["minutes_processing_service"].process_minutes.return_value = [
        SpeakerSpeech(speaker="田中太郎", speech_content="発言1"),
        SpeakerSpeech(speaker="山田花子", speech_content="発言2"),
    ]

    # Conversationのバルク作成をモック
    created_conversations = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="田中太郎",
            comment="発言1",
            sequence_number=1,
        ),
        Conversation(
            id=2,
            minutes_id=1,
            speaker_name="山田花子",
            comment="発言2",
            sequence_number=2,
        ),
    ]
    mock_unit_of_work.conversation_repository.bulk_create.return_value = (
        created_conversations
    )

    # Speakerの作成をモック
    # Issue #865: 両メソッドで呼ばれるため4回分設定
    mock_services["speaker_service"].extract_party_from_name.side_effect = [
        ("田中太郎", "自民党"),  # _save_conversations 1回目
        ("山田花子", "立憲民主党"),  # _save_conversations 2回目
        ("田中太郎", "自民党"),  # _extract_and_create_speakers 1回目
        ("山田花子", "立憲民主党"),  # _extract_and_create_speakers 2回目
    ]
    mock_unit_of_work.speaker_repository.get_by_name_party_position.return_value = None
    mock_unit_of_work.speaker_repository.create.return_value = Mock()

    # 実行
    request = ExecuteMinutesProcessingDTO(meeting_id=1)
    result = await use_case.execute(request)

    # 検証
    assert result.meeting_id == 1
    assert result.minutes_id == 1
    assert result.total_conversations == 2
    assert result.unique_speakers == 2
    assert result.processing_time_seconds > 0
    assert result.errors is None

    # リポジトリメソッドが呼ばれたことを確認
    mock_unit_of_work.meeting_repository.get_by_id.assert_called_once_with(1)
    mock_unit_of_work.minutes_repository.create.assert_called_once()
    mock_unit_of_work.conversation_repository.bulk_create.assert_called_once()
    assert mock_unit_of_work.speaker_repository.create.call_count == 2
    # Unit of Workのcommitが呼ばれたことを確認
    mock_unit_of_work.commit.assert_called_once()
    mock_unit_of_work.flush.assert_called_once()


@pytest.mark.asyncio
async def test_execute_meeting_not_found(use_case, mock_unit_of_work):
    """会議が見つからない場合のエラーテスト"""
    # モックの設定
    mock_unit_of_work.meeting_repository.get_by_id.return_value = None

    # 実行と検証
    request = ExecuteMinutesProcessingDTO(meeting_id=999)
    with pytest.raises(ValueError, match="Meeting 999 not found"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_execute_already_has_conversations(
    use_case, mock_unit_of_work, sample_meeting, sample_minutes
):
    """既にConversationsが存在する場合のエラーテスト"""
    # モックの設定
    mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
    mock_unit_of_work.minutes_repository.get_by_meeting.return_value = sample_minutes
    mock_unit_of_work.conversation_repository.get_by_minutes.return_value = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="既存の発言者",
            comment="既存の発言",
            sequence_number=1,
        )
    ]

    # 実行と検証
    request = ExecuteMinutesProcessingDTO(meeting_id=1, force_reprocess=False)
    with pytest.raises(ValueError, match="already has conversations"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_execute_force_reprocess(
    use_case, mock_unit_of_work, mock_services, sample_meeting, sample_minutes
):
    """強制再処理の場合、既存のConversationsがあっても処理されることをテスト"""
    # モックの設定
    mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
    mock_unit_of_work.minutes_repository.get_by_meeting.return_value = sample_minutes
    mock_unit_of_work.conversation_repository.get_by_minutes.return_value = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="既存の発言者",
            comment="既存の発言",
            sequence_number=1,
        )
    ]

    # Storage serviceをモック - download_file returns bytes
    mock_services[
        "storage_service"
    ].download_file.return_value = "議事録テキスト".encode()

    # MinutesProcessingServiceをモック
    mock_services["minutes_processing_service"].process_minutes.return_value = []

    mock_unit_of_work.conversation_repository.bulk_create.return_value = []

    # 実行
    request = ExecuteMinutesProcessingDTO(meeting_id=1, force_reprocess=True)
    result = await use_case.execute(request)

    # 検証
    assert result.meeting_id == 1
    assert result.total_conversations == 0


@pytest.mark.asyncio
async def test_execute_no_gcs_uri(use_case, mock_unit_of_work):
    """GCS URIがない場合のエラーテスト"""
    # モックの設定
    meeting_without_gcs = Meeting(
        id=1,
        conference_id=1,
        date=datetime(2024, 1, 1),
        url="https://example.com",
        gcs_text_uri=None,
        gcs_pdf_uri=None,
    )
    mock_unit_of_work.meeting_repository.get_by_id.return_value = meeting_without_gcs
    mock_unit_of_work.minutes_repository.get_by_meeting.return_value = None

    # 実行と検証
    request = ExecuteMinutesProcessingDTO(meeting_id=1)
    with pytest.raises(ValueError, match="No valid source found"):
        await use_case.execute(request)


@pytest.mark.skip(
    reason="Legacy test - API key validation no longer happens in UseCase layer. "
    "LLM service handles API key validation internally."
)
@pytest.mark.asyncio
async def test_execute_api_key_not_set(use_case, mock_repositories, sample_meeting):
    """APIキーが設定されていない場合のエラーテスト"""
    # モックの設定
    mock_repositories["meeting_repo"].get_by_id.return_value = sample_meeting
    mock_repositories["minutes_repo"].get_by_meeting.return_value = None
    mock_repositories["minutes_repo"].create.return_value = Minutes(
        id=1, meeting_id=1, url="https://example.com"
    )

    # Storage serviceをモック - download_file returns bytes
    mock_repositories[
        "storage_service"
    ].download_file.return_value = "議事録テキスト".encode()

    # 環境変数をモック（APIキーなし）
    with patch.dict("os.environ", {}, clear=True):
        # 実行と検証
        request = ExecuteMinutesProcessingDTO(meeting_id=1)
        with pytest.raises(APIKeyError, match="GOOGLE_API_KEY not set"):
            await use_case.execute(request)


@pytest.mark.asyncio
async def test_extract_and_create_speakers(use_case, mock_unit_of_work, mock_services):
    """発言者の抽出と作成のテスト"""
    # テストデータ
    conversations = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="田中太郎（自民党）",
            comment="発言1",
            sequence_number=1,
        ),
        Conversation(
            id=2,
            minutes_id=1,
            speaker_name="山田花子",
            comment="発言2",
            sequence_number=2,
        ),
        Conversation(
            id=3,
            minutes_id=1,
            speaker_name="田中太郎（自民党）",  # 重複
            comment="発言3",
            sequence_number=3,
        ),
    ]

    # モックの設定
    mock_services["speaker_service"].extract_party_from_name.side_effect = [
        ("田中太郎", "自民党"),
        ("山田花子", None),
        ("田中太郎", "自民党"),  # 重複
    ]
    mock_unit_of_work.speaker_repository.get_by_name_party_position.return_value = None

    # 実行
    created_count = await use_case._extract_and_create_speakers(conversations)

    # 検証
    assert created_count == 2  # 重複を除いた数
    assert mock_unit_of_work.speaker_repository.create.call_count == 2
