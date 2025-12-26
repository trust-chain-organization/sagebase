"""Utilities for Japan map visualization with Folium."""

from typing import Any

import folium
import pandas as pd
from folium import plugins


# 日本の都道府県の中心座標
PREFECTURE_CENTERS = {
    "北海道": [43.0640, 141.3469],
    "青森県": [40.8246, 140.7406],
    "岩手県": [39.7036, 141.1527],
    "宮城県": [38.2689, 140.8721],
    "秋田県": [39.7186, 140.1024],
    "山形県": [38.2404, 140.3628],
    "福島県": [37.7503, 140.4676],
    "茨城県": [36.3418, 140.4468],
    "栃木県": [36.5657, 139.8836],
    "群馬県": [36.3909, 139.0604],
    "埼玉県": [35.8570, 139.6489],
    "千葉県": [35.6051, 140.1233],
    "東京都": [35.6895, 139.6917],
    "神奈川県": [35.4475, 139.6424],
    "新潟県": [37.9024, 139.0232],
    "富山県": [36.6953, 137.2114],
    "石川県": [36.5947, 136.6256],
    "福井県": [36.0652, 136.2217],
    "山梨県": [35.6642, 138.5684],
    "長野県": [36.6513, 138.1810],
    "岐阜県": [35.3912, 136.7223],
    "静岡県": [34.9777, 138.3831],
    "愛知県": [35.1802, 136.9066],
    "三重県": [34.7303, 136.5086],
    "滋賀県": [35.0045, 135.8687],
    "京都府": [35.0212, 135.7556],
    "大阪府": [34.6863, 135.5200],
    "兵庫県": [34.6913, 135.1830],
    "奈良県": [34.6851, 135.8328],
    "和歌山県": [34.2261, 135.1675],
    "鳥取県": [35.5039, 134.2378],
    "島根県": [35.4723, 133.0505],
    "岡山県": [34.6619, 133.9351],
    "広島県": [34.3966, 132.4596],
    "山口県": [34.1861, 131.4705],
    "徳島県": [34.0658, 134.5593],
    "香川県": [34.3401, 134.0434],
    "愛媛県": [33.8417, 132.7658],
    "高知県": [33.5597, 133.5311],
    "福岡県": [33.6064, 130.4183],
    "佐賀県": [33.2494, 130.2988],
    "長崎県": [32.7448, 129.8737],
    "熊本県": [32.7898, 130.7417],
    "大分県": [33.2382, 131.6126],
    "宮崎県": [31.9111, 131.4239],
    "鹿児島県": [31.5602, 130.5581],
    "沖縄県": [26.2124, 127.6809],
}


def get_prefecture_geojson() -> dict[str, Any]:
    """Get GeoJSON data for Japanese prefectures.

    This is a simplified version. In production, you would load from a proper
    GeoJSON file. For now, we'll create markers for each prefecture center.
    """
    # Note: In a real implementation, you would load a proper GeoJSON file
    # containing prefecture boundaries. For this example, we'll use point data.
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": name, "name_ja": name},
                "geometry": {
                    "type": "Point",
                    "coordinates": [coords[1], coords[0]],  # GeoJSON uses [lon, lat]
                },
            }
            for name, coords in PREFECTURE_CENTERS.items()
        ],
    }


