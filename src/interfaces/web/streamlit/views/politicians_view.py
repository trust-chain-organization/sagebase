"""View for politician management."""

import streamlit as st

from src.interfaces.web.streamlit.components import (
    render_verification_badge,
    render_verification_checkbox_with_warning,
    render_verification_filter,
)
from src.interfaces.web.streamlit.presenters.politician_presenter import (
    PoliticianPresenter,
)
from src.seed_generator import SeedGenerator


def render_politicians_page() -> None:
    """Render the politicians management page."""
    st.header("政治家管理")
    st.markdown("政治家の情報を管理します")

    presenter = PoliticianPresenter()

    # Create tabs
    tabs = st.tabs(["政治家一覧", "新規登録", "編集・削除", "重複統合"])

    with tabs[0]:
        render_politicians_list_tab(presenter)

    with tabs[1]:
        render_new_politician_tab(presenter)

    with tabs[2]:
        render_edit_delete_tab(presenter)

    with tabs[3]:
        render_merge_tab(presenter)


def render_politicians_list_tab(presenter: PoliticianPresenter) -> None:
    """Render the politicians list tab."""
    st.subheader("政治家一覧")

    # SEEDファイル生成セクション（一番上に配置）
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### SEEDファイル生成")
            st.markdown("現在登録されている政治家データからSEEDファイルを生成します")
        with col2:
            if st.button(
                "SEEDファイル生成",
                key="generate_politicians_seed",
                type="primary",
            ):
                with st.spinner("SEEDファイルを生成中..."):
                    try:
                        generator = SeedGenerator()
                        seed_content = generator.generate_politicians_seed()

                        # ファイルを保存
                        output_path = "database/seed_politicians_generated.sql"
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(seed_content)

                        st.success(f"✅ SEEDファイルを生成しました: {output_path}")

                        # 生成内容をプレビュー表示
                        with st.expander("生成内容をプレビュー", expanded=False):
                            st.code(seed_content[:5000], language="sql")
                    except Exception as e:
                        st.error(
                            f"❌ SEEDファイル生成中にエラーが発生しました: {str(e)}"
                        )

    st.divider()

    # Get parties for filter
    parties = presenter.get_all_parties()

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        party_options = ["すべて"] + [p.name for p in parties]
        party_map = {p.name: p.id for p in parties}
        selected_party = st.selectbox("政党でフィルタ", party_options)

    with col2:
        search_name = st.text_input("名前で検索", placeholder="例: 山田")

    with col3:
        verification_filter = render_verification_filter(key="politician_verification")

    # Load politicians
    party_id = party_map.get(selected_party) if selected_party != "すべて" else None
    politicians = presenter.load_politicians_with_verification_filter(
        party_id, search_name if search_name else None, verification_filter
    )

    if politicians:
        # Display data in DataFrame
        df = presenter.to_dataframe(politicians, parties)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Statistics
        st.markdown("### 統計情報")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総数", f"{len(politicians)}名")
        with col2:
            party_counts = {}
            for p in politicians:
                party_name = next(
                    (
                        party.name
                        for party in parties
                        if party.id == p.political_party_id
                    ),
                    "無所属",
                )
                party_counts[party_name] = party_counts.get(party_name, 0) + 1
            if party_counts:
                max_party = max(party_counts, key=party_counts.get)  # type: ignore[arg-type]
                st.metric("最多政党", f"{max_party} ({party_counts[max_party]}名)")
        with col3:
            with_url = len([p for p in politicians if p.profile_page_url])
            st.metric("プロフィールURL登録", f"{with_url}名")
    else:
        st.info("政治家が登録されていません")


def render_new_politician_tab(presenter: PoliticianPresenter) -> None:
    """Render the new politician registration tab."""
    st.subheader("新規政治家登録")

    # Get parties
    parties = presenter.get_all_parties()

    with st.form("new_politician_form"):
        name = st.text_input("名前", placeholder="山田太郎")

        party_options = ["無所属"] + [p.name for p in parties]
        party_map = {p.name: p.id for p in parties}
        selected_party = st.selectbox("政党", party_options)

        district = st.text_input("選挙区（任意）", placeholder="東京1区")
        profile_url = st.text_input(
            "プロフィールURL（任意）", placeholder="https://example.com/profile"
        )
        image_url = st.text_input(
            "画像URL（任意）", placeholder="https://example.com/image.jpg"
        )

        submitted = st.form_submit_button("登録")

        if submitted:
            if not name:
                st.error("名前を入力してください")
            else:
                party_id = (
                    party_map.get(selected_party)
                    if selected_party != "無所属"
                    else None
                )
                success, politician_id, error = presenter.create(
                    name,
                    party_id,
                    district if district else None,
                    profile_url if profile_url else None,
                    image_url if image_url else None,
                )
                if success:
                    st.success(f"政治家「{name}」を登録しました（ID: {politician_id}）")
                    st.rerun()
                else:
                    st.error(f"登録に失敗しました: {error}")


