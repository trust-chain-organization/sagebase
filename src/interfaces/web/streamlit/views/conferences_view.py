"""View for conference management."""

import asyncio
import logging
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.application.usecases.manage_conferences_usecase import (
    ManageConferencesUseCase,
)
from src.domain.repositories import ConferenceRepository, GoverningBodyRepository
from src.infrastructure.external.conference_member_extractor.extractor import (
    ConferenceMemberExtractor,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.conference_presenter import (
    ConferencePresenter,
)

logger = logging.getLogger(__name__)


def render_conferences_page() -> None:
    """Render conferences management page."""
    st.title("会議体管理")

    # Initialize repositories
    conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
    governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    extracted_member_repo = RepositoryAdapter(ExtractedConferenceMemberRepositoryImpl)

    # Initialize use case and presenter
    # Type: ignore - RepositoryAdapter duck-types as repository protocol
    use_case = ManageConferencesUseCase(conference_repo)  # type: ignore[arg-type]
    presenter = ConferencePresenter(use_case)

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["会議体一覧", "新規登録", "編集・削除", "SEED生成", "抽出結果確認"]
    )

    with tab1:
        render_conferences_list(
            presenter, cast(GoverningBodyRepository, governing_body_repo)
        )

    with tab2:
        render_new_conference_form(
            presenter, cast(GoverningBodyRepository, governing_body_repo)
        )

    with tab3:
        render_edit_delete_form(
            presenter,
            cast(ConferenceRepository, conference_repo),
            cast(GoverningBodyRepository, governing_body_repo),
        )

    with tab4:
        render_seed_generator(presenter)

    with tab5:
        render_extracted_members(extracted_member_repo, conference_repo)


