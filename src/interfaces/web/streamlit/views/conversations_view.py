"""View for conversations and speakers management (unified page).

This module combines the functionality of the former conversations list page
and conversations speakers page into a single unified page.
"""

import asyncio

import pandas as pd
import streamlit as st

from src.application.usecases.authenticate_user_usecase import (
    AuthenticateUserUseCase,
)
from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.infrastructure.di.container import Container
from src.infrastructure.external.langgraph_tools.politician_matching_tools import (
    create_politician_matching_tools,
)
from src.infrastructure.external.langgraph_tools.speaker_matching_tools import (
    create_speaker_matching_tools,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.components import (
    get_verification_badge_text,
    render_verification_filter,
)


def render_conversations_page() -> None:
    """Render the conversations and speakers management page."""
    st.header("発言・発言者管理")
    st.markdown("発言記録と発言者の情報を管理します")

    # Create tabs
    tabs = st.tabs(
        [
            "発言一覧",
            "検索・フィルタ",
            "発言者一覧",
            "発言マッチング",
            "統計情報",
            "ツールテスト",
            "Agentテスト",
            "政治家マッチングAgent",
        ]
    )

    with tabs[0]:
        render_conversations_list_tab()

    with tabs[1]:
        render_search_filter_tab()

    with tabs[2]:
        render_speakers_list_tab()

    with tabs[3]:
        render_matching_tab()

    with tabs[4]:
        render_statistics_tab()

    with tabs[5]:
        render_tools_test_tab()

    with tabs[6]:
        render_agent_test_tab()

    with tabs[7]:
        render_politician_matching_agent_tab()


def render_conversations_list_tab() -> None:
    """Render the conversations list tab."""
    st.subheader("発言一覧")

    # Initialize repositories
    conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)

    # Get all meetings for filter
    meetings = meeting_repo.get_all()
    meeting_options: dict[str, int | None] = {"すべて": None}
    meeting_options.update({m.name or f"会議 {m.id}": m.id for m in meetings[:100]})

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
        conversations = conversation_repo.get_by_minutes(meeting_id, limit=limit)
    else:
        conversations = conversation_repo.get_all(limit=limit)

    # Filter by speaker name
    if search_text:
        conversations = [
            c
            for c in conversations
            if c.speaker_name and search_text.lower() in c.speaker_name.lower()
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
        comment_preview = c.comment[:100] + "..." if len(c.comment) > 100 else c.comment
        data.append(
            {
                "ID": c.id,
                "発言者": c.speaker_name or "-",
                "議事録ID": c.minutes_id,
                "発言内容": comment_preview,
                "検証状態": get_verification_badge_text(c.is_manually_verified),
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail and verification section
    st.markdown("### 発言詳細と検証状態更新")

    for conversation in conversations[:20]:  # Limit to 20 for performance
        speaker = conversation.speaker_name or "-"
        comment_short = (
            conversation.comment[:50] + "..."
            if len(conversation.comment) > 50
            else conversation.comment
        )
        badge = get_verification_badge_text(conversation.is_manually_verified)
        with st.expander(f"{speaker}: {comment_short} - {badge}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**ID:** {conversation.id}")
                st.write(f"**発言者:** {speaker}")
                st.write(f"**議事録ID:** {conversation.minutes_id}")
                st.markdown("**発言内容:**")
                st.text_area(
                    "発言内容",
                    value=conversation.comment,
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
                                    entity_id=conversation.id,
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


def render_speakers_list_tab() -> None:
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


def render_matching_tab() -> None:
    """Render the matching tab."""
    st.subheader("発言マッチング")

    st.markdown("""
    ### LLMによる発言者マッチング

    発言者と政治家のマッチングを行います。
    """)

    # Get user info
    user_info: dict[str, str] | None = google_sign_in.get_user_info()
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
                # Import services directly (same pattern as meeting_presenter.py)
                # Get container for repositories and use cases
                container = Container.create_for_environment()

                # Initialize use cases
                auth_usecase = AuthenticateUserUseCase(
                    user_repository=container.repositories.user_repository()
                )
                # DIコンテナからMatchSpeakersUseCaseを取得
                match_usecase = container.use_cases.match_speakers_usecase()

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


def render_statistics_tab() -> None:
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


def render_tools_test_tab() -> None:
    """Render the speaker matching tools test tab."""
    st.subheader("名寄せツールテスト")

    st.markdown("""
    ### 名寄せAgent用ツールの動作確認

    3つのツールを個別にテストできます：
    1. **evaluate_matching_candidates**: マッチング候補の評価
    2. **search_additional_info**: 追加情報の検索
    3. **judge_confidence**: 確信度の判定
    """)

    # Create sub-tabs for each tool
    tool_tabs = st.tabs(["候補評価", "追加情報検索", "確信度判定"])

    with tool_tabs[0]:
        render_evaluate_candidates_test()

    with tool_tabs[1]:
        render_search_info_test()

    with tool_tabs[2]:
        render_judge_confidence_test()


def render_evaluate_candidates_test() -> None:
    """Test evaluate_matching_candidates tool."""
    st.subheader("マッチング候補の評価")

    st.markdown("""
    発言者名を入力すると、政治家候補をスコア順に表示します。
    """)

    # Input form
    speaker_name = st.text_input(
        "発言者名", value="田中太郎", help="マッチング対象の発言者名を入力してください"
    )

    col1, col2 = st.columns(2)
    with col1:
        meeting_date = st.date_input(
            "会議開催日（オプション）",
            value=None,
            help="会議開催日を指定すると、所属情報を考慮します",
        )

    with col2:
        conference_id = st.number_input(
            "会議体ID（オプション）",
            value=None,
            min_value=1,
            help="会議体IDを指定すると、所属情報を考慮します",
        )

    max_candidates = st.slider(
        "最大候補数", min_value=1, max_value=20, value=10, help="返す候補の最大数"
    )

    if st.button("候補を評価", type="primary", key="eval_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        with st.spinner("候補を評価中..."):
            try:
                # Get container for repositories
                container = Container.create_for_environment()

                # Create tools with repositories
                tools = create_speaker_matching_tools(
                    speaker_repo=container.repositories.speaker_repository(),
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=container.repositories.politician_affiliation_repository(),
                )
                evaluate_tool = tools[0]

                # Prepare input
                tool_input = {
                    "speaker_name": speaker_name,
                    "max_candidates": max_candidates,
                }

                if meeting_date:
                    tool_input["meeting_date"] = meeting_date.isoformat()

                if conference_id:
                    tool_input["conference_id"] = int(conference_id)

                # Execute tool
                result = asyncio.run(evaluate_tool.ainvoke(tool_input))

                # Display results
                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    st.success(
                        f"✅ {result['total_candidates']}人の候補から"
                        f"上位{len(result['candidates'])}人を表示"
                    )

                    # Display evaluation criteria
                    with st.expander("評価基準"):
                        criteria = result.get("evaluation_criteria", {})
                        st.json(criteria)

                    # Display candidates
                    st.markdown("### マッチング候補")
                    for i, candidate in enumerate(result.get("candidates", []), 1):
                        with st.container():
                            col1, col2, col3 = st.columns([3, 2, 2])

                            with col1:
                                st.markdown(
                                    f"**{i}. {candidate.get('politician_name')}**"
                                )

                            with col2:
                                score = candidate.get("score", 0.0)
                                st.metric("スコア", f"{score:.2f}")

                            with col3:
                                match_type = candidate.get("match_type", "")
                                type_label = {
                                    "exact": "完全一致",
                                    "partial": "部分一致",
                                    "fuzzy": "類似",
                                }.get(match_type, match_type)
                                st.write(type_label)

                            # Additional info
                            party = candidate.get("party")
                            if party:
                                st.caption(f"政党: {party}")

                            is_affiliated = candidate.get("is_affiliated", False)
                            if is_affiliated:
                                st.caption("✅ 会議体所属")

                            st.divider()

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())


def render_search_info_test() -> None:
    """Test search_additional_info tool."""
    st.subheader("追加情報の検索")

    st.markdown("""
    政治家または発言者のIDを指定して、追加情報を取得します。
    """)

    # Input form
    entity_type = st.selectbox(
        "エンティティタイプ",
        options=["politician", "speaker"],
        format_func=lambda x: {"politician": "政治家", "speaker": "発言者"}[x],
        help="検索対象のエンティティタイプ",
    )

    entity_id = st.number_input(
        "エンティティID", value=1, min_value=1, help="検索対象のID"
    )

    info_types = st.multiselect(
        "取得する情報タイプ",
        options=["affiliation", "party", "history"],
        default=["affiliation", "party"],
        format_func=lambda x: {
            "affiliation": "所属情報",
            "party": "政党情報",
            "history": "履歴情報",
        }[x],
        help="取得する情報のタイプを選択",
    )

    if st.button("情報を検索", type="primary", key="search_button"):
        with st.spinner("情報を検索中..."):
            try:
                # Get container for repositories
                container = Container.create_for_environment()

                # Create tools with repositories
                tools = create_speaker_matching_tools(
                    speaker_repo=container.repositories.speaker_repository(),
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=container.repositories.politician_affiliation_repository(),
                )
                search_tool = tools[1]

                # Execute tool
                result = asyncio.run(
                    search_tool.ainvoke(
                        {
                            "entity_type": entity_type,
                            "entity_id": entity_id,
                            "info_types": info_types,
                        }
                    )
                )

                # Display results
                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    st.success(f"✅ {result['entity_name']} の情報を取得しました")

                    # Display basic info
                    st.markdown("### 基本情報")
                    st.write(f"- **エンティティタイプ**: {result['entity_type']}")
                    st.write(f"- **エンティティID**: {result['entity_id']}")
                    st.write(f"- **名前**: {result['entity_name']}")

                    # Display additional info
                    info = result.get("info", {})

                    if "affiliation" in info and info["affiliation"]:
                        st.markdown("### 所属情報")
                        for aff in info["affiliation"]:
                            with st.container():
                                st.write(f"**{aff.get('conference_name', 'Unknown')}**")
                                st.write(f"- 開始日: {aff.get('start_date', 'N/A')}")
                                st.write(f"- 終了日: {aff.get('end_date', 'N/A')}")
                                st.divider()

                    if "party" in info and info["party"]:
                        st.markdown("### 政党情報")
                        party = info["party"]
                        st.write(f"- **政党名**: {party.get('party_name', 'N/A')}")
                        if party.get("party_id"):
                            st.write(f"- **政党ID**: {party.get('party_id')}")

                    if "history" in info and info["history"]:
                        st.markdown("### 履歴情報")
                        st.json(info["history"])

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())


def render_judge_confidence_test() -> None:
    """Test judge_confidence tool."""
    st.subheader("確信度の判定")

    st.markdown("""
    マッチング候補の情報を入力して、確信度を判定します。
    """)

    # Input form for speaker name
    speaker_name = st.text_input(
        "発言者名", value="田中太郎", help="マッチング対象の発言者名"
    )

    st.markdown("### 候補情報")

    col1, col2 = st.columns(2)
    with col1:
        politician_id = st.number_input("政治家ID", value=101, min_value=1)
        politician_name = st.text_input("政治家名", value="田中太郎")

    with col2:
        party = st.text_input("政党", value="〇〇党")
        score = st.slider("スコア", min_value=0.0, max_value=1.0, value=0.85, step=0.05)

    match_type = st.selectbox(
        "マッチタイプ",
        options=["exact", "partial", "fuzzy"],
        format_func=lambda x: {
            "exact": "完全一致",
            "partial": "部分一致",
            "fuzzy": "類似",
        }[x],
    )

    is_affiliated = st.checkbox("会議体所属", value=False)

    # Optional additional info
    use_additional_info = st.checkbox("追加情報を使用", value=False)

    additional_info = None
    if use_additional_info:
        st.markdown("### 追加情報（オプション）")
        has_affiliation = st.checkbox("所属情報あり", value=True)
        has_party = st.checkbox("政党情報あり", value=True)

        additional_info = {
            "entity_type": "politician",
            "entity_id": politician_id,
            "entity_name": politician_name,
            "info": {},
        }

        if has_affiliation:
            additional_info["info"]["affiliation"] = [
                {
                    "conference_id": 1,
                    "conference_name": "〇〇市議会",
                    "start_date": "2023-01-01",
                    "end_date": None,
                }
            ]

        if has_party:
            additional_info["info"]["party"] = {"party_id": 1, "party_name": party}

    if st.button("確信度を判定", type="primary", key="judge_button"):
        if not speaker_name or not politician_name:
            st.warning("発言者名と政治家名を入力してください")
            return

        with st.spinner("確信度を判定中..."):
            try:
                # Get container for repositories
                container = Container.create_for_environment()

                # Create tools with repositories
                tools = create_speaker_matching_tools(
                    speaker_repo=container.repositories.speaker_repository(),
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=container.repositories.politician_affiliation_repository(),
                )
                judge_tool = tools[2]

                # Prepare candidate
                candidate = {
                    "politician_id": politician_id,
                    "politician_name": politician_name,
                    "party": party,
                    "score": score,
                    "match_type": match_type,
                    "is_affiliated": is_affiliated,
                }

                # Execute tool
                tool_input = {
                    "speaker_name": speaker_name,
                    "candidate": candidate,
                }

                if additional_info:
                    tool_input["additional_info"] = additional_info

                result = asyncio.run(judge_tool.ainvoke(tool_input))

                # Display results
                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    # Main metrics
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        confidence = result.get("confidence", 0.0)
                        st.metric("確信度", f"{confidence:.2f}")

                    with col2:
                        level = result.get("confidence_level", "unknown")
                        level_label = {
                            "high": "高",
                            "medium": "中",
                            "low": "低",
                        }.get(level, level)
                        st.metric("レベル", level_label)

                    with col3:
                        should_match = result.get("should_match", False)
                        match_label = "✅ 推奨" if should_match else "❌ 非推奨"
                        st.metric("マッチング", match_label)

                    # Reason
                    st.markdown("### 判定理由")
                    st.info(result.get("reason", ""))

                    # Recommendation
                    st.markdown("### 推奨アクション")
                    st.success(result.get("recommendation", ""))

                    # Contributing factors
                    st.markdown("### 確信度に寄与した要素")
                    factors = result.get("contributing_factors", [])
                    for factor in factors:
                        with st.container():
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**{factor.get('description')}**")
                            with col2:
                                impact = factor.get("impact", 0.0)
                                st.metric("影響", f"+{impact:.2f}")

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())


def render_agent_test_tab() -> None:
    """Test SpeakerMatchingAgent."""
    st.subheader("名寄せAgentテスト")

    st.markdown("""
    ### SpeakerMatchingAgent の動作確認

    LangGraphのReActエージェントを使用した発言者-政治家マッチングをテストします。
    エージェントは3つのツールを使って反復的にマッチングを行います。

    **使用するツール:**
    1. `evaluate_matching_candidates`: 候補評価
    2. `search_additional_info`: 追加情報検索
    3. `judge_confidence`: 確信度判定
    """)

    # Input form
    st.markdown("### 入力")
    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        help="マッチング対象の発言者名を入力してください",
        key="agent_test_speaker_name",
    )

    col1, col2 = st.columns(2)
    with col1:
        meeting_date = st.date_input(
            "会議開催日（オプション）",
            value=None,
            help="会議開催日を指定すると、所属情報を考慮します",
            key="agent_test_meeting_date",
        )

    with col2:
        conference_id = st.number_input(
            "会議体ID（オプション）",
            value=None,
            min_value=1,
            help="会議体IDを指定すると、所属情報を考慮します",
            key="agent_test_conference_id",
        )

    # Advanced settings
    with st.expander("詳細設定"):
        st.info(
            "エージェントの設定（現在は固定値）\n\n"
            "- MAX_REACT_STEPS: 10\n"
            "- 確信度閾値: 0.8"
        )

    if st.button("Agentを実行", type="primary", key="agent_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        with st.spinner("エージェントを実行中..."):
            try:
                # Get container for repositories
                container = Container.create_for_environment()

                # Create LLM service
                from langchain_google_genai import ChatGoogleGenerativeAI

                from src.infrastructure.external import (
                    langgraph_speaker_matching_agent as agent_module,
                )

                llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")

                # Create agent
                agent = agent_module.SpeakerMatchingAgent(
                    llm=llm,
                    speaker_repo=container.repositories.speaker_repository(),
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=container.repositories.politician_affiliation_repository(),
                )

                # Prepare input
                agent_input = {"speaker_name": speaker_name}

                if meeting_date:
                    agent_input["meeting_date"] = meeting_date.isoformat()

                if conference_id:
                    pass  # conference_id is handled in match_speaker call

                # Execute agent
                result = asyncio.run(
                    agent.match_speaker(
                        speaker_name=speaker_name,
                        meeting_date=meeting_date.isoformat() if meeting_date else None,
                        conference_id=int(conference_id) if conference_id else None,
                    )
                )

                # Display results
                st.markdown("### マッチング結果")

                if result.get("error_message"):
                    st.error(f"エラー: {result['error_message']}")
                elif result["matched"]:
                    # Success case
                    st.success("✅ マッチング成功！")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "マッチした政治家",
                            result.get("politician_name", "Unknown"),
                        )
                    with col2:
                        confidence = result.get("confidence", 0.0)
                        st.metric("確信度", f"{confidence:.2f}")

                    # Reason
                    st.markdown("### 判定理由")
                    st.info(result.get("reason", ""))

                    # Show politician details
                    with st.expander("政治家詳細"):
                        st.json(
                            {
                                "politician_id": result.get("politician_id"),
                                "politician_name": result.get("politician_name"),
                                "confidence": result.get("confidence"),
                            }
                        )

                else:
                    # No match case
                    st.warning("マッチする政治家が見つかりませんでした")
                    st.info(result.get("reason", ""))

                # Show full result
                with st.expander("詳細結果（JSON）"):
                    st.json(result)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())

    # Usage example
    st.markdown("---")
    st.markdown("""
    ### 使い方

    1. **発言者名** を入力（例: 田中太郎）
    2. 必要に応じて **会議開催日** と **会議体ID** を入力
    3. **「Agentを実行」** ボタンをクリック
    4. エージェントが自動的にツールを使ってマッチングを行います

    **動作の流れ:**
    1. エージェントが候補評価ツールで政治家候補を取得
    2. 上位候補の追加情報を検索
    3. 確信度判定ツールで最終判定
    4. 確信度0.8以上ならマッチング成功

    **注意:**
    - エージェントの実行には数秒〜十数秒かかることがあります
    - LLM API（Gemini）を使用するため、API キーが必要です
    """)


