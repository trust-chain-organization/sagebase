"""ConferencePresenterのテスト"""

from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_conferences_usecase import (
    ConferenceListOutputDto,
    CreateConferenceOutputDto,
    DeleteConferenceOutputDto,
    GenerateSeedFileOutputDto,
    ManageConferencesUseCase,
    UpdateConferenceOutputDto,
)
from src.domain.entities import Conference
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferenceFormData,
    ConferencePresenter,
)


@pytest.fixture
def mock_use_case():
    """ManageConferencesUseCaseのモック"""
    return AsyncMock(spec=ManageConferencesUseCase)


@pytest.fixture
def presenter(mock_use_case):
    """ConferencePresenterのインスタンス"""
    with patch(
        "src.interfaces.web.streamlit.presenters.conference_presenter.SessionManager"
    ):
        return ConferencePresenter(use_case=mock_use_case)


@pytest.fixture
def sample_conferences():
    """サンプル会議体リスト"""
    return [
        Conference(
            id=1,
            name="総務委員会",
            governing_body_id=100,
            type="常任委員会",
            prefecture="東京都",
            members_introduction_url="https://example.com/members1",
        ),
        Conference(
            id=2,
            name="本会議",
            governing_body_id=100,
            type="本会議",
            prefecture="東京都",
            members_introduction_url=None,
        ),
    ]


