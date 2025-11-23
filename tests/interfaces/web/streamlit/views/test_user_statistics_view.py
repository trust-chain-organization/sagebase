"""ユーザー統計ビューのテスト"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.application.dtos.user_statistics_dto import (
    ContributorRank,
    TimelineDataPoint,
    UserStatisticsDTO,
)
from src.application.dtos.work_history_dto import WorkType


@pytest.fixture
def mock_presenter():
    """プレゼンターのモック"""
    mock = MagicMock()
    mock.get_statistics.return_value = UserStatisticsDTO(
        total_count=10,
        work_type_counts={WorkType.SPEAKER_POLITICIAN_MATCHING.value: 10},
        user_counts={"Test User (test@example.com)": 10},
        timeline_data=[
            TimelineDataPoint(date=date(2024, 1, 1), count=10, work_type=None)
        ],
        top_contributors=[
            ContributorRank(
                rank=1,
                user_name="Test User",
                user_email="test@example.com",
                total_works=10,
                work_type_breakdown={WorkType.SPEAKER_POLITICIAN_MATCHING.value: 10},
            )
        ],
    )
    mock.get_timeline_dataframe.return_value = None
    mock.get_contributors_dataframe.return_value = None
    mock.get_work_type_display_names.return_value = {
        WorkType.SPEAKER_POLITICIAN_MATCHING: "発言者-政治家紐付け",
        WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION: "議員団メンバー作成",
    }
    return mock


@patch("src.interfaces.web.streamlit.views.user_statistics_view.st")
@patch(
    "src.interfaces.web.streamlit.views.user_statistics_view.UserStatisticsPresenter"
)
def test_render_overall_statistics_tab_displays_metrics(
    mock_presenter_class, mock_st, mock_presenter
):
    """全体統計タブが正しくメトリックを表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.user_statistics_view import (
        render_overall_statistics_tab,
    )

    mock_presenter_class.return_value = mock_presenter

    # st.columns()がコンテキストマネージャーのタプルを返すようにモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_col3 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2, mock_col3)

    # Act
    render_overall_statistics_tab(mock_presenter)

    # Assert
    mock_presenter.get_statistics.assert_called_once()
    # コラムが作成されることを確認
    assert mock_st.columns.called


@patch("src.interfaces.web.streamlit.views.user_statistics_view.st")
@patch("src.interfaces.web.streamlit.views.user_statistics_view.google_sign_in")
def test_render_my_page_tab_requires_login(mock_auth, mock_st):
    """マイページタブがログインを要求することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.user_statistics_view import (
        render_my_page_tab,
    )

    mock_auth.get_user_info.return_value = None  # 未ログイン
    mock_presenter = MagicMock()

    # Act
    render_my_page_tab(mock_presenter)

    # Assert
    mock_st.warning.assert_called_once_with("ログインしていません")


@patch("src.interfaces.web.streamlit.views.user_statistics_view.st")
@patch("src.interfaces.web.streamlit.views.user_statistics_view.google_sign_in")
def test_render_my_page_tab_with_login(mock_auth, mock_st, mock_presenter):
    """マイページタブがログイン時に統計を表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.user_statistics_view import (
        render_my_page_tab,
    )

    # ログイン状態をモック
    mock_auth.get_user_info.return_value = {"email": "test@example.com"}

    # st.columns()がコンテキストマネージャーのタプルを返すようにモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    # Act
    render_my_page_tab(mock_presenter)

    # Assert
    mock_presenter.get_statistics.assert_called()
    # コラムが作成されることを確認
    assert mock_st.columns.called


@patch("src.interfaces.web.streamlit.views.user_statistics_view.st")
@patch(
    "src.interfaces.web.streamlit.views.user_statistics_view.UserStatisticsPresenter"
)
def test_render_user_statistics_page_creates_tabs(
    mock_presenter_class, mock_st, mock_presenter
):
    """ユーザー統計ページがタブを作成することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.user_statistics_view import (
        render_user_statistics_page,
    )

    mock_presenter_class.return_value = mock_presenter
    # st.tabsがコンテキストマネージャーを返すようにモック
    mock_tab1 = MagicMock()
    mock_tab2 = MagicMock()
    mock_st.tabs.return_value = (mock_tab1, mock_tab2)

    # st.columns()がコンテキストマネージャーのタプルを返すようにモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_col3 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2, mock_col3)

    # Act
    render_user_statistics_page()

    # Assert
    # タブが作成されることを確認
    mock_st.tabs.assert_called_once()
    assert mock_st.title.called or mock_st.header.called
