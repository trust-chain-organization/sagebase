"""View for proposal management in Streamlit.

This module provides the UI layer for proposal management,
using the presenter pattern for business logic.
"""

from typing import Any

import streamlit as st

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.interfaces.web.streamlit.presenters.proposal_presenter import ProposalPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_proposals_page() -> None:
    """Render the proposals management page."""
    st.title("議案管理")
    st.markdown("議案の情報を自動収集・管理します。")

    # Initialize presenter
    presenter = ProposalPresenter()

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["議案管理", "LLM抽出結果", "確定賛否情報"])

    with tab1:
        render_proposals_tab(presenter)

    with tab2:
        render_extracted_judges_tab(presenter)

    with tab3:
        render_final_judges_tab(presenter)


# ========== Tab 1: Proposal Management ==========


def render_proposals_tab(presenter: ProposalPresenter) -> None:
    """Render the proposals management tab."""
    # Filter section
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_options = {
            "すべて": "all",
            "会議別": "by_meeting",
            "会議体別": "by_conference",
        }
        selected_filter = st.selectbox(
            "表示フィルター", options=list(filter_options.keys()), index=0
        )
        filter_type = filter_options[selected_filter]

    # Additional filters based on selection
    meeting_filter = None
    conference_filter = None

    if filter_type == "by_meeting":
        with col2:
            meeting_filter = st.number_input("会議ID", min_value=1, step=1)

    elif filter_type == "by_conference":
        with col2:
            conference_filter = st.number_input("会議体ID", min_value=1, step=1)

    # Load data
    try:
        result = presenter.load_data_filtered(
            filter_type=filter_type,
            meeting_id=meeting_filter,
            conference_id=conference_filter,
        )

        # Display statistics
        with col3:
            st.metric("議案数", result.statistics.total)

        # New proposal section
        render_new_proposal_form(presenter)

        # Scrape proposal section
        render_scrape_proposal_section(presenter)

        # Display proposals list
        if result.proposals:
            st.subheader("議案一覧")
            for proposal in result.proposals:
                render_proposal_row(presenter, proposal)
        else:
            st.info("表示する議案がありません。")

    except Exception as e:
        handle_ui_error(e, "議案一覧の読み込み")


