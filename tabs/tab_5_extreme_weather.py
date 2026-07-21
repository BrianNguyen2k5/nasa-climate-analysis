from __future__ import annotations

import html
import math
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PRIMARY = "#1E3A5F"
SECONDARY = "#2A9D8F"
EXTREME = "#E76F51"
BORDER = "#E2E8F0"
MUTED = "#64748B"
CARD = "#FFFFFF"

ALL_REGIONS_LABEL = "Tất cả 7 nhóm vùng"
REGION_ORDER = [
    "Tây Bắc",
    "Đông Bắc",
    "Đồng bằng Bắc Bộ",
    "Bắc Trung Bộ",
    "Nam Trung Bộ",
    "Tây Nguyên",
    "Nam Bộ",
]
REGION_COLOR_MAP = {
    "Tây Bắc": "#4C78A8",
    "Đông Bắc": "#72B7B2",
    "Đồng bằng Bắc Bộ": "#54A24B",
    "Bắc Trung Bộ": "#ECA82C",
    "Nam Trung Bộ": "#F58518",
    "Tây Nguyên": "#B279A2",
    "Nam Bộ": "#E45756",
}
HEATMAP_SCALE = [
    [0.0, "#F8FAFC"],
    [0.25, "#DCEFEF"],
    [0.5, "#F4D7A1"],
    [0.75, "#F3A46B"],
    [1.0, "#D95F4F"],
]
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

