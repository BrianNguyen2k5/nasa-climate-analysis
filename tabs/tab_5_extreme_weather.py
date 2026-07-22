from __future__ import annotations

import html
from typing import Any

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from sidebar import ALL_REGIONS_LABEL, LOCATION_VIETNAMESE, REGION_ORDER


PRIMARY = "#1E3A5F"
SECONDARY = "#2A9D8F"
EXTREME = "#E76F51"
BORDER = "#E2E8F0"
MUTED = "#64748B"
CARD = "#FFFFFF"

REGION_COLORS = {
    "Bắc Trung Bộ": "#8B5CF6",
    "Nam Trung Bộ": "#F59E0B",
    "Trung du và miền núi phía Bắc": "#3B82F6",
    "Đông Nam Bộ": "#EF4444",
    "Đồng bằng sông Cửu Long": "#06B6D4",
    "Đồng bằng sông Hồng": "#10B981",
}
REGION_LEGEND_LABELS = {
    "Đồng bằng sông Cửu Long": "ĐB sông Cửu Long",
    "Đồng bằng sông Hồng": "ĐB sông Hồng",
}

REQUIRED_COLUMNS = {"year", "location_name", "region"}
NUMERIC_COLUMNS = [
    "year",
    "latitude",
    "longitude",
    "T2M_MAX",
    "PRECTOTCORR",
    "hot_day",
    "heavy_rain_day",
    "dry_day",
    "dry_run_length",
    "heatwave_event_length",
]
COMPACT_CHART_HEIGHT = 305
DRY_SPELL_ROW_HEIGHT = 24
PLOT_CONFIG = {"displayModeBar": True, "displaylogo": False, "responsive": True}
HEAVY_RAIN_BUBBLE_BINS = [-0.01, 2, 4, 6, 8, float("inf")]
HEAVY_RAIN_BUBBLE_LABELS = ["0-2 ngày", "2-4 ngày", "4-6 ngày", "6-8 ngày", ">8 ngày"]
HEAVY_RAIN_BUBBLE_LEVELS = [1, 2, 3, 4, 5]
HEAVY_RAIN_BUBBLE_DIAMETERS = [8, 13, 19, 27, 38]
HEAVY_RAIN_BUBBLE_SIZE_MAP = dict(zip(HEAVY_RAIN_BUBBLE_LEVELS, HEAVY_RAIN_BUBBLE_DIAMETERS))
HEATWAVE_COLOR_DOMAIN = [0, 2, 4, 6]
HEATWAVE_COLOR_RANGE = ["#FEE8C8", "#FDBB84", "#E34A33", "#B30000"]