def render_new_proposal_form(presenter: ProposalPresenter) -> None:
    """Render new proposal creation form."""
    with st.expander("新規議案登録"):
        with st.form("new_proposal_form"):
            title = st.text_area("議案タイトル *", placeholder="議案のタイトルを入力")

            col1, col2 = st.columns(2)
            with col1:
                detail_url = st.text_input("詳細URL", placeholder="https://...")
                status_url = st.text_input(
                    "状態URL (optional)", placeholder="https://..."
                )
                votes_url = st.text_input(
                    "賛否URL (optional)", placeholder="https://..."
                )

            with col2:
                # Load meetings and conferences for selection
                try:
                    meetings = presenter.load_meetings()
                    meeting_options: dict[str, int | None] = {"なし": None}
                    meeting_options.update(
                        {f"{m['name']} (ID: {m['id']})": m["id"] for m in meetings}
                    )
                    selected_meeting = st.selectbox(
                        "紐づく会議 (optional)",
                        options=list(meeting_options.keys()),
                        index=0,
                    )
                    meeting_id = meeting_options[selected_meeting]
                except Exception:
                    meeting_id = None
                    st.warning("会議一覧の読み込みに失敗しました")

                conferences: list[dict[str, Any]] = []
                try:
                    conferences = presenter.load_conferences()
                    conference_options: dict[str, int | None] = {"なし": None}
                    for c in conferences:
                        conference_options[f"{c['name']} (ID: {c['id']})"] = c["id"]
                    selected_conference = st.selectbox(
                        "紐づく会議体 (optional)",
                        options=list(conference_options.keys()),
                        index=0,
                    )
                    conference_id = conference_options[selected_conference]
                except Exception:
                    conference_id = None
                    st.warning("会議体一覧の読み込みに失敗しました")

            # Load politicians for submitter selection
            st.markdown("**提出者の選択**")
            submitter_politician_ids: list[int] = []
            submitter_conference_ids: list[int] = []

            try:
                politicians = presenter.load_politicians()
                politician_options = {
                    f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id
                }
                selected_politicians = st.multiselect(
                    "政治家から選択（複数選択可能）",
                    options=list(politician_options.keys()),
                )
                submitter_politician_ids = [
                    politician_options[name] for name in selected_politicians
                ]
            except Exception:
                st.warning("政治家一覧の読み込みに失敗しました")

            try:
                # Use already loaded conferences for submitter selection
                submitter_conference_options: dict[str, int] = {}
                for c in conferences:
                    key = f"{c['name']} (ID: {c['id']})"
                    submitter_conference_options[key] = c["id"]
                selected_submitter_conferences = st.multiselect(
                    "会議体から選択（複数選択可能）",
                    options=list(submitter_conference_options.keys()),
                )
                submitter_conference_ids = [
                    submitter_conference_options[name]
                    for name in selected_submitter_conferences
                ]
            except Exception:
                st.warning("会議体一覧の読み込みに失敗しました")

            submitted = st.form_submit_button("登録")

            if submitted:
                if not title:
                    st.error("議案タイトルは必須です")
                else:
                    try:
                        user_id = presenter.get_current_user_id()
                        result = presenter.create(
                            title=title,
                            detail_url=detail_url or None,
                            status_url=status_url or None,
                            votes_url=votes_url or None,
                            meeting_id=meeting_id,
                            conference_id=conference_id,
                            user_id=user_id,
                        )

                        if result.success:
                            # Register submitters if selected
                            if (
                                submitter_politician_ids or submitter_conference_ids
                            ) and result.proposal:
                                presenter.update_submitters(
                                    result.proposal.id,  # type: ignore[arg-type]
                                    politician_ids=submitter_politician_ids,
                                    conference_ids=submitter_conference_ids,
                                )
                            st.success(result.message)
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "議案の登録")


def render_scrape_proposal_section(presenter: ProposalPresenter) -> None:
    """Render proposal scraping section."""
    with st.expander("議案情報の自動抽出"):
        st.markdown("URLから議案情報を自動的に抽出してデータベースに保存します。")

        with st.form("scrape_proposal_form"):
            url = st.text_input("議案詳細URL *", placeholder="https://...")
            meeting_id = st.number_input(
                "会議ID (オプション)", min_value=0, value=0, step=1
            )

            submitted = st.form_submit_button("抽出実行")

            if submitted:
                if not url:
                    st.error("URLは必須です")
                else:
                    with st.spinner("議案情報を抽出中..."):
                        try:
                            result = presenter.scrape_proposal(
                                url=url,
                                meeting_id=meeting_id if meeting_id > 0 else None,
                            )

                            if result:
                                st.success("議案情報を抽出しました")
                                st.json(
                                    {
                                        "タイトル": result.title[:100] + "..."
                                        if len(result.title) > 100
                                        else result.title,
                                    }
                                )
                                st.rerun()
                            else:
                                st.warning("議案情報を抽出できませんでした")
                        except Exception as e:
                            handle_ui_error(e, "議案の抽出")


def render_proposal_row(presenter: ProposalPresenter, proposal: Proposal) -> None:
    """Render a single proposal row."""
    # Check if this proposal is being edited
    if proposal.id is not None and presenter.is_editing(proposal.id):
        render_edit_proposal_form(presenter, proposal)
    else:
        render_proposal_display(presenter, proposal)


