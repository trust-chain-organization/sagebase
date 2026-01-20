"""GoverningBodyPresenterのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_governing_bodies_usecase import (
    CreateGoverningBodyOutputDto,
    DeleteGoverningBodyOutputDto,
    GoverningBodyListOutputDto,
    GoverningBodyStatistics,
    ManageGoverningBodiesUseCase,
    UpdateGoverningBodyOutputDto,
)
from src.domain.entities import GoverningBody


@pytest.fixture
def mock_use_case():
    """ManageGoverningBodiesUseCaseのモック"""
    return AsyncMock(spec=ManageGoverningBodiesUseCase)


@pytest.fixture
def sample_governing_bodies():
    """サンプル開催主体リスト"""
    return [
        GoverningBody(
            id=1,
            name="東京都議会",
            type="都道府県議会",
            organization_code="131001",
        ),
        GoverningBody(
            id=2,
            name="大阪府議会",
            type="都道府県議会",
            organization_code="271004",
        ),
    ]


@pytest.fixture
def presenter(mock_use_case):
    """GoverningBodyPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.governing_body_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.governing_body_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.governing_body_presenter.ManageGoverningBodiesUseCase"
        ) as mock_uc_class,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.governing_body_presenter import (
            GoverningBodyPresenter,
        )

        presenter = GoverningBodyPresenter()
        presenter.use_case = mock_use_case
        return presenter


class TestGoverningBodyPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.governing_body_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.governing_body_presenter.SessionManager"
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.governing_body_presenter.ManageGoverningBodiesUseCase"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.governing_body_presenter import (  # noqa: E501
                GoverningBodyPresenter,
            )

            presenter = GoverningBodyPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    async def test_load_data_async_success(
        self, presenter, mock_use_case, sample_governing_bodies
    ):
        """開催主体リストを非同期で読み込めることを確認"""
        # Arrange
        stats = GoverningBodyStatistics(
            total_count=2,
            country_count=0,
            prefecture_count=2,
            city_count=0,
            with_conference_count=2,
            without_conference_count=0,
        )
        mock_use_case.list_governing_bodies.return_value = GoverningBodyListOutputDto(
            governing_bodies=sample_governing_bodies, statistics=stats
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert len(result) == 2
        assert result[0].name == "東京都議会"

    async def test_load_data_async_empty(self, presenter, mock_use_case):
        """空の開催主体リストを処理できることを確認"""
        # Arrange
        stats = GoverningBodyStatistics(
            total_count=0,
            country_count=0,
            prefecture_count=0,
            city_count=0,
            with_conference_count=0,
            without_conference_count=0,
        )
        mock_use_case.list_governing_bodies.return_value = GoverningBodyListOutputDto(
            governing_bodies=[], statistics=stats
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert result == []

    async def test_load_data_async_exception(self, presenter, mock_use_case):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_use_case.list_governing_bodies.side_effect = Exception("Database error")

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert result == []


class TestLoadGoverningBodiesWithFilters:
    """load_governing_bodies_with_filtersメソッドのテスト"""

    async def test_with_type_filter(
        self, presenter, mock_use_case, sample_governing_bodies
    ):
        """種別フィルタで開催主体を絞り込めることを確認"""
        # Arrange
        stats = GoverningBodyStatistics(
            total_count=2,
            country_count=0,
            prefecture_count=2,
            city_count=0,
            with_conference_count=2,
            without_conference_count=0,
        )
        mock_use_case.list_governing_bodies.return_value = GoverningBodyListOutputDto(
            governing_bodies=sample_governing_bodies, statistics=stats
        )

        # Act
        result, _ = await presenter._load_governing_bodies_with_filters_async(
            type_filter="都道府県議会"
        )

        # Assert
        assert len(result) == 2

    async def test_with_conference_filter(
        self, presenter, mock_use_case, sample_governing_bodies
    ):
        """会議体フィルタで開催主体を絞り込めることを確認"""
        # Arrange
        stats = GoverningBodyStatistics(
            total_count=1,
            country_count=0,
            prefecture_count=1,
            city_count=0,
            with_conference_count=1,
            without_conference_count=0,
        )
        mock_use_case.list_governing_bodies.return_value = GoverningBodyListOutputDto(
            governing_bodies=[sample_governing_bodies[0]], statistics=stats
        )

        # Act
        result, _ = await presenter._load_governing_bodies_with_filters_async(
            conference_filter="with"
        )

        # Assert
        assert len(result) == 1

    async def test_with_both_filters(
        self, presenter, mock_use_case, sample_governing_bodies
    ):
        """複数フィルタで開催主体を絞り込めることを確認"""
        # Arrange
        stats = GoverningBodyStatistics(
            total_count=1,
            country_count=0,
            prefecture_count=1,
            city_count=0,
            with_conference_count=1,
            without_conference_count=0,
        )
        mock_use_case.list_governing_bodies.return_value = GoverningBodyListOutputDto(
            governing_bodies=[sample_governing_bodies[0]], statistics=stats
        )

        # Act
        result, _ = await presenter._load_governing_bodies_with_filters_async(
            type_filter="都道府県議会", conference_filter="with"
        )

        # Assert
        assert len(result) == 1


class TestGetTypeOptions:
    """get_type_optionsメソッドのテスト"""

    def test_get_type_options(self, presenter, mock_use_case):
        """種別オプションを取得できることを確認"""
        # Arrange - mock_use_caseの同期メソッドとして設定
        mock_use_case.get_type_options = MagicMock(
            return_value=["都道府県議会", "市議会", "町村議会"]
        )

        # Act
        options = presenter.get_type_options()

        # Assert
        assert isinstance(options, list)
        assert len(options) == 3
        assert "都道府県議会" in options

    def test_get_type_options_exception(self, presenter, mock_use_case):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_use_case.get_type_options = MagicMock(side_effect=Exception("Error"))

        # Act
        options = presenter.get_type_options()

        # Assert
        assert options == []


class TestCreate:
    """createメソッドのテスト"""

    async def test_create_success(self, presenter, mock_use_case):
        """開催主体の作成が成功することを確認"""
        # Arrange
        mock_use_case.create_governing_body.return_value = CreateGoverningBodyOutputDto(
            success=True, governing_body_id=1, error_message=None
        )

        # Act
        success, result = await presenter._create_async(
            name="新規議会",
            type="都道府県議会",
        )

        # Assert
        assert success is True
        assert result == "1"

    async def test_create_failure(self, presenter, mock_use_case):
        """開催主体の作成が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.create_governing_body.return_value = CreateGoverningBodyOutputDto(
            success=False, governing_body_id=None, error_message="重複する開催主体"
        )

        # Act
        success, error = await presenter._create_async(
            name="重複議会",
            type="都道府県議会",
        )

        # Assert
        assert success is False
        assert "重複" in error

    async def test_create_exception(self, presenter, mock_use_case):
        """例外発生時にエラーを返すことを確認"""
        # Arrange
        mock_use_case.create_governing_body.side_effect = Exception("Database error")

        # Act
        success, error = await presenter._create_async(
            name="テスト",
            type="市議会",
        )

        # Assert
        assert success is False
        assert "Failed to create" in error


class TestUpdate:
    """updateメソッドのテスト"""

    async def test_update_success(self, presenter, mock_use_case):
        """開催主体の更新が成功することを確認"""
        # Arrange
        mock_use_case.update_governing_body.return_value = UpdateGoverningBodyOutputDto(
            success=True, error_message=None
        )

        # Act
        success, error = await presenter._update_async(
            id=1,
            name="更新された議会",
            type="都道府県議会",
        )

        # Assert
        assert success is True
        assert error is None

    async def test_update_failure(self, presenter, mock_use_case):
        """開催主体の更新が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.update_governing_body.return_value = UpdateGoverningBodyOutputDto(
            success=False, error_message="開催主体が見つかりません"
        )

        # Act
        success, error = await presenter._update_async(
            id=999,
            name="不明",
            type="市議会",
        )

        # Assert
        assert success is False
        assert "見つかりません" in error


class TestDelete:
    """deleteメソッドのテスト"""

    async def test_delete_success(self, presenter, mock_use_case):
        """開催主体の削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_governing_body.return_value = DeleteGoverningBodyOutputDto(
            success=True, error_message=None
        )

        # Act
        success, error = await presenter._delete_async(id=1)

        # Assert
        assert success is True
        assert error is None

    async def test_delete_failure(self, presenter, mock_use_case):
        """開催主体の削除が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.delete_governing_body.return_value = DeleteGoverningBodyOutputDto(
            success=False, error_message="関連データが存在します"
        )

        # Act
        success, error = await presenter._delete_async(id=1)

        # Assert
        assert success is False
        assert "関連" in error


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト"""

    async def test_generate_seed_file_success(self, presenter, mock_use_case):
        """シードファイルの生成が成功することを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = MagicMock(
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
        assert file_path == "/tmp/seed.sql"

    async def test_generate_seed_file_failure(self, presenter, mock_use_case):
        """シードファイルの生成が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = MagicMock(
            success=False,
            seed_content=None,
            file_path=None,
            error_message="ファイル書き込みエラー",
        )

        # Act
        success, seed_content, error = await presenter._generate_seed_file_async()

        # Assert
        assert success is False
        assert seed_content is None
        assert "ファイル書き込み" in error


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(self, presenter, sample_governing_bodies):
        """開催主体リストをDataFrameに変換できることを確認"""
        # Act
        df = presenter.to_dataframe(sample_governing_bodies)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "名称" in df.columns
        assert "種別" in df.columns
        assert "会議体数" in df.columns
        assert "組織コード" in df.columns

    def test_to_dataframe_empty(self, presenter):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([])

        # Assert
        assert df is None


class TestFormState:
    """フォーム状態管理のテスト"""

    def test_set_editing_mode_calls_save(self, presenter):
        """set_editing_modeがform_stateを更新することを確認"""
        # Arrange
        presenter.form_state = {"editing_mode": None, "editing_id": None}
        presenter._save_form_state = MagicMock()

        # Act
        presenter.set_editing_mode(mode="edit", id=1)

        # Assert
        presenter._save_form_state.assert_called_once()

    def test_cancel_editing_calls_save(self, presenter):
        """cancel_editingがform_stateを更新することを確認"""
        # Arrange
        presenter.form_state = {"editing_mode": "edit", "editing_id": 1}
        presenter._save_form_state = MagicMock()

        # Act
        presenter.cancel_editing()

        # Assert
        presenter._save_form_state.assert_called_once()

    def test_is_editing_returns_true(self, presenter):
        """is_editingが正しく動作することを確認"""
        # Arrange
        presenter.form_state = {"editing_mode": "edit", "editing_id": 1}

        # Act & Assert
        assert presenter.is_editing(id=1) is True

    def test_is_editing_returns_false_for_different_id(self, presenter):
        """is_editingが異なるIDでfalseを返すことを確認"""
        # Arrange
        presenter.form_state = {"editing_mode": "edit", "editing_id": 1}

        # Act & Assert
        assert presenter.is_editing(id=2) is False


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_list(self, presenter):
        """listアクションが正しく処理されることを確認"""
        with patch.object(
            presenter, "load_governing_bodies_with_filters", return_value=[]
        ) as mock_method:
            # Act
            presenter.handle_action("list", body_type="市議会")

            # Assert
            mock_method.assert_called_once()

    def test_handle_action_create(self, presenter):
        """createアクションが正しく処理されることを確認"""
        with patch.object(
            presenter, "create", return_value=(True, 1, None)
        ) as mock_method:
            # Act
            presenter.handle_action(
                "create", name="新規議会", body_type="市議会", prefecture="東京都"
            )

            # Assert
            mock_method.assert_called_once()

    def test_handle_action_unknown(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown_action")
