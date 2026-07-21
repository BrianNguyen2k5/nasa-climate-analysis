from pathlib import Path
import html
import logging

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from sidebar import LOCATION_VIETNAMESE, REGION_ORDER


logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "nasa_power_vietnam_daily_clean.csv"

BASE_REQUIRED_COLUMNS = {
    "date",
    "year",
    "month",
    "location_id",
    "location_name",
    "region",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
}
TEMPERATURE_COLUMNS = ["T2M", "T2M_MAX", "T2M_MIN", "temperature_range"]

PRIMARY = "#1E3A5F"
TEMP_ACCENT = "#F4A261"
BORDER = "#E2E8F0"

REGION_COLORS = {
    "Trung du và miền núi phía Bắc": "#3B82F6",
    "Đồng bằng sông Hồng": "#8B5CF6",
    "Bắc Trung Bộ": "#EC4899",
    "Nam Trung Bộ": "#F59E0B",
    "Đông Nam Bộ": "#EF4444",
    "Đồng bằng sông Cửu Long": "#06B6D4",
}
REGION_DISPLAY_SHORT = {
    "Trung du và miền núi phía Bắc": "Trung du & miền núi PB",
    "Đồng bằng sông Hồng": "ĐBS Hồng",
    "Bắc Trung Bộ": "Bắc Trung Bộ",
    "Nam Trung Bộ": "Nam Trung Bộ",
    "Đông Nam Bộ": "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long": "ĐBS Cửu Long",
}
LOCATION_PALETTE = [
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
]


def _display_location(raw_name: object) -> str:
    name = str(raw_name)
    return LOCATION_VIETNAMESE.get(name, name)


def _format_temperature(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",") + " °C"


def _active_region_order(data: pd.DataFrame) -> list[str]:
    present = set(data["region"].astype(str).unique())
    return [region for region in REGION_ORDER if region in present]


def _region_color_encoding(
    active_regions: list[str],
    legend: alt.Legend | None = None,
    field: str = "region",
) -> alt.Color:
    return alt.Color(
        f"{field}:N",
        title="Vùng",
        scale=alt.Scale(
            domain=active_regions,
            range=[REGION_COLORS[region] for region in active_regions],
        ),
        legend=legend,
    )