def inject_extreme_weather_css() -> None:
    st.markdown(
        """
        <style>
            .block-container [data-testid="stVerticalBlock"] {
                gap: 1rem !important;
            }

            .extreme-chart-title {
                color: #1E3A5F;
                font-size: 15px;
                font-weight: 750;
                line-height: 1.25;
                margin: 8px 0 6px 0;
                white-space: normal;
            }

            .extreme-kpi-spacer {
                height: 0.75rem;
            }

            .maplibregl-ctrl-attrib,
            .maplibregl-ctrl-logo,
            .mapboxgl-ctrl-attrib,
            .mapboxgl-ctrl-logo {
                display: none !important;
            }

            .extreme-map-legend {
                min-height: 305px;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                padding: 16px 18px;
                box-sizing: border-box;
                background: #FFFFFF;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
            }

            .extreme-map-legend-title {
                color: #64748B;
                font-size: 0.82rem;
                font-weight: 700;
                line-height: 1.15;
                margin: 0 0 10px;
            }

            .extreme-map-region-row,
            .extreme-map-size-row {
                display: grid;
                align-items: center;
                column-gap: 8px;
                margin-bottom: 8px;
            }

            .extreme-map-region-row {
                grid-template-columns: 14px minmax(0, 1fr);
            }

            .extreme-map-size-row {
                grid-template-columns: 30px minmax(0, 1fr);
            }

            .extreme-map-region-dot {
                width: 13px;
                height: 13px;
                border-radius: 999px;
            }

            .extreme-map-size-dot {
                border-radius: 999px;
                background: rgba(90, 90, 90, 0.78);
                justify-self: center;
            }

            .extreme-map-region-label,
            .extreme-map-size-label {
                color: #1F2937;
                font-size: 0.72rem;
                line-height: 1.22;
                white-space: normal;
            }

            .extreme-map-legend-break {
                height: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_kpi_number(value: float) -> str:
    rounded = round(float(value), 1)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.1f}".replace(".", ",")


def _format_year_span(start_date: Any, end_date: Any) -> str:
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start) and pd.isna(end):
        return "Không rõ năm"
    if pd.isna(end):
        return str(int(start.year))
    if pd.isna(start):
        return str(int(end.year))
    if start.year == end.year:
        return str(int(start.year))
    return f"{int(start.year)}-{int(end.year)}"


def _selected_values(filters: dict[str, Any] | None, keys: tuple[str, ...]) -> list[str] | None:
    if not filters:
        return None

    for key in keys:
        if key in filters:
            value = filters.get(key)
            break
    else:
        return None

    if value is None:
        return None
    if isinstance(value, str):
        if value == ALL_REGIONS_LABEL or value.startswith("Tất cả"):
            return []
        return [value]

    return [
        str(item)
        for item in value
        if item and not str(item).startswith("Tất cả")
    ]


def _year_bounds(df: pd.DataFrame, filters: dict[str, Any] | None) -> tuple[int, int] | None:
    years = pd.to_numeric(df.get("year"), errors="coerce").dropna()
    if years.empty:
        return None

    default_bounds = (int(years.min()), int(years.max()))
    raw_bounds = None if not filters else (
        filters.get("year_range")
        or filters.get("selected_year_range")
        or filters.get("period")
    )
    if not isinstance(raw_bounds, (tuple, list)) or len(raw_bounds) != 2:
        return default_bounds

    start, end = sorted((int(raw_bounds[0]), int(raw_bounds[1])))
    return start, end


def prepare_filtered_climate_data(
    climate_df: pd.DataFrame | None,
    filters: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, list[int]]:
    if climate_df is None or climate_df.empty:
        return pd.DataFrame(), []

    missing = REQUIRED_COLUMNS - set(climate_df.columns)
    if missing:
        return pd.DataFrame(), []

    df = climate_df.copy()
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif {"year", "month", "day"}.issubset(df.columns):
        df["date"] = pd.to_datetime(df[["year", "month", "day"]], errors="coerce")
    else:
        df["date"] = pd.NaT

    if "location_id" in df.columns:
        df["location_key"] = df["location_id"].astype(str)
    else:
        df["location_key"] = df["location_name"].astype(str)

    df["location_name"] = df["location_name"].astype(str)
    df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE).fillna(df["location_name"])
    df["region_vn"] = df["region"].astype(str)
    df = df.dropna(subset=["year", "location_key"]).copy()
    df["year"] = df["year"].astype(int)

    regions = _selected_values(
        filters,
        ("selected_regions", "selected_region_keys", "selected_region", "region"),
    )
    if regions is not None:
        if not regions:
            return pd.DataFrame(), []
        df = df[df["region_vn"].isin(regions) | df["region"].isin(regions)]

    locations = _selected_values(
        filters,
        ("selected_reference_points", "selected_locations", "locations"),
    )
    if locations is not None:
        if not locations:
            return pd.DataFrame(), []
        df = df[
            df["location_name"].isin(locations)
            | df["location_vn"].isin(locations)
            | df["location_key"].isin(locations)
        ]

    bounds = _year_bounds(df, filters)
    if bounds is None:
        return pd.DataFrame(), []

    start_year, end_year = bounds
    selected_years = list(range(start_year, end_year + 1))
    df = df[df["year"].between(start_year, end_year)]
    return df.sort_values(["location_key", "date"]).reset_index(drop=True), selected_years


def create_location_year_grid(filtered_df: pd.DataFrame, selected_years: list[int]) -> pd.DataFrame:
    columns = ["location_key", "location_vn", "region_vn", "latitude", "longitude", "year"]
    if filtered_df.empty or not selected_years:
        return pd.DataFrame(columns=columns)

    location_columns = ["location_key", "location_vn", "region_vn", "latitude", "longitude"]
    locations = (
        filtered_df[location_columns]
        .sort_values(["region_vn", "location_vn", "location_key"])
        .drop_duplicates("location_key")
    )
    years = pd.DataFrame({"year": selected_years})
    return locations.merge(years, how="cross")[columns]


def _sum_by_location_year(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
    source_column: str,
    output_column: str,
) -> pd.DataFrame:
    if location_year_grid.empty:
        return location_year_grid.assign(**{output_column: pd.Series(dtype="float")})

    if source_column not in filtered_df.columns:
        result = location_year_grid.copy()
        result[output_column] = 0.0
        return result

    counts = (
        filtered_df.groupby(["location_key", "year"], as_index=False)[source_column]
        .sum(min_count=1)
        .rename(columns={source_column: output_column})
    )
    result = location_year_grid.merge(counts, on=["location_key", "year"], how="left")
    result[output_column] = pd.to_numeric(result[output_column], errors="coerce").fillna(0.0)
    return result


def _valid_event_ids(series: pd.Series) -> pd.Series:
    event_ids = series.astype("string").str.strip()
    invalid = event_ids.isna() | event_ids.str.lower().isin({"", "0", "0.0", "nan", "none", "nat"})
    return event_ids.mask(invalid)


def prepare_heatwave_event_table(filtered_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["location_key", "heatwave_event_id", "event_start_date", "year", "region_vn", "location_vn"]
    if filtered_df.empty or "heatwave_event_id" not in filtered_df.columns or "date" not in filtered_df.columns:
        return pd.DataFrame(columns=columns)

    events = filtered_df.dropna(subset=["location_key", "date"]).copy()
    events["_heatwave_event_id"] = _valid_event_ids(events["heatwave_event_id"])
    events = events.dropna(subset=["_heatwave_event_id"])
    if events.empty:
        return pd.DataFrame(columns=columns)

    event_table = (
        events.groupby(["location_key", "_heatwave_event_id"], as_index=False)
        .agg(
            event_start_date=("date", "min"),
            region_vn=("region_vn", "first"),
            location_vn=("location_vn", "first"),
        )
        .rename(columns={"_heatwave_event_id": "heatwave_event_id"})
    )
    event_table["year"] = event_table["event_start_date"].dt.year
    event_table = event_table.dropna(subset=["year"]).copy()
    event_table["year"] = event_table["year"].astype(int)
    return event_table[columns]


def prepare_dry_spell_event_table(filtered_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "location_key",
        "dry_spell_id",
        "dry_spell_length",
        "dry_spell_start",
        "dry_spell_end",
        "region_vn",
        "location_vn",
    ]
    if filtered_df.empty or "date" not in filtered_df.columns:
        return pd.DataFrame(columns=columns)

    df = filtered_df.dropna(subset=["location_key", "date"]).sort_values(["location_key", "date"]).copy()
    if "dry_day" in df.columns:
        df["is_dry"] = pd.to_numeric(df["dry_day"], errors="coerce").fillna(0).eq(1)
    elif "PRECTOTCORR" in df.columns:
        df["is_dry"] = pd.to_numeric(df["PRECTOTCORR"], errors="coerce").lt(1)
    else:
        return pd.DataFrame(columns=columns)

    previous_date = df.groupby("location_key")["date"].shift()
    previous_dry = df.groupby("location_key")["is_dry"].shift().fillna(False).astype(bool)
    date_gap = (df["date"] - previous_date).dt.days
    starts_spell = df["is_dry"] & (~previous_dry | date_gap.ne(1))
    df["dry_spell_id"] = starts_spell.groupby(df["location_key"]).cumsum()

    dry_rows = df[df["is_dry"]].copy()
    if dry_rows.empty:
        return pd.DataFrame(columns=columns)

    return dry_rows.groupby(["location_key", "dry_spell_id"], as_index=False).agg(
        dry_spell_length=("date", "size"),
        dry_spell_start=("date", "min"),
        dry_spell_end=("date", "max"),
        region_vn=("region_vn", "first"),
        location_vn=("location_vn", "first"),
    )[columns]


def _heatwave_grid(location_year_grid: pd.DataFrame, heatwave_events: pd.DataFrame) -> pd.DataFrame:
    if location_year_grid.empty:
        return location_year_grid.assign(heatwave_events=pd.Series(dtype="float"))

    if heatwave_events.empty:
        result = location_year_grid.copy()
        result["heatwave_events"] = 0.0
        return result

    counts = (
        heatwave_events.groupby(["location_key", "year"], as_index=False)
        .size()
        .rename(columns={"size": "heatwave_events"})
    )
    result = location_year_grid.merge(counts, on=["location_key", "year"], how="left")
    result["heatwave_events"] = pd.to_numeric(result["heatwave_events"], errors="coerce").fillna(0.0)
    return result


def _top_region_average_kpi(
    location_year_grid: pd.DataFrame,
    filtered_df: pd.DataFrame,
    source_column: str,
    output_column: str,
    label: str,
    unit: str,
) -> dict[str, str]:
    metric_grid = _sum_by_location_year(filtered_df, location_year_grid, source_column, output_column)
    if metric_grid.empty:
        return {"label": label, "value": f"0 {unit}", "subject": "Không có dữ liệu"}

    ranking = metric_grid.groupby("region_vn", as_index=False).agg(metric_value=(output_column, "mean"))
    if ranking.empty:
        return {"label": label, "value": f"0 {unit}", "subject": "Không có dữ liệu"}

    top_row = ranking.sort_values(["metric_value", "region_vn"], ascending=[False, True]).iloc[0]
    return {
        "label": label,
        "value": f"{_format_kpi_number(float(top_row['metric_value']))} {unit}",
        "subject": str(top_row["region_vn"]),
    }


def build_extreme_weather_kpis(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
    heatwave_events: pd.DataFrame,
    dry_spells: pd.DataFrame,
) -> list[dict[str, str]]:
    hot_kpi = _top_region_average_kpi(
        location_year_grid,
        filtered_df,
        "hot_day",
        "hot_days",
        "Số ngày nóng nhiều nhất",
        "ngày/năm",
    )
    rain_kpi = _top_region_average_kpi(
        location_year_grid,
        filtered_df,
        "heavy_rain_day",
        "heavy_rain_days",
        "Số ngày mưa lớn nhiều nhất",
        "ngày/năm",
    )

    if heatwave_events.empty:
        heatwave_kpi = {
            "label": "Số đợt nắng nóng nhiều nhất",
            "value": "0 đợt",
            "subject": "Không có dữ liệu",
        }
    else:
        ranking = (
            _heatwave_grid(location_year_grid, heatwave_events)
            .groupby("region_vn", as_index=False)
            .agg(metric_value=("heatwave_events", "mean"))
        )
        top_row = ranking.sort_values(["metric_value", "region_vn"], ascending=[False, True]).iloc[0]
        heatwave_kpi = {
            "label": "Số đợt nắng nóng nhiều nhất",
            "value": f"{_format_kpi_number(float(top_row['metric_value']))} đợt/năm",
            "subject": str(top_row["region_vn"]),
        }

    if dry_spells.empty:
        dry_kpi = {
            "label": "Chuỗi ngày khô dài nhất",
            "value": "0 ngày",
            "subject": "Không có dữ liệu",
        }
    else:
        top_dry = dry_spells.sort_values(
            ["dry_spell_length", "dry_spell_start", "location_vn"],
            ascending=[False, True, True],
        ).iloc[0]
        dry_kpi = {
            "label": "Chuỗi ngày khô dài nhất",
            "value": f"{int(top_dry['dry_spell_length'])} ngày",
            "subject": (
                f"{top_dry['location_vn']} · "
                f"{_format_year_span(top_dry['dry_spell_start'], top_dry['dry_spell_end'])}"
            ),
        }

    return [hot_kpi, rain_kpi, heatwave_kpi, dry_kpi]


def _active_regions(data: pd.DataFrame) -> list[str]:
    present = [str(region) for region in data.get("region_vn", pd.Series(dtype=str)).dropna().unique()]
    ordered = [region for region in REGION_ORDER if region in present]
    return ordered + [region for region in present if region not in ordered]


def _region_color(active_regions: list[str], legend: alt.Legend | None = None) -> alt.Color:
    return alt.Color(
        "region_vn:N",
        title="Vùng",
        scale=alt.Scale(
            domain=active_regions,
            range=[REGION_COLORS.get(region, SECONDARY) for region in active_regions],
        ),
        legend=legend,
    )


def _finish_chart(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(
            height=height,
            background=CARD,
            padding={"left": 10, "right": 10, "top": 10, "bottom": 10},
        )
        .configure_view(fill=CARD, stroke="transparent")
        .configure_axis(
            labelFont="Plus Jakarta Sans",
            titleFont="Plus Jakarta Sans",
            labelColor="#475569",
            titleColor=PRIMARY,
            labelFontSize=12,
            titleFontSize=13,
            gridColor="#F1F5F9",
            domainColor="#CBD5E1",
            tickColor="#CBD5E1",
        )
        .configure_legend(
            labelFont="Plus Jakarta Sans",
            titleFont="Plus Jakarta Sans",
            labelColor="#475569",
            titleColor=PRIMARY,
            labelLimit=240,
        )
    )


def create_hot_day_ranking_chart(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
) -> alt.Chart | None:
    if filtered_df.empty or location_year_grid.empty or "hot_day" not in filtered_df.columns:
        return None

    ranking = (
        _sum_by_location_year(filtered_df, location_year_grid, "hot_day", "hot_days")
        .groupby("region_vn", as_index=False)
        .agg(
            hot_day_avg=("hot_days", "mean"),
            location_count=("location_key", "nunique"),
        )
        .sort_values("hot_day_avg", ascending=False)
    )
    if ranking.empty:
        return None

    ranking["hot_day_label"] = ranking["hot_day_avg"].map(lambda value: f"{value:.1f}")
    region_sort = ranking["region_vn"].tolist()
    x_max = max(float(ranking["hot_day_avg"].max()) * 1.18, 1)
    base = alt.Chart(ranking).encode(
        x=alt.X(
            "hot_day_avg:Q",
            title="Ngày nắng nóng TB/năm/địa điểm",
            scale=alt.Scale(domain=[0, x_max]),
        ),
        y=alt.Y(
            "region_vn:N",
            title="Vùng",
            sort=region_sort,
            axis=alt.Axis(labelLimit=260),
        ),
        tooltip=[
            alt.Tooltip("region_vn:N", title="Vùng"),
            alt.Tooltip("hot_day_avg:Q", title="Ngày nắng nóng TB/năm", format=".1f"),
            alt.Tooltip("location_count:Q", title="Số địa điểm"),
        ],
    )
    chart = (
        base.mark_bar(color="#F59E0B", cornerRadiusEnd=3)
        + base.mark_text(align="left", baseline="middle", dx=5, color=PRIMARY).encode(
            text="hot_day_label:N"
        )
    )
    return _finish_chart(chart, COMPACT_CHART_HEIGHT)


def prepare_heavy_rain_location_data(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
) -> pd.DataFrame:
    if filtered_df.empty or location_year_grid.empty or "heavy_rain_day" not in filtered_df.columns:
        return pd.DataFrame()

    location_data = (
        _sum_by_location_year(filtered_df, location_year_grid, "heavy_rain_day", "heavy_rain_days")
        .groupby(["location_key", "location_vn", "region_vn", "latitude", "longitude"], dropna=False)
        .agg(heavy_rain_avg=("heavy_rain_days", "mean"))
        .reset_index()
        .dropna(subset=["latitude", "longitude"])
    )
    if location_data.empty:
        return location_data

    rain_values = location_data["heavy_rain_avg"].clip(lower=0)
    location_data["bubble_size"] = pd.cut(
        rain_values,
        bins=HEAVY_RAIN_BUBBLE_BINS,
        labels=HEAVY_RAIN_BUBBLE_LEVELS,
        include_lowest=True,
    ).astype(float)
    location_data["bubble_diameter"] = (
        location_data["bubble_size"]
        .map(HEAVY_RAIN_BUBBLE_SIZE_MAP)
        .fillna(HEAVY_RAIN_BUBBLE_DIAMETERS[0])
        .astype(float)
    )
    location_data["bubble_range"] = pd.cut(
        rain_values,
        bins=HEAVY_RAIN_BUBBLE_BINS,
        labels=HEAVY_RAIN_BUBBLE_LABELS,
        include_lowest=True,
    ).astype(str)
    location_data["heavy_rain_label"] = location_data["heavy_rain_avg"].map(lambda value: f"{value:.1f}")
    return location_data


def create_heavy_rain_map(location_data: pd.DataFrame, height: int = COMPACT_CHART_HEIGHT) -> Any | None:
    if location_data.empty:
        return None

    scatter_map = getattr(px, "scatter_map", None)
    map_kwargs = dict(
        data_frame=location_data,
        lat="latitude",
        lon="longitude",
        size="bubble_diameter",
        color="region_vn",
        color_discrete_map=REGION_COLORS,
        size_max=max(HEAVY_RAIN_BUBBLE_DIAMETERS),
        zoom=4,
        custom_data=["location_vn", "region_vn", "heavy_rain_avg", "bubble_range"],
    )
    if scatter_map is not None:
        fig = scatter_map(**map_kwargs, map_style="carto-positron")
        center, zoom = _map_center_and_zoom(location_data)
        fig.update_layout(map=dict(center=center, zoom=zoom))
    else:
        fig = px.scatter_mapbox(**map_kwargs, mapbox_style="carto-positron")
        center, zoom = _map_center_and_zoom(location_data)
        fig.update_layout(mapbox=dict(center=center, zoom=zoom))

    fig.update_traces(
        marker=dict(opacity=0.76, sizemode="diameter", sizeref=1),
        hovertemplate=(
            "Địa điểm: %{customdata[0]}<br>"
            "Vùng: %{customdata[1]}<br>"
            "Số ngày mưa lớn TB/năm: %{customdata[2]:.1f}<extra></extra>"
        ),
    )
    fig.update_layout(
        height=height,
        margin=dict(l=2, r=2, t=8, b=28),
        paper_bgcolor=CARD,
        showlegend=False,
    )
    return fig


def _map_center_and_zoom(location_data: pd.DataFrame) -> tuple[dict[str, float], float]:
    center = {
        "lat": float(location_data["latitude"].mean()),
        "lon": float(location_data["longitude"].mean()),
    }
    lat_span = float(location_data["latitude"].max() - location_data["latitude"].min())
    lon_span = float(location_data["longitude"].max() - location_data["longitude"].min())
    span = max(lat_span, lon_span)
    if span <= 0.5:
        zoom = 7.0
    elif span <= 1.5:
        zoom = 6.0
    elif span <= 3:
        zoom = 5.0
    elif span <= 6:
        zoom = 4.2
    else:
        zoom = 3.8
    return center, zoom


def _bubble_level_diameter(level: int) -> float:
    return HEAVY_RAIN_BUBBLE_SIZE_MAP[level]


def render_heavy_rain_map_legend(location_data: pd.DataFrame, height: int = COMPACT_CHART_HEIGHT) -> None:
    visible_regions = [region for region in REGION_ORDER if region in set(location_data["region_vn"])]
    region_rows = "\n".join(
        (
            '<div class="extreme-map-region-row">'
            f'<span class="extreme-map-region-dot" style="background: {REGION_COLORS.get(region, SECONDARY)};"></span>'
            f'<span class="extreme-map-region-label">{html.escape(REGION_LEGEND_LABELS.get(region, region))}</span>'
            "</div>"
        )
        for region in visible_regions
    )
    size_rows = "\n".join(
        (
            '<div class="extreme-map-size-row">'
            f'<span class="extreme-map-size-dot" style="width: {diameter:.1f}px; height: {diameter:.1f}px;"></span>'
            f'<span class="extreme-map-size-label">{html.escape(label)}</span>'
            "</div>"
        )
        for level, label in zip(HEAVY_RAIN_BUBBLE_LEVELS, HEAVY_RAIN_BUBBLE_LABELS)
        for diameter in [_bubble_level_diameter(level)]
    )
    st.markdown(
        (
            f'<div class="extreme-map-legend" style="min-height: {height}px;">'
            '<div class="extreme-map-legend-title">Vùng</div>'
            f"{region_rows}"
            '<div class="extreme-map-legend-break"></div>'
            '<div class="extreme-map-legend-title">Số ngày mưa lớn TB/năm</div>'
            f"{size_rows}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def dry_spell_ranking_height(dry_spells: pd.DataFrame) -> int:
    if dry_spells.empty:
        return COMPACT_CHART_HEIGHT

    ranking = dry_spells.dropna(subset=["location_vn", "dry_spell_length"]).copy()
    ranking["dry_spell_length"] = pd.to_numeric(ranking["dry_spell_length"], errors="coerce")
    ranking = ranking.dropna(subset=["dry_spell_length"])
    if ranking.empty:
        return COMPACT_CHART_HEIGHT

    row_count = (
        ranking.sort_values(
            ["location_vn", "dry_spell_length", "dry_spell_start"],
            ascending=[True, False, True],
        )
        .groupby("location_vn", as_index=False)
        .head(1)
        .shape[0]
    )
    return max(COMPACT_CHART_HEIGHT, 56 + row_count * DRY_SPELL_ROW_HEIGHT)


def _period_labels(years: pd.Series) -> pd.DataFrame:
    periods = pd.DataFrame({"year": years.astype(int)})
    periods["period_start"] = ((periods["year"] - 1991) // 5) * 5 + 1991
    periods["period_end"] = periods["period_start"] + 4
    periods["period_label"] = periods["period_start"].astype(str) + "-" + periods["period_end"].astype(str)
    return periods


def create_heatwave_heatmap(
    location_year_grid: pd.DataFrame,
    heatwave_events: pd.DataFrame,
    has_heatwave_event_id: bool,
) -> alt.Chart | None:
    if location_year_grid.empty or not has_heatwave_event_id:
        return None

    heatwave_grid = _heatwave_grid(location_year_grid, heatwave_events)
    heatwave_grid = heatwave_grid.merge(_period_labels(heatwave_grid["year"]), on="year", how="left")
    heatmap_data = heatwave_grid.groupby(["region_vn", "period_start", "period_label"], as_index=False).agg(
        heatwave_avg=("heatwave_events", "mean")
    )
    if heatmap_data.empty:
        return None

    period_order = (
        heatmap_data[["period_start", "period_label"]]
        .drop_duplicates()
        .sort_values("period_start")["period_label"]
        .tolist()
    )
    region_order = [region for region in REGION_ORDER if region in set(heatmap_data["region_vn"])]
    heatmap_data["heatwave_color_value"] = heatmap_data["heatwave_avg"].clip(
        lower=HEATWAVE_COLOR_DOMAIN[0],
        upper=HEATWAVE_COLOR_DOMAIN[-1],
    )
    heatmap_data["heatwave_label"] = heatmap_data["heatwave_avg"].map(lambda value: f"{value:.1f}")

    base = alt.Chart(heatmap_data).encode(
        x=alt.X(
            "period_label:O",
            title="Giai đoạn",
            sort=period_order,
            axis=alt.Axis(labelAngle=-25, labelOverlap=False, labelFlush=False),
        ),
        y=alt.Y(
            "region_vn:N",
            title="Vùng",
            sort=region_order,
            axis=alt.Axis(labelLimit=260),
        ),
        tooltip=[
            alt.Tooltip("region_vn:N", title="Vùng"),
            alt.Tooltip("period_label:O", title="Giai đoạn"),
            alt.Tooltip("heatwave_avg:Q", title="Số đợt nắng nóng TB", format=".1f"),
        ],
    )
    chart = (
        base.mark_rect().encode(
            color=alt.Color(
                "heatwave_color_value:Q",
                title="Số đợt",
                scale=alt.Scale(
                    domain=HEATWAVE_COLOR_DOMAIN,
                    range=HEATWAVE_COLOR_RANGE,
                    clamp=True,
                ),
                legend=alt.Legend(values=HEATWAVE_COLOR_DOMAIN),
            )
        )
        + base.mark_text(fontSize=11, fontWeight=600).encode(
            text="heatwave_label:N",
            color=alt.condition("datum.heatwave_avg >= 3", alt.value("#FFFFFF"), alt.value(PRIMARY)),
        )
    )
    return _finish_chart(chart, COMPACT_CHART_HEIGHT)


def create_dry_spell_ranking_chart(dry_spells: pd.DataFrame) -> alt.Chart | None:
    if dry_spells.empty:
        return None

    ranking = dry_spells.dropna(subset=["location_vn", "dry_spell_length"]).copy()
    ranking["dry_spell_length"] = pd.to_numeric(ranking["dry_spell_length"], errors="coerce")
    ranking = ranking.dropna(subset=["dry_spell_length"])
    if ranking.empty:
        return None

    ranking = (
        ranking.sort_values(
            ["location_vn", "dry_spell_length", "dry_spell_start"],
            ascending=[True, False, True],
        )
        .groupby("location_vn", as_index=False)
        .head(1)
        .sort_values("dry_spell_length", ascending=False)
        .sort_values("dry_spell_length", ascending=False)
    )
    ranking["zero"] = 0
    ranking["dry_spell_length"] = ranking["dry_spell_length"].round().astype(int)
    ranking["dry_spell_label"] = ranking["dry_spell_length"].astype(str)
    ranking["dry_spell_start_label"] = pd.to_datetime(
        ranking["dry_spell_start"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")
    ranking["dry_spell_end_label"] = pd.to_datetime(
        ranking["dry_spell_end"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

    location_sort = ranking["location_vn"].tolist()
    x_max = max(float(ranking["dry_spell_length"].max()) * 1.16, 1)
    base = alt.Chart(ranking).encode(
        y=alt.Y(
            "location_vn:N",
            title="Địa điểm",
            sort=location_sort,
            axis=alt.Axis(labelLimit=220, labelOverlap=False),
        ),
        tooltip=[
            alt.Tooltip("location_vn:N", title="Địa điểm"),
            alt.Tooltip("region_vn:N", title="Vùng"),
            alt.Tooltip("dry_spell_length:Q", title="Chuỗi ngày khô", format=".0f"),
            alt.Tooltip("dry_spell_start_label:N", title="Bắt đầu"),
            alt.Tooltip("dry_spell_end_label:N", title="Kết thúc"),
        ],
    )
    rules = base.mark_rule(strokeWidth=3).encode(
        x=alt.X("zero:Q", title="Chuỗi ngày khô dài nhất (ngày)", scale=alt.Scale(domain=[0, x_max])),
        x2="dry_spell_length:Q",
        color=alt.value("#C45A1A"),
    )
    points = base.mark_circle(size=72).encode(
        x="dry_spell_length:Q",
        color=alt.value("#C45A1A"),
    )
    labels = base.mark_text(align="left", baseline="middle", dx=6, color="#7C2D12", fontSize=11).encode(
        x="dry_spell_length:Q",
        text="dry_spell_label:N",
    )
    height = max(COMPACT_CHART_HEIGHT, 56 + len(ranking) * DRY_SPELL_ROW_HEIGHT)
    return _finish_chart(rules + points + labels, height)


def _split_kpi_value(value: str) -> tuple[str, str]:
    parts = value.split(" ", 1)
    if len(parts) == 1:
        return value, ""
    return parts[0], parts[1]


def render_kpi_card(label: str, value: str, subject: str) -> None:
    number, unit = _split_kpi_value(value)
    unit_html = f'<span class="kpi-unit">{html.escape(unit)}</span>' if unit else ""
    st.markdown(
        f"""
        <div class="metric-card overview-kpi-card">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="kpi-value-row">
                <span class="kpi-number">{html.escape(number)}</span>{unit_html}
            </div>
            <div class="overview-kpi-subject">{html.escape(subject)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chart_card(title: str, chart: alt.Chart | None, empty_message: str) -> None:
    st.markdown(f'<div class="extreme-chart-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if chart is None:
        st.info(empty_message)
    else:
        st.altair_chart(chart, use_container_width=True)


def render_heavy_rain_map_card(
    title: str,
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
    empty_message: str,
    height: int = COMPACT_CHART_HEIGHT,
) -> None:
    st.markdown(f'<div class="extreme-chart-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    location_data = prepare_heavy_rain_location_data(filtered_df, location_year_grid)
    figure = create_heavy_rain_map(location_data, height)
    if figure is None:
        st.info(empty_message)
    else:
        map_col, legend_col = st.columns([4.7, 1.35], gap="small")
        with map_col:
            st.plotly_chart(figure, use_container_width=True, config=PLOT_CONFIG)
        with legend_col:
            render_heavy_rain_map_legend(location_data, height)


def render_extreme_weather_tab(
    placeholder_box=None,
    climate_df: pd.DataFrame | None = None,
    filters: dict[str, Any] | None = None,
) -> None:
    inject_extreme_weather_css()
    filtered_df, selected_years = prepare_filtered_climate_data(climate_df, filters)
    if filtered_df.empty:
        st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
        return

    location_year_grid = create_location_year_grid(filtered_df, selected_years)
    heatwave_events = prepare_heatwave_event_table(filtered_df)
    dry_spells = prepare_dry_spell_event_table(filtered_df)
    kpi_items = build_extreme_weather_kpis(
        filtered_df,
        location_year_grid,
        heatwave_events,
        dry_spells,
    )

    row1 = st.columns(4)
    for col, kpi in zip(row1, kpi_items):
        with col:
            render_kpi_card(kpi["label"], kpi["value"], kpi["subject"])

    st.markdown('<div class="extreme-kpi-spacer"></div>', unsafe_allow_html=True)

    row2 = st.columns([1, 1])
    with row2[0]:
        render_chart_card(
            "Xếp hạng số ngày nắng nóng trung bình theo vùng (nhiệt độ ≥ 35°C)",
            create_hot_day_ranking_chart(filtered_df, location_year_grid),
            "Không đủ dữ liệu ngày nắng nóng.",
        )
    with row2[1]:
        render_chart_card(
            "Số đợt nắng nóng trung bình theo vùng và giai đoạn (≥ 3 ngày liên tiếp có nhiệt độ ≥ 35°C)",
            create_heatwave_heatmap(location_year_grid, heatwave_events, "heatwave_event_id" in filtered_df.columns),
            "Không đủ dữ liệu đợt nắng nóng.",
        )

    row3 = st.columns([1, 1])
    dry_chart_height = dry_spell_ranking_height(dry_spells)
    with row3[0]:
        render_heavy_rain_map_card(
            "Phân bố số ngày mưa lớn trung bình theo địa điểm (lượng mưa > 50 mm/ngày)",
            filtered_df,
            location_year_grid,
            "Không đủ dữ liệu mưa lớn hoặc tọa độ.",
            dry_chart_height,
        )
    with row3[1]:
        render_chart_card(
            "Xếp hạng chuỗi ngày khô dài nhất theo địa điểm (lượng mưa < 1 mm/ngày)",
            create_dry_spell_ranking_chart(dry_spells),
            "Không có chuỗi ngày khô phù hợp với bộ lọc hiện tại.",
        )
