"""ExecuteMinutesProcessingUseCaseのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.application.dtos.role_name_mapping_dto import (
    RoleNameMappingDTO,
    RoleNameMappingResultDTO,
)
from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
    ExecuteMinutesProcessingUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.infrastructure.exceptions import APIKeyError
from src.minutes_divide_processor.models import MinutesBoundary


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


@pytest.fixture
def use_case_with_role_mapping(mock_unit_of_work, mock_services):
    """役職-人名マッピングサービス付きユースケースのフィクスチャ"""
    mock_update_statement_usecase = AsyncMock()
    mock_update_statement_usecase.execute = AsyncMock()

    mock_role_name_mapping_service = AsyncMock()

    # minutes_divider_serviceはAsyncMockとMagicMockのハイブリッド
    # detect_attendee_boundaryはasync、split_minutes_by_boundaryは同期
    mock_minutes_divider_service = MagicMock()
    mock_minutes_divider_service.detect_attendee_boundary = AsyncMock()
    mock_minutes_divider_service.split_minutes_by_boundary = MagicMock()

    return ExecuteMinutesProcessingUseCase(
        speaker_domain_service=mock_services["speaker_service"],
        minutes_processing_service=mock_services["minutes_processing_service"],
        storage_service=mock_services["storage_service"],
        unit_of_work=mock_unit_of_work,
        update_statement_usecase=mock_update_statement_usecase,
        role_name_mapping_service=mock_role_name_mapping_service,
        minutes_divider_service=mock_minutes_divider_service,
    )


@pytest.mark.asyncio
async def test_extract_role_name_mappings_success(use_case_with_role_mapping):
    """役職-人名マッピング抽出が正常に動作することをテスト"""
    # モックの設定
    mock_boundary = MinutesBoundary(
        boundary_found=True,
        boundary_text="出席者一覧｜境界｜○議長 発言開始",
        boundary_type="separator_line",
        confidence=0.9,
        reason="セパレータラインが検出されました",
    )
    divider = use_case_with_role_mapping.minutes_divider_service
    divider.detect_attendee_boundary.return_value = mock_boundary
    divider.split_minutes_by_boundary.return_value = (
        "出席者一覧テキスト",
        "発言テキスト",
    )

    mock_mapping_result = RoleNameMappingResultDTO(
        mappings=[
            RoleNameMappingDTO(role="議長", name="伊藤条一"),
            RoleNameMappingDTO(role="副議長", name="梶谷大志"),
        ],
        attendee_section_found=True,
        confidence=0.95,
    )
    mapping_svc = use_case_with_role_mapping.role_name_mapping_service
    mapping_svc.extract_role_name_mapping.return_value = mock_mapping_result

    # 実行
    result = await use_case_with_role_mapping._extract_role_name_mappings(
        "テスト議事録テキスト"
    )

    # 検証
    assert result is not None
    assert "議長" in result
    assert result["議長"] == "伊藤条一"
    assert result["副議長"] == "梶谷大志"


@pytest.mark.asyncio
async def test_extract_role_name_mappings_no_service(use_case):
    """役職-人名マッピングサービスが設定されていない場合はNoneを返すことをテスト"""
    # サービスが設定されていないuse_caseを使用
    result = await use_case._extract_role_name_mappings("テスト議事録テキスト")

    # 検証
    assert result is None


@pytest.mark.asyncio
async def test_extract_role_name_mappings_empty_text(use_case_with_role_mapping):
    """空のテキストの場合はNoneを返すことをテスト"""
    # 実行
    result = await use_case_with_role_mapping._extract_role_name_mappings("")

    # 検証
    assert result is None


@pytest.mark.asyncio
async def test_extract_role_name_mappings_no_boundary(use_case_with_role_mapping):
    """境界が見つからない場合もマッピング抽出を試みることをテスト"""
    # モックの設定（境界が見つからない）
    mock_boundary = MinutesBoundary(
        boundary_found=False,
        boundary_text=None,
        boundary_type="none",
        confidence=0.0,
        reason="境界が検出されませんでした",
    )
    divider = use_case_with_role_mapping.minutes_divider_service
    divider.detect_attendee_boundary.return_value = mock_boundary

    # マッピング抽出結果
    mock_mapping_result = RoleNameMappingResultDTO(
        mappings=[RoleNameMappingDTO(role="議長", name="田中太郎")],
        attendee_section_found=True,
        confidence=0.8,
    )
    mapping_svc = use_case_with_role_mapping.role_name_mapping_service
    mapping_svc.extract_role_name_mapping.return_value = mock_mapping_result

    # 実行
    result = await use_case_with_role_mapping._extract_role_name_mappings(
        "テスト議事録テキスト"
    )

    # 検証
    assert result is not None
    assert result["議長"] == "田中太郎"


@pytest.mark.asyncio
async def test_execute_with_role_name_mappings(
    use_case_with_role_mapping, mock_unit_of_work, mock_services, sample_meeting
):
    """役職-人名マッピングが議事録処理時に抽出・保存されることをテスト"""
    # モックの設定
    mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
    mock_unit_of_work.minutes_repository.get_by_meeting.return_value = None
    mock_unit_of_work.conversation_repository.get_by_minutes.return_value = []

    # Storage serviceをモック
    mock_services[
        "storage_service"
    ].download_file.return_value = "議事録テキスト".encode()

    # MinutesProcessingServiceをモック
    mock_services["minutes_processing_service"].process_minutes.return_value = []
    mock_unit_of_work.conversation_repository.bulk_create.return_value = []

    # 役職-人名マッピング抽出をモック
    mock_boundary = MinutesBoundary(
        boundary_found=True,
        boundary_text="出席者一覧｜境界｜○議長",
        boundary_type="separator_line",
        confidence=0.9,
        reason="test",
    )
    divider = use_case_with_role_mapping.minutes_divider_service
    divider.detect_attendee_boundary.return_value = mock_boundary
    divider.split_minutes_by_boundary.return_value = (
        "出席者一覧テキスト",
        "発言テキスト",
    )
    mock_mapping_result = RoleNameMappingResultDTO(
        mappings=[RoleNameMappingDTO(role="議長", name="伊藤条一")],
        attendee_section_found=True,
        confidence=0.95,
    )
    mapping_svc = use_case_with_role_mapping.role_name_mapping_service
    mapping_svc.extract_role_name_mapping.return_value = mock_mapping_result

    # Minutes作成時にrole_name_mappingsが含まれることを確認
    created_minutes = Minutes(id=1, meeting_id=1, url="https://example.com")
    mock_unit_of_work.minutes_repository.create.return_value = created_minutes

    # 実行
    request = ExecuteMinutesProcessingDTO(meeting_id=1)
    result = await use_case_with_role_mapping.execute(request)

    # 検証
    assert result.meeting_id == 1
    # minutes_repository.createが呼ばれたことを確認
    mock_unit_of_work.minutes_repository.create.assert_called_once()
    # 作成されたMinutesのrole_name_mappingsを確認
    created_call = mock_unit_of_work.minutes_repository.create.call_args
    created_entity = created_call[0][0]
    assert created_entity.role_name_mappings == {"議長": "伊藤条一"}