def render_proposal_display(presenter: ProposalPresenter, proposal: Proposal) -> None:
    """Render proposal in display mode."""
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**議案 #{proposal.id}**")
            st.markdown(f"{proposal.title[:100]}...")

            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**会議ID**: {proposal.meeting_id or '未設定'}")
            with col_info2:
                st.markdown(f"**会議体ID**: {proposal.conference_id or '未設定'}")

            # Display submitters
            try:
                submitters = presenter.load_submitters(proposal.id)  # type: ignore[arg-type]
                if submitters:
                    politicians = presenter.load_politicians()
                    politician_names = {p.id: p.name for p in politicians}
                    conferences = presenter.load_conferences()
                    conference_names = {c["id"]: c["name"] for c in conferences}

                    submitter_display_parts = []

                    # Politician submitters
                    for s in submitters:
                        if s.politician_id:
                            name = politician_names.get(
                                s.politician_id, f"政治家ID:{s.politician_id}"
                            )
                            submitter_display_parts.append(name)

                    # Conference submitters
                    for s in submitters:
                        if s.conference_id:
                            conf_name = conference_names.get(
                                s.conference_id, f"ID:{s.conference_id}"
                            )
                            submitter_display_parts.append(f"[会議体] {conf_name}")

                    if submitter_display_parts:
                        st.markdown(f"**提出者**: {', '.join(submitter_display_parts)}")
            except Exception:
                pass

            if proposal.detail_url:
                st.markdown(f"[詳細URL]({proposal.detail_url})")
            if proposal.status_url:
                st.markdown(f"[状態URL]({proposal.status_url})")
            if proposal.votes_url:
                st.markdown(f"[賛否URL]({proposal.votes_url})")

        with col2:
            # Action buttons
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("編集", key=f"edit_proposal_{proposal.id}"):
                    if proposal.id is not None:
                        presenter.set_editing_mode(proposal.id)
                        st.rerun()

            with col_btn2:
                if st.button(
                    "削除",
                    key=f"delete_proposal_{proposal.id}",
                    type="secondary",
                ):
                    st.session_state[f"confirm_delete_{proposal.id}"] = True

            # Delete confirmation
            if st.session_state.get(f"confirm_delete_{proposal.id}", False):
                st.warning("本当に削除しますか？")
                col_confirm1, col_confirm2 = st.columns(2)
                with col_confirm1:
                    if st.button("はい", key=f"confirm_yes_{proposal.id}"):
                        try:
                            user_id = presenter.get_current_user_id()
                            result = presenter.delete(
                                proposal_id=proposal.id,
                                user_id=user_id,
                            )
                            if result.success:
                                st.success(result.message)
                                del st.session_state[f"confirm_delete_{proposal.id}"]
                                st.rerun()
                            else:
                                st.error(result.message)
                        except Exception as e:
                            handle_ui_error(e, "議案の削除")
                with col_confirm2:
                    if st.button("いいえ", key=f"confirm_no_{proposal.id}"):
                        del st.session_state[f"confirm_delete_{proposal.id}"]
                        st.rerun()

        st.divider()


