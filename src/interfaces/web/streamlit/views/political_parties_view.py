"""View for political party management in Streamlit.

This module provides the UI layer for political party management,
using the presenter pattern for business logic.
"""

from typing import Any

import streamlit as st
from src.interfaces.web.streamlit.presenters.political_party_presenter import (
    PoliticalPartyPresenter,
)
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_political_parties_page() -> None:
    """Render the political parties management page."""
    st.title("政党管理")
    st.markdown("政党の議員一覧URLを管理します。")

    # Initialize presenter
    presenter = PoliticalPartyPresenter()

    # Create tabs
    tab1, tab2 = st.tabs(["政党一覧", "SEEDファイル生成"])

    with tab1:
        render_parties_list_tab(presenter)

    with tab2:
        render_seed_generation_tab(presenter)


def render_parties_list_tab(presenter: PoliticalPartyPresenter) -> None:
    """Render the parties list tab.

    Args:
        presenter: Political party presenter
    """
    # Filter section
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_options = {
            "すべて": "all",
            "URL設定済み": "with_url",
            "URL未設定": "without_url",
        }
        selected_filter = st.selectbox(
            "表示フィルター", options=list(filter_options.keys()), index=0
        )
        filter_type = filter_options[selected_filter]

    # Load data
    try:
        # Run async function
        result = presenter.load_data_filtered(filter_type)

        # Display statistics
        with col2:
            st.metric("全政党数", result.statistics.total)

        with col3:
            st.metric(
                "URL設定率",
                f"{result.statistics.with_url_percentage:.1f}%",
                f"{result.statistics.with_url}/{result.statistics.total}",
            )

        # Display parties table
        if result.parties:
            st.subheader("政党一覧")

            # Create editable table
            for party in result.parties:
                render_party_row(presenter, party)
        else:
            st.info("表示する政党がありません。")

    except Exception as e:
        handle_ui_error(e, "政党一覧の読み込み")


def render_party_row(presenter: PoliticalPartyPresenter, party: Any) -> None:
    """Render a single party row with edit capability.

    Args:
        presenter: Political party presenter
        party: Political party entity
    """
    col1, col2, col3, col4, col5 = st.columns([1, 2, 3, 1, 1])

    with col1:
        st.text(str(party.id))

    with col2:
        st.text(party.name)

    new_url: str = ""  # Initialize outside the if block
    with col3:
        if presenter.is_editing(party.id):
            # Edit mode
            new_url = st.text_input(
                "URL",
                value=party.members_list_url or "",
                key=f"edit_url_{party.id}",
                label_visibility="collapsed",
            )
        else:
            # Display mode
            if party.members_list_url:
                st.markdown(f"[{party.members_list_url}]({party.members_list_url})")
            else:
                st.text("未設定")

    with col4:
        if presenter.is_editing(party.id):
            # Edit mode buttons
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("保存", key=f"save_{party.id}"):
                    save_party_url(presenter, party.id, new_url)
            with col_cancel:
                if st.button("キャンセル", key=f"cancel_{party.id}"):
                    presenter.cancel_editing()
                    st.rerun()
        else:
            # Edit button
            if st.button("編集", key=f"edit_{party.id}"):
                presenter.set_editing_mode(party.id)
                st.rerun()

    with col5:
        # Extraction button
        render_extraction_button(presenter, party)

    # Show extraction statistics below the row
    render_extraction_statistics(presenter, party)


def save_party_url(presenter: PoliticalPartyPresenter, party_id: int, url: str) -> None:
    """Save political party URL.

    Args:
        presenter: Political party presenter
        party_id: Party ID
        url: New URL value
    """
    try:
        # Clean up the URL (empty string becomes None)
        url_cleaned: str | None = url.strip() if url else None

        # Update the URL
        result = presenter.update(party_id=party_id, members_list_url=url_cleaned)

        if result.success:
            st.success(result.message)
            presenter.cancel_editing()
            st.rerun()
        else:
            st.error(result.message)

    except Exception as e:
        handle_ui_error(e, "URLの更新")


