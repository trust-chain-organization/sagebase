"""MeetingPresenterのテスト"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.domain.entities.meeting import Meeting


@pytest.fixture
def mock_container():
    """Containerのモック"""
    return MagicMock()


@pytest.fixture
def mock_meeting_repo():
    """MeetingRepositoryのモック"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    repo.get_by_id = MagicMock(return_value=None)
    repo.create = MagicMock()
    repo.update = MagicMock()
    repo.delete = MagicMock(return_value=True)
    return repo


@pytest.fixture
def mock_governing_body_repo():
    """GoverningBodyRepositoryのモック"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    repo.get_by_id = MagicMock(return_value=None)
    return repo


@pytest.fixture
def mock_conference_repo():
    """ConferenceRepositoryのモック"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    repo.get_by_id = MagicMock(return_value=None)
    repo.get_by_governing_body = MagicMock(return_value=[])
    return repo


@pytest.fixture
def sample_meetings():
    """サンプル会議リスト"""
    return [
        Meeting(
            id=1,
            conference_id=100,
            date=date(2024, 1, 15),
            url="https://example.com/meeting1",
            gcs_pdf_uri="gs://bucket/meeting1.pdf",
            gcs_text_uri="gs://bucket/meeting1.txt",
        ),
        Meeting(
            id=2,
            conference_id=100,
            date=date(2024, 1, 16),
            url="https://example.com/meeting2",
            gcs_pdf_uri=None,
            gcs_text_uri=None,
        ),
    ]


