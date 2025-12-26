"""Google Analytics integration for Streamlit.

このモジュールは、StreamlitアプリケーションにGoogle Analyticsトラッキングを
統合するためのコンポーネントを提供します。
"""

import os

import streamlit.components.v1 as components

import streamlit as st


def inject_google_analytics():
    """Google Analytics (GA4) トラッキングコードをページに挿入する。

    環境変数 GOOGLE_ANALYTICS_ID が設定されている場合のみ、
    Google Analyticsのトラッキングコードを挿入します。

    環境変数:
        GOOGLE_ANALYTICS_ID: Google Analytics測定ID (例: G-XXXXXXXXXX)
    """
    ga_id = os.getenv("GOOGLE_ANALYTICS_ID")

    if not ga_id:
        # 開発環境や測定IDが未設定の場合はトラッキングを無効化
        return

    # Google Analytics (GA4) のトラッキングコード
    ga_code = f"""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());

      gtag('config', '{ga_id}', {{
        'anonymize_ip': true,
        'cookie_flags': 'SameSite=None;Secure'
      }});
    </script>
    """

    # HTMLコンポーネントとして挿入
    components.html(ga_code, height=0)


def track_page_view(page_title: str, page_path: str | None = None):
    """ページビューを手動でトラッキングする。

    Args:
        page_title: ページタイトル
        page_path: ページパス（省略時は現在のURLパスを使用）
    """
    ga_id = os.getenv("GOOGLE_ANALYTICS_ID")

    if not ga_id:
        return

    if page_path is None:
        # Streamlitのquery_paramsから現在のパスを取得
        page_path = st.query_params.get("page", "/")

    tracking_code = f"""
    <script>
      if (typeof gtag !== 'undefined') {{
        gtag('event', 'page_view', {{
          'page_title': '{page_title}',
          'page_path': '{page_path}'
        }});
      }}
    </script>
    """

    components.html(tracking_code, height=0)


def track_event(
    event_name: str,
    event_category: str | None = None,
    event_label: str | None = None,
    event_value: int | None = None,
):
    """カスタムイベントをトラッキングする。

    Args:
        event_name: イベント名
        event_category: イベントカテゴリ（任意）
        event_label: イベントラベル（任意）
        event_value: イベント値（任意）

    使用例:
        >>> track_event("button_click", "navigation", "home_button")
        >>> track_event("file_upload", "data", "minutes_pdf", 1)
    """
    ga_id = os.getenv("GOOGLE_ANALYTICS_ID")

    if not ga_id:
        return

    # イベントパラメータの構築
    params = {}
    if event_category:
        params["event_category"] = event_category
    if event_label:
        params["event_label"] = event_label
    if event_value is not None:
        params["value"] = event_value

    params_json = str(params).replace("'", '"')

    tracking_code = f"""
    <script>
      if (typeof gtag !== 'undefined') {{
        gtag('event', '{event_name}', {params_json});
      }}
    </script>
    """

    components.html(tracking_code, height=0)
