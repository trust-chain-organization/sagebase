"""View for extracted politicians review management."""

from datetime import datetime, timedelta

import streamlit as st

from src.interfaces.web.streamlit.presenters.extracted_politician_presenter import (
    ExtractedPoliticianPresenter,
)


def render_extracted_politicians_page() -> None:
    """Render the extracted politicians review page."""
    st.header("政治家レビュー")
    st.markdown("LLMが抽出した政治家データをレビューして承認・却下を行います")

    presenter = ExtractedPoliticianPresenter()

    # Create tabs
    tabs = st.tabs(["レビュー", "統計", "一括変換"])

    with tabs[0]:
        render_review_tab(presenter)

    with tabs[1]:
        render_statistics_tab(presenter)

    with tabs[2]:
        render_conversion_tab(presenter)


def render_review_tab(presenter: ExtractedPoliticianPresenter) -> None:
    """Render the review tab."""
    st.subheader("抽出済み政治家レビュー")

    # Get parties for filter
    parties = presenter.get_all_parties()

    # Filters section
    st.markdown("### フィルター")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Status filter (multi-select)
        status_options = {
            "⏳ 未レビュー": "pending",
            "👀 レビュー済み": "reviewed",
            "✅ 承認済み": "approved",
            "❌ 却下": "rejected",
            "✔️ 変換済み": "converted",
        }
        selected_status_labels = st.multiselect(
            "ステータス",
            options=list(status_options.keys()),
            default=["⏳ 未レビュー"],
        )
        selected_statuses = [status_options[label] for label in selected_status_labels]

    with col2:
        # Party filter
        party_options = ["すべて"] + [p.name for p in parties]
        party_map = {p.name: p.id for p in parties}
        selected_party = st.selectbox("政党", party_options)
        party_id = party_map.get(selected_party) if selected_party != "すべて" else None

    with col3:
        # Name search
        search_name = st.text_input("名前検索", placeholder="例: 山田")

    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "抽出開始日",
            value=datetime.now() - timedelta(days=30),
            max_value=datetime.now(),
        )
    with col2:
        end_date = st.date_input(
            "抽出終了日", value=datetime.now(), max_value=datetime.now()
        )

    # Convert dates to datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Get filtered politicians
    politicians = presenter.get_filtered_politicians(
        statuses=selected_statuses,
        party_id=party_id,
        start_date=start_datetime,
        end_date=end_datetime,
        search_name=search_name if search_name else None,
        limit=100,
    )

    if not politicians:
        st.info("該当するレコードがありません")
        return

    # Display statistics
    st.markdown(f"### 検索結果: {len(politicians)}件")

    # Bulk actions
    st.markdown("### 一括アクション")
    col1, col2, col3, col4 = st.columns(4)

    # Initialize session state for selected items
    if "selected_politicians" not in st.session_state:
        st.session_state.selected_politicians = []

    with col1:
        if st.button("全選択", key="select_all"):
            st.session_state.selected_politicians = [p.id for p in politicians if p.id]

    with col2:
        if st.button("選択解除", key="deselect_all"):
            st.session_state.selected_politicians = []

    with col3:
        selected_count = len(st.session_state.selected_politicians)
        st.metric("選択数", f"{selected_count}件")

    # Bulk action buttons
    if selected_count > 0:
        st.markdown("#### 選択したレコードに対する操作")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("一括承認", type="primary", key="bulk_approve"):
                with st.spinner("承認処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_politicians, "approve"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件を承認しました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の承認に失敗しました")
                    st.session_state.selected_politicians = []
                    st.rerun()

        with col2:
            if st.button("一括却下", key="bulk_reject"):
                with st.spinner("却下処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_politicians, "reject"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件を却下しました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の却下に失敗しました")
                    st.session_state.selected_politicians = []
                    st.rerun()

        with col3:
            if st.button("一括レビュー済み", key="bulk_review"):
                with st.spinner("レビュー済み処理中..."):
                    success, failed, message = presenter.bulk_review(
                        st.session_state.selected_politicians, "review"
                    )
                    if success > 0:
                        st.success(f"✅ {success}件をレビュー済みにしました")
                    if failed > 0:
                        st.error(f"❌ {failed}件の処理に失敗しました")
                    st.session_state.selected_politicians = []
                    st.rerun()

    # Display data table
    st.markdown("### データ一覧")

    # Convert to DataFrame for display
    df = presenter.to_dataframe(politicians, parties)

    if df is not None:
        # Add checkboxes for each row
        for idx, politician in enumerate(politicians):
            if politician.id is None:
                continue

            col1, col2 = st.columns([1, 9])

            with col1:
                selected = st.checkbox(
                    "選択",
                    key=f"check_{politician.id}",
                    value=politician.id in st.session_state.selected_politicians,
                    label_visibility="hidden",
                )
                if (
                    selected
                    and politician.id not in st.session_state.selected_politicians
                ):
                    st.session_state.selected_politicians.append(politician.id)
                elif (
                    not selected
                    and politician.id in st.session_state.selected_politicians
                ):
                    st.session_state.selected_politicians.remove(politician.id)

            with col2:
                party = df.iloc[idx]["政党"]
                status = df.iloc[idx]["ステータス"]
                with st.expander(f"{politician.name} ({party}) - {status}"):
                    # Display details
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**ID:** {politician.id}")
                        st.write(f"**名前:** {politician.name}")
                        st.write(f"**政党:** {df.iloc[idx]['政党']}")
                        st.write(f"**選挙区:** {politician.district or '-'}")

                    with col_b:
                        st.write(f"**ステータス:** {df.iloc[idx]['ステータス']}")
                        st.write(f"**抽出日時:** {df.iloc[idx]['抽出日時']}")
                        st.write(
                            f"**レビュー日時:** {df.iloc[idx]['レビュー日時'] or '-'}"
                        )

                    if politician.profile_url:
                        st.write(f"**プロフィールURL:** {politician.profile_url}")

                    # Individual action buttons
                    st.markdown("---")
                    col_1, col_2, col_3, col_4 = st.columns(4)

                    with col_1:
                        if st.button("✏️ 編集", key=f"edit_{politician.id}"):
                            st.session_state[f"editing_{politician.id}"] = True

                    with col_2:
                        if st.button(
                            "✅ 承認", key=f"approve_{politician.id}", type="primary"
                        ):
                            if politician.id is not None:
                                success, message = presenter.review_politician(
                                    politician.id, "approve"
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    with col_3:
                        if st.button("❌ 却下", key=f"reject_{politician.id}"):
                            if politician.id is not None:
                                success, message = presenter.review_politician(
                                    politician.id, "reject"
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    with col_4:
                        if st.button("👀 レビュー済み", key=f"review_{politician.id}"):
                            if politician.id is not None:
                                success, message = presenter.review_politician(
                                    politician.id, "review"
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    # Edit dialog
                    if st.session_state.get(f"editing_{politician.id}", False):
                        with st.container():
                            st.markdown("#### 政治家情報の編集")

                            # Create edit form
                            edit_name = st.text_input(
                                "名前",
                                value=politician.name,
                                key=f"edit_name_{politician.id}",
                            )

                            # Party selection
                            party_names = ["無所属"] + [p.name for p in parties]
                            party_map: dict[str, int | None] = {
                                p.name: p.id for p in parties if p.id
                            }
                            party_map["無所属"] = None

                            current_party = "無所属"
                            if politician.party_id:
                                for p in parties:
                                    if p.id == politician.party_id:
                                        current_party = p.name
                                        break

                            edit_party = st.selectbox(
                                "政党",
                                party_names,
                                index=party_names.index(current_party),
                                key=f"edit_party_{politician.id}",
                            )

                            edit_district = st.text_input(
                                "選挙区",
                                value=politician.district or "",
                                key=f"edit_district_{politician.id}",
                            )

                            edit_profile_url = st.text_input(
                                "プロフィールURL",
                                value=politician.profile_url or "",
                                key=f"edit_profile_url_{politician.id}",
                            )

                            # Save/Cancel buttons
                            save_col, cancel_col = st.columns(2)
                            with save_col:
                                if st.button(
                                    "💾 保存",
                                    key=f"save_{politician.id}",
                                    type="primary",
                                ):
                                    if politician.id is not None:
                                        success, message = presenter.update_politician(
                                            politician.id,
                                            edit_name,
                                            party_map[edit_party],
                                            edit_district if edit_district else None,
                                            edit_profile_url
                                            if edit_profile_url
                                            else None,
                                        )
                                        if success:
                                            st.success(message)
                                            st.session_state[
                                                f"editing_{politician.id}"
                                            ] = False
                                            st.rerun()
                                        else:
                                            st.error(message)

                            with cancel_col:
                                if st.button(
                                    "❌ キャンセル", key=f"cancel_{politician.id}"
                                ):
                                    st.session_state[f"editing_{politician.id}"] = False
                                    st.rerun()


def render_statistics_tab(presenter: ExtractedPoliticianPresenter) -> None:
    """Render the statistics tab."""
    st.subheader("統計情報")

    stats = presenter.get_statistics()

    # Overall statistics
    st.markdown("### 全体統計")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総レコード数", f"{stats['total']}件")
    with col2:
        st.metric("未レビュー", f"{stats['pending']}件")
    with col3:
        st.metric("承認済み", f"{stats['approved']}件")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("レビュー済み", f"{stats['reviewed']}件")
    with col2:
        st.metric("却下", f"{stats['rejected']}件")
    with col3:
        st.metric("変換済み", f"{stats['converted']}件")

    # Party statistics
    if stats["by_party"]:
        st.markdown("### 政党別統計")
        for party_name, party_stats in stats["by_party"].items():
            with st.expander(f"{party_name} (総数: {party_stats['total']}件)"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("未レビュー", f"{party_stats.get('pending', 0)}件")
                    st.metric("レビュー済み", f"{party_stats.get('reviewed', 0)}件")
                with col2:
                    st.metric("承認済み", f"{party_stats.get('approved', 0)}件")
                    st.metric("却下", f"{party_stats.get('rejected', 0)}件")
                with col3:
                    st.metric("変換済み", f"{party_stats.get('converted', 0)}件")


def render_conversion_tab(presenter: ExtractedPoliticianPresenter) -> None:
    """Render the conversion tab."""
    st.subheader("一括変換")
    st.markdown(
        "承認済み（approved）のレコードを政治家（politicians）テーブルに変換します"
    )

    # Get parties for filter
    parties = presenter.get_all_parties()

    # Conversion options
    col1, col2 = st.columns(2)
    with col1:
        party_options = ["すべて"] + [p.name for p in parties]
        party_map = {p.name: p.id for p in parties}
        selected_party = st.selectbox("対象政党", party_options, key="conv_party")
        party_id = party_map.get(selected_party) if selected_party != "すべて" else None

    with col2:
        batch_size = st.number_input(
            "バッチサイズ", min_value=1, max_value=1000, value=100, step=10
        )

    # Dry run option
    dry_run = st.checkbox("ドライラン（実際には変換しない）", value=False)

    # Get approved count for preview
    approved_politicians = presenter.get_filtered_politicians(
        statuses=["approved"], party_id=party_id, limit=batch_size
    )

    st.info(f"変換対象: {len(approved_politicians)}件の承認済みレコード")

    # Conversion button
    if st.button(
        "変換実行" if not dry_run else "ドライラン実行",
        type="primary" if not dry_run else "secondary",
    ):
        with st.spinner("変換処理中..." if not dry_run else "ドライラン実行中..."):
            converted, skipped, errors, error_messages = (
                presenter.convert_approved_politicians(
                    party_id=party_id, batch_size=batch_size, dry_run=dry_run
                )
            )

            # Display results
            if dry_run:
                st.info("🔍 ドライラン結果")
            else:
                st.success("✅ 変換完了")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("変換成功", f"{converted}件")
            with col2:
                st.metric("スキップ", f"{skipped}件")
            with col3:
                st.metric("エラー", f"{errors}件")

            # Display error messages if any
            if error_messages:
                st.error("エラー詳細:")
                for error in error_messages:
                    st.write(f"- {error}")

            if not dry_run and converted > 0:
                st.balloons()
