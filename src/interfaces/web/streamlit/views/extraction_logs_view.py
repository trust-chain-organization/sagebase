"""抽出ログ閲覧ビュー for Streamlit web interface."""

from datetime import datetime, timedelta

import plotly.express as px
import streamlit as st

from src.domain.entities.extraction_log import ExtractionLog
from src.interfaces.web.streamlit.presenters.extraction_log_presenter import (
    ExtractionLogPresenter,
)
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_extraction_logs_page() -> None:
    """抽出ログページを描画する。"""
    presenter = ExtractionLogPresenter()

    st.header("📋 抽出ログ一覧")
    st.markdown("LLM抽出処理の履歴を照会・検索できます")

    # タブを作成
    tab1, tab2 = st.tabs(["履歴一覧", "統計ダッシュボード"])

    with tab1:
        render_logs_list_tab(presenter)

    with tab2:
        render_statistics_tab(presenter)


def render_logs_list_tab(presenter: ExtractionLogPresenter) -> None:
    """履歴一覧タブを描画する。

    Args:
        presenter: 抽出ログPresenterインスタンス
    """
    st.subheader("抽出履歴一覧")

    # 検索フィルターセクション
    with st.expander("🔍 検索フィルター", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # エンティティタイプフィルタ
            entity_types = presenter.get_entity_types()
            selected_entity_type = st.selectbox(
                "エンティティタイプ",
                entity_types,
                key="filter_entity_type",
            )

        with col2:
            # パイプラインバージョンフィルタ
            pipeline_versions = presenter.get_pipeline_versions()
            selected_pipeline = st.selectbox(
                "パイプラインバージョン",
                pipeline_versions,
                key="filter_pipeline_version",
            )

        with col3:
            # 信頼度スコアフィルタ
            min_confidence = st.slider(
                "最小信頼度スコア",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.1,
                key="filter_confidence",
            )

        # 日付範囲フィルタ
        col4, col5, col6 = st.columns(3)
        with col4:
            default_start_date = datetime.now() - timedelta(days=30)
            start_date = st.date_input(
                "開始日",
                value=default_start_date,
                key="filter_start_date",
            )

        with col5:
            end_date = st.date_input(
                "終了日",
                value=datetime.now(),
                key="filter_end_date",
            )

        with col6:
            # エンティティIDフィルタ（オプション）
            entity_id_input = st.text_input(
                "エンティティID（任意）",
                value="",
                key="filter_entity_id",
            )

    # ページネーション設定
    items_per_page = st.selectbox(
        "表示件数",
        [10, 25, 50, 100],
        index=1,
        key="items_per_page",
    )

    # 現在のページ番号
    if "extraction_logs_current_page" not in st.session_state:
        st.session_state.extraction_logs_current_page = 0

    offset = st.session_state.extraction_logs_current_page * items_per_page

    # 日付をdatetimeに変換
    start_datetime = None
    end_datetime = None
    if start_date and end_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

    # エンティティIDの処理
    entity_id = None
    if entity_id_input and entity_id_input.strip():
        try:
            entity_id = int(entity_id_input.strip())
        except ValueError:
            st.warning("エンティティIDは数値で入力してください")

    # 信頼度スコアの処理
    min_confidence_score = min_confidence if min_confidence > 0 else None

    # ログを検索
    try:
        response = presenter.search_logs(
            entity_type=selected_entity_type,
            entity_id=entity_id,
            pipeline_version=selected_pipeline,
            start_date=start_datetime,
            end_date=end_datetime,
            min_confidence_score=min_confidence_score,
            limit=items_per_page,
            offset=offset,
        )

        if response.success and response.data:
            logs = response.data["logs"]
            total_count = response.data["total_count"]

            if logs:
                # CSVエクスポートボタン
                csv_data = presenter.export_to_csv(logs)
                st.download_button(
                    label="📥 CSVダウンロード",
                    data=csv_data,
                    file_name=f"extraction_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

                st.info(f"検索結果: {total_count}件")

                # ログ一覧を表示
                for log in logs:
                    render_log_item(log, presenter)

                # ページネーション
                total_pages = (total_count + items_per_page - 1) // items_per_page
                render_pagination(total_pages)

            else:
                st.info("検索条件に一致するログが見つかりませんでした")
        else:
            st.error(response.message)
    except Exception as e:
        handle_ui_error(e, "ログ検索中にエラーが発生しました")


def render_log_item(log: ExtractionLog, presenter: ExtractionLogPresenter) -> None:
    """単一のログアイテムを描画する。

    Args:
        log: 抽出ログエンティティ
        presenter: 抽出ログPresenterインスタンス
    """
    with st.container():
        # 各ログアイテム用のexpanderを作成
        confidence_emoji = (
            "🟢"
            if (log.confidence_score or 0) >= 0.8
            else ("🟡" if (log.confidence_score or 0) >= 0.5 else "🔴")
        )

        created_at_str = (
            log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
        )
        header = (
            f"{confidence_emoji} [{log.id}] "
            f"{log.entity_type.value} (ID: {log.entity_id}) - {created_at_str}"
        )

        with st.expander(header):
            # 基本情報
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("エンティティタイプ", log.entity_type.value)
                st.metric("エンティティID", log.entity_id)

            with col2:
                st.metric(
                    "信頼度スコア",
                    f"{log.confidence_score:.2f}" if log.confidence_score else "N/A",
                )
                st.metric("パイプライン", log.pipeline_version)

            with col3:
                st.metric("モデル名", log.model_name or "N/A")
                if log.processing_time_ms:
                    st.metric("処理時間", f"{log.processing_time_ms}ms")

            # トークン情報
            if log.token_count_input or log.token_count_output:
                st.write("**トークン使用量:**")
                token_col1, token_col2, token_col3 = st.columns(3)
                with token_col1:
                    st.metric("入力トークン", f"{log.token_count_input or 0:,}")
                with token_col2:
                    st.metric("出力トークン", f"{log.token_count_output or 0:,}")
                with token_col3:
                    total_tokens = (log.token_count_input or 0) + (
                        log.token_count_output or 0
                    )
                    st.metric("合計トークン", f"{total_tokens:,}")

            # 詳細ボタン
            if st.button("詳細を表示", key=f"detail_{log.id}"):
                render_log_detail(log, presenter)


def render_log_detail(log: ExtractionLog, presenter: ExtractionLogPresenter) -> None:
    """ログの詳細情報を描画する。

    Args:
        log: 抽出ログエンティティ
        presenter: 抽出ログPresenterインスタンス
    """
    st.subheader(f"ログ詳細 ID: {log.id}")

    # 抽出データ
    if log.extracted_data:
        st.write("**抽出データ:**")
        st.json(log.extracted_data)

    # メタデータ
    if log.extraction_metadata:
        st.write("**抽出メタデータ:**")
        st.json(log.extraction_metadata)


def render_statistics_tab(presenter: ExtractionLogPresenter) -> None:
    """統計ダッシュボードタブを描画する。

    Args:
        presenter: 抽出ログPresenterインスタンス
    """
    st.subheader("統計ダッシュボード")

    # 日付範囲設定
    col1, col2, col3 = st.columns(3)
    with col1:
        stats_start_date = st.date_input(
            "統計開始日",
            value=datetime.now() - timedelta(days=30),
            key="stats_start_date",
        )

    with col2:
        stats_end_date = st.date_input(
            "統計終了日",
            value=datetime.now(),
            key="stats_end_date",
        )

    with col3:
        # エンティティタイプフィルタ
        entity_types = presenter.get_entity_types()
        stats_entity_type = st.selectbox(
            "エンティティタイプ",
            entity_types,
            key="stats_entity_type",
        )

    # 日付をdatetimeに変換
    start_datetime = None
    end_datetime = None
    if stats_start_date and stats_end_date:
        start_datetime = datetime.combine(stats_start_date, datetime.min.time())
        end_datetime = datetime.combine(stats_end_date, datetime.max.time())

    # 統計情報を取得
    try:
        response = presenter.get_statistics(
            entity_type=stats_entity_type,
            start_date=start_datetime,
            end_date=end_datetime,
        )

        if response.success and response.data:
            stats = response.data

            # 全体統計
            st.write("### 全体統計")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("総抽出件数", f"{stats['total_count']:,}")

            with col2:
                avg_confidence = stats.get("average_confidence")
                st.metric(
                    "平均信頼度スコア",
                    f"{avg_confidence:.3f}" if avg_confidence else "N/A",
                )

            with col3:
                entity_type_count = len(stats.get("by_entity_type", {}))
                st.metric("エンティティタイプ数", entity_type_count)

            # エンティティタイプ別の円グラフ
            st.write("### エンティティタイプ別内訳")
            by_entity_type = stats.get("by_entity_type", {})
            if by_entity_type:
                fig_pie = px.pie(
                    names=list(by_entity_type.keys()),
                    values=list(by_entity_type.values()),
                    title="エンティティタイプ別件数",
                )
                st.plotly_chart(fig_pie, use_container_width=True)

                # 数値でも表示
                for entity_type, count in by_entity_type.items():
                    percentage = (count / stats["total_count"]) * 100
                    st.write(f"**{entity_type}**: {count:,}件 ({percentage:.1f}%)")

            # 時系列の抽出件数
            st.write("### 日別抽出件数")
            daily_counts = stats.get("daily_counts", [])
            if daily_counts:
                dates = [item["date"] for item in daily_counts]
                counts = [item["count"] for item in daily_counts]

                fig_line = px.line(
                    x=dates,
                    y=counts,
                    title="日別抽出件数の推移",
                    labels={"x": "日付", "y": "件数"},
                )
                st.plotly_chart(fig_line, use_container_width=True)

            # パイプラインバージョン別統計
            st.write("### パイプラインバージョン別")
            by_pipeline = stats.get("by_pipeline_version", {})
            confidence_by_pipeline = stats.get("confidence_by_pipeline", {})

            if by_pipeline:
                fig_bar = px.bar(
                    x=list(by_pipeline.keys()),
                    y=list(by_pipeline.values()),
                    title="パイプラインバージョン別件数",
                    labels={"x": "バージョン", "y": "件数"},
                )
                st.plotly_chart(fig_bar, use_container_width=True)

                # パイプライン別の信頼度
                if confidence_by_pipeline:
                    st.write("**パイプラインバージョン別平均信頼度:**")
                    for version, confidence in confidence_by_pipeline.items():
                        count = by_pipeline.get(version, 0)
                        st.write(
                            f"**{version}**: {count:,}件 (平均信頼度: {confidence:.3f})"
                        )

        else:
            st.error(response.message)
    except Exception as e:
        handle_ui_error(e, "統計情報取得中にエラーが発生しました")


def render_pagination(total_pages: int) -> None:
    """ページネーションコントロールを描画する。

    Args:
        total_pages: 総ページ数
    """
    if total_pages <= 1:
        return

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button(
            "← 前へ", disabled=st.session_state.extraction_logs_current_page == 0
        ):
            st.session_state.extraction_logs_current_page -= 1
            st.rerun()

    with col2:
        current_page = st.session_state.extraction_logs_current_page + 1
        st.write(
            f"ページ {current_page} / {total_pages}",
            unsafe_allow_html=True,
        )

    with col3:
        if st.button(
            "次へ →",
            disabled=st.session_state.extraction_logs_current_page >= total_pages - 1,
        ):
            st.session_state.extraction_logs_current_page += 1
            st.rerun()


def main() -> None:
    """抽出ログビューのメインエントリーポイント。"""
    render_extraction_logs_page()


if __name__ == "__main__":
    main()
