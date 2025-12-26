"""ヘッダーコンポーネント。

このモジュールは、Streamlitアプリケーションのヘッダーを提供します。
ユーザーのログイン状態を表示し、ログアウト機能を提供します。
"""

import os

import streamlit as st

from src.interfaces.web.streamlit.auth import google_sign_in


def render_header() -> None:
    """アプリケーションのヘッダーをレンダリングします。

    ユーザーのログイン状態を表示し、ログアウトボタンを提供します。
    認証が無効化されている場合は、開発モードであることを表示します。
    """
    auth_disabled = os.getenv("GOOGLE_OAUTH_DISABLED", "false").lower() == "true"

    # サイドバーにユーザー情報を表示
    with st.sidebar:
        st.divider()

        if auth_disabled:
            st.caption("🔓 開発モード（認証無効）")
        elif google_sign_in.is_user_logged_in():
            _render_authenticated_user_info()
        else:
            st.caption("未認証")


def _render_authenticated_user_info() -> None:
    """認証済みユーザーの情報を表示します。"""
    user_info = google_sign_in.get_user_info()

    if not user_info:
        return

    # ユーザー情報を表示
    user_name = user_info.get("name", "")
    user_email = user_info.get("email", "")
    user_picture = user_info.get("picture", "")

    # プロフィール画像とユーザー名を表示
    col1, col2 = st.columns([1, 3])

    with col1:
        if user_picture:
            st.image(user_picture, width=50)
        else:
            st.write("👤")

    with col2:
        if user_name:
            st.caption(f"**{user_name}**")
        st.caption(user_email)

    # ログアウトボタン
    if st.button("🚪 ログアウト", use_container_width=True, key="logout_button"):
        _handle_logout()


def _handle_logout() -> None:
    """ログアウト処理を実行します。"""
    try:
        # Streamlit標準のログアウトを実行
        google_sign_in.logout_user()
        # ページをリロード
        st.rerun()
    except Exception as e:
        st.error(f"ログアウトに失敗しました: {e}")