def render_edit_delete_tab(presenter: PoliticianPresenter) -> None:
    """Render the edit/delete tab."""
    st.subheader("政治家の編集・削除")

    # Load all politicians
    politicians = presenter.load_data()
    if not politicians:
        st.info("編集する政治家がありません")
        return

    # Get parties
    parties = presenter.get_all_parties()

    # Select politician to edit
    politician_options = [f"{p.name} (ID: {p.id})" for p in politicians]
    selected_politician_str = st.selectbox("編集する政治家を選択", politician_options)

    # Get selected politician
    selected_id = int(selected_politician_str.split("ID: ")[1].replace(")", ""))
    selected_politician = next(p for p in politicians if p.id == selected_id)

    # Display current verification status
    st.markdown("#### 検証状態")
    render_verification_badge(selected_politician.is_manually_verified)

    # Edit and delete forms
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 編集")
        with st.form("edit_politician_form"):
            new_name = st.text_input("名前", value=selected_politician.name)

            party_options = ["無所属"] + [p.name for p in parties]
            party_map = {p.name: p.id for p in parties}
            current_party = next(
                (
                    p.name
                    for p in parties
                    if p.id == selected_politician.political_party_id
                ),
                "無所属",
            )
            new_party = st.selectbox(
                "政党",
                party_options,
                index=party_options.index(current_party),
            )

            new_district = st.text_input(
                "選挙区", value=selected_politician.district or ""
            )
            new_profile_url = st.text_input(
                "プロフィールURL", value=selected_politician.profile_page_url or ""
            )

            submitted = st.form_submit_button("更新")

            if submitted:
                if not new_name:
                    st.error("名前を入力してください")
                else:
                    party_id = (
                        party_map.get(new_party) if new_party != "無所属" else None
                    )
                    success, error = presenter.update(
                        selected_politician.id,  # type: ignore[arg-type]
                        new_name,
                        party_id,
                        new_district if new_district else None,
                        new_profile_url if new_profile_url else None,
                    )
                    if success:
                        st.success("政治家を更新しました")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### 手動検証")
        new_verified, changed = render_verification_checkbox_with_warning(
            current_value=selected_politician.is_manually_verified,
            key=f"verify_politician_{selected_id}",
        )

        if changed:
            if st.button("検証状態を更新", type="primary"):
                success, error = presenter.update_verification_status(
                    selected_id, new_verified
                )
                if success:
                    status_text = "手動検証済み" if new_verified else "未検証"
                    st.success(f"検証状態を「{status_text}」に更新しました")
                    st.rerun()
                else:
                    st.error(f"検証状態の更新に失敗しました: {error}")

        st.markdown("#### 削除")
        st.warning("⚠️ 政治家を削除すると、関連する発言記録も影響を受けます")

        if st.button("🗑️ この政治家を削除", type="secondary"):
            success, error = presenter.delete(selected_politician.id)  # type: ignore[arg-type]
            if success:
                st.success(f"政治家「{selected_politician.name}」を削除しました")
                st.rerun()
            else:
                st.error(f"削除に失敗しました: {error}")


def render_merge_tab(presenter: PoliticianPresenter) -> None:
    """Render the merge tab."""
    st.subheader("重複統合")
    st.markdown("重複している政治家を統合します")

    # Load all politicians
    politicians = presenter.load_data()
    if not politicians or len(politicians) < 2:
        st.info("統合する政治家が不足しています")
        return

    politician_options = [f"{p.name} (ID: {p.id})" for p in politicians]

    col1, col2 = st.columns(2)

    with col1:
        source_str = st.selectbox("統合元（削除される）", politician_options)
        source_id = int(source_str.split("ID: ")[1].replace(")", ""))

    with col2:
        target_str = st.selectbox("統合先（残る）", politician_options)
        target_id = int(target_str.split("ID: ")[1].replace(")", ""))

    if source_id == target_id:
        st.error("同じ政治家を選択することはできません")
    else:
        st.info("統合元のすべてのデータが統合先に移動され、統合元は削除されます")

        if st.button("統合を実行", type="primary"):
            success, error = presenter.merge(source_id, target_id)
            if success:
                st.success("政治家を統合しました")
                st.rerun()
            else:
                st.error(f"統合に失敗しました: {error}")


def main() -> None:
    """Main function for testing."""
    render_politicians_page()


if __name__ == "__main__":
    main()