def render_politician_matching_agent_tab() -> None:
    """Test PoliticianMatchingAgent (Issue #904)."""
    st.subheader("政治家マッチングAgentテスト")

    st.markdown("""
    ### PoliticianMatchingAgent の動作確認 (Issue #904)

    LangGraphのReActエージェントを使用した政治家マッチングをテストします。
    BAMLをLLM通信層として使用し、反復的推論で高精度なマッチングを実現します。

    **使用するツール:**
    1. `search_politician_candidates`: 候補検索・スコアリング
    2. `verify_politician_affiliation`: 所属情報検証
    3. `match_politician_with_baml`: BAMLマッチング実行
    """)

    # Create sub-tabs for tools and agent test
    sub_tabs = st.tabs(["ツール個別テスト", "Agentテスト"])

    with sub_tabs[0]:
        render_politician_matching_tools_test()

    with sub_tabs[1]:
        render_politician_matching_agent_test()


def render_politician_matching_tools_test() -> None:
    """Test politician matching tools individually."""
    st.markdown("### 政治家マッチング用ツールの個別テスト")

    tool_tabs = st.tabs(["候補検索", "所属検証", "BAMLマッチング"])

    with tool_tabs[0]:
        render_politician_search_test()

    with tool_tabs[1]:
        render_politician_affiliation_test()

    with tool_tabs[2]:
        render_politician_baml_match_test()


