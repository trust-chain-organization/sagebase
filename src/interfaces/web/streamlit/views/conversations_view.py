"""View for conversations list."""

import streamlit as st


def render_conversations_page() -> None:
    """Render the conversations list page."""
    st.header("発言レコード一覧")
    st.markdown("会議での発言記録を管理・閲覧します")

    # Create tabs
    tabs = st.tabs(["発言一覧", "検索・フィルタ", "エクスポート"])

    with tabs[0]:
        render_conversations_list_tab()

    with tabs[1]:
        render_search_filter_tab()

    with tabs[2]:
        render_export_tab()


def render_conversations_list_tab() -> None:
    """Render the conversations list tab."""
    st.subheader("発言一覧")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        st.selectbox("会議選択", ["すべて"], key="conv_meeting_filter")

    with col2:
        st.selectbox("発言者選択", ["すべて"], key="conv_speaker_filter")

    with col3:
        st.date_input("日付範囲", key="conv_date_filter")

    # Placeholder for conversation list
    st.info("発言レコードの表示機能は実装中です")

    # Sample display
    st.markdown("""
    ### 表示項目
    - 発言ID
    - 会議名
    - 発言者
    - 発言内容（要約）
    - 発言時刻
    - タグ
    """)


def render_search_filter_tab() -> None:
    """Render the search and filter tab."""
    st.subheader("検索・フィルタ")

    # Search box
    st.text_input(
        "キーワード検索",
        placeholder="発言内容を検索...",
    )

    # Advanced filters
    st.markdown("### 詳細フィルタ")

    col1, col2 = st.columns(2)

    with col1:
        st.multiselect("政党", ["自民党", "立憲民主党", "公明党"], key="party_filter")
        st.multiselect("会議体", ["本会議", "委員会"], key="conference_filter")

    with col2:
        st.slider("発言文字数", 0, 1000, (0, 500), key="length_filter")
        st.multiselect("タグ", ["重要", "質問", "答弁"], key="tag_filter")

    if st.button("検索実行", type="primary"):
        with st.spinner("検索中..."):
            st.info("検索機能は実装中です")


def render_export_tab() -> None:
    """Render the export tab."""
    st.subheader("エクスポート")

    st.markdown("""
    ### エクスポート設定

    発言レコードをファイルとしてエクスポートします。
    """)

    # Export format
    export_format = st.radio(
        "エクスポート形式",
        ["CSV", "Excel", "JSON"],
    )

    # Export options
    st.checkbox("発言全文を含める", key="include_full_text")
    st.checkbox("メタデータを含める", key="include_metadata")

    if st.button("エクスポート実行", type="primary"):
        st.info(f"{export_format}形式でのエクスポート機能は実装中です")


def main() -> None:
    """Main function for testing."""
    render_conversations_page()


if __name__ == "__main__":
    main()
