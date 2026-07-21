from __future__ import annotations

import html
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

ALL_REGIONS_LABEL = "Tất cả 6 nhóm vùng"
REGION_ORDER = [
    "Bắc Trung Bộ",
    "Nam Trung Bộ",
    "Trung du và miền núi phía Bắc",
    "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long",
    "Đồng bằng sông Hồng",
]
REGION_COLOR_MAP = {
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
    "Trung du và miền núi phía Bắc": "Trung du và miền núi phía Bắc",
}
HEATMAP_SCALE = [
    [0.0, "#FFF7DA"],
    [0.25, "#FDE7A6"],
    [0.5, "#FDBA74"],
    [0.75, "#FB7185"],
    [1.0, "#E11D48"],
]
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}
COMPACT_CHART_HEIGHT = 305
HEAVY_RAIN_BUBBLE_BINS = [-0.01, 2, 4, 6, 8, float("inf")]
HEAVY_RAIN_BUBBLE_LABELS = ["0-2 ngày", "2-4 ngày", "4-6 ngày", "6-8 ngày", ">8 ngày"]
HEAVY_RAIN_BUBBLE_LEVELS = [1, 2, 3, 4, 5]

LOCATION_ID_TO_REGION = {
    "DBP": "Trung du và miền núi phía Bắc",
    "LCA": "Trung du và miền núi phía Bắc",
    "HAN": "Đồng bằng sông Hồng",
    "HPH": "Đồng bằng sông Hồng",
    "VDH": "Bắc Trung Bộ",
    "VII": "Bắc Trung Bộ",
    "HUI": "Bắc Trung Bộ",
    "DAD": "Nam Trung Bộ",
    "UIH": "Nam Trung Bộ",
    "CXR": "Nam Trung Bộ",
    "PRT": "Nam Trung Bộ",
    "BMV": "Nam Trung Bộ",
    "PXU": "Nam Trung Bộ",
    "DLI": "Nam Trung Bộ",
    "SGN": "Đông Nam Bộ",
    "VTG": "Đông Nam Bộ",
    "VCA": "Đồng bằng sông Cửu Long",
    "CDO": "Đồng bằng sông Cửu Long",
    "CAH": "Đồng bằng sông Cửu Long",
    "PQC": "Đồng bằng sông Cửu Long",
}
RAW_REGION_TO_VI = {
    "Bắc Trung Bộ": "Bắc Trung Bộ",
    "Nam Trung Bộ": "Nam Trung Bộ",
    "Trung du và miền núi phía Bắc": "Trung du và miền núi phía Bắc",
    "Đông Nam Bộ": "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long": "Đồng bằng sông Cửu Long",
    "Đồng bằng sông Hồng": "Đồng bằng sông Hồng",
    "North": "Đồng bằng sông Hồng",
    "North Central": "Bắc Trung Bộ",
    "Central": "Nam Trung Bộ",
    "South Central Coast": "Nam Trung Bộ",
    "Central Highlands": "Nam Trung Bộ",
    "Southeast": "Đông Nam Bộ",
    "Mekong Delta": "Đồng bằng sông Cửu Long",
}
LOCATION_ID_TO_NAME = {
    "HAN": "Hà Nội",
    "LCA": "Lào Cai",
    "DBP": "Điện Biên Phủ",
    "HPH": "Hải Phòng",
    "VDH": "Đồng Hới",
    "VII": "Vinh",
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
    "Điện Biên Phủ": ["DBP"],
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
            .block-container [data-testid="stVerticalBlock"] {
                gap: 1rem !important;
            }

            /* Removed .white-card-marker and wrapper css because we will render charts directly */

            .extreme-kpi-card {
                min-height: 112px;
                background: #FFFFFF;
                border: 1px solid rgba(226, 232, 240, 0.95);
                border-radius: 8px;
                box-shadow: 0 10px 24px rgba(30, 58, 95, 0.07);
                padding: 16px 22px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                box-sizing: border-box;
                margin-bottom: 0.35rem;
            }

            .extreme-kpi-content {
                min-width: 0;
            }

            .extreme-kpi-label {
                font-size: 0.92rem;
                font-weight: 760;
                line-height: 1.25;
                margin-bottom: 18px;
                white-space: nowrap;
            }

            .extreme-kpi-value-row {
                display: flex;
                align-items: baseline;
                gap: 7px;
                white-space: nowrap;
            }

            .extreme-kpi-value {
                font-size: 2rem;
                font-weight: 800;
                letter-spacing: 0;
                line-height: 1;
            }

            .extreme-kpi-unit {
                color: #1E3A5F;
                font-size: 0.88rem;
                font-weight: 700;
            }

            .extreme-kpi-icon {
                width: 54px;
                height: 54px;
                border-radius: 999px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex: 0 0 auto;
            }

            .extreme-kpi-icon .material-symbols-rounded {
                font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
                font-size: 31px;
                font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 36;
            }

            .extreme-kpi-spacer {
                height: 0.75rem;
            }

            .extreme-chart-title {
                color: #1E3A5F;
                font-size: 15px;
                font-weight: 750;
                line-height: 1.25;
                margin: 8px 0 6px 0;
                white-space: normal;
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
                padding: 12px 16px;
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
                margin: 0 0 6px;
            }

            .extreme-map-region-row,
            .extreme-map-size-row {
                display: grid;
                align-items: center;
                column-gap: 8px;
                margin-bottom: 3px;
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
                line-height: 1.1;
                white-space: normal;
            }

            .extreme-map-legend-break {
                height: 3px;
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

    value = (
        filters.get("selected_regions")
        or filters.get("selected_region_keys")
        or filters.get("selected_region")
        or filters.get("region")
    )
    if value is None:
        return []
    if isinstance(value, str):
        if value == ALL_REGIONS_LABEL or value.startswith("Tất cả"):
            return []
        return [value]
    return [region for region in value if region and not str(region).startswith("Tất cả")]


def _filter_has_region_selection(filters: dict[str, Any] | None) -> bool:
    return bool(
        filters
        and any(key in filters for key in ("selected_regions", "selected_region_keys", "selected_region", "region"))
    )


def _selected_location_ids(filters: dict[str, Any] | None) -> list[str]:
    if not filters:
        return []

    selected_locations = (
        filters.get("selected_reference_points")
        or filters.get("selected_locations")
        or filters.get("locations")
        or []
    )
    if isinstance(selected_locations, str):
        selected_locations = [selected_locations]

    location_ids: list[str] = []
    for location in selected_locations:
        location_ids.extend(LOCATION_LABEL_TO_IDS.get(location, []))
    return sorted(set(location_ids))


def _filter_has_location_selection(filters: dict[str, Any] | None) -> bool:
    return bool(
        filters
        and any(key in filters for key in ("selected_reference_points", "selected_locations", "locations"))
    )


def _selected_years(df: pd.DataFrame, filters: dict[str, Any] | None) -> list[int]:
    available_years = pd.to_numeric(df.get("year"), errors="coerce").dropna()
    if available_years.empty:
        return []

    default_start = int(available_years.min())
    default_end = int(available_years.max())
    year_range = None if not filters else (
        filters.get("year_range")
        or filters.get("selected_year_range")
        or filters.get("period")
    )

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
    elif _filter_has_region_selection(filters) and (
        filters.get("selected_regions") == [] or filters.get("selected_region_keys") == []
    ):
        df = df.iloc[0:0]

    location_ids = _selected_location_ids(filters)
    if location_ids:
        df = df[df["location_id"].isin(location_ids)]
    elif _filter_has_location_selection(filters) and (
        filters.get("selected_reference_points") == []
        or filters.get("selected_locations") == []
        or filters.get("locations") == []
    ):
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
    columns = [
        "location_id",
        "dry_spell_id",
        "dry_spell_length",
        "dry_spell_start",
        "dry_spell_end",
        "region",
        "location_name",
    ]
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
        dry_spell_start=("date", "min"),
        dry_spell_end=("date", "max"),
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


def _format_kpi_number(value: float) -> str:
    rounded = round(float(value), 1)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.1f}".replace(".", ",")


def _format_year_span(start_date: Any, end_date: Any) -> str:
    start_year = pd.to_datetime(start_date, errors="coerce")
    end_year = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start_year) and pd.isna(end_year):
        return "Không rõ năm"
    if pd.isna(end_year):
        return str(int(start_year.year))
    if pd.isna(start_year):
        return str(int(end_year.year))
    if start_year.year == end_year.year:
        return str(int(start_year.year))
    return f"{int(start_year.year)}–{int(end_year.year)}"


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

    ranking = metric_grid.dropna(subset=["region"]).copy()
    ranking[output_column] = pd.to_numeric(ranking[output_column], errors="coerce").fillna(0.0)
    ranking = ranking.groupby("region", as_index=False).agg(metric_value=(output_column, "mean"))
    if ranking.empty:
        return {"label": label, "value": f"0 {unit}", "subject": "Không có dữ liệu"}

    top_row = ranking.sort_values(
        ["metric_value", "region"],
        ascending=[False, True],
    ).iloc[0]
    return {
        "label": label,
        "value": f"{_format_kpi_number(float(top_row['metric_value']))} {unit}",
        "subject": str(top_row["region"]),
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
            "label": "Số đợt nắng nóng nhiều nhất/năm",
            "value": "0 đợt",
            "subject": "Không có dữ liệu",
        }
    else:
        heatwave_counts = (
            heatwave_events.groupby(["location_id", "year"], as_index=False)
            .size()
            .rename(columns={"size": "heatwave_events"})
        )
        heatwave_grid = location_year_grid.merge(heatwave_counts, on=["location_id", "year"], how="left")
        heatwave_grid["heatwave_events"] = pd.to_numeric(
            heatwave_grid["heatwave_events"], errors="coerce"
        ).fillna(0.0)
        heatwave_ranking = heatwave_grid.dropna(subset=["region"]).groupby("region", as_index=False).agg(
            metric_value=("heatwave_events", "mean")
        )
        top_heatwave = heatwave_ranking.sort_values(
            ["metric_value", "region"],
            ascending=[False, True],
        ).iloc[0]
        heatwave_kpi = {
            "label": "Số đợt nắng nóng nhiều nhất",
            "value": f"{_format_kpi_number(float(top_heatwave['metric_value']))} đợt/năm",
            "subject": str(top_heatwave["region"]),
        }

    if dry_spells.empty:
        dry_kpi = {
            "label": "Chuỗi ngày khô dài nhất",
            "value": "0 ngày",
            "subject": "Không có dữ liệu",
        }
    else:
        dry_ranking = dry_spells.copy()
        dry_ranking["dry_spell_length"] = pd.to_numeric(
            dry_ranking["dry_spell_length"], errors="coerce"
        ).fillna(0.0)
        top_dry = dry_ranking.sort_values(
            ["dry_spell_length", "dry_spell_start", "location_name"],
            ascending=[False, True, True],
        ).iloc[0]
        dry_kpi = {
            "label": "Chuỗi ngày khô dài nhất",
            "value": f"{int(round(float(top_dry['dry_spell_length'])))} ngày",
            "subject": (
                f"{top_dry['location_name']} · "
                f"{_format_year_span(top_dry['dry_spell_start'], top_dry['dry_spell_end'])}"
            ),
        }

    return [hot_kpi, rain_kpi, heatwave_kpi, dry_kpi]


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
        color_discrete_sequence=["#F59E0B"],
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
    fig.update_xaxes(
        title="Ngày nắng nóng TB/năm/địa điểm",
        rangemode="tozero",
        gridcolor=BORDER,
        zerolinecolor=BORDER,
        automargin=True,
    )
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=ranking["region"].tolist(),
        title="Nhóm vùng",
        ticks="",
        automargin=True,
    )
    max_value = float(ranking["hot_day_avg"].max())
    if max_value > 0:
        fig.update_xaxes(range=[0, max_value * 1.18])
    return _base_chart_layout(fig, COMPACT_CHART_HEIGHT)


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