def render_politician_search_test() -> None:
    """Test search_politician_candidates tool."""
    st.subheader("政治家候補の検索・スコアリング")

    st.markdown("発言者名を入力すると、政治家候補をスコア順に表示します。")

    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        help="マッチング対象の発言者名",
        key="pol_search_speaker_name",
    )

    speaker_party = st.text_input(
        "所属政党（オプション）",
        value="",
        help="政党が一致するとスコアがブーストされます",
        key="pol_search_party",
    )

    max_candidates = st.slider(
        "最大候補数",
        min_value=5,
        max_value=30,
        value=10,
        key="pol_search_max",
    )

    if st.button("候補を検索", type="primary", key="pol_search_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        with st.spinner("候補を検索中..."):
            try:
                container = Container.create_for_environment()
                tools = create_politician_matching_tools(
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=(
                        container.repositories.politician_affiliation_repository()
                    ),
                )
                search_tool = tools[0]

                tool_input = {
                    "speaker_name": speaker_name,
                    "max_candidates": max_candidates,
                }
                if speaker_party:
                    tool_input["speaker_party"] = speaker_party

                result = asyncio.run(search_tool.ainvoke(tool_input))

                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    st.success(
                        f"✅ {result['total_candidates']}人の候補から"
                        f"上位{len(result['candidates'])}人を表示"
                    )

                    for i, candidate in enumerate(result.get("candidates", []), 1):
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.markdown(f"**{i}. {candidate.get('politician_name')}**")
                        with col2:
                            score = candidate.get("score", 0.0)
                            st.metric("スコア", f"{score:.2f}")
                        with col3:
                            match_type = candidate.get("match_type", "")
                            type_label = {
                                "exact": "完全一致",
                                "partial": "部分一致",
                                "fuzzy": "類似",
                                "none": "なし",
                            }.get(match_type, match_type)
                            st.write(type_label)

                        party = candidate.get("party_name")
                        if party:
                            st.caption(f"政党: {party}")
                        st.divider()

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())


