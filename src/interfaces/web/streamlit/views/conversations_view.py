"""View for conversations list."""

import asyncio

import pandas as pd
import streamlit as st

from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.components import (
    get_verification_badge_text,
    render_verification_filter,
)


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

    # Initialize repositories
    conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)

    # Get all meetings for filter
    meetings = meeting_repo.get_all()
    meeting_options = {"すべて": None}
    meeting_options.update({m.title or f"会議 {m.id}": m.id for m in meetings[:100]})

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_meeting = st.selectbox(
            "会議選択", list(meeting_options.keys()), key="conv_meeting_filter"
        )
        meeting_id = meeting_options[selected_meeting]

    with col2:
        search_text = st.text_input("発言者名で検索", key="conv_speaker_search")

    with col3:
        limit = st.number_input(
            "表示件数", min_value=10, max_value=500, value=50, key="conv_limit"
        )

    with col4:
        verification_filter = render_verification_filter(key="conv_verification")

    # Load conversations
    if meeting_id:
        conversations = conversation_repo.get_by_meeting(meeting_id, limit=limit)
    else:
        conversations = conversation_repo.get_all(limit=limit)

    # Filter by speaker name
    if search_text:
        conversations = [
            c for c in conversations if search_text.lower() in c.speaker_name.lower()
        ]

    # Filter by verification status
    if verification_filter is not None:
        conversations = [
            c for c in conversations if c.is_manually_verified == verification_filter
        ]

    if not conversations:
        st.info("該当する発言レコードがありません")
        return

    # Statistics
    st.markdown(f"### 検索結果: {len(conversations)}件")

    verified_count = sum(1 for c in conversations if c.is_manually_verified)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("手動検証済み", f"{verified_count}件")
    with col2:
        st.metric("未検証", f"{len(conversations) - verified_count}件")

    # Initialize verification use case
    verify_use_case = MarkEntityAsVerifiedUseCase(
        conversation_repository=conversation_repo  # type: ignore[arg-type]
    )

    # Convert to DataFrame
    data = []
    for c in conversations:
        data.append(
            {
                "ID": c.id,
                "発言者": c.speaker_name,
                "会議ID": c.meeting_id,
                "発言内容": c.content[:100] + "..."
                if len(c.content) > 100
                else c.content,
                "検証状態": get_verification_badge_text(c.is_manually_verified),
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail and verification section
    st.markdown("### 発言詳細と検証状態更新")

    for conversation in conversations[:20]:  # Limit to 20 for performance
        with st.expander(
            f"{conversation.speaker_name}: {conversation.content[:50]}... "
            f"- {get_verification_badge_text(conversation.is_manually_verified)}"
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** {conversation.id}")
                st.write(f"**発言者:** {conversation.speaker_name}")
                st.write(f"**会議ID:** {conversation.meeting_id}")
                st.markdown("**発言内容:**")
                st.text_area(
                    "発言内容",
                    value=conversation.content,
                    height=150,
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"content_{conversation.id}",
                )

            with col2:
                st.markdown("#### 検証状態")
                current_verified = conversation.is_manually_verified
                new_verified = st.checkbox(
                    "手動検証済み",
                    value=current_verified,
                    key=f"verify_conv_{conversation.id}",
                    help="チェックすると、AI再実行でこのデータが上書きされなくなります",
                )

                if new_verified != current_verified:
                    if st.button(
                        "検証状態を更新",
                        key=f"update_verify_conv_{conversation.id}",
                        type="primary",
                    ):
                        result = asyncio.run(
                            verify_use_case.execute(
                                MarkEntityAsVerifiedInputDto(
                                    entity_type=EntityType.CONVERSATION,
                                    entity_id=conversation.id,  # type: ignore[arg-type]
                                    is_verified=new_verified,
                                )
                            )
                        )
                        if result.success:
                            status_text = "手動検証済み" if new_verified else "未検証"
                            st.success(f"検証状態を「{status_text}」に更新しました")
                            st.rerun()
                        else:
                            st.error(f"更新に失敗しました: {result.error_message}")


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