LOCATION_ID_TO_REGION = {
    "DBP": "Tây Bắc",
    "LCA": "Đông Bắc",
    "HAN": "Đồng bằng Bắc Bộ",
    "HPH": "Đồng bằng Bắc Bộ",
    "VDH": "Bắc Trung Bộ",
    "VII": "Bắc Trung Bộ",
    "HUI": "Bắc Trung Bộ",
    "DAD": "Nam Trung Bộ",
    "UIH": "Nam Trung Bộ",
    "CXR": "Nam Trung Bộ",
    "PRT": "Nam Trung Bộ",
    "BMV": "Tây Nguyên",
    "PXU": "Tây Nguyên",
    "DLI": "Tây Nguyên",
    "SGN": "Nam Bộ",
    "VTG": "Nam Bộ",
    "VCA": "Nam Bộ",
    "CDO": "Nam Bộ",
    "CAH": "Nam Bộ",
    "PQC": "Nam Bộ",
}
RAW_REGION_TO_VI = {
    "North": "Đồng bằng Bắc Bộ",
    "North Central": "Bắc Trung Bộ",
    "Central": "Nam Trung Bộ",
    "South Central Coast": "Nam Trung Bộ",
    "Central Highlands": "Tây Nguyên",
    "Southeast": "Nam Bộ",
    "Mekong Delta": "Nam Bộ",
}
LOCATION_ID_TO_NAME = {
    "HAN": "Hà Nội",
    "LCA": "Lào Cai",
    "DBP": "Điện Biên",
    "HPH": "Hải Phòng",
    "VDH": "Đồng Hới",
    "VII": "Nghệ An",
    "HUI": "Huế",
    "DAD": "Đà Nẵng",
    "UIH": "Quy Nhơn",
    "CXR": "Nha Trang",
    "PRT": "Phan Rang - Tháp Chàm",
    "BMV": "Buôn Ma Thuột",
    "PXU": "Pleiku",
    "DLI": "Đà Lạt",
    "SGN": "TP. Hồ Chí Minh",
    "VTG": "Vũng Tàu",
    "VCA": "Cần Thơ",
    "CDO": "Châu Đốc",
    "CAH": "Cà Mau",
    "PQC": "Phú Quốc",
}
LOCATION_LABEL_TO_IDS = {
    "Hà Nội": ["HAN"],
    "Ha Noi": ["HAN"],
    "Lào Cai": ["LCA"],
    "Lao Cai": ["LCA"],
    "Điện Biên": ["DBP"],
    "Dien Bien Phu": ["DBP"],
    "Hải Phòng": ["HPH"],
    "Hai Phong": ["HPH"],
    "Đồng Hới": ["VDH"],
    "Dong Hoi": ["VDH"],
    "Nghệ An": ["VII"],
    "Vinh": ["VII"],
    "Huế": ["HUI"],
    "Hue": ["HUI"],
    "Đà Nẵng": ["DAD"],
    "Da Nang": ["DAD"],
    "Quy Nhơn": ["UIH"],
    "Quy Nhon": ["UIH"],
    "Nha Trang": ["CXR"],
    "Phan Rang - Tháp Chàm": ["PRT"],
    "Phan Rang-Thap Cham": ["PRT"],
    "Buôn Ma Thuột": ["BMV"],
    "Buon Ma Thuot": ["BMV"],
    "Pleiku": ["PXU"],
    "Đà Lạt": ["DLI"],
    "Da Lat": ["DLI"],
    "TP. Hồ Chí Minh": ["SGN"],
    "Ho Chi Minh City": ["SGN"],
    "Vũng Tàu": ["VTG"],
    "Vung Tau": ["VTG"],
    "Cần Thơ": ["VCA"],
    "Can Tho": ["VCA"],
    "Châu Đốc": ["CDO"],
    "Chau Doc": ["CDO"],
    "Cà Mau": ["CAH"],
    "Ca Mau": ["CAH"],
    "Phú Quốc": ["PQC"],
    "Phu Quoc": ["PQC"],
}
COLUMN_ALIASES = {
    "date": ["DATE", "datetime", "time"],
    "year": ["YEAR"],
    "month": ["MONTH"],
    "day": ["DAY"],
    "location_id": ["station_id", "site_id"],
    "location_name": ["station_name", "site_name", "name"],
    "region": ["climate_region", "zone"],
    "latitude": ["lat", "LATITUDE"],
    "longitude": ["lon", "lng", "LONGITUDE"],
    "T2M_MAX": ["t2m_max", "temperature_max", "temp_max"],
    "PRECTOTCORR": ["prectotcorr", "precipitation", "rainfall"],
    "hot_day": ["is_hot_day"],
    "heavy_rain_day": ["is_heavy_rain_day"],
    "dry_day": ["is_dry_day"],
    "dry_run_length": ["dry_spell_length"],
    "heatwave_event_id": ["heatwave_id", "heat_wave_event_id"],
    "heatwave_event_length": ["heatwave_length", "heat_wave_event_length"],
}
NUMERIC_COLUMNS = [
    "year",
    "month",
    "day",
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


def inject_extreme_weather_css() -> None:
    st.markdown(
        """
        <style>
            .extreme-kpi-card {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 7px;
                padding: 16px 18px;
                min-height: 112px;
                box-shadow: 0 1px 2px rgba(30, 58, 95, 0.04);
            }

            .extreme-kpi-label {
                color: #64748B;
                font-size: 0.8rem;
                font-weight: 680;
                margin-bottom: 9px;
            }

            .extreme-kpi-value {
                color: #1E3A5F;
                font-size: 1.86rem;
                font-weight: 760;
                line-height: 1.05;
                margin-bottom: 4px;
            }

            .extreme-kpi-unit {
                color: #64748B;
                font-size: 0.82rem;
                font-weight: 600;
            }

            .extreme-chart-title {
                color: #1E3A5F;
                font-size: 1rem;
                font-weight: 720;
                margin: 0 0 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_expected_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    lower_to_original = {column.lower(): column for column in df.columns}
    for target, aliases in COLUMN_ALIASES.items():
        if target in df.columns:
            continue
        for alias in aliases:
            source = lower_to_original.get(alias.lower())
            if source is not None:
                df[target] = df[source]
                break
    return df


def _selected_regions(filters: dict[str, Any] | None) -> list[str]:
    if not filters:
        return []
    value = filters.get("selected_regions", filters.get("selected_region"))
    if value is None or value == ALL_REGIONS_LABEL:
        return []
    if isinstance(value, str):
        return [value]
    return [region for region in value if region != ALL_REGIONS_LABEL]


def _selected_location_ids(filters: dict[str, Any] | None) -> list[str]:
    if not filters:
        return []
    selected_locations = filters.get("selected_locations", [])
    if isinstance(selected_locations, str):
        selected_locations = [selected_locations]

    location_ids: list[str] = []
    for location in selected_locations:
        location_ids.extend(LOCATION_LABEL_TO_IDS.get(location, []))
    return sorted(set(location_ids))


def _selected_years(df: pd.DataFrame, filters: dict[str, Any] | None) -> list[int]:
    available_years = pd.to_numeric(df.get("year"), errors="coerce").dropna()
    if available_years.empty:
        return []

    default_start = int(available_years.min())
    default_end = int(available_years.max())
    year_range = None if not filters else filters.get("selected_year_range")

    if isinstance(year_range, (tuple, list)) and len(year_range) == 2:
        start, end = sorted((int(year_range[0]), int(year_range[1])))
    else:
        start, end = default_start, default_end

    return list(range(start, end + 1))


def prepare_filtered_climate_data(
    climate_df: pd.DataFrame | None,
    filters: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, list[int]]:
    if climate_df is None or climate_df.empty:
        return pd.DataFrame(), []

    df = _ensure_expected_columns(climate_df)
    if "location_id" not in df.columns:
        return pd.DataFrame(), []

    if "location_name" in df.columns:
        df["raw_location_name"] = df["location_name"]
    else:
        df["location_name"] = df["location_id"]
        df["raw_location_name"] = df["location_id"]

    if "region" not in df.columns:
        df["region"] = pd.NA

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif {"year", "month", "day"}.issubset(df.columns):
        df["date"] = pd.to_datetime(
            {
                "year": df["year"],
                "month": df["month"],
                "day": df["day"],
            },
            errors="coerce",
        )
    else:
        df["date"] = pd.NaT

    if "year" not in df.columns or df["year"].isna().all():
        df["year"] = df["date"].dt.year

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["location_id", "year"]).copy()
    df["year"] = df["year"].astype(int)
    df["location_id"] = df["location_id"].astype(str)

    df["region"] = (
        df["location_id"]
        .map(LOCATION_ID_TO_REGION)
        .fillna(df["region"].map(RAW_REGION_TO_VI))
        .fillna(df["region"])
    )
    df["location_name"] = df["location_id"].map(LOCATION_ID_TO_NAME).fillna(df["location_name"])

    regions = _selected_regions(filters)
    if regions:
        df = df[df["region"].isin(regions)]

    location_ids = _selected_location_ids(filters)
    if location_ids:
        df = df[df["location_id"].isin(location_ids)]
    elif filters and filters.get("selected_locations"):
        df = df.iloc[0:0]

    years = _selected_years(df, filters)
    if years:
        df = df[df["year"].isin(years)]

    sort_columns = [column for column in ["location_id", "date"] if column in df.columns]
    if sort_columns:
        df = df.sort_values(sort_columns)

    return df.reset_index(drop=True), years


def create_location_year_grid(filtered_df: pd.DataFrame, selected_years: list[int]) -> pd.DataFrame:
    grid_columns = ["location_id", "location_name", "region", "latitude", "longitude", "year"]
    if filtered_df.empty or not selected_years:
        return pd.DataFrame(columns=grid_columns)

    location_columns = ["location_id", "location_name", "region", "latitude", "longitude"]
    available_columns = [column for column in location_columns if column in filtered_df.columns]
    locations = (
        filtered_df[available_columns]
        .sort_values(["region", "location_name", "location_id"])
        .drop_duplicates("location_id")
        .copy()
    )
    if locations.empty:
        return pd.DataFrame(columns=grid_columns)

    years = pd.DataFrame({"year": sorted(set(int(year) for year in selected_years))})
    locations["_join_key"] = 1
    years["_join_key"] = 1
    grid = locations.merge(years, on="_join_key", how="inner").drop(columns="_join_key")
    return grid[grid_columns]


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
        filtered_df.groupby(["location_id", "year"], as_index=False)[source_column]
        .sum(min_count=1)
        .rename(columns={source_column: output_column})
    )
    result = location_year_grid.merge(counts, on=["location_id", "year"], how="left")
    result[output_column] = pd.to_numeric(result[output_column], errors="coerce").fillna(0.0)
    return result


def _valid_heatwave_event_ids(series: pd.Series) -> pd.Series:
    event_ids = series.astype("string").str.strip()
    invalid = event_ids.isna() | event_ids.str.lower().isin({"", "0", "0.0", "nan", "none", "nat"})
    return event_ids.mask(invalid)


def prepare_heatwave_event_table(filtered_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["location_id", "heatwave_event_id", "event_start_date", "year", "region", "location_name"]
    if filtered_df.empty or "heatwave_event_id" not in filtered_df.columns or "date" not in filtered_df.columns:
        return pd.DataFrame(columns=columns)

    events = filtered_df.dropna(subset=["location_id", "date"]).copy()
    events["_heatwave_event_id"] = _valid_heatwave_event_ids(events["heatwave_event_id"])
    events = events.dropna(subset=["_heatwave_event_id"])
    if events.empty:
        return pd.DataFrame(columns=columns)

    event_table = (
        events.groupby(["location_id", "_heatwave_event_id"], as_index=False)
        .agg(
            event_start_date=("date", "min"),
            region=("region", "first"),
            location_name=("location_name", "first"),
        )
        .rename(columns={"_heatwave_event_id": "heatwave_event_id"})
    )
    event_table["year"] = event_table["event_start_date"].dt.year
    event_table = event_table.dropna(subset=["year"]).copy()
    event_table["year"] = event_table["year"].astype(int)
    return event_table[columns]


def prepare_dry_spell_event_table(filtered_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["location_id", "dry_spell_id", "dry_spell_length", "region", "location_name"]
    if filtered_df.empty or "date" not in filtered_df.columns or "location_id" not in filtered_df.columns:
        return pd.DataFrame(columns=columns)

    df = filtered_df.dropna(subset=["location_id", "date"]).sort_values(["location_id", "date"]).copy()
    if "dry_day" in df.columns:
        df["is_dry"] = pd.to_numeric(df["dry_day"], errors="coerce").fillna(0).eq(1)
    elif "PRECTOTCORR" in df.columns:
        df["is_dry"] = pd.to_numeric(df["PRECTOTCORR"], errors="coerce").lt(1)
    else:
        return pd.DataFrame(columns=columns)

    previous_date = df.groupby("location_id")["date"].shift()
    previous_dry = df.groupby("location_id")["is_dry"].shift().fillna(False).astype(bool)
    date_gap = (df["date"] - previous_date).dt.days
    new_spell = df["is_dry"] & (~previous_dry | date_gap.ne(1))
    df["dry_spell_id"] = new_spell.groupby(df["location_id"]).cumsum()

    dry_rows = df[df["is_dry"]].copy()
    if dry_rows.empty:
        return pd.DataFrame(columns=columns)

    spell_table = dry_rows.groupby(["location_id", "dry_spell_id"], as_index=False).agg(
        dry_spell_length=("date", "size"),
        region=("region", "first"),
        location_name=("location_name", "first"),
    )
    return spell_table[columns]


def calculate_extreme_weather_kpis(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
    heatwave_events: pd.DataFrame,
    dry_spells: pd.DataFrame,
) -> dict[str, float | int]:
    hot_grid = _sum_by_location_year(filtered_df, location_year_grid, "hot_day", "hot_days")
    rain_grid = _sum_by_location_year(filtered_df, location_year_grid, "heavy_rain_day", "heavy_rain_days")

    if location_year_grid.empty:
        heatwave_grid = location_year_grid.assign(heatwave_events=[])
    else:
        heatwave_counts = heatwave_events.groupby(["location_id", "year"], as_index=False).size()
        heatwave_counts = heatwave_counts.rename(columns={"size": "heatwave_events"})
        heatwave_grid = location_year_grid.merge(heatwave_counts, on=["location_id", "year"], how="left")
        heatwave_grid["heatwave_events"] = (
            pd.to_numeric(heatwave_grid["heatwave_events"], errors="coerce").fillna(0.0)
        )

    longest_dry_spell = 0 if dry_spells.empty else int(dry_spells["dry_spell_length"].max())
    return {
        "hot_days_avg": round(float(hot_grid["hot_days"].mean()), 1) if not hot_grid.empty else 0.0,
        "heavy_rain_days_avg": round(float(rain_grid["heavy_rain_days"].mean()), 1) if not rain_grid.empty else 0.0,
        "heatwave_events_avg": round(float(heatwave_grid["heatwave_events"].mean()), 1)
        if not heatwave_grid.empty
        else 0.0,
        "longest_dry_spell": longest_dry_spell,
    }


def _base_chart_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=18, t=8, b=36),
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font=dict(color="#1F2937", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
            bgcolor="rgba(255,255,255,0)",
        ),
    )
    return fig


def create_hot_day_ranking_chart(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
) -> go.Figure | None:
    if filtered_df.empty or location_year_grid.empty or "hot_day" not in filtered_df.columns:
        return None

    hot_grid = _sum_by_location_year(filtered_df, location_year_grid, "hot_day", "hot_days")
    ranking = (
        hot_grid.groupby("region", as_index=False)
        .agg(
            hot_day_avg=("hot_days", "mean"),
            location_count=("location_id", "nunique"),
        )
        .sort_values("hot_day_avg", ascending=True)
    )
    if ranking.empty:
        return None

    ranking["hot_day_label"] = ranking["hot_day_avg"].map(lambda value: f"{value:.1f}")
    fig = px.bar(
        ranking,
        x="hot_day_avg",
        y="region",
        orientation="h",
        color="region",
        color_discrete_map=REGION_COLOR_MAP,
        text="hot_day_label",
        custom_data=["region", "hot_day_avg", "location_count"],
        labels={"hot_day_avg": "Ngày nắng nóng TB/năm/địa điểm", "region": ""},
    )
    fig.update_traces(
        textposition="outside",
        texttemplate="%{text}",
        cliponaxis=False,
        hovertemplate=(
            "Nhóm vùng: %{customdata[0]}<br>"
            "Ngày nắng nóng trung bình/năm: %{customdata[1]:.1f}<br>"
            "Số địa điểm đang được tính: %{customdata[2]}<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, bargap=0.28)
    fig.update_xaxes(rangemode="tozero", gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=ranking["region"].tolist(),
        title="",
        ticks="",
    )
    max_value = float(ranking["hot_day_avg"].max())
    if max_value > 0:
        fig.update_xaxes(range=[0, max_value * 1.18])
    return _base_chart_layout(fig, 390)


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


def create_heavy_rain_bubble_map(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
) -> go.Figure | None:
    if filtered_df.empty or location_year_grid.empty or "heavy_rain_day" not in filtered_df.columns:
        return None

    rain_grid = _sum_by_location_year(filtered_df, location_year_grid, "heavy_rain_day", "heavy_rain_days")
    location_data = (
        rain_grid.groupby(["location_id", "location_name", "region", "latitude", "longitude"], dropna=False)
        .agg(heavy_rain_avg=("heavy_rain_days", "mean"))
        .reset_index()
        .dropna(subset=["latitude", "longitude"])
    )
    if location_data.empty:
        return None

    max_value = float(location_data["heavy_rain_avg"].max())
    if max_value <= 0:
        location_data["bubble_size"] = 1.0
    else:
        location_data["bubble_size"] = location_data["heavy_rain_avg"].clip(lower=max_value * 0.08)

    scatter_map = getattr(px, "scatter_map", None)
    if scatter_map is not None:
        fig = scatter_map(
            location_data,
            lat="latitude",
            lon="longitude",
            size="bubble_size",
            color="region",
            color_discrete_map=REGION_COLOR_MAP,
            size_max=26,
            zoom=4,
            map_style="carto-positron",
            custom_data=["location_name", "region", "heavy_rain_avg"],
        )
        center, zoom = _map_center_and_zoom(location_data)
        fig.update_layout(map=dict(center=center, zoom=zoom))
    else:
        fig = px.scatter_mapbox(
            location_data,
            lat="latitude",
            lon="longitude",
            size="bubble_size",
            color="region",
            color_discrete_map=REGION_COLOR_MAP,
            size_max=26,
            zoom=4,
            mapbox_style="carto-positron",
            custom_data=["location_name", "region", "heavy_rain_avg"],
        )
        center, zoom = _map_center_and_zoom(location_data)
        fig.update_layout(mapbox=dict(center=center, zoom=zoom))

    fig.update_traces(
        marker=dict(opacity=0.76),
        hovertemplate=(
            "Địa điểm: %{customdata[0]}<br>"
            "Nhóm vùng: %{customdata[1]}<br>"
            "Số ngày mưa lớn trung bình/năm: %{customdata[2]:.1f}<extra></extra>"
        ),
    )
    return _base_chart_layout(fig, 390)


def _period_labels(years: pd.Series) -> pd.DataFrame:
    periods = pd.DataFrame({"year": years.astype(int)})
    periods["period_start"] = ((periods["year"] - 1991) // 5) * 5 + 1991
    periods["period_end"] = periods["period_start"] + 4
    periods["period_label"] = (
        periods["period_start"].astype(str) + "–" + periods["period_end"].astype(str)
    )
    return periods


def create_heatwave_heatmap(
    location_year_grid: pd.DataFrame,
    heatwave_events: pd.DataFrame,
    has_heatwave_event_id: bool,
) -> go.Figure | None:
    if location_year_grid.empty or not has_heatwave_event_id:
        return None

    heatwave_counts = heatwave_events.groupby(["location_id", "year"], as_index=False).size()
    heatwave_counts = heatwave_counts.rename(columns={"size": "heatwave_events"})
    heatwave_grid = location_year_grid.merge(heatwave_counts, on=["location_id", "year"], how="left")
    heatwave_grid["heatwave_events"] = (
        pd.to_numeric(heatwave_grid["heatwave_events"], errors="coerce").fillna(0.0)
    )
    heatwave_grid = heatwave_grid.merge(_period_labels(heatwave_grid["year"]), on="year", how="left")
    if heatwave_grid.empty:
        return None

    heatmap_data = heatwave_grid.groupby(["region", "period_start", "period_label"], as_index=False).agg(
        heatwave_avg=("heatwave_events", "mean")
    )
    period_order = (
        heatmap_data[["period_start", "period_label"]]
        .drop_duplicates()
        .sort_values("period_start")["period_label"]
        .tolist()
    )
    region_order = [region for region in REGION_ORDER if region in set(heatmap_data["region"])]
    pivot = (
        heatmap_data.pivot(index="region", columns="period_label", values="heatwave_avg")
        .reindex(index=region_order, columns=period_order)
        .fillna(0.0)
    )
    if pivot.empty:
        return None

    z_values = pivot.round(1).to_numpy()
    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=HEATMAP_SCALE,
            colorbar=dict(title="Số đợt", thickness=12),
            text=z_values,
            texttemplate="%{text:.1f}",
            hovertemplate=(
                "Nhóm vùng: %{y}<br>"
                "Giai đoạn: %{x}<br>"
                "Số đợt nắng nóng trung bình: %{z:.1f}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(side="bottom", ticks="", gridcolor=CARD)
    fig.update_yaxes(ticks="", gridcolor=CARD)
    return _base_chart_layout(fig, 390)


def create_dry_spell_histogram(dry_spells: pd.DataFrame) -> go.Figure | None:
    if dry_spells.empty:
        return None

    event_count = len(dry_spells)
    nbins = min(30, max(10, round(math.sqrt(event_count))))
    fig = px.histogram(
        dry_spells,
        x="dry_spell_length",
        nbins=nbins,
        color_discrete_sequence=[SECONDARY],
        labels={
            "dry_spell_length": "Độ dài chuỗi ngày khô (ngày)",
            "count": "Số chuỗi",
        },
    )
    fig.update_traces(
        marker=dict(line=dict(width=0.8, color="#FFFFFF")),
        hovertemplate="Khoảng độ dài: %{x}<br>Số chuỗi: %{y}<extra></extra>",
    )
    fig.update_layout(bargap=0.06, showlegend=False)
    fig.update_xaxes(title="Độ dài chuỗi ngày khô (ngày)", gridcolor=BORDER, rangemode="tozero")
    fig.update_yaxes(title="Số chuỗi", gridcolor=BORDER, rangemode="tozero")
    return _base_chart_layout(fig, 390)


def render_kpi_card(label: str, value: str, unit: str) -> None:
    st.markdown(
        f"""
        <div class="extreme-kpi-card">
            <div class="extreme-kpi-label">{html.escape(label)}</div>
            <div class="extreme-kpi-value">{html.escape(value)}</div>
            <div class="extreme-kpi-unit">{html.escape(unit)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chart_card(title: str, figure: go.Figure | None, empty_message: str) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="extreme-chart-title">{html.escape(title)}</div>', unsafe_allow_html=True)
        if figure is None:
            st.info(empty_message)
        else:
            st.plotly_chart(figure, use_container_width=True, config=PLOT_CONFIG)


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
    kpis = calculate_extreme_weather_kpis(
        filtered_df,
        location_year_grid,
        heatwave_events,
        dry_spells,
    )

    row1 = st.columns(4)
    with row1[0]:
        render_kpi_card("Ngày nắng nóng TB/năm", f"{kpis['hot_days_avg']:.1f}", "ngày")
    with row1[1]:
        render_kpi_card("Ngày mưa lớn TB/năm", f"{kpis['heavy_rain_days_avg']:.1f}", "ngày")
    with row1[2]:
        render_kpi_card("Đợt nắng nóng TB/năm", f"{kpis['heatwave_events_avg']:.1f}", "đợt")
    with row1[3]:
        render_kpi_card("Chuỗi ngày khô dài nhất", f"{kpis['longest_dry_spell']}", "ngày")

    st.write("")
    row2 = st.columns([1, 1])
    with row2[0]:
        render_chart_card(
            "Xếp hạng số ngày nắng nóng theo vùng",
            create_hot_day_ranking_chart(filtered_df, location_year_grid),
            "Không đủ dữ liệu ngày nắng nóng.",
        )
    with row2[1]:
        render_chart_card(
            "Phân bố số ngày mưa lớn theo địa điểm",
            create_heavy_rain_bubble_map(filtered_df, location_year_grid),
            "Không đủ dữ liệu mưa lớn hoặc tọa độ.",
        )

    row3 = st.columns([1, 1])
    with row3[0]:
        render_chart_card(
            "Số đợt nắng nóng theo vùng và giai đoạn",
            create_heatwave_heatmap(location_year_grid, heatwave_events, "heatwave_event_id" in filtered_df.columns),
            "Không đủ dữ liệu đợt nắng nóng.",
        )
    with row3[1]:
        render_chart_card(
            "Phân bố độ dài chuỗi ngày khô",
            create_dry_spell_histogram(dry_spells),
            "Không đủ dữ liệu chuỗi ngày khô.",
        )
