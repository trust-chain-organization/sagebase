"""手動検証フィルタコンポーネント。

手動検証状態でフィルタリングするためのセレクトボックスコンポーネント。
一覧画面で使用される。
"""

import streamlit as st


def render_verification_filter(key: str) -> bool | None:
    """手動検証フィルタを表示する。

    Args:
        key: Streamlitのウィジェットキー

    Returns:
        フィルタ値（True=手動検証済みのみ、False=未検証のみ、None=すべて）
    """
    options: dict[str, bool | None] = {
        "すべて": None,
        "✅ 手動検証済みのみ": True,
        "🤖 未検証のみ": False,
    }

    selected: str | None = st.selectbox(
        "検証状態でフィルタ",
        options=list(options.keys()),
        key=key,
        help="手動検証状態でデータをフィルタリングします",
    )

    return options.get(selected) if selected else None


def render_verification_filter_inline(key: str) -> bool | None:
    """インラインの手動検証フィルタを表示する。

    ラベルなしでコンパクトに表示する。

    Args:
        key: Streamlitのウィジェットキー

    Returns:
        フィルタ値（True=手動検証済みのみ、False=未検証のみ、None=すべて）
    """
    options: dict[str, bool | None] = {
        "すべて": None,
        "✅ 検証済み": True,
        "🤖 未検証": False,
    }

    selected: str | None = st.selectbox(
        "検証状態",
        options=list(options.keys()),
        key=key,
        label_visibility="collapsed",
    )

    return options.get(selected) if selected else None


def filter_by_verification_status[T](
    items: list[T],
    verification_filter: bool | None,
) -> list[T]:
    """検証状態でアイテムをフィルタリングする。

    Args:
        items: フィルタリング対象のアイテムリスト
               各アイテムはis_manually_verified属性を持つ必要がある
        verification_filter: フィルタ値（True/False/None）

    Returns:
        フィルタリングされたアイテムリスト
    """
    if verification_filter is None:
        return items

    return [
        item
        for item in items
        if getattr(item, "is_manually_verified", False) == verification_filter
    ]