@pytest.fixture
def presenter(mock_meeting_repo, mock_governing_body_repo, mock_conference_repo):
    """MeetingPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.meeting_presenter.RepositoryAdapter"
        ) as mock_adapter,
        patch(
            "src.interfaces.web.streamlit.presenters.meeting_presenter.SessionManager"
        ) as mock_session,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        # RepositoryAdapterが適切なリポジトリを返すように設定
        def adapter_side_effect(repo_class):
            if "Meeting" in repo_class.__name__:
                return mock_meeting_repo
            elif "GoverningBody" in repo_class.__name__:
                return mock_governing_body_repo
            elif "Conference" in repo_class.__name__:
                return mock_conference_repo
            return MagicMock()

        mock_adapter.side_effect = adapter_side_effect

        # SessionManagerのモック設定
        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.meeting_presenter import (
            MeetingPresenter,
        )

        presenter = MeetingPresenter()
        presenter.meeting_repo = mock_meeting_repo
        presenter.governing_body_repo = mock_governing_body_repo
        presenter.conference_repo = mock_conference_repo
        return presenter


class TestMeetingPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.meeting_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.meeting_presenter.SessionManager"
            ) as mock_session,
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.meeting_presenter import (
                MeetingPresenter,
            )

            presenter = MeetingPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    def test_load_data_returns_meetings(
        self, presenter, sample_meetings, mock_meeting_repo
    ):
        """会議リストを読み込めることを確認"""
        # Arrange
        mock_meeting_repo.get_all.return_value = sample_meetings

        # Act
        result = presenter.load_data()

        # Assert
        assert len(result) == 2
        mock_meeting_repo.get_all.assert_called_once()

    def test_load_data_returns_empty_list(self, presenter, mock_meeting_repo):
        """空の会議リストを処理できることを確認"""
        # Arrange
        mock_meeting_repo.get_all.return_value = []

        # Act
        result = presenter.load_data()

        # Assert
        assert result == []


class TestGetGoverningBodies:
    """get_governing_bodiesメソッドのテスト"""

    def test_get_governing_bodies_success(self, presenter, mock_governing_body_repo):
        """開催主体リストを取得できることを確認"""
        # Arrange
        mock_body = MagicMock()
        mock_body.id = 1
        mock_body.name = "東京都議会"
        mock_body.type = "都道府県議会"
        mock_governing_body_repo.get_all.return_value = [mock_body]

        # Act
        result = presenter.get_governing_bodies()

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "東京都議会"
        assert result[0]["display_name"] == "東京都議会 (都道府県議会)"


class TestGetConferencesByGoverningBody:
    """get_conferences_by_governing_bodyメソッドのテスト"""

    def test_get_conferences_success(self, presenter, mock_conference_repo):
        """開催主体に紐づく会議体リストを取得できることを確認"""
        # Arrange
        mock_conf = MagicMock()
        mock_conf.id = 100
        mock_conf.name = "本会議"
        mock_conf.governing_body_id = 1
        mock_conference_repo.get_by_governing_body.return_value = [mock_conf]

        # Act
        result = presenter.get_conferences_by_governing_body(1)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 100
        assert result[0]["name"] == "本会議"


class TestCreate:
    """createメソッドのテスト"""

    def test_create_meeting_success(self, presenter, mock_meeting_repo):
        """会議の作成が成功することを確認"""
        # Arrange
        created_meeting = Meeting(
            id=1,
            conference_id=100,
            date=date(2024, 1, 15),
            url="https://example.com/meeting",
        )
        mock_meeting_repo.create.return_value = created_meeting

        # Act
        result = presenter.create(
            conference_id=100,
            date=date(2024, 1, 15),
            url="https://example.com/meeting",
        )

        # Assert
        assert result.success is True
        assert result.data == created_meeting
        assert result.message == "会議を登録しました"

    def test_create_meeting_missing_required_field(self, presenter):
        """必須フィールドがない場合にエラーを返すことを確認"""
        # Act
        result = presenter.create(
            conference_id=100,
            # date と url が不足
        )

        # Assert
        assert result.success is False
        assert "必須" in result.message or "required" in result.message.lower()

    def test_create_meeting_exception(self, presenter, mock_meeting_repo):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        mock_meeting_repo.create.side_effect = Exception("Database error")

        # Act
        result = presenter.create(
            conference_id=100,
            date=date(2024, 1, 15),
            url="https://example.com/meeting",
        )

        # Assert
        assert result.success is False
        assert "失敗" in result.message


class TestRead:
    """readメソッドのテスト"""

    def test_read_meeting_success(self, presenter, mock_meeting_repo, sample_meetings):
        """会議を読み込めることを確認"""
        # Arrange
        mock_meeting_repo.get_by_id.return_value = sample_meetings[0]

        # Act
        result = presenter.read(meeting_id=1)

        # Assert
        assert result is not None
        assert result.id == 1

    def test_read_meeting_not_found(self, presenter, mock_meeting_repo):
        """会議が見つからない場合にNoneを返すことを確認"""
        # Arrange
        mock_meeting_repo.get_by_id.return_value = None

        # Act
        result = presenter.read(meeting_id=999)

        # Assert
        assert result is None

    def test_read_meeting_without_id_raises_error(self, presenter):
        """meeting_idが指定されていない場合にエラーを発生させることを確認"""
        # Act & Assert
        with pytest.raises(ValueError, match="meeting_id is required"):
            presenter.read()


class TestUpdate:
    """updateメソッドのテスト"""

    def test_update_meeting_success(
        self, presenter, mock_meeting_repo, sample_meetings
    ):
        """会議の更新が成功することを確認"""
        # Arrange
        mock_meeting_repo.get_by_id.return_value = sample_meetings[0]
        updated_meeting = Meeting(
            id=1,
            conference_id=100,
            date=date(2024, 1, 20),
            url="https://example.com/meeting_updated",
        )
        mock_meeting_repo.update.return_value = updated_meeting

        # Act
        result = presenter.update(
            meeting_id=1,
            date=date(2024, 1, 20),
            url="https://example.com/meeting_updated",
        )

        # Assert
        assert result.success is True
        assert result.message == "会議を更新しました"

    def test_update_meeting_not_found(self, presenter, mock_meeting_repo):
        """会議が見つからない場合にエラーを返すことを確認"""
        # Arrange
        mock_meeting_repo.get_by_id.return_value = None

        # Act
        result = presenter.update(meeting_id=999)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message

    def test_update_meeting_without_id(self, presenter):
        """meeting_idが指定されていない場合にエラーを返すことを確認"""
        # Act
        result = presenter.update()

        # Assert
        assert result.success is False
        assert "meeting_id is required" in result.message


class TestDelete:
    """deleteメソッドのテスト"""

    def test_delete_meeting_success(self, presenter, mock_meeting_repo):
        """会議の削除が成功することを確認"""
        # Arrange
        mock_meeting_repo.delete.return_value = True

        # Act
        result = presenter.delete(meeting_id=1)

        # Assert
        assert result.success is True
        assert result.message == "会議を削除しました"

    def test_delete_meeting_failure(self, presenter, mock_meeting_repo):
        """会議の削除が失敗した場合にエラーを返すことを確認"""
        # Arrange
        mock_meeting_repo.delete.return_value = False

        # Act
        result = presenter.delete(meeting_id=1)

        # Assert
        assert result.success is False
        assert "失敗" in result.message

    def test_delete_meeting_without_id(self, presenter):
        """meeting_idが指定されていない場合にエラーを返すことを確認"""
        # Act
        result = presenter.delete()

        # Assert
        assert result.success is False
        assert "meeting_id is required" in result.message


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(self, presenter):
        """会議データをDataFrameに変換できることを確認"""
        # Arrange
        meetings_data = [
            {
                "id": 1,
                "conference_id": 100,
                "date": date(2024, 1, 15),
                "url": "https://example.com/meeting1",
                "gcs_pdf_uri": "gs://bucket/meeting1.pdf",
                "gcs_text_uri": "gs://bucket/meeting1.txt",
                "conference_name": "本会議",
                "governing_body_name": "東京都議会",
                "governing_body_type": "都道府県議会",
                "conversation_count": 50,
                "speaker_count": 10,
            }
        ]

        # Act
        df = presenter.to_dataframe(meetings_data)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "開催日" in df.columns
        assert "開催主体・会議体" in df.columns
        assert "GCS" in df.columns
        assert df.iloc[0]["GCS"] == "✓"

    def test_to_dataframe_empty(self, presenter):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([])

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "開催日" in df.columns

    def test_to_dataframe_no_gcs(self, presenter):
        """GCSがない場合の表示を確認"""
        # Arrange
        meetings_data = [
            {
                "id": 1,
                "conference_id": 100,
                "date": date(2024, 1, 15),
                "url": "https://example.com/meeting1",
                "gcs_pdf_uri": None,
                "gcs_text_uri": None,
                "conference_name": "本会議",
                "governing_body_name": "東京都議会",
                "governing_body_type": "都道府県議会",
                "conversation_count": 0,
                "speaker_count": 0,
            }
        ]

        # Act
        df = presenter.to_dataframe(meetings_data)

        # Assert
        assert df.iloc[0]["GCS"] == ""


class TestFormState:
    """フォーム状態管理のテスト"""

    def test_set_editing_mode(self, presenter):
        """編集モードを設定できることを確認"""
        # Act
        presenter.set_editing_mode(meeting_id=1)

        # Assert
        assert presenter.form_state.is_editing is True
        assert presenter.form_state.current_id == 1

    def test_cancel_editing(self, presenter):
        """編集モードをキャンセルできることを確認"""
        # Arrange
        presenter.set_editing_mode(meeting_id=1)

        # Act
        presenter.cancel_editing()

        # Assert
        assert presenter.form_state.is_editing is False
        assert presenter.form_state.current_id is None

    def test_is_editing_with_id(self, presenter):
        """特定のIDで編集中かどうかを確認できることを確認"""
        # Arrange
        presenter.set_editing_mode(meeting_id=1)

        # Act & Assert
        assert presenter.is_editing(meeting_id=1) is True
        assert presenter.is_editing(meeting_id=2) is False

    def test_is_editing_without_id(self, presenter):
        """編集中かどうかを確認できることを確認"""
        # Arrange
        presenter.set_editing_mode(meeting_id=1)

        # Act & Assert
        assert presenter.is_editing() is True

        presenter.cancel_editing()
        assert presenter.is_editing() is False


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト"""

    def test_generate_seed_file_success(self, presenter):
        """シードファイルの生成が成功することを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.meeting_presenter.SeedGenerator"
        ) as mock_generator:
            # Arrange
            mock_instance = MagicMock()
            mock_instance.generate_meetings_seed.return_value = "INSERT INTO..."
            mock_generator.return_value = mock_instance

            # Act
            result = presenter.generate_seed_file()

            # Assert
            assert result.success is True
            assert result.data == "INSERT INTO..."
            assert "SEED" in result.message

    def test_generate_seed_file_failure(self, presenter):
        """シードファイルの生成が失敗した場合にエラーを返すことを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.meeting_presenter.SeedGenerator"
        ) as mock_generator:
            # Arrange
            mock_generator.return_value.generate_meetings_seed.side_effect = Exception(
                "File error"
            )

            # Act
            result = presenter.generate_seed_file()

            # Assert
            assert result.success is False
            assert "失敗" in result.message
