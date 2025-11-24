"""発言者管理ビューのテスト"""

from unittest.mock import MagicMock, patch


@patch("src.interfaces.web.streamlit.views.conversations_speakers_view.st")
def test_render_speakers_list_tab_displays_placeholder(mock_st):
    """発言者一覧タブがプレースホルダーを表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations_speakers_view import (
        render_speakers_list_tab,
    )

    # Act
    render_speakers_list_tab()

    # Assert
    mock_st.info.assert_called_once_with("発言者リストの表示機能は実装中です")


@patch("src.interfaces.web.streamlit.views.conversations_speakers_view.st")
@patch("src.interfaces.web.streamlit.views.conversations_speakers_view.google_sign_in")
def test_render_matching_tab_requires_login(mock_auth, mock_st):
    """発言マッチングタブがログインを要求することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations_speakers_view import (
        render_matching_tab,
    )

    mock_auth.get_user_info.return_value = None  # 未ログイン

    # Act
    render_matching_tab()

    # Assert
    mock_st.warning.assert_called_once_with(
        "ユーザー情報を取得できません。ログインしてください。"
    )


@patch("src.interfaces.web.streamlit.views.conversations_speakers_view.st")
@patch("src.interfaces.web.streamlit.views.conversations_speakers_view.google_sign_in")
def test_render_matching_tab_with_login(mock_auth, mock_st):
    """発言マッチングタブがログイン時にユーザー情報を表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations_speakers_view import (
        render_matching_tab,
    )

    # ログイン状態をモック
    mock_auth.get_user_info.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
    }

    # st.button()をモック（クリックされていない）
    mock_st.button.return_value = False

    # Act
    render_matching_tab()

    # Assert
    # ユーザー情報が表示されることを確認
    mock_st.info.assert_called()
    # get_user_info()が呼ばれたことを確認
    mock_auth.get_user_info.assert_called_once()


@patch("src.interfaces.web.streamlit.views.conversations_speakers_view.st")
def test_render_statistics_tab_displays_metrics(mock_st):
    """統計情報タブがメトリックを表示することを確認"""
    # Arrange
    from src.interfaces.web.streamlit.views.conversations_speakers_view import (
        render_statistics_tab,
    )

    # st.columns()をモック
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_col3 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2, mock_col3)

    # Act
    render_statistics_tab()

    # Assert
    mock_st.subheader.assert_called_once_with("統計情報")
    mock_st.columns.assert_called()


def test_render_conversations_speakers_page_return_type():
    """render_conversations_speakers_page関数の戻り値型がNoneであることを確認"""
    import inspect

    from src.interfaces.web.streamlit.views.conversations_speakers_view import (
        render_conversations_speakers_page,
    )

    sig = inspect.signature(render_conversations_speakers_page)
    assert sig.return_annotation is None


def test_user_info_type_hint_is_correct():
    """user_infoの型ヒントが正しいことを確認"""
    import inspect

    from src.interfaces.web.streamlit.views.conversations_speakers_view import (
        render_matching_tab,
    )

    # 関数のソースコードから型ヒントを確認
    source = inspect.getsource(render_matching_tab)
    # user_infoの型ヒントがdict[str, str] | Noneであることを確認
    assert "user_info: dict[str, str] | None" in source
