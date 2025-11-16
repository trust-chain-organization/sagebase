"""View for conversations and speakers management."""

import asyncio

import streamlit as st

from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.auth import google_sign_in


def render_conversations_speakers_page():
    """Render the conversations and speakers management page."""
    st.header("発言・発言者管理")
    st.markdown("発言記録と発言者の情報を管理します")

    # Create tabs
    tabs = st.tabs(["発言者一覧", "発言マッチング", "統計情報"])

    with tabs[0]:
        render_speakers_list_tab()

    with tabs[1]:
        render_matching_tab()

    with tabs[2]:
        render_statistics_tab()


def render_speakers_list_tab():
    """Render the speakers list tab."""
    st.subheader("発言者一覧")

    # Placeholder for speaker list
    st.info("発言者リストの表示機能は実装中です")

    # Sample data display
    st.markdown("""
    ### 機能概要
    - 発言者の一覧表示
    - 政治家とのマッチング状況
    - 発言回数の統計
    """)


def render_matching_tab():
    """Render the matching tab."""
    st.subheader("発言マッチング")

    st.markdown("""
    ### LLMによる発言者マッチング

    発言者と政治家のマッチングを行います。
    """)

    # Get user info
    user_info = google_sign_in.get_user_info()
    if not user_info:
        st.warning("ユーザー情報を取得できません。ログインしてください。")
        return

    # Display current user
    user_name = user_info.get("name", "Unknown")
    user_email = user_info.get("email", "Unknown")
    st.info(f"実行ユーザー: {user_name} ({user_email})")

    if st.button("マッチング実行", type="primary"):
        with st.spinner("マッチング処理を実行中..."):
            try:
                # Get container and use cases
                container = Container()
                auth_usecase = AuthenticateUserUseCase(
                    user_repository=container.repositories.user_repository()
                )
                match_usecase = MatchSpeakersUseCase(
                    speaker_repository=container.repositories.speaker_repository(),
                    politician_repository=container.repositories.politician_repository(),
                    conversation_repository=container.repositories.conversation_repository(),
                    speaker_domain_service=container.services.speaker_domain_service(),
                    llm_service=container.services.llm_service(),
                )

                # Authenticate user and get user_id
                email = user_info.get("email", "")
                name = user_info.get("name")
                user = asyncio.run(auth_usecase.execute(email=email, name=name))

                # Execute matching with user_id
                results = asyncio.run(
                    match_usecase.execute(
                        use_llm=True,
                        limit=10,  # Limit to 10 for testing
                        user_id=user.user_id,
                    )
                )

                # Display results
                st.success(
                    f"マッチング処理が完了しました。{len(results)}件の発言者を処理しました。"
                )

                # Show summary
                matched_count = sum(1 for r in results if r.matched_politician_id)
                st.metric("マッチング成功", f"{matched_count}/{len(results)}")

                # Show details in expandable section
                with st.expander("マッチング詳細"):
                    for result in results:
                        status = "✅" if result.matched_politician_id else "❌"
                        politician_name = result.matched_politician_name or "マッチなし"
                        st.write(
                            f"{status} {result.speaker_name} → {politician_name} "
                            f"({result.matching_method}, "
                            f"信頼度: {result.confidence_score:.2f})"
                        )

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                st.code(traceback.format_exc())


def render_statistics_tab():
    """Render the statistics tab."""
    st.subheader("統計情報")

    # Statistics placeholders
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("総発言者数", "0名")

    with col2:
        st.metric("マッチング済み", "0名")

    with col3:
        st.metric("マッチング率", "0%")

    st.markdown("""
    ### 詳細統計
    - 会議別発言者数
    - 政党別発言数
    - 時系列発言推移
    """)


def main():
    """Main function for testing."""
    render_conversations_speakers_page()


if __name__ == "__main__":
    main()
