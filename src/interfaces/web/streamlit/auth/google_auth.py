"""Google OAuth 2.0 authentication implementation for Streamlit.

このモジュールは、Streamlitアプリケーション向けのGoogle OAuth 2.0認証を提供します。
環境変数から認証設定を読み込み、ホワイトリストベースのアクセス制御を実装します。
"""

import os
from typing import Any

import requests
from streamlit_oauth import OAuth2Component

import streamlit as st


class GoogleAuthenticator:
    """Google OAuth 2.0認証を管理するクラス。

    このクラスは、Google OAuth 2.0フローを簡素化し、
    ホワイトリストベースのアクセス制御を提供します。
    """

    # Google OAuth 2.0エンドポイント
    AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
    USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v1/userinfo"

    # 必要なスコープ
    DEFAULT_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        allowed_emails: list[str] | None = None,
    ):
        """Google認証を初期化します。

        Args:
            client_id: Google OAuth 2.0クライアントID（環境変数から取得可能）
            client_secret: Google OAuth 2.0クライアントシークレット
                （環境変数から取得可能）
            redirect_uri: リダイレクトURI（環境変数から取得可能）
            allowed_emails: 許可されたメールアドレスのリスト
                （環境変数から取得可能）
        """
        self.client_id = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv(
            "GOOGLE_OAUTH_CLIENT_SECRET", ""
        )
        self.redirect_uri = redirect_uri or os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")

        # ホワイトリストの読み込み
        if allowed_emails is None:
            allowed_emails_str = os.getenv("GOOGLE_OAUTH_ALLOWED_EMAILS", "")
            self.allowed_emails = (
                [
                    email.strip()
                    for email in allowed_emails_str.split(",")
                    if email.strip()
                ]
                if allowed_emails_str
                else []
            )
        else:
            self.allowed_emails = allowed_emails

        # 設定の検証
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Google OAuth credentials not configured. "
                "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET "
                "environment variables."
            )

        # OAuth2Componentの初期化
        self.oauth2 = OAuth2Component(
            client_id=self.client_id,
            client_secret=self.client_secret,
            authorize_endpoint=self.AUTHORIZE_ENDPOINT,
            token_endpoint=self.TOKEN_ENDPOINT,
            refresh_token_endpoint=self.TOKEN_ENDPOINT,
            revoke_token_endpoint=self.REVOKE_ENDPOINT,
        )

    def is_email_allowed(self, email: str) -> bool:
        """メールアドレスがホワイトリストに含まれているか確認します。

        Args:
            email: 確認するメールアドレス

        Returns:
            ホワイトリストが空の場合はTrue、
            それ以外の場合はメールアドレスがホワイトリストに含まれているかどうか
        """
        # ホワイトリストが設定されていない場合は全て許可
        if not self.allowed_emails:
            return True
        return email.lower() in [e.lower() for e in self.allowed_emails]

    def get_user_info(self, access_token: str) -> dict[str, Any] | None:
        """アクセストークンを使用してユーザー情報を取得します。

        Args:
            access_token: Googleアクセストークン

        Returns:
            ユーザー情報の辞書、エラーの場合はNone
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(self.USERINFO_ENDPOINT, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            st.error(f"ユーザー情報の取得に失敗しました: {e}")
            return None

    def authorize_button(
        self,
        button_text: str = "Googleでログイン",
        key: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Google OAuth認証ボタンを表示します。

        Args:
            button_text: ボタンに表示するテキスト
            key: Streamlitコンポーネントのキー
            **kwargs: OAuth2Componentに渡す追加のパラメータ

        Returns:
            認証結果の辞書、認証されていない場合はNone
        """
        scope = " ".join(self.DEFAULT_SCOPES)

        # デフォルトパラメータを設定
        params = {
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "extras_params": {"access_type": "offline", "prompt": "consent"},
            "key": key or "google_oauth",
            "use_container_width": True,
        }
        params.update(kwargs)

        result = self.oauth2.authorize_button(button_text, **params)

        if result and "token" in result:
            return result

        return None

    def logout(self, token: dict[str, Any]) -> bool:
        """ユーザーをログアウトします。

        Args:
            token: 無効化するトークン

        Returns:
            ログアウトが成功した場合True
        """
        try:
            self.oauth2.revoke_token(token)
            return True
        except Exception as e:
            st.error(f"ログアウトに失敗しました: {e}")
            return False
