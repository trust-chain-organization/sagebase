"""BackfillRoleNameMappingsUseCaseのテスト

Issue #947: 既存議事録への役職-人名マッピングのバックフィル
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.application.usecases.backfill_role_name_mappings_usecase import (
    BackfillResultDTO,
    BackfillRoleNameMappingsUseCase,
)
from src.domain.dtos.role_name_mapping_dto import (
    RoleNameMappingDTO,
    RoleNameMappingResultDTO,
)
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes


@pytest.fixture
def mock_unit_of_work():
    """モックUnit of Workのフィクスチャ"""
    uow = AsyncMock()
    uow.meeting_repository = AsyncMock()
    uow.minutes_repository = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.flush = AsyncMock()
    return uow


@pytest.fixture
def mock_storage_service():
    """モックストレージサービスのフィクスチャ"""
    return AsyncMock()


@pytest.fixture
def mock_role_name_mapping_service():
    """モック役職-人名マッピングサービスのフィクスチャ"""
    return AsyncMock()


@pytest.fixture
def mock_minutes_divider_service():
    """モック議事録分割サービスのフィクスチャ"""
    service = MagicMock()
    # 非同期メソッドのモック
    service.detect_attendee_boundary = AsyncMock()
    # 同期メソッドのモック
    service.split_minutes_by_boundary = Mock()
    return service


@pytest.fixture
def use_case(
    mock_unit_of_work,
    mock_storage_service,
    mock_role_name_mapping_service,
    mock_minutes_divider_service,
):
    """ユースケースのフィクスチャ"""
    return BackfillRoleNameMappingsUseCase(
        unit_of_work=mock_unit_of_work,
        storage_service=mock_storage_service,
        role_name_mapping_service=mock_role_name_mapping_service,
        minutes_divider_service=mock_minutes_divider_service,
    )


@pytest.fixture
def sample_meeting():
    """サンプル会議エンティティ"""
    return Meeting(
        id=1,
        conference_id=1,
        date=None,
        url="https://example.com",
        gcs_text_uri="gs://bucket/text.txt",
        gcs_pdf_uri=None,
    )


@pytest.fixture
def sample_minutes():
    """サンプル議事録エンティティ（マッピングなし）"""
    return Minutes(
        id=1,
        meeting_id=1,
        url="https://example.com",
        role_name_mappings=None,
    )


@pytest.fixture
def sample_minutes_with_mapping():
    """サンプル議事録エンティティ（マッピングあり）"""
    return Minutes(
        id=2,
        meeting_id=2,
        url="https://example.com",
        role_name_mappings={"議長": "田中太郎"},
    )


@pytest.fixture
def sample_mapping_result():
    """サンプルマッピング抽出結果"""
    return RoleNameMappingResultDTO(
        mappings=[
            RoleNameMappingDTO(role="議長", name="田中太郎", member_number=None),
            RoleNameMappingDTO(role="副議長", name="山田花子", member_number=None),
        ],
        attendee_section_found=True,
        confidence=0.9,
    )


class TestBackfillRoleNameMappingsUseCase:
    """BackfillRoleNameMappingsUseCaseのテストクラス"""

    @pytest.mark.asyncio
    async def test_execute_success_single_minutes(
        self,
        use_case,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        sample_meeting,
        sample_minutes,
        sample_mapping_result,
    ):
        """単一議事録の処理が正常に完了することをテスト"""
        # モック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = [sample_minutes]
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_storage_service.download_file.return_value = "議事録テキスト".encode()
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            sample_mapping_result
        )
        mock_unit_of_work.minutes_repository.update_role_name_mappings.return_value = (
            True
        )

        # 実行
        result = await use_case.execute()

        # 検証
        assert result.total_processed == 1
        assert result.success_count == 1
        assert result.skip_count == 0
        assert result.error_count == 0
        assert len(result.errors) == 0

        # 更新が呼ばれたことを確認
        mock_unit_of_work.minutes_repository.update_role_name_mappings.assert_called_once_with(
            1, {"議長": "田中太郎", "副議長": "山田花子"}
        )

    @pytest.mark.asyncio
    async def test_execute_skip_existing_mapping(
        self,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        sample_minutes,
        sample_minutes_with_mapping,
        sample_mapping_result,
        sample_meeting,
    ):
        """既存マッピングがある議事録をスキップすることをテスト"""
        # minutes_divider_serviceをNoneにしてシンプルなケースをテスト
        use_case = BackfillRoleNameMappingsUseCase(
            unit_of_work=mock_unit_of_work,
            storage_service=mock_storage_service,
            role_name_mapping_service=mock_role_name_mapping_service,
            minutes_divider_service=None,
        )

        # モック設定: マッピングありとなしの両方を返す
        mock_unit_of_work.minutes_repository.get_all.return_value = [
            sample_minutes,
            sample_minutes_with_mapping,
        ]
        # マッピングなしの議事録の処理に必要なモック
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_storage_service.download_file.return_value = "議事録テキスト".encode()
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            sample_mapping_result
        )
        mock_unit_of_work.minutes_repository.update_role_name_mappings.return_value = (
            True
        )

        # 実行（skip_existing=True）
        result = await use_case.execute(skip_existing=True)

        # 検証: マッピングありの議事録はスキップされる
        # skip_count = フィルター時のスキップ(1) + 処理成功(0)
        assert result.skip_count == 1
        # マッピングなしの議事録は処理される
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_execute_force_reprocess(
        self,
        use_case,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        sample_meeting,
        sample_minutes_with_mapping,
        sample_mapping_result,
    ):
        """force_reprocess時に既存マッピングを上書きすることをテスト"""
        # モック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = [
            sample_minutes_with_mapping
        ]
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_storage_service.download_file.return_value = "議事録テキスト".encode()
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            sample_mapping_result
        )
        mock_unit_of_work.minutes_repository.update_role_name_mappings.return_value = (
            True
        )

        # 実行（force_reprocess=True）
        result = await use_case.execute(force_reprocess=True)

        # 検証
        assert result.success_count == 1
        assert result.skip_count == 0

    @pytest.mark.asyncio
    async def test_execute_with_meeting_id(
        self,
        use_case,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        sample_meeting,
        sample_minutes,
        sample_mapping_result,
    ):
        """特定の会議IDを指定した場合の処理をテスト"""
        # モック設定
        mock_unit_of_work.minutes_repository.get_by_meeting.return_value = (
            sample_minutes
        )
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_storage_service.download_file.return_value = "議事録テキスト".encode()
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            sample_mapping_result
        )
        mock_unit_of_work.minutes_repository.update_role_name_mappings.return_value = (
            True
        )

        # 実行
        result = await use_case.execute(meeting_id=1)

        # 検証
        mock_unit_of_work.minutes_repository.get_by_meeting.assert_called_once_with(1)
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_limit(
        self,
        use_case,
        mock_unit_of_work,
    ):
        """limit指定時の処理をテスト"""
        # モック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = []

        # 実行
        await use_case.execute(limit=10)

        # 検証
        mock_unit_of_work.minutes_repository.get_all.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_execute_no_gcs_text_uri(
        self,
        use_case,
        mock_unit_of_work,
        sample_minutes,
    ):
        """GCSテキストURIがない場合にスキップすることをテスト"""
        # GCSテキストURIがないMeeting
        meeting_no_uri = Meeting(
            id=1,
            conference_id=1,
            date=None,
            url="https://example.com",
            gcs_text_uri=None,  # URIなし
            gcs_pdf_uri=None,
        )

        # モック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = [sample_minutes]
        mock_unit_of_work.meeting_repository.get_by_id.return_value = meeting_no_uri

        # 実行
        result = await use_case.execute()

        # 検証: スキップされる（成功でもエラーでもない）
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_execute_no_mapping_extracted(
        self,
        use_case,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        sample_meeting,
        sample_minutes,
    ):
        """マッピングが抽出されなかった場合の処理をテスト"""
        # 空のマッピング結果
        empty_result = RoleNameMappingResultDTO(
            mappings=[],
            attendee_section_found=False,
            confidence=0.0,
        )

        # モック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = [sample_minutes]
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_storage_service.download_file.return_value = "議事録テキスト".encode()
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            empty_result
        )

        # 実行
        result = await use_case.execute()

        # 検証: マッピングなしでスキップ
        assert result.success_count == 0
        mock_unit_of_work.minutes_repository.update_role_name_mappings.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_error_handling_continues(
        self,
        use_case,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        sample_meeting,
        sample_mapping_result,
    ):
        """個別エラー発生時に処理を継続することをテスト

        注意: GCSダウンロードエラーは内部で捕捉され「スキップ」として扱われます。
        エラーとしてカウントされるのは、_process_single_minutes自体が例外を
        投げた場合のみです。
        """
        minutes1 = Minutes(id=1, meeting_id=1, role_name_mappings=None)
        minutes2 = Minutes(id=2, meeting_id=2, role_name_mappings=None)

        meeting1 = sample_meeting
        meeting2 = Meeting(
            id=2,
            conference_id=1,
            date=None,
            url="https://example.com/2",
            gcs_text_uri="gs://bucket/text2.txt",
        )

        # モック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = [minutes1, minutes2]
        mock_unit_of_work.meeting_repository.get_by_id.side_effect = [
            meeting1,
            meeting2,
        ]

        # 1件目はGCSエラー（スキップとして扱われる）、2件目は成功
        mock_storage_service.download_file.side_effect = [
            Exception("GCS error"),  # 1件目: GCSエラー → スキップ
            "議事録テキスト".encode(),  # 2件目: 成功
        ]
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            sample_mapping_result
        )
        mock_unit_of_work.minutes_repository.update_role_name_mappings.return_value = (
            True
        )

        # 実行
        result = await use_case.execute()

        # 検証: 2件処理され、1件スキップ（GCSエラー）、1件成功
        assert result.total_processed == 2
        # GCSダウンロードエラーは_process_single_minutes内で捕捉されてFalseを返す
        # → skip_countとしてカウントされる
        assert result.skip_count == 1
        assert result.success_count == 1
        # エラーではなくスキップなのでerror_countは0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_execute_with_boundary_detection(
        self,
        use_case,
        mock_unit_of_work,
        mock_storage_service,
        mock_role_name_mapping_service,
        mock_minutes_divider_service,
        sample_meeting,
        sample_minutes,
        sample_mapping_result,
    ):
        """境界検出による出席者セクション抽出をテスト"""
        # 境界検出結果のモック
        boundary = MagicMock()
        boundary.boundary_found = True
        boundary.boundary_text = "--- 出席者 ---"

        mock_minutes_divider_service.detect_attendee_boundary.return_value = boundary
        mock_minutes_divider_service.split_minutes_by_boundary.return_value = (
            "出席者セクションのテキスト",
            "本文",
        )

        # その他のモック設定
        mock_unit_of_work.minutes_repository.get_all.return_value = [sample_minutes]
        mock_unit_of_work.meeting_repository.get_by_id.return_value = sample_meeting
        mock_storage_service.download_file.return_value = "議事録テキスト".encode()
        mock_role_name_mapping_service.extract_role_name_mapping.return_value = (
            sample_mapping_result
        )
        mock_unit_of_work.minutes_repository.update_role_name_mappings.return_value = (
            True
        )

        # 実行
        result = await use_case.execute()

        # 検証
        assert result.success_count == 1
        mock_minutes_divider_service.detect_attendee_boundary.assert_called_once()
        mock_minutes_divider_service.split_minutes_by_boundary.assert_called_once()


class TestBackfillResultDTO:
    """BackfillResultDTOのテストクラス"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        result = BackfillResultDTO()
        assert result.total_processed == 0
        assert result.success_count == 0
        assert result.skip_count == 0
        assert result.error_count == 0
        assert result.errors == []

    def test_custom_values(self):
        """カスタム値のテスト"""
        result = BackfillResultDTO(
            total_processed=10,
            success_count=8,
            skip_count=1,
            error_count=1,
            errors=["Error 1"],
        )
        assert result.total_processed == 10
        assert result.success_count == 8
        assert result.skip_count == 1
        assert result.error_count == 1
        assert len(result.errors) == 1
