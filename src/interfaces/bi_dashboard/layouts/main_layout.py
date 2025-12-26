"""Main layout for BI Dashboard POC.

This module defines the layout structure of the dashboard.
"""

from typing import TYPE_CHECKING

from dash import dcc, html


if TYPE_CHECKING:
    from dash.html import Div


def create_layout() -> html.Div:
    """Create the main dashboard layout.

    Returns:
        html.Div: Dashboard layout component
    """
    return html.Div(
        [
            # Header
            html.Div(
                [
                    html.H1(
                        "Polibase データカバレッジダッシュボード",
                        style={"textAlign": "center", "color": "#2c3e50"},
                    ),
                    html.P(
                        "全国の自治体データ収集状況を可視化",
                        style={"textAlign": "center", "color": "#7f8c8d"},
                    ),
                ],
                style={"padding": "20px"},
            ),
            # Filter Section
            html.Div(
                [
                    html.H3("フィルタ", style={"textAlign": "center"}),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("期間選択"),
                                    dcc.Dropdown(
                                        id="period-filter",
                                        options=[
                                            {"label": "過去7日", "value": "7d"},
                                            {"label": "過去30日", "value": "30d"},
                                            {"label": "過去90日", "value": "90d"},
                                        ],
                                        value="30d",
                                        clearable=False,
                                    ),
                                ],
                                style={
                                    "width": "30%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Label("会議体フィルタ"),
                                    dcc.Dropdown(
                                        id="conference-filter",
                                        options=[],  # Populated by callback
                                        value=None,
                                        placeholder="全ての会議体",
                                        clearable=True,
                                    ),
                                ],
                                style={
                                    "width": "30%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "データを更新",
                                        id="refresh-button",
                                        n_clicks=0,
                                        style={
                                            "padding": "10px 30px",
                                            "fontSize": "16px",
                                            "backgroundColor": "#3498db",
                                            "color": "white",
                                            "border": "none",
                                            "borderRadius": "5px",
                                            "cursor": "pointer",
                                            "marginTop": "25px",
                                        },
                                    )
                                ],
                                style={
                                    "width": "30%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "textAlign": "center",
                                },
                            ),
                        ],
                        style={"display": "flex", "justifyContent": "space-around"},
                    ),
                ],
                style={
                    "padding": "20px",
                    "backgroundColor": "#ecf0f1",
                    "marginBottom": "20px",
                },
            ),
            # Summary Cards
            html.Div(
                id="summary-cards",
                style={
                    "display": "flex",
                    "justifyContent": "space-around",
                    "padding": "20px",
                    "backgroundColor": "#ecf0f1",
                    "flexWrap": "wrap",
                },
            ),
            # Section 1: 自治体カバレッジ
            html.Div(
                [
                    html.H2(
                        "📊 自治体カバレッジ",
                        style={"textAlign": "center", "color": "#2c3e50"},
                    ),
                    html.Div(
                        [
                            # Coverage Pie Chart
                            html.Div(
                                [
                                    html.H3(
                                        "全体カバレッジ率",
                                        style={"textAlign": "center"},
                                    ),
                                    dcc.Graph(id="coverage-pie-chart"),
                                ],
                                style={
                                    "width": "48%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                            # Coverage by Type Bar Chart
                            html.Div(
                                [
                                    html.H3(
                                        "組織タイプ別カバレッジ",
                                        style={"textAlign": "center"},
                                    ),
                                    dcc.Graph(id="coverage-by-type-chart"),
                                ],
                                style={
                                    "width": "48%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                        ],
                        style={"padding": "20px"},
                    ),
                    # Prefecture Coverage Table
                    html.Div(
                        [
                            html.H3(
                                "都道府県別カバレッジ", style={"textAlign": "center"}
                            ),
                            html.Div(id="prefecture-table"),
                        ],
                        style={"padding": "20px"},
                    ),
                ],
                style={"marginBottom": "40px"},
            ),
            # Section 2: 会議カバレッジ
            html.Div(
                [
                    html.H2(
                        "📅 会議カバレッジ",
                        style={"textAlign": "center", "color": "#2c3e50"},
                    ),
                    html.Div(
                        [
                            # Meetings Coverage Pie Chart
                            html.Div(
                                [
                                    html.H3(
                                        "議事録完了率", style={"textAlign": "center"}
                                    ),
                                    dcc.Graph(id="meetings-coverage-pie"),
                                ],
                                style={
                                    "width": "48%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                            # Meetings by Conference Bar Chart
                            html.Div(
                                [
                                    html.H3(
                                        "会議体別会議数", style={"textAlign": "center"}
                                    ),
                                    dcc.Graph(id="meetings-by-conference-bar"),
                                ],
                                style={
                                    "width": "48%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                        ],
                        style={"padding": "20px"},
                    ),
                ],
                style={"marginBottom": "40px", "backgroundColor": "#f8f9fa"},
            ),
            # Section 3: Speaker紐付け率
            html.Div(
                [
                    html.H2(
                        "🎤 Speaker紐付け統計",
                        style={"textAlign": "center", "color": "#2c3e50"},
                    ),
                    html.Div(
                        [
                            # Speaker Matching Gauge
                            html.Div(
                                [
                                    html.H3(
                                        "Speaker紐付け率", style={"textAlign": "center"}
                                    ),
                                    dcc.Graph(id="speaker-matching-gauge"),
                                ],
                                style={
                                    "width": "32%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                            # Conversation Linkage Gauge
                            html.Div(
                                [
                                    html.H3(
                                        "発言紐付け率", style={"textAlign": "center"}
                                    ),
                                    dcc.Graph(id="conversation-linkage-gauge"),
                                ],
                                style={
                                    "width": "32%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                            # Speaker Stats Bar Chart
                            html.Div(
                                [
                                    html.H3(
                                        "紐付け状況", style={"textAlign": "center"}
                                    ),
                                    dcc.Graph(id="speaker-stats-bar"),
                                ],
                                style={
                                    "width": "32%",
                                    "display": "inline-block",
                                    "padding": "10px",
                                    "verticalAlign": "top",
                                },
                            ),
                        ],
                        style={"padding": "20px"},
                    ),
                ],
                style={"marginBottom": "40px"},
            ),
            # Section 4: 活動推移
            html.Div(
                [
                    html.H2(
                        "📈 活動推移", style={"textAlign": "center", "color": "#2c3e50"}
                    ),
                    html.Div(
                        [
                            # Activity Trend Line Chart
                            html.Div(
                                [
                                    html.H3(
                                        "日別活動推移", style={"textAlign": "center"}
                                    ),
                                    dcc.Graph(id="activity-trend-line"),
                                ],
                                style={"padding": "10px"},
                            ),
                            # Activity Heatmap
                            html.Div(
                                [
                                    html.H3(
                                        "活動ヒートマップ",
                                        style={"textAlign": "center"},
                                    ),
                                    dcc.Graph(id="activity-heatmap"),
                                ],
                                style={"padding": "10px"},
                            ),
                        ],
                        style={"padding": "20px"},
                    ),
                ],
                style={"marginBottom": "40px", "backgroundColor": "#f8f9fa"},
            ),
            # Hidden div for storing data
            html.Div(id="data-store", style={"display": "none"}),
        ],
        style={
            "fontFamily": "Arial, sans-serif",
            "maxWidth": "1400px",
            "margin": "0 auto",
            "backgroundColor": "#ffffff",
        },
    )


def create_summary_card(title: str, value: str, color: str) -> "Div":
    """Create a summary card component.

    Args:
        title: Card title
        value: Display value
        color: Card background color

    Returns:
        html.Div: Summary card component
    """
    return html.Div(
        [
            html.H4(title, style={"margin": "0", "color": "#2c3e50"}),
            html.H2(value, style={"margin": "10px 0", "color": color}),
        ],
        style={
            "backgroundColor": "white",
            "padding": "20px",
            "borderRadius": "10px",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            "minWidth": "200px",
            "textAlign": "center",
        },
    )
