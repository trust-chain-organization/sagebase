"""View for conversations and speakers management."""

import asyncio

import streamlit as st

from src.application.usecases.authenticate_user_usecase import (
    AuthenticateUserUseCase,
)
from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.infrastructure.di.container import Container
from src.infrastructure.external.langgraph_tools.speaker_matching_tools import (
    create_speaker_matching_tools,
)
from src.interfaces.web.streamlit.auth import google_sign_in


def render_conversations_speakers_page() -> None:
    """Render the conversations and speakers management page."""
    st.header("発言・発言者管理")
    st.markdown("発言記録と発言者の情報を管理します")

    # Create tabs
    tabs = st.tabs(
        ["発言者一覧", "発言マッチング", "統計情報", "ツールテスト", "Agentテスト"]
    )

    with tabs[0]:
        render_speakers_list_tab()

    with tabs[1]:
        render_matching_tab()

    with tabs[2]:
        render_statistics_tab()

    with tabs[3]:
        render_tools_test_tab()

    with tabs[4]:
        render_agent_test_tab()


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
                from src.domain.services.speaker_domain_service import (
                    SpeakerDomainService,
                )
                from src.infrastructure.external.llm_service import GeminiLLMService

                # Get container for repositories
                container = Container()

                # Initialize services with default values
                llm_service = (
                    GeminiLLMService()
                )  # Uses defaults, implements ILLMService
                speaker_domain_service = SpeakerDomainService()

                # Initialize use cases
                auth_usecase = AuthenticateUserUseCase(
                    user_repository=container.repositories.user_repository()
                )
                match_usecase = MatchSpeakersUseCase(
                    speaker_repository=container.repositories.speaker_repository(),
                    politician_repository=container.repositories.politician_repository(),
                    conversation_repository=container.repositories.conversation_repository(),
                    speaker_domain_service=speaker_domain_service,
                    llm_service=llm_service,
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
    st.subheader("🧪 名寄せツールテスト")

    st.markdown("""
    ### 名寄せAgent用ツールの動作確認

    3つのツールを個別にテストできます：
    1. **evaluate_matching_candidates**: マッチング候補の評価
    2. **search_additional_info**: 追加情報の検索
    3. **judge_confidence**: 確信度の判定
    """)

    # Create sub-tabs for each tool
    tool_tabs = st.tabs(["① 候補評価", "② 追加情報検索", "③ 確信度判定"])

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
                container = Container()

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
                                    "exact": "🎯 完全一致",
                                    "partial": "📍 部分一致",
                                    "fuzzy": "🔍 類似",
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
                container = Container()

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
        party = st.text_input("政党", value="○○党")
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
                    "conference_name": "○○市議会",
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
                container = Container()

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
                            "high": "🟢 高",
                            "medium": "🟡 中",
                            "low": "🔴 低",
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
    st.subheader("🤖 名寄せAgentテスト")

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
    with st.expander("⚙️ 詳細設定"):
        st.info(
            "エージェントの設定（現在は固定値）\n\n"
            "- MAX_REACT_STEPS: 10\n"
            "- 確信度閾値: 0.8"
        )

    if st.button("🚀 Agentを実行", type="primary", key="agent_button"):
        if not speaker_name:
            st.warning("発言者名を入力してください")
            return

        with st.spinner("エージェントを実行中..."):
            try:
                # Get container for repositories
                container = Container()

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
                st.markdown("### 🎯 マッチング結果")

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
                    with st.expander("📋 政治家詳細"):
                        st.json(
                            {
                                "politician_id": result.get("politician_id"),
                                "politician_name": result.get("politician_name"),
                                "confidence": result.get("confidence"),
                            }
                        )

                else:
                    # No match case
                    st.warning("⚠️ マッチする政治家が見つかりませんでした")
                    st.info(result.get("reason", ""))

                # Show full result
                with st.expander("🔍 詳細結果（JSON）"):
                    st.json(result)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
                import traceback

                with st.expander("エラー詳細"):
                    st.code(traceback.format_exc())

    # Usage example
    st.markdown("---")
    st.markdown("""
    ### 💡 使い方

    1. **発言者名** を入力（例: 田中太郎）
    2. 必要に応じて **会議開催日** と **会議体ID** を入力
    3. **「🚀 Agentを実行」** ボタンをクリック
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


def main() -> None:
    """Main function for testing."""
    render_conversations_speakers_page()


if __name__ == "__main__":
    main()
