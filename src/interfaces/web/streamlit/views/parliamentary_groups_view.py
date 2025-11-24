"""View for parliamentary group management."""

import asyncio
from datetime import date
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
    ParliamentaryGroupMemberPresenter,
)
from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_parliamentary_groups_page() -> None:
    """Render the parliamentary groups management page."""
    st.header("議員団管理")
    st.markdown("議員団（会派）の情報を管理します")

    presenter = ParliamentaryGroupPresenter()

    # Create tabs
    tabs = st.tabs(
        [
            "議員団一覧",
            "新規登録",
            "編集・削除",
            "メンバー抽出",
            "メンバーレビュー",
            "メンバーシップ一覧",
        ]
    )

    with tabs[0]:
        render_parliamentary_groups_list_tab(presenter)

    with tabs[1]:
        render_new_parliamentary_group_tab(presenter)

    with tabs[2]:
        render_edit_delete_tab(presenter)

    with tabs[3]:
        render_member_extraction_tab(presenter)

    with tabs[4]:
        render_member_review_tab()

    with tabs[5]:
        render_memberships_list_tab(presenter)


def render_parliamentary_groups_list_tab(
    presenter: ParliamentaryGroupPresenter,
) -> None:
    """Render the parliamentary groups list tab."""
    st.subheader("議員団一覧")

    # Get conferences for filter
    conferences = presenter.get_all_conferences()

    # Conference filter
    def get_conf_display_name(c: Any) -> str:
        gb_name = (
            c.governing_body.name
            if hasattr(c, "governing_body") and c.governing_body
            else ""
        )
        return f"{gb_name} - {c.name}"

    conf_options = ["すべて"] + [get_conf_display_name(c) for c in conferences]
    conf_map = {get_conf_display_name(c): c.id for c in conferences}

    selected_conf_filter = st.selectbox(
        "会議体でフィルタ", conf_options, key="conf_filter"
    )

    # Load parliamentary groups
    if selected_conf_filter == "すべて":
        groups = presenter.load_data()
    else:
        conf_id = conf_map[selected_conf_filter]
        groups = presenter.load_parliamentary_groups_with_filters(conf_id, False)

    if groups:
        # Seed file generation section
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### SEEDファイル生成")
                st.markdown(
                    "現在登録されている議員団データからSEEDファイルを生成します"
                )
            with col2:
                if st.button(
                    "SEEDファイル生成", key="generate_pg_seed", type="primary"
                ):
                    with st.spinner("SEEDファイルを生成中..."):
                        success, seed_content, file_path_or_error = (
                            presenter.generate_seed_file()
                        )
                        if success:
                            st.success(
                                f"✅ SEEDファイルを生成しました: {file_path_or_error}"
                            )
                            with st.expander("生成されたSEEDファイル", expanded=False):
                                st.code(seed_content, language="sql")
                        else:
                            st.error(
                                f"❌ SEEDファイル生成中にエラーが発生しました: "
                                f"{file_path_or_error}"
                            )

        st.markdown("---")

        # Display data in DataFrame
        df = presenter.to_dataframe(groups, conferences)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Display member counts
        st.markdown("### メンバー数")
        member_df = presenter.get_member_counts(groups)
        if member_df is not None:
            st.dataframe(member_df, use_container_width=True, hide_index=True)
    else:
        st.info("議員団が登録されていません")


