"""認証ミドルウェア。

このモジュールは、Streamlitページへのアクセスを制御する認証ミドルウェアを提供します。
未認証のユーザーがアクセスした場合、ログインページを表示します。
"""

import os

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.auth.google_sign_in import render_login_page


__all__ = ["require_auth", "render_login_page"]


def require_auth[F: Callable[..., Any]](func: F) -> F:
    """認証を必須とするデコレータ。

    このデコレータは、関数実行前にユーザーの認証状態をチェックします。
    未認証の場合はログインページを表示し、認証済みの場合は元の関数を実行します。

    Args:
        func: デコレートする関数

    Returns:
        デコレートされた関数

    Example:
        @require_auth
        def my_protected_page():
            st.write("この内容は認証されたユーザーのみ閲覧可能")
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # 認証が無効化されている場合はスキップ
        auth_disabled = os.getenv("GOOGLE_OAUTH_DISABLED", "false").lower() == "true"
        if auth_disabled:
            return func(*args, **kwargs)

        # 認証状態をチェック
        if google_sign_in.is_user_logged_in():
            # 認証済み - 元の関数を実行
            return func(*args, **kwargs)

        # 未認証 - ログインページを表示
        google_sign_in.render_login_page()
        st.stop()
        return None

    return wrapper  # type: ignore