def render_politician_affiliation_test() -> None:
    """Test verify_politician_affiliation tool."""
    st.subheader("政治家所属情報の検証")

    st.markdown("政治家IDを指定して、所属情報を検証します。")

    politician_id = st.number_input(
        "政治家ID",
        value=1,
        min_value=1,
        key="pol_aff_id",
    )

    expected_party = st.text_input(
        "期待される政党（オプション）",
        value="",
        help="指定すると、政党の一致を確認します",
        key="pol_aff_party",
    )

    if st.button("所属を検証", type="primary", key="pol_aff_button"):
        with st.spinner("所属情報を検証中..."):
            try:
                container = Container.create_for_environment()
                tools = create_politician_matching_tools(
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=(
                        container.repositories.politician_affiliation_repository()
                    ),
                )
                verify_tool = tools[1]

                tool_input: dict[str, int | str] = {"politician_id": politician_id}
                if expected_party:
                    tool_input["expected_party"] = expected_party

                result = asyncio.run(verify_tool.ainvoke(tool_input))

                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    st.success(f"✅ {result['politician_name']} の情報を取得しました")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("政治家名", result.get("politician_name", "N/A"))
                    with col2:
                        st.metric("所属政党", result.get("current_party", "N/A"))

                    if expected_party:
                        party_matches = result.get("party_matches")
                        if party_matches:
                            st.success("✅ 政党が一致しています")
                        else:
                            st.warning("政党が一致しません")

                    affiliations = result.get("affiliations", [])
                    if affiliations:
                        st.markdown("### 所属会議体")
                        for aff in affiliations:
                            st.write(
                                f"- 会議体ID: {aff.get('conference_id')}, "
                                f"開始: {aff.get('start_date')}, "
                                f"終了: {aff.get('end_date', '現在')}"
                            )

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())