def render_conferences_list(
    presenter: ConferencePresenter,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render conferences list tab."""
    st.header("会議体一覧")

    # Filters
    col1, col2 = st.columns(2)

    with col1:
        # Load governing bodies for filter
        governing_bodies = governing_body_repo.get_all()
        gb_options = {"すべて": None}
        gb_options.update({f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies})

        selected_gb = st.selectbox(
            "開催主体で絞り込み",
            options=list(gb_options.keys()),
            key="filter_governing_body",
        )
        governing_body_id = gb_options[selected_gb]

    with col2:
        url_filter_options = {
            "すべて": None,
            "URLあり": True,
            "URLなし": False,
        }
        selected_url_filter = st.selectbox(
            "議員紹介URLで絞り込み",
            options=list(url_filter_options.keys()),
            key="filter_url",
        )
        with_members_url = url_filter_options[selected_url_filter]

    # Load and display conferences
    df, with_url_count, without_url_count = asyncio.run(
        presenter.load_conferences(governing_body_id, with_members_url)
    )

    # Display statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総会議体数", len(df))
    with col2:
        st.metric("URL登録済み", with_url_count)
    with col3:
        st.metric("URL未登録", without_url_count)

    # Display table with selection checkbox
    if not df.empty:
        # Add a selection column for extraction
        df_with_selection = df.copy()
        df_with_selection.insert(0, "抽出", False)

        # Use data_editor to allow selection
        edited_df = st.data_editor(
            df_with_selection,
            use_container_width=True,
            hide_index=True,
            disabled=[col for col in df_with_selection.columns if col != "抽出"],
            column_config={
                "抽出": st.column_config.CheckboxColumn(
                    "抽出",
                    help="議員情報を抽出する会議体を選択してください",
                    default=False,
                )
            },
        )

        # Extract button
        selected_rows = cast(pd.DataFrame, edited_df[edited_df["抽出"]])
        if len(selected_rows) > 0:
            st.info(f"{len(selected_rows)}件の会議体が選択されています")

            if st.button("選択した会議体から議員情報を抽出", type="primary"):
                extract_members_from_conferences(selected_rows)
    else:
        st.info("会議体が登録されていません。")


def render_new_conference_form(
    presenter: ConferencePresenter,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render new conference registration form."""
    st.header("新規会議体登録")

    # Get form data
    form_data = presenter.get_form_data("new")

    # Load governing bodies for dropdown
    governing_bodies = governing_body_repo.get_all()
    gb_options = {f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies}

    with st.form("conference_create_form"):
        # Conference name
        name = st.text_input(
            "会議体名 *",
            value=form_data.name,
            placeholder="例: 議会",
        )

        # Governing body selection
        selected_gb = st.selectbox(
            "開催主体 *",
            options=list(gb_options.keys()),
            index=0 if not form_data.governing_body_id else None,
        )
        governing_body_id = gb_options[selected_gb] if selected_gb else None

        # Type
        conf_type = st.text_input(
            "種別",
            value=form_data.type or "",
            placeholder="例: 本会議, 委員会",
        )

        # Members introduction URL
        members_url = st.text_input(
            "議員紹介URL",
            value=form_data.members_introduction_url or "",
            placeholder="例: https://example.com/members",
        )

        # Submit button
        submitted = st.form_submit_button("登録", type="primary")

        if submitted:
            # Validation
            if not name:
                st.error("会議体名を入力してください。")
            elif not governing_body_id:
                st.error("開催主体を選択してください。")
            else:
                # Update form data
                form_data.name = name
                form_data.governing_body_id = governing_body_id
                form_data.type = conf_type if conf_type else None
                form_data.members_introduction_url = (
                    members_url if members_url else None
                )

                # Create conference
                success, error_message = asyncio.run(
                    presenter.create_conference(form_data)
                )

                if success:
                    st.success("会議体を登録しました。")
                    presenter.clear_form_data("new")
                    st.rerun()
                else:
                    st.error(f"登録に失敗しました: {error_message}")


def render_edit_delete_form(
    presenter: ConferencePresenter,
    conference_repo: ConferenceRepository,
    governing_body_repo: GoverningBodyRepository,
) -> None:
    """Render edit and delete form."""
    st.header("会議体の編集・削除")

    # Load all conferences for selection
    conferences = conference_repo.get_all()

    if not conferences:
        st.info("編集可能な会議体がありません。")
        return

    # Conference selection
    conf_options = {f"{conf.name} (ID: {conf.id})": conf.id for conf in conferences}

    selected_conf = st.selectbox(
        "編集する会議体を選択",
        options=list(conf_options.keys()),
        key="edit_conference_select",
    )

    if selected_conf:
        conference_id = conf_options[selected_conf]
        conference = next(c for c in conferences if c.id == conference_id)

        # Load form data
        form_data = presenter.load_conference_for_edit(conference)

        # Load governing bodies for dropdown
        governing_bodies = governing_body_repo.get_all()
        gb_options = {f"{gb.name} ({gb.type})": gb.id for gb in governing_bodies}

        with st.form(f"conference_edit_form_{conference_id}"):
            # Conference name
            name = st.text_input(
                "会議体名 *",
                value=form_data.name,
            )

            # Governing body selection
            current_gb = next(
                (
                    f"{gb.name} ({gb.type})"
                    for gb in governing_bodies
                    if gb.id == form_data.governing_body_id
                ),
                None,
            )
            selected_gb = st.selectbox(
                "開催主体 *",
                options=list(gb_options.keys()),
                index=list(gb_options.keys()).index(current_gb) if current_gb else 0,
            )
            governing_body_id = gb_options[selected_gb] if selected_gb else None

            # Type
            conf_type = st.text_input(
                "種別",
                value=form_data.type or "",
            )

            # Members introduction URL
            members_url = st.text_input(
                "議員紹介URL",
                value=form_data.members_introduction_url or "",
            )

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                update_button = st.form_submit_button("更新", type="primary")
            with col2:
                delete_button = st.form_submit_button("削除", type="secondary")

            if update_button:
                # Validation
                if not name:
                    st.error("会議体名を入力してください。")
                elif not governing_body_id:
                    st.error("開催主体を選択してください。")
                else:
                    # Update form data
                    form_data.name = name
                    form_data.governing_body_id = governing_body_id
                    form_data.type = conf_type if conf_type else None
                    form_data.members_introduction_url = (
                        members_url if members_url else None
                    )

                    # Update conference
                    success, error_message = asyncio.run(
                        presenter.update_conference(conference_id, form_data)
                    )

                    if success:
                        st.success("会議体を更新しました。")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error_message}")

            if delete_button:
                # Delete conference
                success, error_message = asyncio.run(
                    presenter.delete_conference(conference_id)
                )

                if success:
                    st.success("会議体を削除しました。")
                    st.rerun()
                else:
                    st.error(f"削除に失敗しました: {error_message}")


