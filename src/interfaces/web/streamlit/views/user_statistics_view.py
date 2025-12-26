"""ユーザー統計ビューモジュール

このモジュールは、ユーザー別の作業統計を表示するStreamlitビューを提供します。
"""

import pandas as pd

import streamlit as st

from src.application.dtos.work_history_dto import WorkType
from src.interfaces.web.streamlit.auth import google_sign_in
from src.interfaces.web.streamlit.presenters.user_statistics_presenter import (
    UserStatisticsPresenter,
)


def render_user_statistics_page() -> None:
    """ユーザー統計ページをレンダリングする"""
    presenter = UserStatisticsPresenter()

    st.header("📊 ユーザー作業統計")
    st.markdown("ユーザーごとの作業量や貢献度を確認できます")

    # タブの作成
    tab1, tab2 = st.tabs(["全体統計", "マイページ"])

    with tab1:
        render_overall_statistics_tab(presenter)

    with tab2:
        render_my_page_tab(presenter)


def render_overall_statistics_tab(presenter: UserStatisticsPresenter) -> None:
    """全体統計タブをレンダリングする

    Args:
        presenter: ユーザー統計プレゼンター
    """
    st.subheader("📈 全体統計")

    # 統計情報の取得
    stats = presenter.get_statistics()

    # 総作業数のメトリック
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総作業件数", stats.total_count)
    with col2:
        st.metric("総ユーザー数", len(stats.user_counts))
    with col3:
        avg_works = (
            stats.total_count / len(stats.user_counts) if stats.user_counts else 0
        )
        st.metric("平均作業件数/人", f"{avg_works:.1f}")

    # 作業タイプ別の内訳
    st.subheader("📊 作業タイプ別の実行件数")
    if stats.work_type_counts:
        work_type_display_names = presenter.get_work_type_display_names()

        # 表示名に変換
        display_counts = {}
        for work_type, count in stats.work_type_counts.items():
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

    # 時系列作業推移
    st.subheader("📈 時系列作業推移")
    timeline_df = presenter.get_timeline_dataframe(stats)
    if timeline_df is not None and not timeline_df.empty:
        st.line_chart(timeline_df.set_index("日付"))
        st.dataframe(timeline_df, use_container_width=True, hide_index=True)
    else:
        st.info("時系列データがありません")

    # 上位貢献者ランキング
    st.subheader("🏆 上位貢献者ランキング")
    contributors_df = presenter.get_contributors_dataframe(stats)
    if contributors_df is not None and not contributors_df.empty:
        st.dataframe(contributors_df, use_container_width=True, hide_index=True)
    else:
        st.info("貢献者データがありません")


def render_my_page_tab(presenter: UserStatisticsPresenter) -> None:
    """マイページタブをレンダリングする

    Args:
        presenter: ユーザー統計プレゼンター
    """
    st.subheader("👤 マイページ")

    # 現在のユーザー情報を取得
    user_info = google_sign_in.get_user_info()
    if not user_info:
        st.warning("ログインしていません")
        return

    user_email = user_info.get("email")
    user_name = user_info.get("name", "未設定")

    st.markdown(f"**ユーザー名**: {user_name}")
    st.markdown(f"**メールアドレス**: {user_email}")

    # 現在のユーザーIDを取得（メールアドレスからユーザーを検索）
    # ここでは、全体統計から自分のデータをフィルタリングする簡易的な方法を使用
    all_stats = presenter.get_statistics()

    # 自分の作業統計を計算
    my_total_works = 0
    my_work_type_breakdown: dict[str, int] = {}

    for contributor in all_stats.top_contributors:
        if contributor.user_email == user_email:
            my_total_works = contributor.total_works
            my_work_type_breakdown = contributor.work_type_breakdown
            break

    # メトリック表示
    col1, col2 = st.columns(2)
    with col1:
        st.metric("自分の総作業件数", my_total_works)
    with col2:
        if all_stats.total_count > 0:
            contribution_rate = (my_total_works / all_stats.total_count) * 100
            st.metric("貢献度", f"{contribution_rate:.1f}%")
        else:
            st.metric("貢献度", "0.0%")

    # 作業タイプ別内訳
    st.subheader("📊 自分の作業タイプ別内訳")
    if my_work_type_breakdown:
        work_type_display_names = presenter.get_work_type_display_names()

        # 表示名に変換
        display_breakdown = {}
        for work_type, count in my_work_type_breakdown.items():
            try:
                work_type_enum = WorkType(work_type)
                display_name = work_type_display_names.get(work_type_enum, work_type)
                display_breakdown[display_name] = count
            except ValueError:
                display_breakdown[work_type] = count

        df_my_work_types = pd.DataFrame(
            list(display_breakdown.items()),
            columns=["作業タイプ", "実行件数"],  # type: ignore[call-overload]
        )
        st.bar_chart(df_my_work_types.set_index("作業タイプ"))
        st.dataframe(df_my_work_types, use_container_width=True, hide_index=True)
    else:
        st.info("作業データがありません")

    # 自分の時系列推移（全体統計から自分のデータのみを抽出）
    # 注: 現在の実装では全体の時系列データを表示
    # 将来的には、ユーザー別の時系列データをフィルタリングする機能を追加可能
    st.subheader("📈 自分の作業推移")
    st.info("全体の作業推移を参照してください（個別フィルタリングは今後追加予定）")


def main() -> None:
    """エントリーポイント"""
    render_user_statistics_page()


if __name__ == "__main__":
    main()
