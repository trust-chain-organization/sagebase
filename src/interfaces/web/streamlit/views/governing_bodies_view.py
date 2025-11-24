"""View for governing body management."""

import streamlit as st

from src.interfaces.web.streamlit.presenters.governing_body_presenter import (
    GoverningBodyPresenter,
)


def render_governing_bodies_page() -> None:
    """Render the governing bodies management page."""
    st.header("開催主体管理")
    st.markdown("開催主体（国、都道府県、市町村）の情報を管理します")

    presenter = GoverningBodyPresenter()

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["開催主体一覧", "新規登録", "編集・削除"])

    with tab1:
        render_governing_bodies_list_tab(presenter)

    with tab2:
        render_new_governing_body_tab(presenter)

    with tab3:
        render_edit_delete_tab(presenter)


def render_governing_bodies_list_tab(presenter: GoverningBodyPresenter) -> None:
    """Render the governing bodies list tab."""
    st.subheader("開催主体一覧")

    # Filter options
    col1, col2 = st.columns(2)

    with col1:
        type_options = ["すべて"] + presenter.get_type_options()
        selected_type = st.selectbox(
            "種別でフィルタ", type_options, key="gb_type_filter"
        )

    with col2:
        conference_filter = st.selectbox(
            "会議体でフィルタ",
            ["すべて", "会議体あり", "会議体なし"],
            key="gb_conference_filter",
        )

    # Load data with filters
    governing_bodies, statistics = presenter.load_governing_bodies_with_filters(
        selected_type, conference_filter
    )

    if governing_bodies:
        # Seed file generation section
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### SEEDファイル生成")
                st.markdown(
                    "現在登録されている開催主体データからSEEDファイルを生成します"
                )
            with col2:
                if st.button(
                    "SEEDファイル生成", key="generate_gb_seed", type="primary"
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
        df = presenter.to_dataframe(governing_bodies)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Display statistics
        if statistics:
            st.markdown("### 統計情報")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総数", f"{statistics.total_count}件")
            with col2:
                st.metric("国", f"{statistics.country_count}件")
            with col3:
                st.metric("都道府県", f"{statistics.prefecture_count}件")
            with col4:
                st.metric("市町村", f"{statistics.city_count}件")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("会議体あり", f"{statistics.with_conference_count}件")
            with col2:
                st.metric("会議体なし", f"{statistics.without_conference_count}件")
    else:
        st.info("開催主体が登録されていません")


def render_new_governing_body_tab(presenter: GoverningBodyPresenter) -> None:
    """Render the new governing body registration tab."""
    st.subheader("新規開催主体登録")

    with st.form("new_governing_body_form"):
        name = st.text_input("開催主体名", key="new_gb_name")
        type_options = presenter.get_type_options()
        gb_type = st.selectbox("種別", type_options, key="new_gb_type")
        organization_code = st.text_input(
            "組織コード（オプション）", key="new_gb_org_code"
        )
        organization_type = st.text_input(
            "組織タイプ（オプション）", key="new_gb_org_type"
        )

        submitted = st.form_submit_button("登録")

        if submitted:
            if not name:
                st.error("開催主体名を入力してください")
            else:
                success, id_or_error = presenter.create(
                    name,
                    gb_type,
                    organization_code or None,
                    organization_type or None,
                )
                if success:
                    st.success(f"開催主体「{name}」を登録しました（ID: {id_or_error}）")
                    st.rerun()
                else:
                    st.error(f"登録に失敗しました: {id_or_error}")


def render_edit_delete_tab(presenter: GoverningBodyPresenter) -> None:
    """Render the edit/delete tab."""
    st.subheader("開催主体の編集・削除")

    # Load all governing bodies
    governing_bodies = presenter.load_data()

    if governing_bodies:
        # Select governing body to edit
        gb_options = [f"{gb.name} ({gb.type}) - ID: {gb.id}" for gb in governing_bodies]
        selected_gb_option = st.selectbox(
            "編集する開催主体を選択", gb_options, key="edit_gb_select"
        )

        # Get selected governing body ID
        selected_gb_id = int(selected_gb_option.split("ID: ")[1])
        selected_gb = next(gb for gb in governing_bodies if gb.id == selected_gb_id)

        # Edit and delete forms
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 編集")
            with st.form("edit_governing_body_form"):
                edit_name = st.text_input(
                    "開催主体名", value=selected_gb.name, key="edit_gb_name"
                )
                type_options = presenter.get_type_options()
                edit_type = st.selectbox(
                    "種別",
                    type_options,
                    index=type_options.index(selected_gb.type)
                    if selected_gb.type
                    else 0,
                    key="edit_gb_type",
                )
                edit_org_code = st.text_input(
                    "組織コード",
                    value=selected_gb.organization_code or "",
                    key="edit_gb_org_code",
                )
                edit_org_type = st.text_input(
                    "組織タイプ",
                    value=selected_gb.organization_type or "",
                    key="edit_gb_org_type",
                )

                update_submitted = st.form_submit_button("更新")

                if update_submitted:
                    if not edit_name:
                        st.error("開催主体名を入力してください")
                    else:
                        success, error = presenter.update(
                            selected_gb_id,
                            edit_name,
                            edit_type,
                            edit_org_code or None,
                            edit_org_type or None,
                        )
                        if success:
                            st.success(f"開催主体「{edit_name}」を更新しました")
                            st.rerun()
                        else:
                            st.error(f"更新に失敗しました: {error}")

        with col2:
            st.markdown("### 削除")

            # Show conference count
            conference_count = getattr(selected_gb, "conference_count", 0)
            if conference_count > 0:
                st.warning(
                    f"この開催主体には{conference_count}件の会議体が関連付けられています。"
                    f"削除するには、先に関連する会議体を削除する必要があります。"
                )
            else:
                st.info("この開催主体に関連する会議体はありません。")

                if st.button(
                    "削除",
                    key="delete_gb_button",
                    type="secondary",
                    disabled=conference_count > 0,
                ):
                    # Delete confirmation
                    if st.checkbox(
                        f"「{selected_gb.name}」を本当に削除しますか？",
                        key="confirm_delete_gb",
                    ):
                        if st.button(
                            "削除を実行", key="execute_delete_gb", type="primary"
                        ):
                            success, error = presenter.delete(selected_gb_id)
                            if success:
                                st.success(
                                    f"開催主体「{selected_gb.name}」を削除しました"
                                )
                                st.rerun()
                            else:
                                st.error(f"削除に失敗しました: {error}")
    else:
        st.info("編集する開催主体がありません")


def main() -> None:
    """Main function for testing."""
    render_governing_bodies_page()


if __name__ == "__main__":
    main()