def render_new_parliamentary_group_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the new parliamentary group registration tab."""
    st.subheader("議員団の新規登録")

    # Get conferences
    conferences = presenter.get_all_conferences()
    if not conferences:
        st.error("会議体が登録されていません。先に会議体を登録してください。")
        return

    def get_conf_display_name(c: Any) -> str:
        gb_name = (
            c.governing_body.name
            if hasattr(c, "governing_body") and c.governing_body
            else ""
        )
        return f"{gb_name} - {c.name}"

    conf_options = [get_conf_display_name(c) for c in conferences]
    conf_map = {get_conf_display_name(c): c.id for c in conferences}

    with st.form("new_parliamentary_group_form", clear_on_submit=False):
        selected_conf = st.selectbox("所属会議体", conf_options)

        # Input fields
        group_name = st.text_input("議員団名", placeholder="例: 自民党市議団")
        group_url = st.text_input(
            "議員団URL（任意）",
            placeholder="https://example.com/parliamentary-group",
            help="議員団の公式ページやプロフィールページのURL",
        )
        group_description = st.text_area(
            "説明（任意）", placeholder="議員団の説明や特徴を入力"
        )
        is_active = st.checkbox("活動中", value=True)

        submitted = st.form_submit_button("登録")

    if submitted:
        conf_id = conf_map[selected_conf]
        if not group_name:
            st.error("議員団名を入力してください")
        elif conf_id is None:
            st.error("会議体を選択してください")
        else:
            success, group, error = presenter.create(
                group_name,
                conf_id,
                group_url if group_url else None,
                group_description if group_description else None,
                is_active,
            )
            if success and group:
                presenter.add_created_group(group, selected_conf)
                st.success(f"議員団「{group.name}」を登録しました（ID: {group.id}）")
            else:
                st.error(f"登録に失敗しました: {error}")

    # Display created groups
    created_groups = presenter.get_created_groups()
    if created_groups:
        st.divider()
        st.subheader("作成済み議員団")

        for i, group in enumerate(created_groups):
            with st.expander(f"✅ {group['name']} (ID: {group['id']})", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**議員団名**: {group['name']}")
                    st.write(f"**議員団ID**: {group['id']}")
                    st.write(f"**所属会議体**: {group['conference_name']}")
                    if group["url"]:
                        st.write(f"**URL**: {group['url']}")
                    if group["description"]:
                        st.write(f"**説明**: {group['description']}")
                    active_status = "活動中" if group["is_active"] else "非活動"
                    st.write(f"**活動状態**: {active_status}")
                    if group["created_at"]:
                        st.write(f"**作成日時**: {group['created_at']}")
                with col2:
                    if st.button("削除", key=f"remove_created_{i}"):
                        presenter.remove_created_group(i)
                        st.rerun()


def render_edit_delete_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the edit/delete tab."""
    st.subheader("議員団の編集・削除")

    # Load all parliamentary groups
    groups = presenter.load_data()
    if not groups:
        st.info("編集する議員団がありません")
        return

    # Get conferences for display
    conferences = presenter.get_all_conferences()

    # Select parliamentary group to edit
    group_options: list[str] = []
    group_map: dict[str, Any] = {}
    for group in groups:
        conf = next((c for c in conferences if c.id == group.conference_id), None)
        conf_name = conf.name if conf else "不明"
        display_name = f"{group.name} ({conf_name})"
        group_options.append(display_name)
        group_map[display_name] = group

    selected_group_display = st.selectbox("編集する議員団を選択", group_options)
    selected_group = group_map[selected_group_display]

    # Edit and delete forms
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 編集")
        with st.form("edit_parliamentary_group_form"):
            new_name = st.text_input("議員団名", value=selected_group.name)
            new_url = st.text_input("議員団URL", value=selected_group.url or "")
            new_description = st.text_area(
                "説明", value=selected_group.description or ""
            )
            new_is_active = st.checkbox("活動中", value=selected_group.is_active)

            submitted = st.form_submit_button("更新")

            if submitted:
                if not new_name:
                    st.error("議員団名を入力してください")
                else:
                    success, error = presenter.update(
                        selected_group.id,
                        new_name,
                        new_url if new_url else None,
                        new_description if new_description else None,
                        new_is_active,
                    )
                    if success:
                        st.success("議員団を更新しました")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### メンバー情報")
        # TODO: Display member information when membership repository is available
        st.write("メンバー数: 0名")  # Placeholder

        st.markdown("#### 削除")
        st.warning("⚠️ 議員団を削除すると、所属履歴も削除されます")

        # Can only delete inactive groups
        if selected_group.is_active:
            st.info("活動中の議員団は削除できません。先に非活動にしてください。")
        else:
            if st.button("🗑️ この議員団を削除", type="secondary"):
                success, error = presenter.delete(selected_group.id)
                if success:
                    st.success(f"議員団「{selected_group.name}」を削除しました")
                    st.rerun()
                else:
                    st.error(f"削除に失敗しました: {error}")