def render_seed_generator(presenter: ConferencePresenter) -> None:
    """Render seed file generator."""
    st.header("SEEDファイル生成")

    st.info("現在データベースに登録されている会議体情報からSEEDファイルを生成します。")

    if st.button("SEEDファイル生成", type="primary"):
        success, file_path, error_message = presenter.generate_seed_file()

        if success:
            st.success(f"SEEDファイルを生成しました: {file_path}")

            # Show download button
            with open(file_path) as f:
                seed_content = f.read()

            st.download_button(
                label="SEEDファイルをダウンロード",
                data=seed_content,
                file_name="seed_conferences_generated.sql",
                mime="text/plain",
            )
        else:
            st.error(f"生成に失敗しました: {error_message}")


def _validate_and_filter_rows(
    selected_rows: pd.DataFrame,
) -> tuple[pd.DataFrame, bool]:
    """選択された会議体をバリデーションしてフィルタリング

    Args:
        selected_rows: 選択された会議体のDataFrame

    Returns:
        tuple[pd.DataFrame, bool]: (URLを持つ行のDataFrame, 処理を継続するか)
    """
    # 議員紹介URLがない会議体を除外
    rows_with_url = cast(
        pd.DataFrame,
        selected_rows[
            selected_rows["議員紹介URL"].notna() & (selected_rows["議員紹介URL"] != "")
        ],
    )

    if len(rows_with_url) == 0:
        st.warning("選択された会議体には議員紹介URLが登録されていません。")
        return rows_with_url, False

    # URLがない会議体がある場合は警告
    rows_without_url = cast(
        pd.DataFrame,
        selected_rows[
            selected_rows["議員紹介URL"].isna() | (selected_rows["議員紹介URL"] == "")
        ],
    )
    if len(rows_without_url) > 0:
        st.warning(
            f"{len(rows_without_url)}件の会議体は議員紹介URLが未登録のためスキップされます。"
        )

    return rows_with_url, True


def _parse_conference_row(row: pd.Series, idx: int) -> tuple[int, str, str] | None:
    """DataFrameの行から会議体情報を安全に抽出

    Args:
        row: DataFrame行
        idx: 行インデックス

    Returns:
        tuple[int, str, str] | None: (会議体ID, 会議体名, URL) または None（エラー時）
    """
    try:
        conference_id = int(row["ID"])
        conference_name = str(row["会議体名"])
        url = str(row["議員紹介URL"])
        return conference_id, conference_name, url
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Invalid row data at index {idx}: {e}, skipping this conference")
        return None


def _display_extraction_summary(results: list[dict[str, Any]]) -> None:
    """抽出結果のサマリーを表示

    Args:
        results: 抽出結果のリスト
    """
    st.success("議員情報の抽出が完了しました")

    # 結果詳細
    total_extracted = sum(r.get("extracted_count", 0) for r in results)
    total_saved = sum(r.get("saved_count", 0) for r in results)
    total_failed = sum(r.get("failed_count", 0) for r in results)
    errors = [r for r in results if "error" in r]

    # メトリクス表示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("抽出件数", total_extracted)
    with col2:
        st.metric("保存件数", total_saved)
    with col3:
        st.metric("失敗件数", total_failed)

    # エラー詳細
    if errors:
        st.error(f"{len(errors)}件の会議体で抽出エラーが発生しました")
        with st.expander("エラー詳細"):
            for error_result in errors:
                error_msg = error_result.get("error", "Unknown error")
                conference_name = error_result.get("conference_name", "不明な会議体")
                st.write(f"- {conference_name}: {error_msg}")

    # 詳細結果を表形式で表示
    with st.expander("詳細結果"):
        result_df = pd.DataFrame(results)
        st.dataframe(result_df, use_container_width=True)