def create_japan_map(
    data: pd.DataFrame,
    value_column: str = "total_value",
    center: list[float] | None = None,
    zoom_start: int = 5,
) -> folium.Map:
    """Create a Folium map of Japan with data visualization.

    Args:
        data: DataFrame with prefecture data (must have 'prefecture_name' column)
        value_column: Column name containing values to visualize
        center: Map center coordinates [lat, lon]. Defaults to Japan center.
        zoom_start: Initial zoom level

    Returns:
        Folium map object
    """
    if center is None:
        center = [36.5, 138.0]  # Center of Japan

    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="CartoDB positron",
        max_bounds=True,
        min_zoom=4,
        max_zoom=10,
    )

    # Ensure data has the required columns
    if "prefecture_name" not in data.columns:
        raise ValueError("Data must have 'prefecture_name' column")

    # Normalize values for color mapping
    max_value: float = 100.0
    min_value: float = 0.0

    if value_column in data.columns:
        value_series = data[value_column]  # type: ignore[index]
        if len(value_series) > 0:  # type: ignore[arg-type]
            max_val = value_series.max()  # type: ignore[no-untyped-call]
            min_val = value_series.min()  # type: ignore[no-untyped-call]
            max_value = float(max_val) if max_val is not None else 100.0  # type: ignore[arg-type]
            min_value = float(min_val) if min_val is not None else 0.0  # type: ignore[arg-type]

    # Create a marker for each prefecture
    for prefecture, coords in PREFECTURE_CENTERS.items():
        # Get data for this prefecture
        pref_data = data[data["prefecture_name"] == prefecture]  # type: ignore[index]

        if len(pref_data) > 0:  # type: ignore[arg-type]
            value: float = 0.0
            if value_column in pref_data.columns:  # type: ignore[union-attr]
                val = pref_data.iloc[0][value_column]  # type: ignore[call-overload]
                value = float(val) if val is not None else 0.0  # type: ignore[arg-type]

            # Calculate color based on value
            if max_value > min_value:
                normalized = (value - min_value) / (max_value - min_value)
            else:
                normalized = 0.5

            # Color gradient from red (0) to yellow (0.5) to green (1)
            if normalized < 0.5:
                color = f"#{255:02x}{int(255 * 2 * normalized):02x}00"
            else:
                color = f"#{int(255 * 2 * (1 - normalized)):02x}{255:02x}00"

            # Create popup content
            popup_content = f"""
            <div style="font-family: sans-serif;">
                <h4>{prefecture}</h4>
                <table>
                    <tr><td>全体充実度:</td><td><b>{value:.1f}%</b></td></tr>
            """

            # Add additional metrics if available
            for col in [
                "meetings_count",
                "minutes_count",
                "politicians_count",
                "groups_count",
            ]:
                if col in pref_data.columns:  # type: ignore[union-attr]
                    col_value = pref_data.iloc[0][col]  # type: ignore[call-overload]
                    if col_value is not None:
                        popup_content += (
                            f"<tr><td>{get_column_label(col)}:</td>"
                            f"<td>{int(col_value):,}</td></tr>"  # type: ignore[arg-type]
                        )

            popup_content += "</table></div>"

            # Add circle marker
            folium.CircleMarker(
                location=coords,
                radius=10 + (normalized * 15),  # Size based on value
                popup=folium.Popup(popup_content, max_width=300),
                color="darkgray",
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2,
            ).add_to(m)

            # Add prefecture name label
            folium.Marker(
                location=coords,
                icon=folium.DivIcon(
                    html=(
                        f'<div style="font-size: 10px; font-weight: bold;">'
                        f"{prefecture}</div>"
                    ),
                    icon_size=(50, 12),
                    icon_anchor=(25, 6),
                ),
            ).add_to(m)

    # Add a color scale legend
    colormap = folium.LinearColormap(
        colors=["red", "yellow", "green"],
        vmin=min_value,
        vmax=max_value,
        caption=f"{value_column} (%)",
    )
    colormap.add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    return m


def get_column_label(column_name: str) -> str:
    """Get Japanese label for column name."""
    labels = {
        "meetings_count": "会議数",
        "minutes_count": "議事録数",
        "politicians_count": "議員数",
        "groups_count": "議員団数",
        "total_value": "充実度",
    }
    return labels.get(column_name, column_name)


def create_prefecture_details_card(prefecture_data: pd.Series) -> str:
    """Create HTML content for prefecture details card."""
    html = f"""
    <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px;">
        <h3>{prefecture_data["prefecture_name"]}の詳細データ</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr;
             gap: 10px; margin-top: 10px;">
    """

    metrics = [
        ("conference_count", "議会数", "#1f77b4"),
        ("meetings_count", "会議数", "#ff7f0e"),
        ("minutes_count", "議事録数", "#2ca02c"),
        ("politicians_count", "議員数", "#d62728"),
        ("groups_count", "議員団数", "#9467bd"),
    ]

    for col, label, color in metrics:
        if col in prefecture_data.index:  # type: ignore[operator]
            val = prefecture_data[col]  # type: ignore[index]
            value: int = int(val) if val is not None else 0  # type: ignore[arg-type]
            html += f"""
            <div style="background: white; padding: 10px; border-radius: 5px;
                 border-left: 4px solid {color};">
                <div style="color: #666; font-size: 12px;">{label}</div>
                <div style="font-size: 24px; font-weight: bold;
                     color: {color};">{value:,}</div>
            </div>
            """

    html += """
        </div>
    </div>
    """

    return html