class TestConferencePresenterInit:
    """初期化テスト"""

    def test_init_with_use_case(self, mock_use_case):
        """UseCaseを指定して初期化できることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.SessionManager"
        ):
            presenter = ConferencePresenter(use_case=mock_use_case)
            assert presenter.use_case == mock_use_case


class TestLoadConferences:
    """load_conferencesメソッドのテスト"""

    async def test_load_conferences_success(
        self, presenter, mock_use_case, sample_conferences
    ):
        """会議体リストの読み込みが成功することを確認"""
        # Arrange
        output_dto = ConferenceListOutputDto(
            conferences=sample_conferences,
            with_url_count=1,
            without_url_count=1,
        )
        mock_use_case.list_conferences.return_value = output_dto

        # Act
        df, with_url_count, without_url_count = await presenter.load_conferences()

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert with_url_count == 1
        assert without_url_count == 1
        mock_use_case.list_conferences.assert_called_once()

    async def test_load_conferences_with_filters(
        self, presenter, mock_use_case, sample_conferences
    ):
        """フィルタ付きで会議体リストを読み込めることを確認"""
        # Arrange
        output_dto = ConferenceListOutputDto(
            conferences=sample_conferences[:1],
            with_url_count=1,
            without_url_count=0,
        )
        mock_use_case.list_conferences.return_value = output_dto

        # Act
        df, with_url_count, without_url_count = await presenter.load_conferences(
            governing_body_id=100, with_members_url=True
        )

        # Assert
        assert len(df) == 1
        assert with_url_count == 1
        assert without_url_count == 0

    async def test_load_conferences_empty(self, presenter, mock_use_case):
        """空の会議体リストを処理できることを確認"""
        # Arrange
        output_dto = ConferenceListOutputDto(
            conferences=[],
            with_url_count=0,
            without_url_count=0,
        )
        mock_use_case.list_conferences.return_value = output_dto

        # Act
        df, with_url_count, without_url_count = await presenter.load_conferences()

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert with_url_count == 0
        assert without_url_count == 0


class TestConferencesToDataframe:
    """_conferences_to_dataframeメソッドのテスト"""

    def test_conferences_to_dataframe_success(self, presenter, sample_conferences):
        """会議体リストをDataFrameに変換できることを確認"""
        # Act
        df = presenter._conferences_to_dataframe(sample_conferences)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "会議体名" in df.columns
        assert "都道府県" in df.columns
        assert "開催主体ID" in df.columns
        assert "種別" in df.columns
        assert "議員紹介URL" in df.columns

        # 最初の行の値を確認
        assert df.iloc[0]["ID"] == 1
        assert df.iloc[0]["会議体名"] == "総務委員会"
        assert df.iloc[0]["都道府県"] == "東京都"
        assert df.iloc[0]["議員紹介URL"] == "https://example.com/members1"

    def test_conferences_to_dataframe_with_none_values(self, presenter):
        """None値を含む会議体を正しく変換できることを確認"""
        # Arrange
        conferences = [
            Conference(
                id=1,
                name="テスト会議",
                governing_body_id=None,
                type=None,
                prefecture=None,
                members_introduction_url=None,
            )
        ]

        # Act
        df = presenter._conferences_to_dataframe(conferences)

        # Assert
        assert df.iloc[0]["都道府県"] == ""
        assert df.iloc[0]["開催主体ID"] == ""
        assert df.iloc[0]["種別"] == ""
        assert df.iloc[0]["議員紹介URL"] == ""


class TestFormData:
    """フォームデータ関連メソッドのテスト"""

    def test_get_form_data_creates_new(self, presenter):
        """フォームデータがない場合は新規作成されることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.st"
        ) as mock_st:
            mock_st.session_state = {}

            # Act
            form_data = presenter.get_form_data()

            # Assert
            assert isinstance(form_data, ConferenceFormData)
            assert form_data.name == ""

    def test_get_form_data_returns_existing(self, presenter):
        """既存のフォームデータが返されることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.st"
        ) as mock_st:
            existing_form = ConferenceFormData(name="既存の会議体")
            mock_st.session_state = {"new_conference_form": existing_form}

            # Act
            form_data = presenter.get_form_data()

            # Assert
            assert form_data.name == "既存の会議体"

    def test_get_form_data_with_prefix(self, presenter):
        """プレフィックス付きでフォームデータを取得できることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.st"
        ) as mock_st:
            existing_form = ConferenceFormData(name="編集中の会議体")
            mock_st.session_state = {"edit_conference_form": existing_form}

            # Act
            form_data = presenter.get_form_data(prefix="edit")

            # Assert
            assert form_data.name == "編集中の会議体"

    def test_update_form_data(self, presenter):
        """フォームデータを更新できることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.st"
        ) as mock_st:
            mock_st.session_state = {}
            new_form = ConferenceFormData(name="更新された会議体")

            # Act
            presenter.update_form_data(new_form)

            # Assert
            assert mock_st.session_state["new_conference_form"] == new_form

    def test_clear_form_data(self, presenter):
        """フォームデータをクリアできることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.st"
        ) as mock_st:
            mock_st.session_state = {
                "new_conference_form": ConferenceFormData(name="削除対象")
            }

            # Act
            presenter.clear_form_data()

            # Assert
            assert "new_conference_form" not in mock_st.session_state

    def test_clear_form_data_not_exists(self, presenter):
        """存在しないフォームデータのクリアがエラーにならないことを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.conference_presenter.st"
        ) as mock_st:
            mock_st.session_state = {}

            # Act - エラーが発生しないことを確認
            presenter.clear_form_data()


class TestCreateConference:
    """create_conferenceメソッドのテスト"""

    async def test_create_conference_success(self, presenter, mock_use_case):
        """会議体の作成が成功することを確認"""
        # Arrange
        mock_use_case.create_conference.return_value = CreateConferenceOutputDto(
            success=True, conference_id=1, error_message=None
        )
        form_data = ConferenceFormData(
            name="新規会議体",
            governing_body_id=100,
            type="常任委員会",
            prefecture="東京都",
            members_introduction_url="https://example.com/members",
        )

        # Act
        success, error_message = await presenter.create_conference(form_data)

        # Assert
        assert success is True
        assert error_message is None
        mock_use_case.create_conference.assert_called_once()

    async def test_create_conference_failure(self, presenter, mock_use_case):
        """会議体の作成が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.create_conference.return_value = CreateConferenceOutputDto(
            success=False, conference_id=None, error_message="既に存在する会議体名です"
        )
        form_data = ConferenceFormData(name="重複会議体")

        # Act
        success, error_message = await presenter.create_conference(form_data)

        # Assert
        assert success is False
        assert error_message == "既に存在する会議体名です"


