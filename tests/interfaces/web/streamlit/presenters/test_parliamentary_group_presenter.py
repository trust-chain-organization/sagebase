"""ParliamentaryGroupPresenterのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_parliamentary_groups_usecase import (
    CreateParliamentaryGroupOutputDto,
    DeleteParliamentaryGroupOutputDto,
    ExtractMembersOutputDto,
    GenerateSeedFileOutputDto,
    ManageParliamentaryGroupsUseCase,
    ParliamentaryGroupListOutputDto,
    UpdateParliamentaryGroupOutputDto,
)
from src.domain.entities import Conference, ParliamentaryGroup


@pytest.fixture
def mock_use_case():
    """ManageParliamentaryGroupsUseCaseのモック"""
    return AsyncMock(spec=ManageParliamentaryGroupsUseCase)


@pytest.fixture
def sample_parliamentary_groups():
    """サンプル議員団リスト"""
    return [
        ParliamentaryGroup(
            id=1,
            name="自民党会派",
            conference_id=100,
        ),
        ParliamentaryGroup(
            id=2,
            name="立憲民主党会派",
            conference_id=100,
        ),
    ]


@pytest.fixture
def sample_conferences():
    """サンプル会議体リスト"""
    return [
        Conference(id=100, name="本会議", governing_body_id=1),
        Conference(id=101, name="予算委員会", governing_body_id=1),
    ]


@pytest.fixture
def presenter(mock_use_case):
    """ParliamentaryGroupPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ManageParliamentaryGroupsUseCase"
        ) as mock_uc_class,
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.GeminiLLMService"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ParliamentaryGroupMemberExtractorFactory"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.NoOpSessionAdapter"
        ),
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        mock_session_instance = MagicMock()
        mock_session_instance.get_or_create = MagicMock(
            return_value={
                "editing_mode": None,
                "editing_id": None,
                "conference_filter": "すべて",
                "created_parliamentary_groups": [],
            }
        )
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (  # noqa: E501
            ParliamentaryGroupPresenter,
        )

        presenter = ParliamentaryGroupPresenter()
        presenter.use_case = mock_use_case
        return presenter


class TestParliamentaryGroupPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.SessionManager"
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ManageParliamentaryGroupsUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.GeminiLLMService"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.ParliamentaryGroupMemberExtractorFactory"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_presenter.NoOpSessionAdapter"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get_or_create = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (  # noqa: E501
                ParliamentaryGroupPresenter,
            )

            presenter = ParliamentaryGroupPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    async def test_load_data_async_success(
        self, presenter, mock_use_case, sample_parliamentary_groups
    ):
        """議員団リストを読み込めることを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.return_value = (
            ParliamentaryGroupListOutputDto(
                parliamentary_groups=sample_parliamentary_groups
            )
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert len(result) == 2
        mock_use_case.list_parliamentary_groups.assert_called_once()

    async def test_load_data_async_exception(self, presenter, mock_use_case):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert result == []


class TestLoadParliamentaryGroupsWithFilters:
    """load_parliamentary_groups_with_filtersメソッドのテスト"""

    async def test_with_conference_filter(
        self, presenter, mock_use_case, sample_parliamentary_groups
    ):
        """会議体フィルタで絞り込めることを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.return_value = (
            ParliamentaryGroupListOutputDto(
                parliamentary_groups=sample_parliamentary_groups
            )
        )

        # Act
        result = await presenter._load_parliamentary_groups_with_filters_async(
            conference_id=100
        )

        # Assert
        assert len(result) == 2

    async def test_with_active_only_filter(
        self, presenter, mock_use_case, sample_parliamentary_groups
    ):
        """アクティブのみフィルタで絞り込めることを確認"""
        # Arrange
        mock_use_case.list_parliamentary_groups.return_value = (
            ParliamentaryGroupListOutputDto(
                parliamentary_groups=[sample_parliamentary_groups[0]]
            )
        )

        # Act
        result = await presenter._load_parliamentary_groups_with_filters_async(
            active_only=True
        )

        # Assert
        assert len(result) == 1


class TestGetAllConferences:
    """get_all_conferencesメソッドのテスト"""

    async def test_get_all_conferences_success(self, presenter, sample_conferences):
        """会議体リストを取得できることを確認"""
        # Arrange
        presenter.conference_repo = MagicMock()
        presenter.conference_repo.get_all = AsyncMock(return_value=sample_conferences)

        # Act
        result = await presenter._get_all_conferences_async()

        # Assert
        assert len(result) == 2