def prepare_heavy_rain_location_data(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
) -> pd.DataFrame:
    if filtered_df.empty or location_year_grid.empty or "heavy_rain_day" not in filtered_df.columns:
        return pd.DataFrame()

    rain_grid = _sum_by_location_year(filtered_df, location_year_grid, "heavy_rain_day", "heavy_rain_days")
    location_data = (
        rain_grid.groupby(["location_id", "location_name", "region", "latitude", "longitude"], dropna=False)
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
    location_data["bubble_range"] = pd.cut(
        rain_values,
        bins=HEAVY_RAIN_BUBBLE_BINS,
        labels=HEAVY_RAIN_BUBBLE_LABELS,
        include_lowest=True,
    ).astype(str)
    return location_data


def create_heavy_rain_bubble_map_from_location_data(location_data: pd.DataFrame) -> go.Figure | None:
    if location_data.empty:
        return None

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
            custom_data=["location_name", "region", "heavy_rain_avg", "bubble_range"],
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
            custom_data=["location_name", "region", "heavy_rain_avg", "bubble_range"],
        )
        center, zoom = _map_center_and_zoom(location_data)
        fig.update_layout(mapbox=dict(center=center, zoom=zoom))

    fig.update_traces(
        marker=dict(opacity=0.76),
        hovertemplate=(
            "Địa điểm: %{customdata[0]}<br>"
            "Nhóm vùng: %{customdata[1]}<br>"
            "Số ngày mưa lớn trung bình/năm: %{customdata[2]:.1f}<br>"
            "Bậc kích thước bong bóng: %{customdata[3]}<extra></extra>"
        ),
    )
    fig = _base_chart_layout(fig, COMPACT_CHART_HEIGHT)
    fig.update_layout(
        showlegend=False,
        margin=dict(l=2, r=2, t=8, b=28),
    )
    return fig