def extract_members_from_conferences(selected_rows: pd.DataFrame) -> None:
    """選択された会議体から議員情報を抽出する

    Args:
        selected_rows: 選択された会議体のDataFrame
    """
    # バリデーションとフィルタリング
    rows_with_url, should_continue = _validate_and_filter_rows(selected_rows)
    if not should_continue:
        return

    # 抽出処理を開始
    st.info(f"{len(rows_with_url)}件の会議体から議員情報を抽出します...")

    # UIコンポーネント
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 抽出処理
    results: list[dict[str, Any]] = []
    extractor = ConferenceMemberExtractor()

    try:
        for idx, (_, row) in enumerate(rows_with_url.iterrows()):
            # 行データをパース
            parsed = _parse_conference_row(row, idx)
            if parsed is None:
                continue

            conference_id, conference_name, url = parsed

            # ステータス更新
            status_text.text(
                f"処理中: {conference_name} ({idx + 1}/{len(rows_with_url)})"
            )

            # 抽出実行
            result = asyncio.run(
                extractor.extract_and_save_members(
                    conference_id=conference_id,
                    conference_name=conference_name,
                    url=url,
                )
            )
            results.append(result)

            # プログレスバー更新
            progress_bar.progress((idx + 1) / len(rows_with_url))

        # 完了
        status_text.text("抽出処理が完了しました")
        progress_bar.progress(1.0)

        # 結果表示
        _display_extraction_summary(results)

    except Exception as e:
        logger.exception("抽出処理中に予期しないエラーが発生しました")
        st.error(f"抽出処理中にエラーが発生しました: {str(e)}")
    finally:
        extractor.close()


def render_extracted_members(
    extracted_member_repo: RepositoryAdapter, conference_repo: RepositoryAdapter
):
    """抽出された議員情報を表示する

    Args:
        extracted_member_repo: 抽出メンバーリポジトリ
        conference_repo: 会議体リポジトリ
    """
    st.header("抽出結果確認")

    # 会議体でフィルタリング
    conferences = conference_repo.get_all()
    conference_options = {"すべて": None}
    conference_options.update({conf.name: conf.id for conf in conferences})

    selected_conf = st.selectbox(
        "会議体で絞り込み",
        options=list(conference_options.keys()),
        key="filter_extracted_conference",
    )
    conference_id = conference_options[selected_conf]

    # ステータスでフィルタリング
    status_options = {
        "すべて": None,
        "未マッチング": "pending",
        "マッチング済み": "matched",
        "マッチなし": "no_match",
        "要確認": "needs_review",
    }
    selected_status = st.selectbox(
        "ステータスで絞り込み",
        options=list(status_options.keys()),
        key="filter_extracted_status",
    )
    status = status_options[selected_status]

    # サマリー統計を取得（RepositoryAdapterが自動的にasyncio.run()を実行）
    summary = extracted_member_repo.get_extraction_summary(conference_id)

    # 統計を表示
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("総件数", summary.get("total", 0))
    with col2:
        st.metric("未マッチング", summary.get("pending", 0))
    with col3:
        st.metric("マッチング済み", summary.get("matched", 0))
    with col4:
        st.metric("マッチなし", summary.get("no_match", 0))
    with col5:
        st.metric("要確認", summary.get("needs_review", 0))

    # 抽出結果を取得（RepositoryAdapterが自動的にasyncio.run()を実行）
    if conference_id:
        members = extracted_member_repo.get_by_conference(conference_id)
    else:
        members = extracted_member_repo.get_all(limit=1000)

    # ステータスでフィルタリング
    if status:
        members = [m for m in members if m.matching_status == status]

    if not members:
        st.info("該当する抽出結果がありません。")
        return

    # DataFrameに変換
    data = []
    for member in members:
        data.append(
            {
                "ID": member.id,
                "会議体ID": member.conference_id,
                "名前": member.extracted_name,
                "役職": member.extracted_role or "",
                "政党": member.extracted_party_name or "",
                "ステータス": member.matching_status,
                "マッチング信頼度": (
                    f"{member.matching_confidence:.2f}"
                    if member.matching_confidence
                    else ""
                ),
                "抽出日時": member.extracted_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ソースURL": member.source_url,
            }
        )

    df = pd.DataFrame(data)

    # 表示
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ソースURL": st.column_config.LinkColumn("ソースURL"),
            "マッチング信頼度": st.column_config.NumberColumn(
                "マッチング信頼度",
                format="%.2f",
            ),
        },
    )
