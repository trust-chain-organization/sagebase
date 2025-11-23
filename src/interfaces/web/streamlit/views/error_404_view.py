"""404 Error Page View.

このモジュールは、存在しないページにアクセスした際に表示される
カスタム404エラーページを提供します。
"""

import streamlit as st


def render_404_page():
    """カスタム404エラーページを表示する。

    存在しないページへのアクセス時に、ユーザーフレンドリーな
    エラーメッセージとナビゲーションオプションを提供します。
    """
    st.set_page_config(
        page_title="404 - ページが見つかりません | Polibase",
        page_icon="🔍",
        layout="wide",
    )

    # カスタムCSSで404ページをスタイリング
    st.markdown(
        """
        <style>
        .error-container {
            text-align: center;
            padding: 3rem 1rem;
        }
        .error-code {
            font-size: 6rem;
            font-weight: bold;
            color: #FF4B4B;
            margin-bottom: 1rem;
        }
        .error-message {
            font-size: 1.5rem;
            color: #262730;
            margin-bottom: 2rem;
        }
        .error-description {
            font-size: 1rem;
            color: #808495;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # エラーメッセージの表示
    st.markdown(
        """
        <div class="error-container">
            <div class="error-code">404</div>
            <div class="error-message">お探しのページが見つかりません</div>
            <div class="error-description">
                申し訳ございません。<br>
                お探しのページは存在しないか、移動した可能性があります。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ナビゲーションオプション
    st.markdown("### 📍 こちらはいかがでしょうか？")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🏛️ ホーム")
        st.markdown("トップページに戻る")
        if st.button("ホームへ", key="home"):
            st.switch_page("src/interfaces/web/streamlit/app.py")

    with col2:
        st.markdown("#### 💬 発言レコード")
        st.markdown("会議の発言記録を確認")
        if st.button("発言レコードへ", key="conversations"):
            st.switch_page("pages/conversations.py")

    with col3:
        st.markdown("#### 👤 政治家管理")
        st.markdown("政治家情報を管理")
        if st.button("政治家管理へ", key="politicians"):
            st.switch_page("pages/politicians.py")

    st.divider()

    # サイトマップリンク
    st.markdown("### 🗺️ サイトマップ")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("""
        **データ管理**
        - [会議管理](/meetings)
        - [政党管理](/political_parties)
        - [会議体管理](/conferences)
        - [開催主体管理](/governing_bodies)
        """)

    with col_b:
        st.markdown("""
        **政治家・議員団**
        - [政治家管理](/politicians)
        - [政治家レビュー](/extracted_politicians)
        - [議員団管理](/parliamentary_groups)
        """)

    with col_c:
        st.markdown("""
        **発言・処理**
        - [議案管理](/proposals)
        - [発言レコード一覧](/conversations)
        - [発言・発言者管理](/conversations_speakers)
        - [処理実行](/processes)
        """)

    st.divider()

    # フッター
    st.markdown(
        """
        <div style="text-align: center; color: #808495; padding: 2rem 0;">
            URLが正しいかご確認ください。<br>
            問題が解決しない場合は、管理者にお問い合わせください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ホームページへのリンク
    st.markdown(
        """
        <div style="text-align: center; margin-top: 2rem;">
            <a href="/"
               style="color: #FF4B4B; text-decoration: none; font-weight: bold;">
                🏛️ Polibase ホームに戻る
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
