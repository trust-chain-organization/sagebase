"""View for process execution."""

import streamlit as st
from src.interfaces.web.streamlit.presenters.process_presenter import (
    ProcessPresenter,
)


def render_processes_page() -> None:
    """Render the process execution page."""
    st.header("処理実行")
    st.markdown("各種バッチ処理を実行します")

    presenter = ProcessPresenter()

    # Load available processes
    processes = presenter.load_data()

    # Create tabs for each category
    if processes:
        tabs = st.tabs(list(processes.keys()))

        for i, (category, process_list) in enumerate(processes.items()):
            with tabs[i]:
                render_process_category(presenter, category, process_list)
    else:
        st.info("利用可能な処理がありません")


def render_process_category(
    presenter: ProcessPresenter, category: str, process_list: list[dict[str, str]]
) -> None:
    """Render a process category tab."""
    st.subheader(category)

    for process in process_list:
        with st.expander(f"🔧 {process['name']}", expanded=False):
            st.markdown(f"**説明**: {process['description']}")
            st.markdown(f"**コマンド**: `{process['command']}`")

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(
                    "実行",
                    key=f"execute_{category}_{process['name']}",
                    type="primary",
                ):
                    with st.spinner(f"{process['name']}を実行中..."):
                        success, stdout, stderr = presenter.run_command(
                            process["command"]
                        )

                        if success:
                            st.success(f"✅ {process['name']}が正常に完了しました")
                            if stdout:
                                st.text("実行結果:")
                                st.code(stdout, language="bash")
                        else:
                            st.error(f"❌ {process['name']}の実行に失敗しました")
                            if stderr:
                                st.text("エラー出力:")
                                st.code(stderr, language="bash")

    # Custom command execution
    st.markdown("---")
    st.subheader("カスタムコマンド実行")

    with st.form(f"custom_command_{category}"):
        custom_command = st.text_area(
            "実行するコマンド",
            placeholder="docker compose -f docker/docker-compose.yml exec sagebase ...",
            help="Dockerコンテナ内で実行するコマンドを入力してください",
        )

        col1, col2 = st.columns([3, 1])
        with col2:
            submitted = st.form_submit_button("実行", type="primary")

        if submitted and custom_command:
            with st.spinner("カスタムコマンドを実行中..."):
                success, stdout, stderr = presenter.run_command(custom_command)

                if success:
                    st.success("✅ コマンドが正常に完了しました")
                    if stdout:
                        st.text("実行結果:")
                        st.code(stdout, language="bash")
                else:
                    st.error("❌ コマンドの実行に失敗しました")
                    if stderr:
                        st.text("エラー出力:")
                        st.code(stderr, language="bash")


def main() -> None:
    """Main function for testing."""
    render_processes_page()


if __name__ == "__main__":
    main()