def _render_chart_heading(title: str) -> None:
    st.markdown(
        (
            '<div style="'
            'color:#1E3A5F;'
            'font-size:16px;'
            'font-weight:700;'
            'line-height:1.3;'
            'margin:0 0 10px 0;'
            '">'
            f"{html.escape(title)}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_discrete_legend(
    title: str,
    items: list[tuple[str, str]],
) -> None:
    item_markup = "".join(
        (
            '<span style="display:inline-flex;align-items:center;gap:6px;white-space:nowrap;">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:{html.escape(color, quote=True)};display:inline-block;"></span>'
            f"<span>{html.escape(label)}</span>"
            "</span>"
        )
        for label, color in items
    )
    st.markdown(
        (
            '<div style="margin:0 0 2px 0;color:#475569;font-size:12px;line-height:1.3;">'
            f'<div style="color:#1E3A5F;font-weight:600;margin-bottom:4px;">{html.escape(title)}</div>'
            '<div style="display:flex;flex-wrap:wrap;align-items:center;column-gap:18px;row-gap:6px;">'
            f"{item_markup}"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _dumbbell_height(row_count: int) -> int:
    return min(480, max(320, 20 * row_count + 70))


def _finish_chart(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(height=height)
        .configure_view(stroke=None)
        .configure_axis(
            labelColor="#475569",
            titleColor=PRIMARY,
            gridColor=BORDER,
            domainColor="#CBD5E1",
            tickColor="#CBD5E1",
        )
        .configure_legend(labelColor="#475569", titleColor=PRIMARY)
    )


@st.cache_data(show_spinner=False)
def load_temperature_data(data_path: str = str(DATA_PATH)) -> pd.DataFrame:
    path = Path(data_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {path}")

    header = pd.read_csv(path, nrows=0, encoding="utf-8-sig")
    missing_columns = sorted(BASE_REQUIRED_COLUMNS - set(header.columns))
    if missing_columns:
        raise ValueError("Thiếu cột bắt buộc: " + ", ".join(missing_columns))

    usecols = list(BASE_REQUIRED_COLUMNS)
    range_was_present = "temperature_range" in header.columns
    if range_was_present:
        usecols.append("temperature_range")

    df = pd.read_csv(path, usecols=usecols, encoding="utf-8-sig", low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for column in ["year", "month", "T2M", "T2M_MAX", "T2M_MIN"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if range_was_present:
        df["temperature_range"] = pd.to_numeric(df["temperature_range"], errors="coerce")
    else:
        df["temperature_range"] = df["T2M_MAX"] - df["T2M_MIN"]

    for column in ["location_id", "location_name", "region"]:
        df[column] = df[column].astype("string").str.strip()

    return _validate_temperature_data(df, range_was_present=range_was_present)


def _validate_temperature_data(df: pd.DataFrame, range_was_present: bool = True) -> pd.DataFrame:
    required = BASE_REQUIRED_COLUMNS | {"temperature_range"}
    missing_columns = sorted(required - set(df.columns))
    if missing_columns:
        raise ValueError("Thiếu cột bắt buộc: " + ", ".join(missing_columns))

    if df.empty:
        raise ValueError("File dữ liệu không có bản ghi.")

    identifier_columns = ["date", "location_id", "location_name", "region"]
    if df[identifier_columns].isna().any().any():
        raise ValueError("Dữ liệu thiếu date, location hoặc region.")

    if df[["year", "month"]].isna().any().any():
        raise ValueError("Cột year hoặc month có giá trị không hợp lệ.")

    for column in ["year", "month"]:
        values = df[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or not np.allclose(values, np.round(values)):
            raise ValueError(f"Cột {column} phải chứa số nguyên hợp lệ.")

    df = df.copy()
    df["year"] = df["year"].astype("int16")
    df["month"] = df["month"].astype("int8")

    if not df["month"].between(1, 12).all():
        raise ValueError("Cột month phải nằm trong khoảng 1-12.")
    if (df["year"] != df["date"].dt.year).any() or (df["month"] != df["date"].dt.month).any():
        raise ValueError("Cột year/month không nhất quán với date.")

    if df.duplicated(["location_id", "date"]).any():
        raise ValueError("Dữ liệu có duplicate theo location_id + date.")

    if df[TEMPERATURE_COLUMNS].isna().any().any():
        raise ValueError("Các biến nhiệt độ có giá trị thiếu hoặc không hợp lệ.")
    if not np.isfinite(df[TEMPERATURE_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("Các biến nhiệt độ có giá trị vô cực.")

    calculated_range = df["T2M_MAX"] - df["T2M_MIN"]
    if range_was_present and not np.isclose(
        df["temperature_range"],
        calculated_range,
        atol=1e-8,
        rtol=1e-10,
    ).all():
        raise ValueError("temperature_range không nhất quán với T2M_MAX - T2M_MIN.")
    if not range_was_present:
        df["temperature_range"] = calculated_range

    actual_regions = set(df["region"].astype(str).unique())
    approved_regions = set(REGION_ORDER)
    unexpected_regions = sorted(actual_regions - approved_regions)
    missing_regions = sorted(approved_regions - actual_regions)
    if unexpected_regions:
        raise ValueError("CSV có region ngoài danh sách đã duyệt: " + ", ".join(unexpected_regions))
    if missing_regions:
        raise ValueError("CSV thiếu region đã duyệt: " + ", ".join(missing_regions))

    return df.sort_values(["location_id", "date"]).reset_index(drop=True)


def _parse_period(filters: dict[str, object]) -> tuple[int, int]:
    period = filters.get("year_range")
    if not isinstance(period, (tuple, list)) or len(period) != 2:
        raise ValueError("Giai đoạn phân tích phải gồm năm bắt đầu và năm kết thúc.")
    try:
        start_year, end_year = int(period[0]), int(period[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("Năm bắt đầu/kết thúc không hợp lệ.") from exc
    if start_year > end_year:
        raise ValueError("Năm bắt đầu phải nhỏ hơn hoặc bằng năm kết thúc.")
    return start_year, end_year


def _apply_filters(df: pd.DataFrame, filters: dict[str, object] | None = None) -> pd.DataFrame:
    active_filters = filters or {}
    start_year, end_year = _parse_period(active_filters)
    scoped = df[df["year"].between(start_year, end_year)]

    selected_regions = active_filters.get("selected_regions", [])
    if not isinstance(selected_regions, (list, tuple, set)):
        raise ValueError("Bộ lọc vùng không hợp lệ.")
    selected_regions = list(dict.fromkeys(str(region) for region in selected_regions))
    invalid_regions = [region for region in selected_regions if region not in REGION_ORDER]
    if invalid_regions:
        raise ValueError("Vùng không hợp lệ: " + ", ".join(invalid_regions))
    if not selected_regions:
        return scoped.iloc[0:0].copy()
    scoped = scoped[scoped["region"].isin(selected_regions)]

    selected_locations = active_filters.get("selected_reference_points", [])
    if not isinstance(selected_locations, (list, tuple, set)):
        raise ValueError("Bộ lọc địa điểm không hợp lệ.")
    selected_locations = list(dict.fromkeys(str(location) for location in selected_locations))
    valid_locations = set(df["location_name"].astype(str).unique())
    invalid_locations = [
        location for location in selected_locations if location not in valid_locations
    ]
    if invalid_locations:
        raise ValueError("Địa điểm không hợp lệ: " + ", ".join(invalid_locations))
    if not selected_locations:
        return scoped.iloc[0:0].copy()
    scoped = scoped[scoped["location_name"].isin(selected_locations)]

    return scoped.copy()


def _build_temperature_tables(scoped: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if scoped.empty:
        return {
            "location_period": pd.DataFrame(),
            "region_period": pd.DataFrame(),
            "location_month": pd.DataFrame(),
            "region_month": pd.DataFrame(),
            "location_year": pd.DataFrame(),
            "region_year": pd.DataFrame(),
            "location_seasonality": pd.DataFrame(),
        }

    location_period = (
        scoped.groupby(["region", "location_id", "location_name"], as_index=False, observed=True)
        .agg(
            mean_t2m=("T2M", "mean"),
            mean_tmax=("T2M_MAX", "mean"),
            mean_tmin=("T2M_MIN", "mean"),
            mean_daily_range=("temperature_range", "mean"),
            observation_days=("date", "nunique"),
        )
    )
    location_period["location_label"] = location_period["location_name"].map(_display_location)

    region_period = (
        location_period.groupby("region", as_index=False, observed=True)
        .agg(
            mean_t2m=("mean_t2m", "mean"),
            mean_tmax=("mean_tmax", "mean"),
            mean_tmin=("mean_tmin", "mean"),
            mean_daily_range=("mean_daily_range", "mean"),
            n_locations=("location_id", "nunique"),
            min_location_mean_t2m=("mean_t2m", "min"),
            max_location_mean_t2m=("mean_t2m", "max"),
        )
    )
    region_period["within_region_spread"] = (
        region_period["max_location_mean_t2m"] - region_period["min_location_mean_t2m"]
    )

    hottest_rows = location_period.loc[
        location_period.groupby("region", observed=True)["mean_t2m"].idxmax(),
        ["region", "location_label"],
    ].rename(columns={"location_label": "hottest_location"})
    coolest_rows = location_period.loc[
        location_period.groupby("region", observed=True)["mean_t2m"].idxmin(),
        ["region", "location_label"],
    ].rename(columns={"location_label": "coolest_location"})
    region_period = region_period.merge(hottest_rows, on="region", how="left").merge(
        coolest_rows, on="region", how="left"
    )

    location_month = (
        scoped.groupby(
            ["region", "location_id", "location_name", "month"],
            as_index=False,
            observed=True,
        )
        .agg(monthly_mean_t2m=("T2M", "mean"))
    )
    location_month["location_label"] = location_month["location_name"].map(_display_location)

    region_month = (
        location_month.groupby(["region", "month"], as_index=False, observed=True)
        .agg(monthly_mean_t2m=("monthly_mean_t2m", "mean"))
    )

    location_year = (
        scoped.groupby(
            ["region", "location_id", "location_name", "year"],
            as_index=False,
            observed=True,
        )
        .agg(annual_mean_t2m=("T2M", "mean"))
    )
    location_year["location_label"] = location_year["location_name"].map(_display_location)

    region_year = (
        location_year.groupby(["region", "year"], as_index=False, observed=True)
        .agg(annual_mean_t2m=("annual_mean_t2m", "mean"))
    )

    location_seasonality = (
        location_month.groupby(
            ["region", "location_id", "location_name", "location_label"],
            as_index=False,
            observed=True,
        )
        .agg(
            monthly_min_t2m=("monthly_mean_t2m", "min"),
            monthly_max_t2m=("monthly_mean_t2m", "max"),
        )
    )
    location_seasonality["temperature_seasonality"] = (
        location_seasonality["monthly_max_t2m"] - location_seasonality["monthly_min_t2m"]
    )

    return {
        "location_period": location_period,
        "region_period": region_period,
        "location_month": location_month,
        "region_month": region_month,
        "location_year": location_year,
        "region_year": region_year,
        "location_seasonality": location_seasonality,
    }


def _determine_layout(scoped: pd.DataFrame) -> str:
    if scoped.empty:
        return "empty"
    n_locations = int(scoped["location_id"].nunique())
    n_regions = int(scoped["region"].nunique())
    if n_locations == 1:
        return "single_location"
    if n_regions == 1:
        return "single_region"
    if n_regions >= 2:
        return "multi_region"
    return "empty"


def _render_kpi_cards(items: list[dict[str, object]]) -> None:
    columns = st.columns(4)
    for column, item in zip(columns, items):
        with column:
            label = html.escape(str(item["label"]))
            value = html.escape(_format_temperature(float(item["value"])))
            subject = html.escape(str(item["subject"]))
            caption = html.escape(str(item.get("caption", "")))
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-caption"><strong>{subject}</strong><br>{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _vertical_space(height: int = 24) -> None:
    st.markdown(
        f'<div style="height: {height}px;"></div>',
        unsafe_allow_html=True,
    )


def _region_scatter_chart(region_period: pd.DataFrame) -> alt.Chart:
    active_regions = _active_region_order(region_period)
    tooltip = [
        alt.Tooltip("region:N", title="Vùng"),
        alt.Tooltip("mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_daily_range:Q", title="Biên độ ngày-đêm TB (°C)", format=".2f"),
        alt.Tooltip("n_locations:Q", title="Số điểm đang dùng", format=".0f"),
        alt.Tooltip("within_region_spread:Q", title="Chênh lệch nội vùng (°C)", format=".2f"),
        alt.Tooltip("hottest_location:N", title="Điểm nóng nhất"),
        alt.Tooltip("coolest_location:N", title="Điểm mát nhất"),
    ]
    base = alt.Chart(region_period).encode(
        x=alt.X(
            "mean_t2m:Q",
            title="T2M trung bình (°C)",
            scale=alt.Scale(zero=False, padding=0.5),
            axis=alt.Axis(
                grid=True,
                labelPadding=6,
                titlePadding=12,
            ),
        ),
        y=alt.Y(
            "mean_daily_range:Q",
            title=["Biên độ nhiệt ngày–đêm", "trung bình (°C)"],
            scale=alt.Scale(zero=False, padding=0.5),
            axis=alt.Axis(
                grid=True,
                labelPadding=6,
                titlePadding=12,
                titleLimit=220,
                labelLimit=120,
            ),
        ),
    )
    points = base.mark_circle(size=135, opacity=0.9).encode(
        color=_region_color_encoding(
            active_regions,
            legend=None,
        ),
        tooltip=tooltip,
    )
    chart = points
    return _finish_chart(chart, 310)


def _location_scatter_chart(location_metrics: pd.DataFrame) -> alt.Chart:
    location_order = (
        location_metrics.sort_values("mean_t2m", ascending=False)["location_label"].tolist()
    )
    n_locations = len(location_order)
    location_colors = [
        LOCATION_PALETTE[index % len(LOCATION_PALETTE)]
        for index in range(n_locations)
    ]
    base = alt.Chart(location_metrics).encode(
        x=alt.X(
            "mean_t2m:Q",
            title="T2M trung bình (°C)",
            scale=alt.Scale(zero=False, padding=0.5),
            axis=alt.Axis(
                grid=True,
                labelPadding=6,
                titlePadding=12,
            ),
        ),
        y=alt.Y(
            "mean_daily_range:Q",
            title=["Biên độ nhiệt ngày–đêm", "trung bình (°C)"],
            scale=alt.Scale(zero=False, padding=0.5),
            axis=alt.Axis(
                grid=True,
                labelPadding=6,
                titlePadding=12,
                titleLimit=220,
                labelLimit=120,
            ),
        ),
        tooltip=[
            alt.Tooltip("location_label:N", title="Điểm tham chiếu"),
            alt.Tooltip("mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
            alt.Tooltip("mean_tmin:Q", title="T2M_MIN trung bình (°C)", format=".2f"),
            alt.Tooltip("mean_tmax:Q", title="T2M_MAX trung bình (°C)", format=".2f"),
            alt.Tooltip(
                "mean_daily_range:Q",
                title="Biên độ ngày-đêm TB (°C)",
                format=".2f",
            ),
            alt.Tooltip(
                "temperature_seasonality:Q",
                title="Biên độ mùa (°C)",
                format=".2f",
            ),
        ],
    )
    points = base.mark_circle(size=135, opacity=0.9).encode(
        color=alt.Color(
            "location_label:N",
            title="Điểm tham chiếu",
            scale=alt.Scale(domain=location_order, range=location_colors),
            legend=None,
        )
    )
    return _finish_chart(points, 310)


def _dumbbell_chart(
    location_period: pd.DataFrame,
    multi_region: bool,
    height: int | None = None,
) -> alt.Chart:
    tooltip = [
        alt.Tooltip("region:N", title="Vùng"),
        alt.Tooltip("location_label:N", title="Điểm tham chiếu"),
        alt.Tooltip("mean_tmin:Q", title="T2M_MIN trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_tmax:Q", title="T2M_MAX trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_daily_range:Q", title="Biên độ ngày-đêm TB (°C)", format=".2f"),
    ]
    location_order = (
        location_period.sort_values("mean_t2m", ascending=False)["location_label"].tolist()
    )
    y = alt.Y(
        "location_label:N",
        title=None,
        sort=location_order,
        scale=alt.Scale(domain=location_order),
        axis=alt.Axis(
            values=location_order,
            labelLimit=340,
            labelOverlap=False,
            labelPadding=10,
            labelFontSize=11,
            titlePadding=14,
        ),
    )
    if multi_region:
        active_regions = _active_region_order(location_period)
        color = _region_color_encoding(
            active_regions,
            legend=None,
        )
    else:
        region = str(location_period["region"].iloc[0])
        color = alt.value(REGION_COLORS.get(region, TEMP_ACCENT))
    base = alt.Chart(location_period).encode(y=y, color=color, tooltip=tooltip)
    ranges = base.mark_rule(strokeWidth=3, opacity=0.75).encode(
        x=alt.X(
            "mean_tmin:Q",
            title="Nhiệt độ trung bình (°C)",
            scale=alt.Scale(zero=False, padding=1),
        ),
        x2="mean_tmax:Q",
    )
    min_points = base.mark_circle(size=48, opacity=0.72).encode(x="mean_tmin:Q")
    max_points = base.mark_circle(size=48, opacity=0.72).encode(x="mean_tmax:Q")
    mean_points = base.mark_circle(size=115, stroke="white", strokeWidth=1.2).encode(x="mean_t2m:Q")
    chart = (ranges + min_points + max_points + mean_points).properties(
        padding={"left": 28, "right": 8, "top": 2, "bottom": 4}
    )
    if height is None:
        height = _dumbbell_height(len(location_order))
    return _finish_chart(chart, height)


def _heatmap_chart(
    data: pd.DataFrame,
    row_field: str,
    row_title: str,
    row_order: list[str],
    height: int | None = None,
    color_legend_bottom: bool = False,
) -> alt.Chart:
    row_tooltip_title = "Vùng" if row_field == "region" else "Điểm tham chiếu"
    color_legend = (
        alt.Legend(
            orient="bottom",
            direction="horizontal",
            gradientLength=220,
            gradientThickness=12,
        )
        if color_legend_bottom
        else alt.Legend()
    )
    chart = (
        alt.Chart(data)
        .mark_rect(stroke="white", strokeWidth=1)
        .encode(
            x=alt.X(
                "month:O",
                title="Tháng",
                sort=list(range(1, 13)),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                f"{row_field}:N",
                title=row_title,
                sort=row_order,
                scale=alt.Scale(domain=row_order),
                axis=alt.Axis(
                    values=row_order,
                    labelLimit=320,
                    labelOverlap=False,
                    labelPadding=8,
                    labelFontSize=11,
                    titlePadding=14,
                ),
            ),
            color=alt.Color(
                "monthly_mean_t2m:Q",
                title="T2M trung bình (°C)",
                scale=alt.Scale(scheme="redyellowblue", reverse=True),
                legend=color_legend,
            ),
            tooltip=[
                alt.Tooltip(f"{row_field}:N", title=row_tooltip_title),
                alt.Tooltip("month:O", title="Tháng"),
                alt.Tooltip("monthly_mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
            ],
        )
    )
    chart_height = height if height is not None else max(260, len(row_order) * 45 + 45)
    return _finish_chart(chart, chart_height)


def _monthly_profile_chart(location_month: pd.DataFrame) -> alt.Chart:
    chart = (
        alt.Chart(location_month)
        .mark_line(color=TEMP_ACCENT, strokeWidth=3, point=alt.OverlayMarkDef(size=75, filled=True))
        .encode(
            x=alt.X(
                "month:O",
                title="Tháng",
                sort=list(range(1, 13)),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "monthly_mean_t2m:Q",
                title="T2M trung bình (°C)",
                scale=alt.Scale(zero=False, padding=1),
            ),
            tooltip=[
                alt.Tooltip("location_label:N", title="Điểm tham chiếu"),
                alt.Tooltip("month:O", title="Tháng"),
                alt.Tooltip("monthly_mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
            ],
        )
    )
    return _finish_chart(chart, 320)


def _annual_distribution_chart(
    data: pd.DataFrame,
    category_field: str,
    category_title: str,
    category_order: list[str],
    region_colors: bool,
    height: int | None = None,
    show_category_axis_title: bool = True,
) -> tuple[alt.Chart, bool]:
    n_years = int(data["year"].nunique())
    y = alt.Y(
        f"{category_field}:N",
        title=category_title if show_category_axis_title else None,
        sort=category_order,
        scale=alt.Scale(domain=category_order),
        axis=alt.Axis(
            values=category_order,
            labelLimit=340,
            labelOverlap=False,
            labelPadding=10,
            labelFontSize=11,
            titlePadding=14,
        ),
    )
    x = alt.X(
        "annual_mean_t2m:Q",
        title="Nhiệt độ trung bình năm (°C)",
        scale=alt.Scale(zero=False, padding=1),
    )
    tooltip = [
        alt.Tooltip(f"{category_field}:N", title=category_title or "Phạm vi"),
        alt.Tooltip("year:O", title="Năm"),
        alt.Tooltip("annual_mean_t2m:Q", title="T2M trung bình năm (°C)", format=".2f"),
    ]
    color = (
        _region_color_encoding(_active_region_order(data), legend=None)
        if region_colors
        else alt.value(TEMP_ACCENT)
    )
    base = alt.Chart(data).encode(x=x, y=y, color=color)
    chart_padding = {"left": 42, "right": 6, "top": 2, "bottom": 4}
    if n_years < 3:
        points = base.mark_circle(size=95, opacity=0.9).encode(tooltip=tooltip)
        chart_height = height if height is not None else max(250, len(category_order) * 45)
        return (
            _finish_chart(
                points.properties(padding=chart_padding),
                chart_height,
            ),
            False,
        )

    boxes = base.mark_boxplot(size=30, extent="min-max", opacity=0.72)
    points = base.mark_circle(size=32, opacity=0.28).encode(tooltip=tooltip)
    chart = (boxes + points).properties(padding=chart_padding)
    chart_height = height if height is not None else max(280, len(category_order) * 48)
    return _finish_chart(chart, chart_height), True


def _with_moving_average(
    annual_data: pd.DataFrame,
    group_field: str,
) -> pd.DataFrame:
    result = annual_data.sort_values([group_field, "year"]).copy()
    result["moving_average_5y"] = result.groupby(group_field, observed=True)[
        "annual_mean_t2m"
    ].transform(lambda series: series.rolling(5, min_periods=5).mean())
    return result


def _single_location_trend_chart(
    annual_data: pd.DataFrame,
) -> tuple[alt.Chart, bool]:
    group_field = "location_label"
    moving = _with_moving_average(annual_data, group_field)
    annual_plot = moving[[group_field, "year", "annual_mean_t2m"]].rename(
        columns={"annual_mean_t2m": "plot_value"}
    )
    annual_plot["series"] = "Trung bình năm"
    moving_plot = (
        moving[[group_field, "year", "moving_average_5y"]]
        .dropna()
        .rename(columns={"moving_average_5y": "plot_value"})
    )
    moving_plot["series"] = "TB trượt 5 năm"
    plot_data = pd.concat([annual_plot, moving_plot], ignore_index=True)
    has_moving_average = not moving_plot.empty
    series_domain = ["Trung bình năm", "TB trượt 5 năm"] if has_moving_average else ["Trung bình năm"]
    chart = (
        alt.Chart(plot_data)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=18))
        .encode(
            x=alt.X("year:O", title="Năm", axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
            y=alt.Y(
                "plot_value:Q",
                title="T2M trung bình năm (°C)",
                scale=alt.Scale(zero=False, padding=1),
            ),
            color=alt.Color(
                "series:N",
                title="Chuỗi",
                scale=alt.Scale(
                    domain=series_domain,
                    range=[PRIMARY, TEMP_ACCENT][: len(series_domain)],
                ),
                legend=None,
            ),
            strokeDash=alt.StrokeDash(
                "series:N",
                legend=None,
                scale=alt.Scale(
                    domain=series_domain,
                    range=[[1, 0], [7, 4]][: len(series_domain)],
                ),
            ),
            tooltip=[
                alt.Tooltip("year:O", title="Năm"),
                alt.Tooltip("series:N", title="Chuỗi"),
                alt.Tooltip("plot_value:Q", title="T2M (°C)", format=".2f"),
            ],
        )
    )
    return _finish_chart(chart, 320), has_moving_average


def _warn_if_months_missing(monthly_data: pd.DataFrame, group_field: str) -> None:
    if monthly_data.empty:
        return
    month_counts = monthly_data.groupby(group_field, observed=True)["month"].nunique()
    if (month_counts < 12).any():
        st.warning(
            "Một số chuỗi không đủ 12 tháng. Biểu đồ chỉ hiển thị các tháng có dữ liệu."
        )


def _render_multi_region(tables: dict[str, pd.DataFrame]) -> None:
    location_period = tables["location_period"]
    region_period = tables["region_period"]
    hottest_region = region_period.loc[region_period["mean_t2m"].idxmax()]
    coolest_region = region_period.loc[region_period["mean_t2m"].idxmin()]
    hottest_location = location_period.loc[location_period["mean_t2m"].idxmax()]
    coolest_location = location_period.loc[location_period["mean_t2m"].idxmin()]

    _render_kpi_cards(
        [
            {
                "label": "Vùng nóng nhất",
                "value": hottest_region["mean_t2m"],
                "subject": hottest_region["region"],
                "caption": "T2M trung bình",
            },
            {
                "label": "Vùng mát nhất",
                "value": coolest_region["mean_t2m"],
                "subject": coolest_region["region"],
                "caption": "T2M trung bình",
            },
            {
                "label": "Điểm tham chiếu nóng nhất",
                "value": hottest_location["mean_t2m"],
                "subject": hottest_location["location_label"],
                "caption": str(hottest_location["region"]),
            },
            {
                "label": "Điểm tham chiếu mát nhất",
                "value": coolest_location["mean_t2m"],
                "subject": coolest_location["location_label"],
                "caption": str(coolest_location["region"]),
            },
        ]
    )
    _vertical_space(26)

    region_order = _active_region_order(tables["region_month"])
    region_legend_items = [
        (region, REGION_COLORS[region])
        for region in region_order
    ]

    row1_left, row1_right = st.columns([0.9, 1.1], gap="medium")
    with row1_left:
        _render_chart_heading("Mức nhiệt và biên độ ngày–đêm")
        st.altair_chart(_region_scatter_chart(region_period), width="stretch")
        _render_discrete_legend("Vùng", region_legend_items)
    with row1_right:
        _render_chart_heading("Nhiệt độ theo tháng và vùng")
        _warn_if_months_missing(tables["region_month"], "region")
        st.altair_chart(
            _heatmap_chart(
                tables["region_month"],
                row_field="region",
                row_title="Vùng",
                row_order=region_order,
                height=300,
                color_legend_bottom=True,
            ),
            width="stretch",
        )

    _vertical_space(22)
    dumbbell_height = _dumbbell_height(len(location_period))
    row2_left, row2_right = st.columns([1.08, 0.92], gap="medium")
    with row2_left:
        _render_chart_heading("Khoảng Tmin–Tmax và vị trí Tmean")
        st.altair_chart(
            _dumbbell_chart(
                location_period,
                multi_region=True,
                height=dumbbell_height,
            ),
            width="stretch",
        )
        _render_discrete_legend("Vùng", region_legend_items)
    with row2_right:
        _render_chart_heading("Phân bố nhiệt độ trung bình năm")
        distribution, is_boxplot = _annual_distribution_chart(
            tables["region_year"],
            category_field="region",
            category_title="Vùng",
            category_order=region_order,
            region_colors=True,
            height=360,
            show_category_axis_title=False,
        )
        if not is_boxplot:
            st.info("Giai đoạn quá ngắn; hiển thị giá trị trung bình từng năm.")
        st.altair_chart(distribution, width="stretch")


def _render_single_region(tables: dict[str, pd.DataFrame]) -> None:
    location_period = tables["location_period"]
    metrics = location_period.merge(
        tables["location_seasonality"][["location_id", "temperature_seasonality"]],
        on="location_id",
        how="left",
    )
    hottest = metrics.loc[metrics["mean_t2m"].idxmax()]
    coolest = metrics.loc[metrics["mean_t2m"].idxmin()]
    largest_range = metrics.loc[metrics["mean_daily_range"].idxmax()]
    largest_seasonality = metrics.loc[metrics["temperature_seasonality"].idxmax()]

    _render_kpi_cards(
        [
            {
                "label": "Điểm nóng nhất trong vùng",
                "value": hottest["mean_t2m"],
                "subject": hottest["location_label"],
                "caption": "T2M trung bình",
            },
            {
                "label": "Điểm mát nhất trong vùng",
                "value": coolest["mean_t2m"],
                "subject": coolest["location_label"],
                "caption": "T2M trung bình",
            },
            {
                "label": "Dao động ngày-đêm lớn nhất",
                "value": largest_range["mean_daily_range"],
                "subject": largest_range["location_label"],
                "caption": "Biên độ ngày–đêm TB",
            },
            {
                "label": "Tính mùa nhiệt độ lớn nhất",
                "value": largest_seasonality["temperature_seasonality"],
                "subject": largest_seasonality["location_label"],
                "caption": "Chênh lệch tháng nóng–mát",
            },
        ]
    )
    _vertical_space(26)

    location_order = (
        location_period.sort_values("mean_t2m", ascending=False)["location_label"].tolist()
    )
    location_legend_items = [
        (location, LOCATION_PALETTE[index % len(LOCATION_PALETTE)])
        for index, location in enumerate(location_order)
    ]
    heatmap_height = min(360, max(300, 32 * len(location_period) + 100))
    row1_left, row1_right = st.columns([0.9, 1.1], gap="medium")
    with row1_left:
        _render_chart_heading("Mức nhiệt và biên độ ngày–đêm")
        st.altair_chart(_location_scatter_chart(metrics), width="stretch")
        _render_discrete_legend("Điểm tham chiếu", location_legend_items)
    with row1_right:
        _render_chart_heading("Nhiệt độ theo tháng")
        _warn_if_months_missing(tables["location_month"], "location_id")
        st.altair_chart(
            _heatmap_chart(
                tables["location_month"],
                row_field="location_label",
                row_title="Điểm tham chiếu",
                row_order=location_order,
                height=heatmap_height,
                color_legend_bottom=True,
            ),
            width="stretch",
        )

    _vertical_space(22)
    dumbbell_height = _dumbbell_height(len(location_period))
    distribution_height = min(420, max(340, 36 * len(location_period) + 100))
    row2_left, row2_right = st.columns([1.08, 0.92], gap="medium")
    with row2_left:
        _render_chart_heading("Khoảng Tmin–Tmax theo địa điểm")
        st.altair_chart(
            _dumbbell_chart(
                location_period,
                multi_region=False,
                height=dumbbell_height,
            ),
            width="stretch",
        )
    with row2_right:
        _render_chart_heading("Phân bố nhiệt độ trung bình năm")
        distribution, is_boxplot = _annual_distribution_chart(
            tables["location_year"],
            category_field="location_label",
            category_title="Điểm tham chiếu",
            category_order=location_order,
            region_colors=False,
            height=distribution_height,
        )
        if not is_boxplot:
            st.info("Giai đoạn quá ngắn; hiển thị giá trị trung bình từng năm.")
        st.altair_chart(distribution, width="stretch")


def _render_single_location(tables: dict[str, pd.DataFrame]) -> None:
    location = tables["location_period"].iloc[0]
    location_label = str(location["location_label"])
    region = str(location["region"])
    seasonality = float(tables["location_seasonality"]["temperature_seasonality"].iloc[0])

    _render_kpi_cards(
        [
            {
                "label": "Nhiệt độ trung bình",
                "value": location["mean_t2m"],
                "subject": location_label,
                "caption": region,
            },
            {
                "label": "T2M_MIN trung bình",
                "value": location["mean_tmin"],
                "subject": location_label,
                "caption": "Cực tiểu ngày TB",
            },
            {
                "label": "T2M_MAX trung bình",
                "value": location["mean_tmax"],
                "subject": location_label,
                "caption": "Cực đại ngày TB",
            },
            {
                "label": "Dao động ngày-đêm TB",
                "value": location["mean_daily_range"],
                "subject": location_label,
                "caption": "Biên độ ngày–đêm TB",
            },
        ]
    )
    _vertical_space(26)

    left_col, right_col = st.columns([0.85, 1.15], gap="medium")
    with left_col:
        _render_chart_heading("Chu kỳ nhiệt theo tháng")
        _warn_if_months_missing(tables["location_month"], "location_id")
        st.altair_chart(
            _monthly_profile_chart(tables["location_month"]),
            width="stretch",
        )
        st.caption(f"Biên độ mùa: {_format_temperature(seasonality)}")
    with right_col:
        _render_chart_heading("Xu hướng nhiệt độ trung bình năm")
        trend, has_moving_average = _single_location_trend_chart(
            tables["location_year"],
        )
        if not has_moving_average:
            st.info("Chưa đủ 5 năm để tính trung bình trượt.")
        st.altair_chart(trend, width="stretch")
        series_legend_items = [("Trung bình năm", PRIMARY)]
        if has_moving_average:
            series_legend_items.append(("TB trượt 5 năm", TEMP_ACCENT))
        _render_discrete_legend("Chuỗi", series_legend_items)


def render_temperature_comparison_tab(
    placeholder_box,
    filters: dict[str, object] | None = None,
) -> None:
    _ = placeholder_box

    try:
        daily = load_temperature_data()
        active_filters = filters or {}
        scoped = _apply_filters(daily, active_filters)
    except (FileNotFoundError, ValueError) as exc:
        st.error(f"Không thể chuẩn bị dữ liệu nhiệt độ: {exc}")
        return
    except Exception:
        logger.exception("Lỗi không xác định khi chuẩn bị dữ liệu nhiệt độ")
        st.error("Không thể đọc dữ liệu nhiệt độ. Vui lòng kiểm tra file CSV.")
        return

    if scoped.empty:
        st.info("Không có dữ liệu nhiệt độ phù hợp với bộ lọc hiện tại.")
        return

    try:
        tables = _build_temperature_tables(scoped)
    except Exception:
        logger.exception("Lỗi khi tổng hợp dữ liệu nhiệt độ")
        st.error("Không thể tổng hợp dữ liệu nhiệt độ cho bộ lọc hiện tại.")
        return

    if any(tables[name].empty for name in ["location_period", "location_month", "location_year"]):
        st.info("Không đủ dữ liệu tổng hợp để hiển thị Tab 2.")
        return

    start_year, end_year = _parse_period(active_filters)
    n_regions = int(scoped["region"].nunique())
    n_locations = int(scoped["location_id"].nunique())
    layout = _determine_layout(scoped)
    location_subset_active = bool(active_filters.get("selected_reference_points", []))
    scope_caption = f"{start_year}–{end_year} · {n_regions} vùng · {n_locations} điểm"
    if location_subset_active:
        scope_caption += " · Chỉ tính trên các điểm đã chọn"
    st.caption(scope_caption)

    try:
        if layout == "multi_region":
            _render_multi_region(tables)
        elif layout == "single_region":
            _render_single_region(tables)
        elif layout == "single_location":
            _render_single_location(tables)
        else:
            st.info("Không có dữ liệu phù hợp để hiển thị.")
            return
    except Exception:
        logger.exception("Lỗi khi hiển thị Tab 2")
        st.error("Không thể hiển thị biểu đồ nhiệt độ cho bộ lọc hiện tại.")
        return