class TestCreate:
    """createメソッドのテスト"""

    async def test_create_success(self, presenter, mock_use_case):
        """議員団の作成が成功することを確認"""
        # Arrange
        created_group = ParliamentaryGroup(id=1, name="新規会派", conference_id=100)
        mock_use_case.create_parliamentary_group.return_value = (
            CreateParliamentaryGroupOutputDto(
                success=True, parliamentary_group=created_group, error_message=None
            )
        )

        # Act
        success, group, error_message = await presenter._create_async(
            name="新規会派",
            conference_id=100,
        )

        # Assert
        assert success is True
        assert group is not None
        assert group.id == 1

    async def test_create_failure(self, presenter, mock_use_case):
        """議員団の作成が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.create_parliamentary_group.return_value = (
            CreateParliamentaryGroupOutputDto(
                success=False,
                parliamentary_group=None,
                error_message="作成に失敗しました",
            )
        )

        # Act
        success, group, error_message = await presenter._create_async(
            name="新規会派", conference_id=100
        )

        # Assert
        assert success is False
        assert group is None


class TestUpdate:
    """updateメソッドのテスト"""

    async def test_update_success(self, presenter, mock_use_case):
        """議員団の更新が成功することを確認"""
        # Arrange
        mock_use_case.update_parliamentary_group.return_value = (
            UpdateParliamentaryGroupOutputDto(success=True, error_message=None)
        )

        # Act
        success, error_message = await presenter._update_async(
            id=1, name="更新された会派"
        )

        # Assert
        assert success is True

    async def test_update_failure(self, presenter, mock_use_case):
        """議員団の更新が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.update_parliamentary_group.return_value = (
            UpdateParliamentaryGroupOutputDto(
                success=False, error_message="更新に失敗しました"
            )
        )

        # Act
        success, error_message = await presenter._update_async(id=999, name="不明")

        # Assert
        assert success is False


class TestDelete:
    """deleteメソッドのテスト"""

    async def test_delete_success(self, presenter, mock_use_case):
        """議員団の削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_parliamentary_group.return_value = (
            DeleteParliamentaryGroupOutputDto(success=True, error_message=None)
        )

        # Act
        success, error_message = await presenter._delete_async(id=1)

        # Assert
        assert success is True

    async def test_delete_failure(self, presenter, mock_use_case):
        """議員団の削除が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.delete_parliamentary_group.return_value = (
            DeleteParliamentaryGroupOutputDto(
                success=False, error_message="削除に失敗しました"
            )
        )

        # Act
        success, error_message = await presenter._delete_async(id=1)

        # Assert
        assert success is False


class TestExtractMembers:
    """extract_membersメソッドのテスト"""

    async def test_extract_members_success(self, presenter, mock_use_case):
        """メンバー抽出が成功することを確認"""
        # Arrange
        mock_use_case.extract_members.return_value = ExtractMembersOutputDto(
            success=True,
            extracted_members=[],
            error_message=None,
        )

        # Act
        success, result, error_message = await presenter._extract_members_async(
            parliamentary_group_id=1, url="https://example.com"
        )

        # Assert
        assert success is True
        assert result is not None


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト"""

    async def test_generate_seed_file_success(self, presenter, mock_use_case):
        """シードファイル生成が成功することを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=True,
            seed_content="INSERT INTO...",
            file_path="/tmp/seed.sql",
            error_message=None,
        )

        # Act
        success, seed_content, file_path = await presenter._generate_seed_file_async()

        # Assert
        assert success is True
        assert seed_content == "INSERT INTO..."


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(
        self, presenter, sample_parliamentary_groups, sample_conferences
    ):
        """議員団リストをDataFrameに変換できることを確認"""
        # Act
        df = presenter.to_dataframe(sample_parliamentary_groups, sample_conferences)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "議員団名" in df.columns

    def test_to_dataframe_empty(self, presenter, sample_conferences):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([], sample_conferences)

        # Assert
        assert df is None


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_list(self, presenter):
        """listアクションが正しく処理されることを確認"""
        # Arrange
        presenter.load_parliamentary_groups_with_filters = MagicMock(return_value=[])

        # Act
        presenter.handle_action("list")

        # Assert
        presenter.load_parliamentary_groups_with_filters.assert_called_once()

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")


class TestCreatedGroupsManagement:
    """作成した議員団の管理テスト"""

    def test_add_created_group(self, presenter):
        """作成した議員団を追加できることを確認"""
        # Arrange
        presenter._save_form_state = MagicMock()
        group = ParliamentaryGroup(id=1, name="新規会派", conference_id=100)

        # Act
        presenter.add_created_group(group, "本会議")

        # Assert
        assert len(presenter.form_state["created_parliamentary_groups"]) == 1
        presenter._save_form_state.assert_called_once()

    def test_remove_created_group(self, presenter):
        """作成した議員団を削除できることを確認"""
        # Arrange
        presenter.form_state["created_parliamentary_groups"] = [
            {"id": 1, "name": "会派A"},
            {"id": 2, "name": "会派B"},
        ]
        presenter._save_form_state = MagicMock()

        # Act - indexで削除する
        presenter.remove_created_group(0)

        # Assert
        assert len(presenter.form_state["created_parliamentary_groups"]) == 1
        presenter._save_form_state.assert_called_once()

    def test_get_created_groups(self, presenter):
        """作成した議員団リストを取得できることを確認"""
        # Arrange
        presenter.form_state["created_parliamentary_groups"] = [
            {"id": 1, "name": "会派A"},
            {"id": 2, "name": "会派B"},
        ]

        # Act
        result = presenter.get_created_groups()

        # Assert
        assert len(result) == 2