def render_politician_baml_match_test() -> None:
    """Test match_politician_with_baml tool."""
    st.subheader("BAMLによる政治家マッチング")

    st.markdown("BAMLを使用して、候補から最適な政治家を選択します。")

    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        key="pol_baml_speaker",
    )

    col1, col2 = st.columns(2)
    with col1:
        speaker_type = st.text_input(
            "発言者種別",
            value="議員",
            key="pol_baml_type",
        )
    with col2:
        speaker_party = st.text_input(
            "発言者政党",
            value="〇〇党",
            key="pol_baml_party",
        )

    st.markdown("### 候補政治家（JSON）")
    default_json = (
        '[{"politician_id": 1, "politician_name": "田中太郎", "party_name": "〇〇党"}]'
    )
    candidates_json = st.text_area(
        "候補JSON",
        value=default_json,
        height=100,
        key="pol_baml_candidates",
    )

    if st.button("BAMLマッチング実行", type="primary", key="pol_baml_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        with st.spinner("BAMLマッチング中..."):
            try:
                container = Container.create_for_environment()
                tools = create_politician_matching_tools(
                    politician_repo=container.repositories.politician_repository(),
                    affiliation_repo=(
                        container.repositories.politician_affiliation_repository()
                    ),
                )
                match_tool = tools[2]

                result = asyncio.run(
                    match_tool.ainvoke(
                        {
                            "speaker_name": speaker_name,
                            "speaker_type": speaker_type,
                            "speaker_party": speaker_party,
                            "candidates_json": candidates_json,
                        }
                    )
                )

                if "error" in result:
                    st.error(f"エラー: {result['error']}")
                else:
                    if result.get("matched"):
                        st.success("✅ マッチング成功！")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "マッチした政治家",
                                result.get("politician_name"),
                            )
                        with col2:
                            st.metric(
                                "信頼度",
                                f"{result.get('confidence', 0):.2f}",
                            )
                        st.info(f"理由: {result.get('reason')}")
                    else:
                        st.warning("マッチなし")
                        st.info(f"理由: {result.get('reason')}")

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())