def render_member_extraction_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the member extraction tab."""
    st.subheader("議員団メンバーの抽出")
    st.markdown("議員団のURLから所属議員を自動的に抽出し、メンバーシップを作成します")

    # Get parliamentary groups with URLs
    groups = presenter.load_data()
    groups_with_url = [g for g in groups if g.url]

    if not groups_with_url:
        st.info(
            "URLが設定されている議員団がありません。先に議員団のURLを設定してください。"
        )
        return

    # Get conferences for display
    conferences = presenter.get_all_conferences()

    # Select parliamentary group
    group_options = []
    group_map = {}
    for group in groups_with_url:
        conf = next((c for c in conferences if c.id == group.conference_id), None)
        if conf:
            gb_name = (
                conf.governing_body.name  # type: ignore[attr-defined]
                if hasattr(conf, "governing_body") and conf.governing_body  # type: ignore[attr-defined]
                else ""
            )
            conf_name = f"{gb_name} - {conf.name}"
        else:
            conf_name = "不明"
        display_name = f"{group.name} ({conf_name})"
        group_options.append(display_name)
        group_map[display_name] = group

    selected_group_display = st.selectbox(
        "抽出対象の議員団を選択", group_options, key="extract_group_select"
    )
    selected_group = group_map[selected_group_display]

    # Get extraction summary for selected group
    extraction_summary = presenter.get_extraction_summary(selected_group.id)

    # Display current information
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**議員団URL:** {selected_group.url}")
    with col2:
        st.info(f"**抽出済みメンバー数:** {extraction_summary['total']}名")

    # Display previously extracted members if they exist
    if extraction_summary["total"] > 0:
        st.markdown("### 抽出済みメンバー一覧")

        # Show summary statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("合計", extraction_summary["total"])
        with col2:
            st.metric(
                "紐付け未実行",
                extraction_summary["pending"],
                help="マッチング処理を待っている数",
            )
        with col3:
            st.metric(
                "マッチ済み",
                extraction_summary["matched"],
                help="政治家と正常にマッチングできた数",
            )
        with col4:
            st.metric(
                "マッチなし",
                extraction_summary["no_match"],
                help="マッチングを実行したが見つからなかった数",
            )

        # Get and display extracted members
        extracted_members = presenter.get_extracted_members(selected_group.id)
        if extracted_members:
            # Create DataFrame for display
            members_data = []
            for member in extracted_members:
                members_data.append(
                    {
                        "名前": member.extracted_name,
                        "役職": member.extracted_role or "-",
                        "政党": member.extracted_party_name or "-",
                        "選挙区": member.extracted_district or "-",
                        "ステータス": member.matching_status,
                        "信頼度": f"{member.matching_confidence:.2f}"
                        if member.matching_confidence
                        else "-",
                        "抽出日時": member.extracted_at.strftime("%Y-%m-%d %H:%M")
                        if member.extracted_at
                        else "-",
                    }
                )

            df_extracted = pd.DataFrame(members_data)
            st.dataframe(df_extracted, use_container_width=True, height=300)

        # Add separator
        st.divider()

    # Extraction settings
    st.markdown("### 抽出設定")

    col1, col2 = st.columns(2)
    with col1:
        confidence_threshold = st.slider(
            "マッチング信頼度の閾値",
            min_value=0.5,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="この値以上の信頼度でマッチングされた政治家のみメンバーシップを作成します",
        )

    with col2:
        start_date = st.date_input(
            "所属開始日",
            value=date.today(),
            help="作成されるメンバーシップの所属開始日",
        )

    dry_run = st.checkbox(
        "ドライラン（データベースに保存しない）",
        value=False,
        help="チェックすると、抽出結果の確認のみ行い、データベースには保存しません",
    )

    # Execute extraction
    if st.button("🔍 メンバー抽出を実行", type="primary"):
        with st.spinner("メンバー情報を抽出中..."):
            success, result, error = presenter.extract_members(
                selected_group.id,
                cast(str, selected_group.url),
                confidence_threshold,
                start_date,
                dry_run,
            )

            if success and result:
                if result.extracted_members:
                    st.success(
                        f"✅ {len(result.extracted_members)}名のメンバーを抽出しました"
                    )

                    # Display extracted members
                    st.markdown("### 抽出されたメンバー")

                    # Create a DataFrame for display
                    members_data = []
                    for member in result.extracted_members:
                        members_data.append(
                            {
                                "名前": member.name,
                                "役職": member.role or "-",
                                "政党": member.party_name or "-",
                                "選挙区": member.district or "-",
                                "備考": member.additional_info or "-",
                            }
                        )

                    df_members = pd.DataFrame(members_data)
                    st.dataframe(df_members, use_container_width=True)

                    # Display matching results if not in dry run mode
                    if result.matching_results:
                        st.markdown("### マッチング結果")

                        # Summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("作成済み", result.created_count)
                        with col2:
                            st.metric("スキップ", result.skipped_count)
                        with col3:
                            st.metric("総数", len(result.matching_results))

                        # Detailed results
                        matching_data = []
                        for match in result.matching_results:
                            matching_data.append(
                                {
                                    "メンバー名": match.extracted_member.name,
                                    "政治家ID": match.politician_id or "-",
                                    "政治家名": match.politician_name or "-",
                                    "信頼度": f"{match.confidence_score:.2f}"
                                    if match.politician_id
                                    else "-",
                                    "理由": match.matching_reason,
                                }
                            )

                        df_matching = pd.DataFrame(matching_data)
                        st.dataframe(df_matching, use_container_width=True)
                else:
                    st.warning("メンバーが抽出されませんでした")
            else:
                st.error(f"抽出エラー: {error}")


def render_member_review_tab() -> None:
    """Render the member review tab."""
    st.subheader("議員団メンバーレビュー")
    st.markdown("抽出された議員団メンバーをレビューして、メンバーシップを作成します")

    presenter = ParliamentaryGroupMemberPresenter()

    # Sub-tabs
    sub_tabs = st.tabs(["レビュー", "統計", "メンバーシップ作成", "重複管理"])

    with sub_tabs[0]:
        render_member_review_subtab(presenter)

    with sub_tabs[1]:
        render_member_statistics_subtab(presenter)

    with sub_tabs[2]:
        render_create_memberships_subtab(presenter)

    with sub_tabs[3]:
        render_duplicate_management_subtab(presenter)


def render_member_review_subtab(presenter: ParliamentaryGroupMemberPresenter) -> None:
    """Render the member review sub-tab."""
    st.markdown("### 抽出メンバーレビュー")

    # Display success/error messages from session state
    if "review_success_message" in st.session_state:
        st.success(st.session_state.review_success_message)
        del st.session_state.review_success_message

    if "review_error_message" in st.session_state:
        st.error(st.session_state.review_error_message)
        del st.session_state.review_error_message

    # Get parliamentary groups for filter
    parliamentary_groups = presenter.get_all_parliamentary_groups()

    # Filters section
    st.markdown("#### フィルター")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Parliamentary group filter
        group_options = ["すべて"] + [g.name for g in parliamentary_groups if g.name]
        group_map = {g.name: g.id for g in parliamentary_groups if g.id and g.name}
        selected_group = st.selectbox("議員団", group_options)
        group_id = group_map.get(selected_group) if selected_group != "すべて" else None

    with col2:
        # Status filter (multi-select)
        status_options = {
            "⏳ 紐付け未実行": "pending",
            "✅ マッチ済み": "matched",
            "❌ マッチなし": "no_match",
        }
        selected_status_labels = st.multiselect(
            "ステータス",
            options=list(status_options.keys()),
            default=["⏳ 紐付け未実行"],
        )
        selected_statuses = [status_options[label] for label in selected_status_labels]

    with col3:
        # Name search
        search_name = st.text_input("名前検索", placeholder="例: 山田")

    # Get filtered members
    members = presenter.get_filtered_extracted_members(
        parliamentary_group_id=group_id,
        statuses=selected_statuses,
        search_name=search_name if search_name else None,
        limit=100,
    )

    if not members:
        st.info("該当するレコードがありません")
        return

    # Display statistics
    st.markdown(f"### 検索結果: {len(members)}件")

    # Bulk actions
    st.markdown("### 一括アクション")
    col1, col2, col3 = st.columns(3)

    # Initialize session state for selected items
    if "selected_members" not in st.session_state:
        st.session_state.selected_members = []

    with col1:
        if st.button("全選択", key="select_all_members"):
            st.session_state.selected_members = [m.id for m in members if m.id]

    with col2:
        if st.button("選択解除", key="deselect_all_members"):
            st.session_state.selected_members = []

    with col3:
        selected_count = len(st.session_state.selected_members)
        st.metric("選択数", f"{selected_count}件")

    # Bulk action buttons
    if selected_count > 0:
        st.markdown("#### 選択したレコードに対する操作")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("一括承認", type="primary", key="bulk_approve_members"):
                with st.spinner("承認処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_members, "approve"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件を承認しました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の承認に失敗しました")
                    st.session_state.selected_members = []
                    st.rerun()

        with col2:
            if st.button("一括却下", key="bulk_reject_members"):
                with st.spinner("却下処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_members, "reject"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件を却下しました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の却下に失敗しました")
                    st.session_state.selected_members = []
                    st.rerun()

    # Display data table
    st.markdown("### データ一覧")

    # Convert to DataFrame for display
    df = presenter.to_dataframe(members, parliamentary_groups)

    if df is not None:
        # Add checkboxes for each row
        for idx, member in enumerate(members):
            if member.id is None:
                continue

            col1, col2 = st.columns([1, 9])

            with col1:
                selected = st.checkbox(
                    "選択",
                    key=f"check_member_{member.id}",
                    value=member.id in st.session_state.selected_members,
                    label_visibility="hidden",
                )
                if selected and member.id not in st.session_state.selected_members:
                    st.session_state.selected_members.append(member.id)
                elif not selected and member.id in st.session_state.selected_members:
                    st.session_state.selected_members.remove(member.id)

            with col2:
                status = df.iloc[idx]["ステータス"]
                group = df.iloc[idx]["議員団"]
                with st.expander(f"{member.extracted_name} ({group}) - {status}"):
                    # Display details
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**ID:** {member.id}")
                        st.write(f"**名前:** {member.extracted_name}")
                        st.write(f"**役職:** {member.extracted_role or '-'}")
                        st.write(f"**政党:** {member.extracted_party_name or '-'}")
                        st.write(f"**選挙区:** {member.extracted_district or '-'}")

                    with col_b:
                        st.write(f"**議員団:** {group}")
                        st.write(f"**ステータス:** {status}")
                        st.write(
                            f"**マッチした政治家:** {df.iloc[idx]['マッチした政治家']}"
                        )
                        st.write(f"**信頼度:** {df.iloc[idx]['信頼度']}")
                        st.write(f"**抽出日時:** {df.iloc[idx]['抽出日時']}")

                    # Individual action buttons
                    st.markdown("---")
                    col_1, col_2, col_3 = st.columns(3)

                    with col_1:
                        if st.button(
                            "✅ 承認",
                            key=f"approve_member_{member.id}",
                            type="primary",
                            disabled=member.matching_status != "matched",
                            help=(
                                "マッチ済みのメンバーのみ承認できます"
                                if member.matching_status != "matched"
                                else "このメンバーを承認します"
                            ),
                        ):
                            if member.id is not None:
                                success, message = presenter.review_extracted_member(
                                    member.id, "approve"
                                )
                                if success:
                                    st.session_state["review_success_message"] = message
                                else:
                                    st.session_state["review_error_message"] = message
                                st.rerun()

                    with col_2:
                        if st.button("❌ 却下", key=f"reject_member_{member.id}"):
                            if member.id is not None:
                                success, message = presenter.review_extracted_member(
                                    member.id, "reject"
                                )
                                if success:
                                    st.session_state["review_success_message"] = message
                                else:
                                    st.session_state["review_error_message"] = message
                                st.rerun()

                    with col_3:
                        if st.button("🔗 手動マッチ", key=f"manual_match_{member.id}"):
                            st.session_state[f"matching_{member.id}"] = True

                    # Manual matching dialog
                    if st.session_state.get(f"matching_{member.id}", False):
                        with st.container():
                            st.markdown("#### 手動マッチング")

                            # Search filters
                            search_col1, search_col2 = st.columns(2)

                            with search_col1:
                                search_politician_name = st.text_input(
                                    "政治家名で検索",
                                    value=member.extracted_name,
                                    key=f"search_pol_{member.id}",
                                )

                            with search_col2:
                                # Get all political parties for filter options
                                all_political_parties = (
                                    presenter.get_all_political_parties()
                                )
                                party_filter_options = ["すべて", "無所属"] + [
                                    p.name for p in all_political_parties if p.name
                                ]

                                # Set default to extracted party if available
                                default_index = 0
                                if member.extracted_party_name:
                                    try:
                                        default_index = party_filter_options.index(
                                            member.extracted_party_name
                                        )
                                    except ValueError:
                                        default_index = 0

                                selected_party_filter = st.selectbox(
                                    "政党で絞り込み",
                                    party_filter_options,
                                    index=default_index,
                                    key=f"party_filter_{member.id}",
                                )

                            # Initialize search result state
                            search_key = f"search_results_{member.id}"
                            if search_key not in st.session_state:
                                st.session_state[search_key] = None

                            if st.button(
                                "検索", key=f"search_button_{member.id}", type="primary"
                            ):
                                # Search with name only (party filtering done below)
                                politicians = presenter.search_politicians(
                                    search_politician_name, None
                                )

                                # Filter by party name if specified
                                if selected_party_filter != "すべて" and politicians:
                                    # Get party names for filtering
                                    filtered_politicians = []
                                    for p in politicians:
                                        if p.political_party_id:
                                            party_name = presenter.get_party_name_by_id(
                                                p.political_party_id
                                            )
                                            if (
                                                selected_party_filter.lower()
                                                in party_name.lower()
                                            ):
                                                filtered_politicians.append(p)
                                        elif selected_party_filter == "無所属":
                                            filtered_politicians.append(p)
                                    politicians = filtered_politicians

                                # Store search results in session state
                                st.session_state[search_key] = politicians

                            # Display search results from session state
                            politicians = st.session_state[search_key]

                            if politicians is not None:
                                if politicians:
                                    st.markdown(f"**検索結果: {len(politicians)}件**")

                                    # Display politician options with party names
                                    def format_politician(
                                        p: Any,
                                    ) -> str:
                                        party_name = "無所属"
                                        if p.political_party_id:
                                            party_name = presenter.get_party_name_by_id(
                                                p.political_party_id
                                            )
                                        district = p.district or "-"
                                        return f"{p.name} ({party_name}) - {district}"

                                    politician_options = [
                                        format_politician(p) for p in politicians
                                    ]
                                    politician_map = {
                                        format_politician(p): p.id
                                        for p in politicians
                                        if p.id
                                    }

                                    selected_politician = st.selectbox(
                                        "マッチする政治家を選択",
                                        politician_options,
                                        key=f"select_pol_{member.id}",
                                    )

                                    # Confidence score
                                    confidence = st.slider(
                                        "信頼度",
                                        min_value=0.0,
                                        max_value=1.0,
                                        value=0.8,
                                        step=0.05,
                                        key=f"confidence_{member.id}",
                                    )

                                    # Match button
                                    col_match, col_cancel = st.columns(2)
                                    with col_match:
                                        if st.button(
                                            "マッチング実行",
                                            key=f"execute_match_{member.id}",
                                            type="primary",
                                        ):
                                            import logging

                                            logger = logging.getLogger(__name__)
                                            logger.info(
                                                f"Match button clicked for "
                                                f"member {member.id}"
                                            )

                                            politician_id = politician_map[
                                                selected_politician
                                            ]

                                            logger.info(
                                                f"Calling review_extracted_member: "
                                                f"member_id={member.id}, "
                                                f"politician_id={politician_id}, "
                                                f"confidence={confidence}"
                                            )

                                            if member.id is not None:
                                                (
                                                    success,
                                                    message,
                                                ) = presenter.review_extracted_member(
                                                    member.id,
                                                    "match",
                                                    politician_id,
                                                    confidence,
                                                )

                                                logger.info(
                                                    f"review_extracted_member "
                                                    f"returned: success={success}, "
                                                    f"message={message}"
                                                )

                                                if success:
                                                    st.session_state[
                                                        "review_success_message"
                                                    ] = message
                                                    st.session_state[
                                                        f"matching_{member.id}"
                                                    ] = False
                                                    if search_key in st.session_state:
                                                        del st.session_state[search_key]
                                                    st.rerun()
                                                else:
                                                    st.session_state[
                                                        "review_error_message"
                                                    ] = message
                                                    st.session_state[
                                                        f"matching_{member.id}"
                                                    ] = False
                                                    if search_key in st.session_state:
                                                        del st.session_state[search_key]
                                                    st.rerun()

                                    with col_cancel:
                                        if st.button(
                                            "キャンセル",
                                            key=f"cancel_match_{member.id}",
                                        ):
                                            st.session_state[
                                                f"matching_{member.id}"
                                            ] = False
                                            del st.session_state[search_key]
                                            st.rerun()
                                else:
                                    st.warning("該当する政治家が見つかりませんでした")
                                    if st.button(
                                        "閉じる", key=f"close_no_results_{member.id}"
                                    ):
                                        st.session_state[f"matching_{member.id}"] = (
                                            False
                                        )
                                        del st.session_state[search_key]
                                        st.rerun()


def render_member_statistics_subtab(
    presenter: ParliamentaryGroupMemberPresenter,
) -> None:
    """Render the member statistics sub-tab."""
    st.markdown("### 統計情報")

    # Overall statistics
    stats = presenter.get_statistics()

    st.markdown("#### 全体統計")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総レコード数", f"{stats['total']}件")
    with col2:
        st.metric("紐付け未実行", f"{stats['pending']}件")
    with col3:
        st.metric("マッチ済み", f"{stats['matched']}件")
    with col4:
        st.metric("マッチなし", f"{stats['no_match']}件")

    # Parliamentary group statistics
    parliamentary_groups = presenter.get_all_parliamentary_groups()

    if parliamentary_groups:
        st.markdown("#### 議員団別統計")
        for group in parliamentary_groups:
            if group.id:
                group_stats = presenter.get_statistics(group.id)
                if group_stats["total"] > 0:
                    with st.expander(f"{group.name} (総数: {group_stats['total']}件)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "紐付け未実行", f"{group_stats.get('pending', 0)}件"
                            )
                            st.metric(
                                "マッチ済み", f"{group_stats.get('matched', 0)}件"
                            )
                        with col2:
                            st.metric(
                                "マッチなし", f"{group_stats.get('no_match', 0)}件"
                            )


def render_create_memberships_subtab(
    presenter: ParliamentaryGroupMemberPresenter,
) -> None:
    """Render the create memberships sub-tab."""
    st.markdown("### メンバーシップ作成")
    st.markdown(
        "マッチ済み（matched）のメンバーから、議員団メンバーシップ"
        "（parliamentary_group_memberships）を作成します"
    )

    # Get user info from session (from Google Sign-In)
    user_info: dict[str, str] | None = google_sign_in.get_user_info()
    if not user_info:
        st.warning("ユーザー情報を取得できません。ログインしてください。")
        return

    # Display current user
    user_name = user_info.get("name", "Unknown")
    user_email = user_info.get("email", "Unknown")
    st.info(f"実行ユーザー: {user_name} ({user_email})")

    # Get parliamentary groups
    parliamentary_groups = presenter.get_all_parliamentary_groups()

    # Options
    col1, col2 = st.columns(2)

    with col1:
        group_options = ["すべて"] + [g.name for g in parliamentary_groups if g.name]
        group_map = {g.name: g.id for g in parliamentary_groups if g.id and g.name}
        selected_group = st.selectbox(
            "対象議員団", group_options, key="memberships_group"
        )
        group_id = group_map.get(selected_group) if selected_group != "すべて" else None

    with col2:
        min_confidence = st.slider(
            "最小信頼度", min_value=0.5, max_value=1.0, value=0.7, step=0.05
        )

    # Start date
    start_date = st.date_input(
        "メンバーシップ開始日",
        value=date.today(),
        help="作成されるメンバーシップの所属開始日",
    )

    # Get matched count for preview
    stats = presenter.get_statistics(group_id)
    st.info(
        f"作成対象: {stats['matched']}件のマッチ済みメンバー "
        f"（信頼度 {min_confidence:.2f} 以上）"
    )

    # Re-match button
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🔄 再マッチング実行",
            help="未処理のメンバーに対してマッチング処理を再実行します",
        ):
            with st.spinner("マッチング処理中..."):
                matched_count, total_count, message = presenter.rematch_members(
                    group_id
                )
                st.info(message)
                if matched_count > 0:
                    st.rerun()

    with col2:
        # Creation button
        if st.button("メンバーシップ作成", type="primary"):
            with st.spinner("メンバーシップを作成中..."):
                try:
                    # Authenticate user and get user_id
                    container = Container()
                    auth_usecase = AuthenticateUserUseCase(
                        user_repository=container.repositories.user_repository()
                    )

                    email = user_info.get("email", "")
                    name = user_info.get("name")
                    user = asyncio.run(auth_usecase.execute(email=email, name=name))

                    # Create memberships with user_id
                    created_count, skipped_count, created_memberships = (
                        presenter.create_memberships(
                            parliamentary_group_id=group_id,
                            min_confidence=min_confidence,
                            start_date=start_date,
                            user_id=user.user_id,
                        )
                    )
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
                    import traceback

                    st.code(traceback.format_exc())
                    return

                # Display results
                if created_count > 0:
                    st.success(f"✅ {created_count}件のメンバーシップを作成しました")
                    st.balloons()

                if skipped_count > 0:
                    st.warning(f"⚠️ {skipped_count}件をスキップしました")

                # Display created memberships
                if created_memberships:
                    st.markdown("#### 作成されたメンバーシップ")
                    membership_data = []
                    for membership in created_memberships:
                        membership_data.append(
                            {
                                "メンバー名": membership["member_name"],
                                "政治家ID": membership["politician_id"],
                                "議員団ID": membership["parliamentary_group_id"],
                                "役職": membership["role"] or "-",
                            }
                        )

                    df_memberships = pd.DataFrame(membership_data)
                    st.dataframe(df_memberships, use_container_width=True)


def render_memberships_list_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the memberships list tab."""
    st.subheader("メンバーシップ一覧")

    # Get all parliamentary groups for filter
    all_groups = presenter.load_data()
    conferences = presenter.get_all_conferences()

    # Create conference to groups mapping
    conf_to_groups: dict[int, list[Any]] = {}
    for group in all_groups:
        if group.conference_id not in conf_to_groups:
            conf_to_groups[group.conference_id] = []
        conf_to_groups[group.conference_id].append(group)

    # Conference filter
    def get_conf_display_name(c: Any) -> str:
        gb_name = (
            c.governing_body.name
            if hasattr(c, "governing_body") and c.governing_body
            else ""
        )
        return f"{gb_name} - {c.name}"

    conf_options = ["すべて"] + [get_conf_display_name(c) for c in conferences]
    conf_map = {get_conf_display_name(c): c.id for c in conferences}

    selected_conf = st.selectbox(
        "会議体でフィルタ", conf_options, key="membership_conf_filter"
    )

    # Parliamentary group filter
    if selected_conf == "すべて":
        group_options = ["すべて"] + [g.name for g in all_groups]
        group_map = {g.name: g.id for g in all_groups}
    else:
        conf_id = conf_map.get(selected_conf)
        if conf_id is not None:
            filtered_groups = conf_to_groups.get(conf_id, [])
            group_options = ["すべて"] + [g.name for g in filtered_groups]
            group_map = {g.name: g.id for g in filtered_groups}
        else:
            group_options = ["すべて"]
            group_map = {}

    selected_group = st.selectbox(
        "議員団でフィルタ", group_options, key="membership_group_filter"
    )

    # Get memberships
    try:
        if selected_group == "すべて":
            # Get all memberships for selected conference or all
            all_memberships = []
            if selected_conf == "すべて":
                groups_to_query = all_groups
            else:
                conf_id = conf_map.get(selected_conf)
                if conf_id is not None:
                    groups_to_query = conf_to_groups.get(conf_id, [])
                else:
                    groups_to_query = []

            for group in groups_to_query:
                if group.id:
                    memberships = presenter.membership_repo.get_by_group(group.id)
                    all_memberships.extend(memberships)
        else:
            # Get memberships for specific group
            group_id = group_map[selected_group]
            all_memberships = presenter.membership_repo.get_by_group(group_id)

        if all_memberships:
            # Prepare data for display
            membership_data = []
            for membership in all_memberships:
                # Get group name
                group = next(
                    (
                        g
                        for g in all_groups
                        if g.id == membership.parliamentary_group_id
                    ),
                    None,
                )
                group_name = group.name if group else "不明"

                # Get politician name
                try:
                    politician = presenter.politician_repo.get_by_id(
                        membership.politician_id
                    )
                    politician_name = politician.name if politician else "不明"
                except Exception:
                    politician_name = "不明"

                # Format dates
                start_date_str = (
                    membership.start_date.strftime("%Y-%m-%d")
                    if membership.start_date
                    else "-"
                )
                end_date_str = (
                    membership.end_date.strftime("%Y-%m-%d")
                    if membership.end_date
                    else "現在"
                )

                membership_data.append(
                    {
                        "ID": membership.id,
                        "議員団": group_name,
                        "政治家": politician_name,
                        "役職": membership.role or "-",
                        "開始日": start_date_str,
                        "終了日": end_date_str,
                        "状態": "現在" if membership.end_date is None else "過去",
                    }
                )

            # Display as DataFrame
            df = pd.DataFrame(membership_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Display summary
            st.markdown("### 統計")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総メンバーシップ数", len(all_memberships))
            with col2:
                active_count = sum(1 for m in all_memberships if m.end_date is None)
                st.metric("現在のメンバー数", active_count)
            with col3:
                past_count = sum(1 for m in all_memberships if m.end_date is not None)
                st.metric("過去のメンバー数", past_count)

        else:
            st.info("メンバーシップが登録されていません")

    except Exception as e:
        st.error(f"メンバーシップの取得中にエラーが発生しました: {e}")


def render_duplicate_management_subtab(
    presenter: ParliamentaryGroupMemberPresenter,
) -> None:
    """Render the duplicate management sub-tab."""
    st.markdown("### 重複メンバー管理")
    st.markdown("同じ議員団内で同じ名前の抽出メンバーを検出し、重複を解消します。")

    # Note about automatic prevention
    st.info(
        "📝 注意: 新しい抽出では重複は自動的に防止されます。"
        "このツールは既存の重複レコードを管理するためのものです。"
    )

    try:
        # Get all parliamentary groups
        parliamentary_groups = presenter.get_all_parliamentary_groups()

        if not parliamentary_groups:
            st.warning("議員団が登録されていません")
            return

        # Create dictionary for group selection
        group_options = {
            f"{g.name} (ID: {g.id})": g.id
            for g in parliamentary_groups
            if g.name and g.id
        }

        selected_group = st.selectbox(
            "議員団を選択",
            options=list(group_options.keys()),
            key="duplicate_group_select",
        )

        if selected_group:
            group_id = group_options[selected_group]

            # Get all extracted members for this group
            from src.infrastructure.persistence import (
                extracted_parliamentary_group_member_repository_impl as epgmr_impl,
            )
            from src.infrastructure.persistence.repository_adapter import (
                RepositoryAdapter,
            )

            repo_adapter = RepositoryAdapter(
                epgmr_impl.ExtractedParliamentaryGroupMemberRepositoryImpl
            )

            members = repo_adapter.get_by_parliamentary_group(group_id)

            if not members:
                st.info("この議員団には抽出されたメンバーがいません")
                return

            # Find duplicates by name
            from collections import defaultdict

            members_by_name: dict[str, list[Any]] = defaultdict(list)
            for member in members:
                members_by_name[member.extracted_name].append(member)

            # Filter to only show duplicates (names with more than 1 record)
            duplicates = {
                name: member_list
                for name, member_list in members_by_name.items()
                if len(member_list) > 1
            }

            if not duplicates:
                st.success("✅ 重複レコードは見つかりませんでした")
                return

            st.warning(f"⚠️ {len(duplicates)}件の重複する名前が見つかりました")

            # Display each duplicate group
            for name, duplicate_members in duplicates.items():
                st.markdown(f"#### {name} ({len(duplicate_members)}件のレコード)")

                # Display each duplicate record
                for i, member in enumerate(duplicate_members, 1):
                    with st.expander(
                        f"レコード {i} (ID: {member.id}) - "
                        f"抽出日: {member.extracted_at.strftime('%Y-%m-%d %H:%M')}"
                    ):
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.write(f"**名前:** {member.extracted_name}")
                            st.write(f"**役職:** {member.extracted_role or 'なし'}")
                            st.write(
                                f"**政党:** {member.extracted_party_name or 'なし'}"
                            )
                            st.write(
                                f"**選挙区:** {member.extracted_district or 'なし'}"
                            )
                            st.write(f"**マッチング状態:** {member.matching_status}")
                            if member.matched_politician_id:
                                st.write(
                                    f"**マッチング済み政治家ID:** "
                                    f"{member.matched_politician_id}"
                                )
                            st.write(f"**ソースURL:** {member.source_url}")

                        with col2:
                            # Delete button for each record
                            if st.button(
                                "🗑️ 削除",
                                key=f"delete_member_{member.id}",
                                type="secondary",
                            ):
                                try:
                                    # Delete using async repository method
                                    import asyncio

                                    from sqlalchemy import text

                                    # Create an async function to delete
                                    async def delete_member(member_id: int) -> None:
                                        session_factory = (
                                            repo_adapter.get_async_session_factory()
                                        )
                                        async with session_factory() as session:
                                            delete_query = text(
                                                """
                                                DELETE FROM
                                                    extracted_parliamentary_group_members
                                                WHERE id = :member_id
                                            """
                                            )
                                            await session.execute(
                                                delete_query, {"member_id": member_id}
                                            )
                                            await session.commit()

                                    # Run the async delete
                                    asyncio.run(delete_member(member.id))

                                    st.success(f"レコードID {member.id} を削除しました")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"削除エラー: {e}")

                st.markdown("---")

            # Close the repository adapter
            repo_adapter.close()

    except Exception as e:
        st.error(f"重複管理中にエラーが発生しました: {e}")
        import traceback

        st.code(traceback.format_exc())


def main() -> None:
    """Main function for testing."""
    render_parliamentary_groups_page()


if __name__ == "__main__":
    main()
