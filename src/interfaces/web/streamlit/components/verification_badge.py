"""手動検証済みバッジコンポーネント。

手動検証状態を視覚的に表示するためのコンポーネント。
VerifiableEntityプロトコルを実装したエンティティに対して使用される。
"""

import streamlit as st


def render_verification_badge(is_verified: bool) -> None:
    """手動検証済みバッジを表示する。

    Args:
        is_verified: 手動検証済みかどうか
    """
    if is_verified:
        st.markdown(
            '<span style="background-color: #e8f5e9; padding: 2px 8px; '
            'border-radius: 4px; font-size: 0.85em;">'
            "✅ 手動検証済み</span>",
            unsafe_allow_html=True,
            help="このデータは手動で検証済みです。AI再実行で上書きされません。",
        )
    else:
        st.markdown(
            '<span style="background-color: #e3f2fd; padding: 2px 8px; '
            'border-radius: 4px; font-size: 0.85em;">'
            "🤖 AI抽出</span>",
            unsafe_allow_html=True,
            help="このデータはAIが抽出しました。手動で修正すると保護されます。",
        )


def get_verification_badge_text(is_verified: bool) -> str:
    """検証状態のテキスト表現を取得する。

    DataFrameなどで表示する際に使用する。

    Args:
        is_verified: 手動検証済みかどうか

    Returns:
        検証状態を表すテキスト
    """
    return "✅ 手動検証済み" if is_verified else "🤖 AI抽出"


def get_verification_badge_html(is_verified: bool) -> str:
    """検証状態のHTML表現を取得する。

    HTMLとして表示する際に使用する。

    Args:
        is_verified: 手動検証済みかどうか

    Returns:
        検証状態を表すHTML文字列
    """
    if is_verified:
        return (
            '<span style="background-color: #e8f5e9; padding: 2px 8px; '
            'border-radius: 4px; font-size: 0.85em;">'
            "✅ 手動検証済み</span>"
        )
    else:
        return (
            '<span style="background-color: #e3f2fd; padding: 2px 8px; '
            'border-radius: 4px; font-size: 0.85em;">'
            "🤖 AI抽出</span>"
        )
