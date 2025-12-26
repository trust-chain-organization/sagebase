"""作業履歴ビューモジュール

ユーザーが実行した作業の履歴を表示するビューを定義します。
"""

from datetime import date, datetime, timedelta

import pandas as pd

import streamlit as st

from src.application.dtos.work_history_dto import WorkType
from src.interfaces.web.streamlit.presenters.work_history_presenter import (
    WorkHistoryPresenter,
)


def render_work_history_page() -> None:
    """作業履歴ページをレンダリングする"""
    presenter = WorkHistoryPresenter()

    st.header("📋 作業履歴")
    st.markdown("ユーザーが実行した作業の履歴を照会・検索できます")

    # Create tabs
    tab1, tab2 = st.tabs(["履歴一覧", "統計情報"])

    with tab1:
        render_history_list_tab(presenter)

    with tab2:
        render_statistics_tab(presenter)


def render_history_list_tab(presenter: WorkHistoryPresenter) -> None:
    """履歴一覧タブをレンダリングする

    Args:
        presenter: 作業履歴プレゼンター
    """
    st.subheader("🔍 作業履歴検索")

    # フィルタリングオプション
    with st.expander("🔎 フィルタリングオプション", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # ユーザーIDフィルター（将来的にユーザー選択UIを追加）
            st.text_input(
                "ユーザーID（UUID）",
                key="user_id_filter",
                help="特定のユーザーの作業履歴を絞り込む場合はUUIDを入力してください",
            )

        with col2:
            # 作業タイプフィルター
            work_type_display_names = presenter.get_work_type_display_names()
            selected_work_types = st.multiselect(
                "作業タイプ",
                options=list(work_type_display_names.keys()),
                format_func=lambda x: work_type_display_names[x],
                help="絞り込む作業タイプを選択してください（複数選択可）",
            )

        with col3:
            # 日付範囲フィルター
            date_range_option = st.selectbox(
                "期間",
                options=["すべて", "今日", "過去7日間", "過去30日間", "カスタム"],
                help="作業実行日の期間を選択してください",
            )

    # カスタム日付範囲の入力
    start_date = None
    end_date = None

    if date_range_option == "カスタム":
        col1, col2 = st.columns(2)
        with col1:
            start_date_input = st.date_input(
                "開始日",
                value=date.today() - timedelta(days=30),
            )
            if start_date_input:
                start_date = datetime.combine(start_date_input, datetime.min.time())

        with col2:
            end_date_input = st.date_input(
                "終了日",
                value=date.today(),
            )
            if end_date_input:
                end_date = datetime.combine(end_date_input, datetime.max.time())
    elif date_range_option == "今日":
        start_date = datetime.combine(date.today(), datetime.min.time())
        end_date = datetime.combine(date.today(), datetime.max.time())
    elif date_range_option == "過去7日間":
        start_date = datetime.combine(
            date.today() - timedelta(days=7), datetime.min.time()
        )
        end_date = datetime.now()
    elif date_range_option == "過去30日間":
        start_date = datetime.combine(
            date.today() - timedelta(days=30), datetime.min.time()
        )
        end_date = datetime.now()

    # ページネーション設定
    if "work_history_page" not in st.session_state:
        st.session_state.work_history_page = 0

    items_per_page = 20
    offset = st.session_state.work_history_page * items_per_page

    # ユーザーIDの解析
    user_id = None
    user_id_str = st.session_state.get("user_id_filter", "").strip()
    if user_id_str:
        try:
            from uuid import UUID

            user_id = UUID(user_id_str)
        except ValueError:
            st.warning("無効なUUID形式です。フィルタリングを適用できません。")

    # 作業履歴の取得
    histories = presenter.search_histories(
        user_id=user_id,
        work_types=selected_work_types if selected_work_types else None,
        start_date=start_date,
        end_date=end_date,
        limit=items_per_page,
        offset=offset,
    )

    # 作業履歴の表示
    if histories:
        st.success(f"🎯 {len(histories)}件の作業履歴が見つかりました")

        # データフレームの作成
        df_data = []
        for history in histories:
            df_data.append(
                {
                    "ユーザー名": history.user_name or "不明",
                    "メールアドレス": history.user_email or "不明",
                    "作業タイプ": history.work_type_display_name,
                    "対象データ": history.target_data,
                    "実行日時": history.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        df = pd.DataFrame(df_data)

        # データフレームの表示
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # ページネーション
        render_pagination(len(histories), items_per_page)
    else:
        st.info("📭 該当する作業履歴が見つかりませんでした")


def render_statistics_tab(presenter: WorkHistoryPresenter) -> None:
    """統計情報タブをレンダリングする

    Args:
        presenter: 作業履歴プレゼンター
    """
    st.subheader("📊 作業履歴統計")

    # 統計情報の取得
    stats = presenter.get_statistics()

    # 総件数の表示
    total_count: int = stats["total_count"]  # type: ignore[assignment]
    st.metric("総作業件数", total_count)

    # 作業タイプ別の統計
    st.subheader("作業タイプ別の実行件数")
    if stats["work_type_counts"]:
        work_type_display_names = presenter.get_work_type_display_names()

        # 表示名に変換
        display_counts = {}
        for work_type, count in stats["work_type_counts"].items():
            # work_typeは文字列なので、WorkTypeに変換
            try:
                work_type_enum = WorkType(work_type)
                display_name = work_type_display_names.get(work_type_enum, work_type)
                display_counts[display_name] = count
            except ValueError:
                display_counts[work_type] = count

        df_work_types = pd.DataFrame(
            list(display_counts.items()),
            columns=["作業タイプ", "実行件数"],  # type: ignore[call-overload]
        )
        st.bar_chart(df_work_types.set_index("作業タイプ"))
        st.dataframe(df_work_types, use_container_width=True, hide_index=True)
    else:
        st.info("作業タイプ別のデータがありません")

    # ユーザー別の統計
    st.subheader("ユーザー別の実行件数")
    if stats["user_counts"]:
        df_users = pd.DataFrame(
            list(stats["user_counts"].items()),
            columns=["ユーザー", "実行件数"],  # type: ignore[call-overload]
        )
        df_users = df_users.sort_values("実行件数", ascending=False)
        st.bar_chart(df_users.set_index("ユーザー"))
        st.dataframe(df_users, use_container_width=True, hide_index=True)
    else:
        st.info("ユーザー別のデータがありません")


def render_pagination(current_count: int, items_per_page: int) -> None:
    """ページネーションをレンダリングする

    Args:
        current_count: 現在のページの表示件数
        items_per_page: 1ページあたりの件数
    """
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("⬅️ 前へ", disabled=st.session_state.work_history_page == 0):
            st.session_state.work_history_page -= 1
            st.rerun()

    with col2:
        page_num = st.session_state.work_history_page + 1
        st.markdown(
            f"<div style='text-align: center'>ページ {page_num}</div>",
            unsafe_allow_html=True,
        )

    with col3:
        if st.button("次へ ➡️", disabled=current_count < items_per_page):
            st.session_state.work_history_page += 1
            st.rerun()


def main() -> None:
    """メインエントリーポイント（スタンドアロン実行用）"""
    render_work_history_page()


if __name__ == "__main__":
    main()