def create_heavy_rain_bubble_map(
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
) -> go.Figure | None:
    location_data = prepare_heavy_rain_location_data(filtered_df, location_year_grid)
    return create_heavy_rain_bubble_map_from_location_data(location_data)


def _bubble_level_diameter(level: int) -> float:
    return (float(level) / max(HEAVY_RAIN_BUBBLE_LEVELS)) ** 0.5 * 26


def render_heavy_rain_map_legend(location_data: pd.DataFrame) -> None:
    visible_regions = [region for region in REGION_ORDER if region in set(location_data["region"])]
    region_rows = "\n".join(
        (
            '<div class="extreme-map-region-row">'
            f'<span class="extreme-map-region-dot" style="background: {REGION_COLOR_MAP.get(region, SECONDARY)};"></span>'
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
    legend_html = (
        '<div class="extreme-map-legend">'
        '<div class="extreme-map-legend-title">Nhóm vùng</div>'
        f"{region_rows}"
        '<div class="extreme-map-legend-break"></div>'
        '<div class="extreme-map-legend-title">Số ngày mưa lớn TB/năm</div>'
        f"{size_rows}"
        "</div>"
    )
    st.markdown(legend_html, unsafe_allow_html=True)


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
            zmin=0,
            zmax=6,
            colorbar=dict(
                title="Số đợt",
                thickness=12,
                len=0.82,
                x=1.02,
                tickmode="array",
                tickvals=[0, 2, 4, 6],
                ticktext=["0", "2", "4", "6"],
            ),
            text=z_values,
            texttemplate="%{text:.1f}",
            hovertemplate=(
                "Nhóm vùng: %{y}<br>"
                "Giai đoạn: %{x}<br>"
                "Số đợt nắng nóng trung bình: %{z:.1f}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(
        title="Giai đoạn",
        side="bottom",
        ticks="",
        gridcolor=CARD,
        automargin=True,
    )
    fig.update_yaxes(
        title="Nhóm vùng",
        ticks="",
        gridcolor=CARD,
        automargin=True,
    )
    fig = _base_chart_layout(fig, COMPACT_CHART_HEIGHT)
    fig.update_layout(margin=dict(l=8, r=58, t=8, b=42))
    return fig


def create_dry_spell_ranking_chart(dry_spells: pd.DataFrame) -> go.Figure | None:
    if dry_spells.empty:
        return None

    required_columns = {"region", "location_name", "dry_spell_length", "dry_spell_start", "dry_spell_end"}
    if not required_columns.issubset(dry_spells.columns):
        return None

    ranking = dry_spells.dropna(subset=["location_name", "dry_spell_length"]).copy()
    ranking["dry_spell_length"] = pd.to_numeric(ranking["dry_spell_length"], errors="coerce")
    ranking = ranking.dropna(subset=["dry_spell_length"])
    if ranking.empty:
        return None

    ranking = (
        ranking.sort_values(
            ["location_name", "dry_spell_length", "dry_spell_start"],
            ascending=[True, False, True],
        )
        .groupby("location_name", as_index=False)
        .head(1)
        .sort_values("dry_spell_length", ascending=False)
        .head(10)
        .sort_values("dry_spell_length", ascending=True)
    )
    if ranking.empty:
        return None

    ranking["dry_spell_length"] = ranking["dry_spell_length"].round().astype(int)
    ranking["dry_spell_label"] = ranking["dry_spell_length"].astype(str)
    ranking["dry_spell_start_label"] = pd.to_datetime(
        ranking["dry_spell_start"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")
    ranking["dry_spell_end_label"] = pd.to_datetime(
        ranking["dry_spell_end"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

    fig = go.Figure()
    for _, row in ranking.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[0, row["dry_spell_length"]],
                y=[row["location_name"], row["location_name"]],
                mode="lines",
                line=dict(color="#D85716", width=3),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=ranking["dry_spell_length"],
            y=ranking["location_name"],
            mode="markers+text",
            marker=dict(color="#C84E12", size=9),
            text=ranking["dry_spell_label"],
            textposition="middle right",
            textfont=dict(color="#C84E12", size=11),
            customdata=ranking[
                ["location_name", "region", "dry_spell_length", "dry_spell_start_label", "dry_spell_end_label"]
            ].to_numpy(),
            hovertemplate=(
                "Địa điểm: %{customdata[0]}<br>"
                "Nhóm vùng: %{customdata[1]}<br>"
                "Độ dài chuỗi ngày khô: %{customdata[2]} ngày<br>"
                "Ngày bắt đầu chuỗi: %{customdata[3]}<br>"
                "Ngày kết thúc chuỗi: %{customdata[4]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_layout(showlegend=False)
    fig.update_xaxes(
        title="Chuỗi ngày khô dài nhất (ngày)",
        gridcolor=BORDER,
        rangemode="tozero",
        zerolinecolor=BORDER,
        automargin=True,
    )
    fig.update_yaxes(
        title="Địa điểm",
        categoryorder="array",
        categoryarray=ranking["location_name"].tolist(),
        ticks="",
        automargin=True,
    )
    max_value = float(ranking["dry_spell_length"].max())
    if max_value > 0:
        fig.update_xaxes(range=[0, max_value * 1.16])
    chart_height = max(COMPACT_CHART_HEIGHT, 56 + len(ranking) * 18)
    return _base_chart_layout(fig, chart_height)


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


def render_chart_card(title: str, figure: go.Figure | None, empty_message: str) -> None:
    st.markdown(f'<div class="extreme-chart-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if figure is None:
        st.info(empty_message)
    else:
        st.plotly_chart(figure, use_container_width=True, config=PLOT_CONFIG)


def render_heavy_rain_bubble_map_card(
    title: str,
    filtered_df: pd.DataFrame,
    location_year_grid: pd.DataFrame,
    empty_message: str,
) -> None:
    st.markdown(f'<div class="extreme-chart-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    location_data = prepare_heavy_rain_location_data(filtered_df, location_year_grid)
    figure = create_heavy_rain_bubble_map_from_location_data(location_data)
    if figure is None:
        st.info(empty_message)
        return

    map_col, legend_col = st.columns([4.7, 1.35], gap="small")
    with map_col:
        st.plotly_chart(figure, use_container_width=True, config=PLOT_CONFIG)
    with legend_col:
        render_heavy_rain_map_legend(location_data)


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
    with row3[0]:
        render_heavy_rain_bubble_map_card(
            "Phân bố số ngày mưa lớn trung bình theo địa điểm (lượng mưa > 50 mm/ngày)",
            filtered_df,
            location_year_grid,
            "Không đủ dữ liệu mưa lớn hoặc tọa độ.",
        )
    with row3[1]:
        render_chart_card(
            "Top 10 địa điểm có chuỗi ngày khô dài nhất (lượng mưa < 1 mm/ngày)",
            create_dry_spell_ranking_chart(dry_spells),
            "Không có chuỗi ngày khô phù hợp với bộ lọc hiện tại.",
        )