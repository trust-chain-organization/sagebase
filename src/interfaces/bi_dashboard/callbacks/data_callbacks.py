"""Callbacks for BI Dashboard POC.

This module defines interactive callbacks for the dashboard.
"""

from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html
from data.data_loader import (
    get_activity_trend_data,
    get_coverage_stats,
    get_meeting_coverage_data,
    get_prefecture_coverage,
    get_speaker_matching_data,
)
from layouts.main_layout import create_summary_card


if TYPE_CHECKING:
    from dash import Dash


def register_callbacks(app: "Dash") -> None:
    """Register all callbacks for the dashboard.

    Args:
        app: Dash application instance
    """

    @app.callback(
        [
            Output("summary-cards", "children"),
            Output("coverage-pie-chart", "figure"),
            Output("coverage-by-type-chart", "figure"),
            Output("prefecture-table", "children"),
        ],
        [Input("refresh-button", "n_clicks")],
    )
    def update_dashboard(
        n_clicks: int,
    ) -> tuple[list, go.Figure, go.Figure, html.Table]:
        """Update all dashboard components.

        Args:
            n_clicks: Number of times refresh button was clicked

        Returns:
            tuple: Updated components (cards, charts, table)
        """
        # Get data
        stats = get_coverage_stats()
        prefecture_df = get_prefecture_coverage()

        # Create summary cards
        cards = [
            create_summary_card("総自治体数", f"{stats['total']:,}", "#3498db"),
            create_summary_card("データ取得済み", f"{stats['covered']:,}", "#2ecc71"),
            create_summary_card(
                "カバレッジ率",
                f"{stats['coverage_rate']:.1f}%",
                "#e74c3c"
                if stats["coverage_rate"] < 50
                else "#f39c12"
                if stats["coverage_rate"] < 80
                else "#2ecc71",
            ),
        ]

        # Create pie chart
        pie_data = {
            "labels": ["データあり", "データなし"],
            "values": [stats["covered"], stats["total"] - stats["covered"]],
            "colors": ["#2ecc71", "#e74c3c"],
        }
        pie_fig = go.Figure(
            data=[
                go.Pie(
                    labels=pie_data["labels"],
                    values=pie_data["values"],
                    marker={"colors": pie_data["colors"]},
                    hole=0.3,
                    textinfo="label+percent+value",
                )
            ]
        )
        pie_fig.update_layout(showlegend=True, height=400)

        # Create bar chart for coverage by type
        type_data = []
        for org_type, data in stats["by_type"].items():
            type_data.append(
                {
                    "type": org_type,
                    "covered": data["covered"],
                    "not_covered": data["total"] - data["covered"],
                    "coverage_rate": data["coverage_rate"],
                }
            )

        bar_fig = go.Figure()
        bar_fig.add_trace(
            go.Bar(
                name="データあり",
                x=[d["type"] for d in type_data],
                y=[d["covered"] for d in type_data],
                marker_color="#2ecc71",
            )
        )
        bar_fig.add_trace(
            go.Bar(
                name="データなし",
                x=[d["type"] for d in type_data],
                y=[d["not_covered"] for d in type_data],
                marker_color="#e74c3c",
            )
        )
        bar_fig.update_layout(
            barmode="stack",
            height=400,
            xaxis_title="組織タイプ",
            yaxis_title="自治体数",
        )

        # Create prefecture table
        table_header = html.Thead(
            html.Tr(
                [
                    html.Th(
                        "都道府県",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                        },
                    ),
                    html.Th(
                        "総数",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "textAlign": "right",
                        },
                    ),
                    html.Th(
                        "データあり",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "textAlign": "right",
                        },
                    ),
                    html.Th(
                        "カバレッジ率",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "textAlign": "right",
                        },
                    ),
                ]
            )
        )

        table_rows = []
        for _, row in prefecture_df.head(10).iterrows():
            bg_color = (
                "#d5f4e6"
                if row["coverage_rate"] >= 80
                else "#fff3cd"
                if row["coverage_rate"] >= 50
                else "#f8d7da"
            )
            table_rows.append(
                html.Tr(
                    [
                        html.Td(row["prefecture"], style={"padding": "10px"}),
                        html.Td(
                            f"{int(row['total']):,}",
                            style={"padding": "10px", "textAlign": "right"},
                        ),
                        html.Td(
                            f"{int(row['covered']):,}",
                            style={"padding": "10px", "textAlign": "right"},
                        ),
                        html.Td(
                            f"{row['coverage_rate']:.1f}%",
                            style={"padding": "10px", "textAlign": "right"},
                        ),
                    ],
                    style={"backgroundColor": bg_color},
                )
            )

        table_body = html.Tbody(table_rows)

        table = html.Table(
            [table_header, table_body],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            },
        )

        return cards, pie_fig, bar_fig, table

    @app.callback(
        [
            Output("meetings-coverage-pie", "figure"),
            Output("meetings-by-conference-bar", "figure"),
        ],
        [Input("refresh-button", "n_clicks")],
    )
    def update_meeting_coverage_graphs(
        n_clicks: int,
    ) -> tuple[go.Figure, go.Figure]:
        """Update meeting coverage graphs.

        Args:
            n_clicks: Number of times refresh button was clicked

        Returns:
            tuple: (pie_figure, bar_figure)
        """
        # Get meeting coverage data
        meeting_data = get_meeting_coverage_data()

        # Create pie chart for minutes coverage
        pie_fig = go.Figure(
            data=[
                go.Pie(
                    labels=["議事録あり", "議事録なし"],
                    values=[
                        meeting_data["with_minutes"],
                        meeting_data["total_meetings"] - meeting_data["with_minutes"],
                    ],
                    marker={"colors": ["#2ecc71", "#e74c3c"]},
                    hole=0.3,
                    textinfo="label+percent+value",
                )
            ]
        )
        pie_fig.update_layout(showlegend=True, height=400)

        # Create bar chart for meetings by conference
        conferences = list(meeting_data["meetings_by_conference"].keys())
        meeting_counts = list(meeting_data["meetings_by_conference"].values())

        # Sort by meeting count
        sorted_data = sorted(
            zip(conferences, meeting_counts, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        conferences, meeting_counts = (
            zip(*sorted_data[:10], strict=False) if sorted_data else ([], [])
        )

        bar_fig = go.Figure(
            data=[
                go.Bar(
                    x=list(conferences),
                    y=list(meeting_counts),
                    marker_color="#3498db",
                )
            ]
        )
        bar_fig.update_layout(
            height=400,
            xaxis_title="会議体",
            yaxis_title="会議数",
            xaxis={"tickangle": -45},
        )

        return pie_fig, bar_fig

    @app.callback(
        [
            Output("speaker-matching-gauge", "figure"),
            Output("conversation-linkage-gauge", "figure"),
            Output("speaker-stats-bar", "figure"),
        ],
        [Input("refresh-button", "n_clicks")],
    )
    def update_speaker_matching_graphs(
        n_clicks: int,
    ) -> tuple[go.Figure, go.Figure, go.Figure]:
        """Update speaker matching graphs.

        Args:
            n_clicks: Number of times refresh button was clicked

        Returns:
            tuple: (gauge1, gauge2, bar_figure)
        """
        # Get speaker matching data
        speaker_data = get_speaker_matching_data()

        # Create gauge for speaker matching rate
        gauge1_fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=speaker_data["matching_rate"],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "紐付け率 (%)"},
                delta={"reference": 80},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "#2ecc71"},
                    "steps": [
                        {"range": [0, 50], "color": "#f8d7da"},
                        {"range": [50, 80], "color": "#fff3cd"},
                        {"range": [80, 100], "color": "#d5f4e6"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 80,
                    },
                },
            )
        )
        gauge1_fig.update_layout(height=300)

        # Create gauge for conversation linkage rate
        gauge2_fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=speaker_data["linkage_rate"],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "発言紐付け率 (%)"},
                delta={"reference": 80},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "#3498db"},
                    "steps": [
                        {"range": [0, 50], "color": "#f8d7da"},
                        {"range": [50, 80], "color": "#fff3cd"},
                        {"range": [80, 100], "color": "#d5f4e6"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 80,
                    },
                },
            )
        )
        gauge2_fig.update_layout(height=300)

        # Create bar chart for speaker stats
        bar_fig = go.Figure(
            data=[
                go.Bar(
                    name="紐付け済み",
                    x=["Speakers", "発言"],
                    y=[
                        speaker_data["matched_speakers"],
                        speaker_data["linked_conversations"],
                    ],
                    marker_color="#2ecc71",
                ),
                go.Bar(
                    name="未紐付け",
                    x=["Speakers", "発言"],
                    y=[
                        speaker_data["unmatched_speakers"],
                        speaker_data["total_conversations"]
                        - speaker_data["linked_conversations"],
                    ],
                    marker_color="#e74c3c",
                ),
            ]
        )
        bar_fig.update_layout(
            barmode="stack",
            height=300,
            yaxis_title="数",
        )

        return gauge1_fig, gauge2_fig, bar_fig

    @app.callback(
        [
            Output("activity-trend-line", "figure"),
            Output("activity-heatmap", "figure"),
        ],
        [Input("refresh-button", "n_clicks"), Input("period-filter", "value")],
    )
    def update_activity_trend_graphs(
        n_clicks: int, period: str
    ) -> tuple[go.Figure, go.Figure]:
        """Update activity trend graphs.

        Args:
            n_clicks: Number of times refresh button was clicked
            period: Period filter value

        Returns:
            tuple: (line_figure, heatmap_figure)
        """
        # Get activity trend data
        trend_data = get_activity_trend_data(period)

        if not trend_data:
            # Return empty figures if no data
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="データがありません",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return empty_fig, empty_fig

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(trend_data)
        df["date"] = pd.to_datetime(df["date"])

        # Create line chart for activity trend
        line_fig = go.Figure()
        line_fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["meetings_count"],
                mode="lines+markers",
                name="会議数",
                line={"color": "#3498db"},
            )
        )
        line_fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["conversations_count"],
                mode="lines+markers",
                name="発言数",
                line={"color": "#2ecc71"},
            )
        )
        line_fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["speakers_count"],
                mode="lines+markers",
                name="Speaker数",
                line={"color": "#f39c12"},
            )
        )
        line_fig.update_layout(
            height=400,
            xaxis_title="日付",
            yaxis_title="数",
            hovermode="x unified",
        )

        # Create heatmap
        # Prepare data for heatmap: week vs day of week
        df["weekday"] = df["date"].dt.day_name()
        df["week"] = df["date"].dt.isocalendar().week

        # Pivot for heatmap
        heatmap_data = df.pivot_table(
            index="weekday",
            columns="week",
            values="conversations_count",
            aggfunc="sum",
            fill_value=0,
        )

        # Reorder weekdays
        weekday_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        heatmap_data = heatmap_data.reindex(
            [day for day in weekday_order if day in heatmap_data.index]
        )

        heatmap_fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale="YlGnBu",
                hoverongaps=False,
            )
        )
        heatmap_fig.update_layout(
            height=400,
            xaxis_title="週",
            yaxis_title="曜日",
        )

        return line_fig, heatmap_fig
