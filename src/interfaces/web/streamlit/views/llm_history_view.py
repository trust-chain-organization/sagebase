"""LLM processing history view for Streamlit web interface."""

from datetime import datetime, timedelta

import streamlit as st
from src.domain.entities.llm_processing_history import LLMProcessingHistory
from src.interfaces.web.streamlit.presenters.llm_history_presenter import (
    LLMHistoryPresenter,
)
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_llm_history_page() -> None:
    """Render the LLM processing history page."""
    presenter = LLMHistoryPresenter()

    st.header("🤖 LLM処理履歴")
    st.markdown("LLM APIの処理履歴を照会・検索できます")

    # Create tabs
    tab1, tab2 = st.tabs(["履歴一覧", "統計情報"])

    with tab1:
        render_history_list_tab(presenter)

    with tab2:
        render_statistics_tab(presenter)


def render_history_list_tab(presenter: LLMHistoryPresenter) -> None:
    """Render the history list tab.

    Args:
        presenter: LLM history presenter instance
    """
    st.subheader("処理履歴一覧")

    # Search filters section
    with st.expander("🔍 検索フィルター", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # Processing type filter
            processing_types = presenter.get_processing_types()
            selected_type = st.selectbox(
                "処理タイプ",
                processing_types,
                key="filter_processing_type",
            )

        with col2:
            # Model filter
            model_names = presenter.get_model_names()
            selected_model = st.selectbox(
                "モデル",
                model_names,
                key="filter_model",
            )

        with col3:
            # Status filter
            statuses = presenter.get_statuses()
            selected_status = st.selectbox(
                "ステータス",
                statuses,
                key="filter_status",
            )

        # Date range filter
        col4, col5 = st.columns(2)
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

    # Pagination settings
    items_per_page = st.selectbox(
        "表示件数",
        [10, 25, 50, 100],
        index=1,
        key="items_per_page",
    )

    # Current page number
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    offset = st.session_state.current_page * items_per_page

    # Convert dates to datetime
    if start_date and end_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
    else:
        start_datetime = None
        end_datetime = None

    # Search histories
    try:
        response = presenter.search_histories(
            processing_type=selected_type,
            model_name=selected_model,
            status=selected_status,
            start_date=start_datetime,
            end_date=end_datetime,
            limit=items_per_page,
            offset=offset,
        )

        if response.success and response.data:
            histories = response.data["histories"]
            total_count = response.data["total_count"]

            if histories:
                # CSV export button
                csv_data = presenter.export_to_csv(histories)
                st.download_button(
                    label="📥 CSVダウンロード",
                    data=csv_data,
                    file_name=f"llm_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

                # Display histories
                for history in histories:
                    render_history_item(history, presenter)

                # Pagination
                total_pages = (total_count + items_per_page - 1) // items_per_page
                render_pagination(total_pages)

            else:
                st.info("検索条件に一致する履歴が見つかりませんでした")
        else:
            st.error(response.message)
    except Exception as e:
        handle_ui_error(e, "履歴検索中にエラーが発生しました")


def render_history_item(
    history: LLMProcessingHistory, presenter: LLMHistoryPresenter
) -> None:
    """Render a single history item.

    Args:
        history: LLM processing history entity
        presenter: LLM history presenter instance
    """
    with st.container():
        # Create expander for each history item
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "pending": "⏳",
        }.get(history.status.value, "❓")

        created_at_str = (
            history.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if history.created_at
            else "N/A"
        )
        header = (
            f"{status_emoji} [{history.id}] "
            f"{history.processing_type.value} - {created_at_str}"
        )

        with st.expander(header):
            # Basic information
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("モデル", history.model_name or "N/A")
                st.metric("ステータス", history.status.value)

            with col2:
                st.metric("入力トークン", f"{history.token_count_input or 0:,}")
                st.metric("出力トークン", f"{history.token_count_output or 0:,}")

            with col3:
                total_tokens = (history.token_count_input or 0) + (
                    history.token_count_output or 0
                )
                st.metric("合計トークン", f"{total_tokens:,}")
                if history.model_version:
                    st.metric("モデルバージョン", history.model_version)

            # Error message if failed
            if history.error_message:
                st.error(f"エラー: {history.error_message}")

            # Detail button
            if st.button("詳細を表示", key=f"detail_{history.id}"):
                render_history_detail(history, presenter)


def render_history_detail(
    history: LLMProcessingHistory, presenter: LLMHistoryPresenter
) -> None:
    """Render detailed information for a history item.

    Args:
        history: LLM processing history entity
        presenter: LLM history presenter instance
    """
    st.subheader(f"履歴詳細 ID: {history.id}")

    # Prompt template and variables
    if history.prompt_template:
        st.write("**プロンプトテンプレート:**")
        st.code(history.prompt_template)

    # Prompt variables
    if history.prompt_variables:
        st.write("**プロンプト変数:**")
        st.json(history.prompt_variables)

    # Processing result
    if history.result:
        st.write("**処理結果:**")
        st.json(history.result)

    # Processing metadata
    if history.processing_metadata:
        st.write("**処理メタデータ:**")
        st.json(history.processing_metadata)


def render_statistics_tab(presenter: LLMHistoryPresenter) -> None:
    """Render the statistics tab.

    Args:
        presenter: LLM history presenter instance
    """
    st.subheader("統計情報")

    # Date range for statistics
    col1, col2 = st.columns(2)
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

    # Convert dates to datetime
    if stats_start_date and stats_end_date:
        start_datetime = datetime.combine(stats_start_date, datetime.min.time())
        end_datetime = datetime.combine(stats_end_date, datetime.max.time())
    else:
        start_datetime = None
        end_datetime = None

    # Get statistics
    try:
        response = presenter.get_statistics(
            start_date=start_datetime,
            end_date=end_datetime,
        )

        if response.success and response.data:
            stats = response.data

            # Display overall statistics
            st.write("### 全体統計")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("総処理件数", f"{stats['total_count']:,}")

            with col2:
                st.metric("成功", f"{stats['completed_count']:,}")

            with col3:
                st.metric("失敗", f"{stats['failed_count']:,}")

            with col4:
                st.metric("成功率", f"{stats['success_rate']}%")

            # Token usage statistics
            st.write("### トークン使用量")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("入力トークン", f"{stats['total_input_tokens']:,}")

            with col2:
                st.metric("出力トークン", f"{stats['total_output_tokens']:,}")

            with col3:
                st.metric("合計トークン", f"{stats['total_tokens']:,}")

            # Processing type breakdown
            st.write("### 処理タイプ別内訳")
            type_breakdown = stats["type_breakdown"]
            if type_breakdown:
                for proc_type, count in type_breakdown.items():
                    if count > 0:
                        success_rate = stats["success_rate_by_type"].get(proc_type, 0.0)
                        st.write(
                            f"**{proc_type}**: {count:,}件 (成功率: {success_rate}%)"
                        )

            # Model usage breakdown
            st.write("### モデル別使用状況")
            model_breakdown = stats["model_breakdown"]
            if model_breakdown:
                for model, count in model_breakdown.items():
                    percentage = (count / stats["total_count"]) * 100
                    st.write(f"**{model}**: {count:,}件 ({percentage:.1f}%)")

        else:
            st.error(response.message)
    except Exception as e:
        handle_ui_error(e, "統計情報取得中にエラーが発生しました")


def render_pagination(total_pages: int) -> None:
    """Render pagination controls.

    Args:
        total_pages: Total number of pages
    """
    if total_pages <= 1:
        return

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("← 前へ", disabled=st.session_state.current_page == 0):
            st.session_state.current_page -= 1
            st.rerun()

    with col2:
        st.write(
            f"ページ {st.session_state.current_page + 1} / {total_pages}",
            unsafe_allow_html=True,
        )

    with col3:
        if st.button(
            "次へ →", disabled=st.session_state.current_page >= total_pages - 1
        ):
            st.session_state.current_page += 1
            st.rerun()


def main() -> None:
    """Main entry point for the LLM history view."""
    render_llm_history_page()


if __name__ == "__main__":
    main()
