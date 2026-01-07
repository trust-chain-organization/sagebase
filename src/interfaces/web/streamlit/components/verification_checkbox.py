"""手動検証チェックボックスコンポーネント。

手動検証状態を変更するためのチェックボックスコンポーネント。
VerifiableEntityプロトコルを実装したエンティティに対して使用される。
"""

import streamlit as st


def render_verification_checkbox(
    current_value: bool,
    key: str,
    on_change: bool = False,
) -> bool:
    """手動検証チェックボックスを表示する。

    Args:
        current_value: 現在の手動検証状態
        key: Streamlitのウィジェットキー
        on_change: 変更時にリロードするかどうか

    Returns:
        チェックボックスの新しい値
    """
    new_value = st.checkbox(
        "手動検証済みとしてマーク",
        value=current_value,
        key=key,
        help="チェックすると、AI再実行でこのデータが上書きされなくなります",
    )
    return new_value


def render_verification_checkbox_with_warning(
    current_value: bool,
    key: str,
) -> tuple[bool, bool]:
    """警告付きの手動検証チェックボックスを表示する。

    手動検証を解除する際に警告を表示する。

    Args:
        current_value: 現在の手動検証状態
        key: Streamlitのウィジェットキー

    Returns:
        tuple: (新しい値, 値が変更されたか)
    """
    new_value = st.checkbox(
        "手動検証済みとしてマーク",
        value=current_value,
        key=key,
        help="チェックすると、AI再実行でこのデータが上書きされなくなります",
    )

    changed = new_value != current_value

    # 手動検証を解除する場合に警告
    if changed and current_value and not new_value:
        st.warning(
            "⚠️ 手動検証を解除すると、"
            "次回のAI再実行でこのデータが上書きされる可能性があります。"
        )

    return new_value, changed
