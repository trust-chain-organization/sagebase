"""Edit and delete tab for parliamentary groups.

議員団の編集・削除タブのUI実装を提供します。
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_edit_delete_tab(presenter: ParliamentaryGroupPresenter) -> None:
    """Render the edit/delete tab.

    議員団の編集・削除タブをレンダリングします。
    議員団の選択、情報の編集、削除処理を行います。

    Args:
        presenter: 議員団プレゼンター
    """
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
        # Presenterのメソッドを通じてメンバーシップを取得
        memberships = presenter.get_memberships_by_group(selected_group.id)

        if memberships:
            # アクティブメンバー数をカウント
            active_count = sum(1 for m in memberships if m["is_active"])
            st.write(f"現在のメンバー数: {active_count}名")

            # 表示用にデータを整形
            display_data = []
            for m in memberships:
                start_date_str = (
                    m["start_date"].strftime("%Y-%m-%d") if m["start_date"] else "-"
                )
                end_date_str = (
                    m["end_date"].strftime("%Y-%m-%d") if m["end_date"] else "現在"
                )
                display_data.append(
                    {
                        "政治家": m["politician_name"],
                        "役職": m["role"] or "-",
                        "開始日": start_date_str,
                        "終了日": end_date_str,
                    }
                )

            # DataFrameで表示
            if display_data:
                df = pd.DataFrame(display_data)
                st.dataframe(df, use_container_width=True, hide_index=True, height=200)
        else:
            st.info("メンバーが登録されていません")

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