class TestUpdateConference:
    """update_conferenceメソッドのテスト"""

    async def test_update_conference_success(self, presenter, mock_use_case):
        """会議体の更新が成功することを確認"""
        # Arrange
        mock_use_case.update_conference.return_value = UpdateConferenceOutputDto(
            success=True, error_message=None
        )
        form_data = ConferenceFormData(
            name="更新された会議体",
            governing_body_id=100,
            type="特別委員会",
        )

        # Act
        success, error_message = await presenter.update_conference(1, form_data)

        # Assert
        assert success is True
        assert error_message is None
        mock_use_case.update_conference.assert_called_once()

    async def test_update_conference_failure(self, presenter, mock_use_case):
        """会議体の更新が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.update_conference.return_value = UpdateConferenceOutputDto(
            success=False, error_message="会議体が見つかりません"
        )
        form_data = ConferenceFormData(name="存在しない会議体")

        # Act
        success, error_message = await presenter.update_conference(999, form_data)

        # Assert
        assert success is False
        assert error_message == "会議体が見つかりません"


class TestDeleteConference:
    """delete_conferenceメソッドのテスト"""

    async def test_delete_conference_success(self, presenter, mock_use_case):
        """会議体の削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_conference.return_value = DeleteConferenceOutputDto(
            success=True, error_message=None
        )

        # Act
        success, error_message = await presenter.delete_conference(1)

        # Assert
        assert success is True
        assert error_message is None
        mock_use_case.delete_conference.assert_called_once()

    async def test_delete_conference_failure(self, presenter, mock_use_case):
        """会議体の削除が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.delete_conference.return_value = DeleteConferenceOutputDto(
            success=False, error_message="関連データが存在するため削除できません"
        )

        # Act
        success, error_message = await presenter.delete_conference(1)

        # Assert
        assert success is False
        assert error_message == "関連データが存在するため削除できません"


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト"""

    async def test_generate_seed_file_success(self, presenter, mock_use_case):
        """シードファイルの生成が成功することを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=True, file_path="/tmp/seed.sql", error_message=None
        )

        # Act
        success, file_path, error_message = await presenter.generate_seed_file()

        # Assert
        assert success is True
        assert file_path == "/tmp/seed.sql"
        assert error_message is None

    async def test_generate_seed_file_failure(self, presenter, mock_use_case):
        """シードファイルの生成が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=False, file_path=None, error_message="ファイル書き込みエラー"
        )

        # Act
        success, file_path, error_message = await presenter.generate_seed_file()

        # Assert
        assert success is False
        assert file_path is None
        assert error_message == "ファイル書き込みエラー"


class TestLoadConferenceForEdit:
    """load_conference_for_editメソッドのテスト"""

    def test_load_conference_for_edit_success(self, presenter):
        """会議体データを編集用フォームデータに変換できることを確認"""
        # Arrange
        conference = Conference(
            id=1,
            name="編集対象会議体",
            governing_body_id=100,
            type="常任委員会",
            prefecture="東京都",
            members_introduction_url="https://example.com/members",
        )

        # Act
        form_data = presenter.load_conference_for_edit(conference)

        # Assert
        assert isinstance(form_data, ConferenceFormData)
        assert form_data.name == "編集対象会議体"
        assert form_data.governing_body_id == 100
        assert form_data.type == "常任委員会"
        assert form_data.prefecture == "東京都"
        assert form_data.members_introduction_url == "https://example.com/members"

    def test_load_conference_for_edit_with_none_values(self, presenter):
        """None値を含む会議体を正しく変換できることを確認"""
        # Arrange
        conference = Conference(
            id=1,
            name="会議体",
            governing_body_id=None,
            type=None,
            prefecture=None,
            members_introduction_url=None,
        )

        # Act
        form_data = presenter.load_conference_for_edit(conference)

        # Assert
        assert form_data.governing_body_id is None
        assert form_data.type is None
        assert form_data.prefecture is None
        assert form_data.members_introduction_url is None


class TestConferenceFormData:
    """ConferenceFormDataのテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定されることを確認"""
        form_data = ConferenceFormData()
        assert form_data.name == ""
        assert form_data.governing_body_id is None
        assert form_data.type is None
        assert form_data.members_introduction_url is None
        assert form_data.prefecture is None

    def test_custom_values(self):
        """カスタム値を設定できることを確認"""
        form_data = ConferenceFormData(
            name="テスト会議体",
            governing_body_id=100,
            type="本会議",
            members_introduction_url="https://example.com",
            prefecture="大阪府",
        )
        assert form_data.name == "テスト会議体"
        assert form_data.governing_body_id == 100
        assert form_data.type == "本会議"
        assert form_data.members_introduction_url == "https://example.com"
        assert form_data.prefecture == "大阪府"