def render_edit_proposal_form(presenter: ProposalPresenter, proposal: Proposal) -> None:
    """Render proposal edit form."""
    with st.container():
        st.markdown(f"### 議案 #{proposal.id} を編集中")

        with st.form(f"edit_proposal_form_{proposal.id}"):
            title = st.text_area(
                "議案タイトル *",
                value=proposal.title,
                key=f"edit_title_{proposal.id}",
            )

            col1, col2 = st.columns(2)
            with col1:
                detail_url = st.text_input(
                    "詳細URL",
                    value=proposal.detail_url or "",
                    key=f"edit_detail_url_{proposal.id}",
                )
                status_url = st.text_input(
                    "状態URL",
                    value=proposal.status_url or "",
                    key=f"edit_status_url_{proposal.id}",
                )
                votes_url = st.text_input(
                    "賛否URL",
                    value=proposal.votes_url or "",
                    key=f"edit_votes_url_{proposal.id}",
                )

            with col2:
                # Load meetings
                try:
                    meetings = presenter.load_meetings()
                    meeting_options: dict[str, int | None] = {"なし": None}
                    meeting_options.update(
                        {f"{m['name']} (ID: {m['id']})": m["id"] for m in meetings}
                    )
                    # Find current meeting selection
                    current_meeting_idx = 0
                    if proposal.meeting_id:
                        for idx, (_, mid) in enumerate(meeting_options.items()):
                            if mid == proposal.meeting_id:
                                current_meeting_idx = idx
                                break
                    selected_meeting = st.selectbox(
                        "紐づく会議",
                        options=list(meeting_options.keys()),
                        index=current_meeting_idx,
                        key=f"edit_meeting_{proposal.id}",
                    )
                    meeting_id = meeting_options[selected_meeting]
                except Exception:
                    meeting_id = proposal.meeting_id
                    st.warning("会議一覧の読み込みに失敗しました")

                # Load conferences
                conferences: list[dict[str, Any]] = []
                try:
                    conferences = presenter.load_conferences()
                    conference_options: dict[str, int | None] = {"なし": None}
                    for c in conferences:
                        conference_options[f"{c['name']} (ID: {c['id']})"] = c["id"]
                    # Find current conference selection
                    current_conference_idx = 0
                    if proposal.conference_id:
                        for idx, (_, cid) in enumerate(conference_options.items()):
                            if cid == proposal.conference_id:
                                current_conference_idx = idx
                                break
                    selected_conference = st.selectbox(
                        "紐づく会議体",
                        options=list(conference_options.keys()),
                        index=current_conference_idx,
                        key=f"edit_conference_{proposal.id}",
                    )
                    conference_id = conference_options[selected_conference]
                except Exception:
                    conference_id = proposal.conference_id
                    st.warning("会議体一覧の読み込みに失敗しました")

            # Load current submitters and politicians/conferences for selection
            st.markdown("**提出者の選択**")
            submitter_politician_ids: list[int] = []
            submitter_conference_ids: list[int] = []
            current_conference_ids: list[int] = []

            try:
                politicians = presenter.load_politicians()
                politician_options = {
                    f"{p.name} (ID: {p.id})": p.id for p in politicians if p.id
                }

                # Get current submitters
                current_submitters = presenter.load_submitters(proposal.id)  # type: ignore[arg-type]
                current_politician_ids = [
                    s.politician_id for s in current_submitters if s.politician_id
                ]
                current_conference_ids = [
                    s.conference_id for s in current_submitters if s.conference_id
                ]

                # Find option names for current politician submitters
                current_politician_selections = [
                    name
                    for name, pid in politician_options.items()
                    if pid in current_politician_ids
                ]

                selected_politicians = st.multiselect(
                    "政治家から選択（複数選択可能）",
                    options=list(politician_options.keys()),
                    default=current_politician_selections,
                    key=f"edit_submitters_{proposal.id}",
                )
                submitter_politician_ids = [
                    politician_options[name] for name in selected_politicians
                ]
            except Exception:
                st.warning("政治家情報の読み込みに失敗しました")

            try:
                # Use already loaded conferences for submitter selection
                submitter_conference_options: dict[str, int] = {}
                for c in conferences:
                    key = f"{c['name']} (ID: {c['id']})"
                    submitter_conference_options[key] = c["id"]

                # Find option names for current conference submitters
                current_conference_selections = [
                    name
                    for name, cid in submitter_conference_options.items()
                    if cid in current_conference_ids
                ]

                selected_submitter_conferences = st.multiselect(
                    "会議体から選択（複数選択可能）",
                    options=list(submitter_conference_options.keys()),
                    default=current_conference_selections,
                    key=f"edit_submitter_conferences_{proposal.id}",
                )
                submitter_conference_ids = [
                    submitter_conference_options[name]
                    for name in selected_submitter_conferences
                ]
            except Exception:
                st.warning("会議体情報の読み込みに失敗しました")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("保存", type="primary")
            with col_btn2:
                cancelled = st.form_submit_button("キャンセル")

            if submitted:
                if not title:
                    st.error("議案タイトルは必須です")
                else:
                    try:
                        user_id = presenter.get_current_user_id()
                        result = presenter.update(
                            proposal_id=proposal.id,
                            title=title,
                            detail_url=detail_url or None,
                            status_url=status_url or None,
                            votes_url=votes_url or None,
                            meeting_id=meeting_id,
                            conference_id=conference_id,
                            user_id=user_id,
                        )

                        if result.success:
                            # Update submitters
                            presenter.update_submitters(
                                proposal.id,  # type: ignore[arg-type]
                                politician_ids=submitter_politician_ids,
                                conference_ids=submitter_conference_ids,
                            )
                            st.success(result.message)
                            presenter.cancel_editing()
                            st.rerun()
                        else:
                            st.error(result.message)
                    except Exception as e:
                        handle_ui_error(e, "議案の更新")

            if cancelled:
                presenter.cancel_editing()
                st.rerun()

        st.divider()