def render_politician_matching_agent_test() -> None:
    """Test PoliticianMatchingAgent."""
    st.markdown("### PoliticianMatchingAgent の実行")

    st.info(
        "このエージェントはReActパターンで動作し、"
        "3つのツールを使って反復的にマッチングを行います。"
    )

    speaker_name = st.text_input(
        "発言者名",
        value="田中太郎",
        help="マッチング対象の発言者名",
        key="pol_agent_speaker",
    )

    col1, col2 = st.columns(2)
    with col1:
        speaker_type = st.text_input(
            "発言者種別（オプション）",
            value="",
            help="例: 議員、委員",
            key="pol_agent_type",
        )
    with col2:
        speaker_party = st.text_input(
            "発言者政党（オプション）",
            value="",
            help="所属政党",
            key="pol_agent_party",
        )

    with st.expander("詳細設定"):
        st.info(
            "エージェントの設定（現在は固定値）\n\n"
            "- MAX_REACT_STEPS: 10\n"
            "- 信頼度閾値: 0.7"
        )

    if st.button("政治家マッチングAgentを実行", type="primary", key="pol_agent_btn"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        with st.spinner("エージェントを実行中..."):
            try:
                # DIコンテナからエージェントを取得（Clean Architecture準拠）
                container = Container.create_for_environment()
                agent = container.use_cases.politician_matching_agent()

                result = asyncio.run(
                    agent.match_politician(
                        speaker_name=speaker_name,
                        speaker_type=speaker_type or None,
                        speaker_party=speaker_party or None,
                    )
                )

                st.markdown("### マッチング結果")

                if result.get("error_message"):
                    st.error(f"エラー: {result['error_message']}")
                elif result["matched"]:
                    st.success("✅ マッチング成功！")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "政治家名",
                            result.get("politician_name", "Unknown"),
                        )
                    with col2:
                        st.metric(
                            "政党",
                            result.get("political_party_name", "N/A"),
                        )
                    with col3:
                        st.metric(
                            "信頼度",
                            f"{result.get('confidence', 0):.2f}",
                        )

                    st.markdown("### 判定理由")
                    st.info(result.get("reason", ""))

                    with st.expander("詳細結果（JSON）"):
                        st.json(dict(result))
                else:
                    st.warning("マッチする政治家が見つかりませんでした")
                    st.info(result.get("reason", ""))

                    with st.expander("詳細結果（JSON）"):
                        st.json(dict(result))

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())

    st.markdown("---")
    st.markdown("""
    ### 使い方

    1. **発言者名** を入力（例: 田中太郎）
    2. 必要に応じて **発言者種別** と **発言者政党** を入力
    3. **「政治家マッチングAgentを実行」** ボタンをクリック

    **動作の流れ:**
    1. エージェントが候補検索ツールで政治家候補を取得
    2. 上位候補の所属情報を検証
    3. BAMLを使用して最終的なマッチング判定
    4. 信頼度0.7以上ならマッチング成功

    **注意:**
    - エージェントの実行には数秒〜十数秒かかることがあります
    - LLM API（Gemini）を使用するため、API キーが必要です
    """)


def main() -> None:
    """Main function for testing."""
    render_conversations_page()


if __name__ == "__main__":
    main()
