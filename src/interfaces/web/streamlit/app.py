"""Main Streamlit application using Clean Architecture.

This module provides the main entry point for the Streamlit web interface,
following Clean Architecture principles with presenter pattern.
"""

import os

import streamlit as st

from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.components.analytics import inject_google_analytics
from src.interfaces.web.streamlit.components.header import render_header
from src.interfaces.web.streamlit.middleware.security_headers import (
    inject_https_redirect,
    inject_security_headers,
)

# Import new Clean Architecture views
from src.interfaces.web.streamlit.views.conferences_view import render_conferences_page
from src.interfaces.web.streamlit.views.conversations_speakers_view import (
    render_conversations_speakers_page,
)
from src.interfaces.web.streamlit.views.conversations_view import (
    render_conversations_page,
)
from src.interfaces.web.streamlit.views.extracted_politicians_view import (
    render_extracted_politicians_page,
)
from src.interfaces.web.streamlit.views.extraction_logs_view import (
    render_extraction_logs_page,
)
from src.interfaces.web.streamlit.views.governing_bodies_view import (
    render_governing_bodies_page,
)
from src.interfaces.web.streamlit.views.llm_history_view import render_llm_history_page
from src.interfaces.web.streamlit.views.meetings_view import render_meetings_page
from src.interfaces.web.streamlit.views.parliamentary_groups_view import (
    render_parliamentary_groups_page,
)
from src.interfaces.web.streamlit.views.political_parties_view import (
    render_political_parties_page,
)
from src.interfaces.web.streamlit.views.politicians_view import render_politicians_page
from src.interfaces.web.streamlit.views.processes_view import render_processes_page
from src.interfaces.web.streamlit.views.proposals_view import render_proposals_page
from src.interfaces.web.streamlit.views.user_statistics_view import (
    render_user_statistics_page,
)
from src.interfaces.web.streamlit.views.work_history_view import (
    render_work_history_page,
)


def main():
    """Main entry point for the Streamlit application."""
    st.set_page_config(
        page_title="Polibase - Political Activity Tracking",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # セキュリティヘッダーとHTTPSリダイレクトを挿入
    inject_security_headers()
    inject_https_redirect()

    # Google Analytics トラッキングコードを挿入
    inject_google_analytics()

    # 認証チェック
    auth_disabled = os.getenv("GOOGLE_OAUTH_DISABLED", "false").lower() == "true"

    if not auth_disabled and not google_sign_in.is_user_logged_in():
        # 未認証の場合はログインページを表示
        google_sign_in.render_login_page()
        return

    # Define pages with URL routing
    pages = [
        st.Page(render_home_page, title="ホーム", icon="🏛️", url_path="/"),
        st.Page(render_meetings_page, title="会議管理", icon="📅", url_path="meetings"),
        st.Page(
            render_political_parties_page,
            title="政党管理",
            icon="🎯",
            url_path="political_parties",
        ),
        st.Page(
            render_conferences_page,
            title="会議体管理",
            icon="🏢",
            url_path="conferences",
        ),
        st.Page(
            render_governing_bodies_page,
            title="開催主体管理",
            icon="🌐",
            url_path="governing_bodies",
        ),
        st.Page(
            render_politicians_page,
            title="政治家管理",
            icon="👤",
            url_path="politicians",
        ),
        st.Page(
            render_extracted_politicians_page,
            title="政治家レビュー",
            icon="👥",
            url_path="extracted_politicians",
        ),
        st.Page(
            render_parliamentary_groups_page,
            title="議員団管理",
            icon="👥",
            url_path="parliamentary_groups",
        ),
        st.Page(
            render_proposals_page, title="議案管理", icon="📋", url_path="proposals"
        ),
        st.Page(
            render_conversations_page,
            title="発言レコード一覧",
            icon="💬",
            url_path="conversations",
        ),
        st.Page(
            render_conversations_speakers_page,
            title="発言・発言者管理",
            icon="🎤",
            url_path="conversations_speakers",
        ),
        st.Page(
            render_processes_page, title="処理実行", icon="⚙️", url_path="processes"
        ),
        st.Page(
            render_llm_history_page, title="LLM履歴", icon="🤖", url_path="llm_history"
        ),
        st.Page(
            render_extraction_logs_page,
            title="抽出ログ",
            icon="📋",
            url_path="extraction_logs",
        ),
        st.Page(
            render_work_history_page,
            title="作業履歴",
            icon="📋",
            url_path="work_history",
        ),
        st.Page(
            render_user_statistics_page,
            title="作業統計",
            icon="📊",
            url_path="user_statistics",
        ),
    ]

    # Navigation with automatic sidebar
    pg = st.navigation(pages)

    # ヘッダーを表示（ユーザー情報とログアウトボタン）
    render_header()

    # Footer in sidebar
    st.sidebar.divider()
    st.sidebar.caption("© 2024 Polibase")

    # Run the selected page
    pg.run()


def render_home_page():
    """Render the home page."""
    st.title("🏛️ Polibase")
    st.subheader("政治活動追跡アプリケーション")

    st.markdown("""
    ## ようこそ Polibaseへ

    Polibaseは日本の政治活動を追跡・分析するためのアプリケーションです。
    議会の会議録や政治家の情報を管理し、発言記録を分析できます。

    ### 使い方

    左側のサイドバーから管理したい項目を選択してください。各ページには直接URLでアクセスできます。

    ### 主な機能

    - **📅 会議管理**: 議会や委員会の会議情報を管理
    - **🎯 政党管理**: 政党情報と議員一覧URLの管理
    - **🏢 会議体管理**: 議会や委員会などの会議体を管理
    - **🌐 開催主体管理**: 国、都道府県、市町村などの開催主体を管理
    - **👤 政治家管理**: 政治家の情報を管理
    - **👥 政治家レビュー**: スクレイピングで抽出した政治家データの確認
    - **👥 議員団管理**: 議員団・会派の情報を管理
    - **📋 議案管理**: 議案の情報を自動収集・管理
    - **💬 発言レコード一覧**: 会議での発言記録を閲覧
    - **🎤 発言・発言者管理**: 発言者と発言の詳細管理
    - **⚙️ 処理実行**: 各種データ処理の実行
    - **🤖 LLM履歴**: LLM処理の履歴を確認

    ### 基本的なワークフロー

    #### 1. 初期設定
    1. **開催主体管理**で国、都道府県、市町村を確認
    2. **会議体管理**で議会や委員会を設定
    3. **政党管理**で政党情報と議員一覧URLを登録

    #### 2. データ収集
    1. **会議管理**で会議録のPDFをアップロードまたはURLを登録
    2. **処理実行**で会議録を処理（PDFから発言を抽出）
    3. **政党管理**から政治家情報をスクレイピング

    #### 3. データ確認・分析
    1. **発言レコード一覧**で抽出された発言を確認
    2. **政治家管理**で政治家情報を管理
    3. **議案管理**で議案データを確認

    ### ヘルプ

    各ページには詳細なガイドが表示されます。
    問題が発生した場合は、**LLM履歴**で処理ログを確認してください。
    """)


if __name__ == "__main__":
    main()