# ========== Tab 2: Extracted Judges ==========


def render_extracted_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the extracted judges tab."""
    st.subheader("LLM抽出結果")
    st.markdown("議案の賛否情報を自動抽出し、レビューします。")

    # Extract judges section
    render_extract_judges_section(presenter)

    # Filter section
    col1, col2 = st.columns([2, 1])

    with col1:
        proposal_id_filter = st.number_input(
            "議案IDでフィルター (0=全て)", min_value=0, value=0, step=1
        )

    with col2:
        status_options = ["すべて", "pending", "matched", "needs_review", "no_match"]
        status_filter = st.selectbox("ステータス", options=status_options, index=0)

    # Load extracted judges
    try:
        filter_id = proposal_id_filter if proposal_id_filter > 0 else None
        judges = presenter.load_extracted_judges(proposal_id=filter_id)

        # Filter by status if needed
        if status_filter != "すべて":
            judges = [j for j in judges if j.matching_status == status_filter]

        if judges:
            st.markdown(f"**抽出件数**: {len(judges)}件")

            # Batch operations
            render_batch_operations(presenter, judges)

            # Display judges
            for judge in judges:
                render_extracted_judge_row(presenter, judge)
        else:
            st.info("抽出結果がありません。")

    except Exception as e:
        handle_ui_error(e, "抽出結果の読み込み")


def render_extract_judges_section(presenter: ProposalPresenter) -> None:
    """Render judge extraction section."""
    with st.expander("賛否情報の自動抽出"):
        st.markdown("議案の状態URLから賛否情報を自動的に抽出します。")

        with st.form("extract_judges_form"):
            url = st.text_input("状態URL *", placeholder="https://...")
            proposal_id = st.number_input(
                "議案ID (オプション)", min_value=0, value=0, step=1
            )
            force = st.checkbox("既存データを上書き", value=False)

            submitted = st.form_submit_button("抽出実行")

            if submitted:
                if not url:
                    st.error("URLは必須です")
                else:
                    with st.spinner("賛否情報を抽出中..."):
                        try:
                            result = presenter.extract_judges(
                                url=url,
                                proposal_id=(proposal_id if proposal_id > 0 else None),
                                force=force,
                            )

                            st.success(
                                f"抽出完了！ {result.extracted_count}件の"
                                f"賛否情報を抽出しました。"
                            )
                            st.rerun()
                        except Exception as e:
                            handle_ui_error(e, "賛否情報の抽出")


def render_batch_operations(
    presenter: ProposalPresenter, judges: list[ExtractedProposalJudge]
) -> None:
    """Render batch operations for extracted judges."""
    st.markdown("### 一括操作")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("一括マッチング", type="primary"):
            with st.spinner("マッチング処理中..."):
                try:
                    # Get unique proposal IDs from judges
                    proposal_ids = {j.proposal_id for j in judges if j.proposal_id}

                    for prop_id in proposal_ids:
                        result = presenter.match_judges(proposal_id=prop_id)
                        st.info(f"議案ID {prop_id}: {result.matched_count}件マッチ")

                    st.success("マッチング完了")
                    st.rerun()
                except Exception as e:
                    handle_ui_error(e, "一括マッチング")

    with col2:
        if st.button("一括承認（matched のみ）"):
            with st.spinner("承認処理中..."):
                try:
                    # Get unique proposal IDs from matched judges
                    matched_judges = [
                        j for j in judges if j.matching_status == "matched"
                    ]
                    proposal_ids = {
                        j.proposal_id for j in matched_judges if j.proposal_id
                    }

                    for prop_id in proposal_ids:
                        result = presenter.create_judges_from_matched(
                            proposal_id=prop_id
                        )
                        st.info(f"議案ID {prop_id}: {result.created_count}件作成")

                    st.success("一括承認完了")
                    st.rerun()
                except Exception as e:
                    handle_ui_error(e, "一括承認")


def render_extracted_judge_row(
    presenter: ProposalPresenter, judge: ExtractedProposalJudge
) -> None:
    """Render a single extracted judge row."""
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            # Status badge
            status_emoji = {
                "pending": "?",
                "matched": "OK",
                "needs_review": "!",
                "no_match": "X",
            }
            emoji = status_emoji.get(judge.matching_status or "pending", "?")

            st.markdown(
                f"[{emoji}] **ID {judge.id}** - {judge.extracted_politician_name}"
            )

            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.markdown(f"**賛否**: {judge.extracted_judgment or '未設定'}")
            with col_info2:
                group_name = judge.extracted_parliamentary_group_name or "未設定"
                st.markdown(f"**議員団**: {group_name}")
            with col_info3:
                confidence = judge.matching_confidence
                if confidence:
                    st.markdown(f"**信頼度**: {confidence:.2f}")
                else:
                    st.markdown("**信頼度**: 未計算")

        with col2:
            if judge.matching_status == "matched":
                if st.button("承認", key=f"approve_{judge.id}"):
                    try:
                        # Create single judge
                        result = presenter.create_judges_from_matched(
                            proposal_id=judge.proposal_id
                        )
                        st.success(f"承認完了: {result.created_count}件作成")
                        st.rerun()
                    except Exception as e:
                        handle_ui_error(e, "承認処理")
            elif judge.matching_status == "pending":
                if st.button("マッチング", key=f"match_{judge.id}"):
                    try:
                        result = presenter.match_judges(proposal_id=judge.proposal_id)
                        st.success(f"マッチング完了: {result.matched_count}件")
                        st.rerun()
                    except Exception as e:
                        handle_ui_error(e, "マッチング処理")

        st.divider()


# ========== Tab 3: Final Judges ==========


def render_final_judges_tab(presenter: ProposalPresenter) -> None:
    """Render the final judges tab."""
    st.subheader("確定賛否情報")
    st.markdown("承認済みの最終的な賛否情報を管理します。")

    # Filter section
    col1, col2 = st.columns([2, 1])

    with col1:
        proposal_id_filter = st.number_input(
            "議案IDでフィルター (0=全て)",
            min_value=0,
            value=0,
            step=1,
            key="final_filter",
        )

    # Load final judges
    try:
        filter_id = proposal_id_filter if proposal_id_filter > 0 else None
        judges = presenter.load_proposal_judges(proposal_id=filter_id)

        with col2:
            st.metric("確定件数", len(judges))

        if judges:
            # Display statistics
            render_judge_statistics(judges)

            # Display judges list
            st.subheader("賛否一覧")
            for judge in judges:
                render_final_judge_row(presenter, judge)
        else:
            st.info("確定された賛否情報がありません。")

    except Exception as e:
        handle_ui_error(e, "確定賛否情報の読み込み")


def render_judge_statistics(judges: list[ProposalJudge]) -> None:
    """Render statistics for proposal judges."""
    # Count by vote
    vote_counts: dict[str, int] = {}
    for judge in judges:
        vote = judge.approve or "未設定"
        vote_counts[vote] = vote_counts.get(vote, 0) + 1

    st.markdown("### 統計情報")

    if vote_counts:
        cols = st.columns(len(vote_counts))
        for i, (vote, count) in enumerate(vote_counts.items()):
            with cols[i]:
                st.metric(vote, count)


def render_final_judge_row(presenter: ProposalPresenter, judge: ProposalJudge) -> None:
    """Render a single final judge row."""
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"**ID {judge.id}** - 政治家ID: {judge.politician_id}")

            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.markdown(f"**賛否**: {judge.approve or '未設定'}")
            with col_info2:
                # ProposalJudge doesn't have remarks field, skip it
                pass

        with col2:
            if st.button("削除", key=f"delete_judge_{judge.id}"):
                # Note: Delete functionality would need to be added to presenter
                st.warning("削除機能は未実装です")

        st.divider()


def main() -> None:
    """Main entry point for the proposals page."""
    render_proposals_page()


if __name__ == "__main__":
    main()