def render_extraction_button(presenter: PoliticalPartyPresenter, party: Any) -> None:
    """Render politician extraction button.

    Args:
        presenter: Political party presenter
        party: Political party entity
    """
    # Check if extraction is in progress
    extraction_key = f"extracting_{party.id}"
    is_extracting = st.session_state.get(extraction_key, False)

    if is_extracting:
        st.button("処理中...", disabled=True, key=f"extract_{party.id}")
    elif party.members_list_url:
        if st.button("🔍 メンバー抽出", key=f"extract_{party.id}", type="primary"):
            # Set extraction flag
            st.session_state[extraction_key] = True
            st.rerun()
    else:
        st.button(
            "🔍 メンバー抽出",
            disabled=True,
            key=f"extract_{party.id}",
            help="議員一覧URLを設定してください",
        )

    # Show extraction progress if in progress
    if is_extracting:
        show_extraction_progress(presenter, party.id)


def show_extraction_progress(presenter: PoliticalPartyPresenter, party_id: int) -> None:
    """Show politician extraction progress.

    Args:
        presenter: Political party presenter
        party_id: Party ID
    """
    extraction_key = f"extracting_{party_id}"

    # Create placeholder for progress messages
    progress_placeholder = st.empty()
    progress_messages = []

    def progress_callback(message: str):
        """Callback to update progress in real-time."""
        progress_messages.append(message)
        with progress_placeholder.container():
            for msg in progress_messages:
                st.write(msg)

    with st.status("政治家情報を抽出中...", expanded=True) as status:
        try:
            # Execute extraction with progress callback
            result = presenter.extract_politicians(
                party_id, progress_callback=progress_callback
            )

            if result["success"]:
                status.update(label="✅ 抽出完了", state="complete")

                # Show extracted politicians
                if result["politicians"]:
                    st.write(f"抽出された政治家: {len(result['politicians'])}人")
                    with st.expander("詳細を表示"):
                        for politician in result["politicians"][:10]:
                            st.write(f"- {politician.name}")
                        if len(result["politicians"]) > 10:
                            st.write(f"... 他{len(result['politicians']) - 10}人")
                else:
                    st.warning("政治家が抽出されませんでした")
            else:
                st.error(result["message"])
                status.update(label="❌ 抽出失敗", state="error")

        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            status.update(label="❌ エラー", state="error")
        finally:
            # Clear extraction flag
            st.session_state[extraction_key] = False


def render_extraction_statistics(
    presenter: PoliticalPartyPresenter, party: Any
) -> None:
    """Render extraction statistics for a party.

    Args:
        presenter: Political party presenter
        party: Political party entity
    """
    try:
        stats = presenter.get_extraction_statistics(party.id)

        if stats["total"] > 0:
            stats_parts = []

            # Total extracted
            stats_parts.append(f"📊 抽出済み: {stats['total']}")

            # Approved
            if stats["approved"] > 0:
                stats_parts.append(f"✅ 承認: {stats['approved']}")

            # Pending
            if stats["pending"] > 0:
                stats_parts.append(f"⏳ 保留: {stats['pending']}")

            # Rejected
            if stats["rejected"] > 0:
                stats_parts.append(f"❌ 却下: {stats['rejected']}")

            st.caption(" | ".join(stats_parts))

    except Exception:
        # Silently ignore errors in statistics display
        pass


def render_seed_generation_tab(presenter: PoliticalPartyPresenter) -> None:
    """Render the seed file generation tab.

    Args:
        presenter: Political party presenter
    """
    st.subheader("SEEDファイル生成")
    st.markdown("""
    現在のデータベースの政党情報からSEEDファイルを生成します。
    生成されたファイルは `database/seeds/` ディレクトリに保存されます。
    """)

    if st.button("SEEDファイルを生成", type="primary"):
        with st.spinner("生成中..."):
            try:
                result = presenter.generate_seed_file()

                if result.success:
                    st.success(result.message)

                    # Display the generated content
                    if result.content:
                        st.subheader("生成されたSEEDファイル")
                        st.code(result.content, language="sql")

                        # Download button
                        st.download_button(
                            label="ダウンロード",
                            data=result.content,
                            file_name="01_political_parties.sql",
                            mime="text/plain",
                        )
                else:
                    st.error(result.message)

            except Exception as e:
                handle_ui_error(e, "SEEDファイル生成")


# For backward compatibility with existing app.py
def main() -> None:
    """Main entry point for the political parties page."""
    render_political_parties_page()


if __name__ == "__main__":
    main()
