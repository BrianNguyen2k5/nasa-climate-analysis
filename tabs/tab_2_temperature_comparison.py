from pathlib import Path
import html
import logging

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from sidebar import ALL_REGIONS_LABEL, LOCATION_VIETNAMESE, REGION_ORDER


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
SECONDARY = "#2A9D8F"
TEMP_ACCENT = "#F4A261"
MUTED = "#64748B"
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

LOCATION_ENGLISH = {display_name: raw_name for raw_name, display_name in LOCATION_VIETNAMESE.items()}


def _display_location(raw_name: object) -> str:
    name = str(raw_name)
    return LOCATION_VIETNAMESE.get(name, name)


def _format_temperature(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",") + " °C"


def _region_color_encoding(legend: alt.Legend | None = None) -> alt.Color:
    return alt.Color(
        "region:N",
        title="Vùng",
        scale=alt.Scale(
            domain=REGION_ORDER,
            range=[REGION_COLORS[region] for region in REGION_ORDER],
        ),
        legend=legend,
    )


def _short_region_legend(columns: int = 3) -> alt.Legend:
    label_expression = "datum.label"
    for region, short_name in reversed(list(REGION_DISPLAY_SHORT.items())):
        label_expression = (
            f"datum.label === {region!r} ? {short_name!r} : ({label_expression})"
        )
    return alt.Legend(
        title="Vùng",
        orient="bottom",
        direction="horizontal",
        columns=columns,
        labelExpr=label_expression,
        labelLimit=170,
    )


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
        .configure_title(color=PRIMARY, fontSize=16, fontWeight=700, anchor="start")
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


def _parse_period(filters: dict[str, object], df: pd.DataFrame) -> tuple[int, int]:
    default_period = (int(df["year"].min()), int(df["year"].max()))
    period = filters.get("period", default_period)
    if not isinstance(period, (tuple, list)) or len(period) != 2:
        raise ValueError("Giai đoạn phân tích phải gồm năm bắt đầu và năm kết thúc.")
    try:
        start_year, end_year = int(period[0]), int(period[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("Năm bắt đầu/kết thúc không hợp lệ.") from exc
    if start_year > end_year:
        raise ValueError("Năm bắt đầu phải nhỏ hơn hoặc bằng năm kết thúc.")
    return start_year, end_year


def _raw_location_names(selected_locations: object, df: pd.DataFrame) -> list[str]:
    if selected_locations in (None, []):
        return []
    if not isinstance(selected_locations, (list, tuple, set)):
        raise ValueError("Bộ lọc địa điểm không hợp lệ.")

    valid_raw_names = set(df["location_name"].astype(str).unique())
    raw_names: list[str] = []
    invalid_names: list[str] = []
    for selected_name in selected_locations:
        name = str(selected_name)
        raw_name = name if name in valid_raw_names else LOCATION_ENGLISH.get(name)
        if raw_name is None or raw_name not in valid_raw_names:
            invalid_names.append(name)
        elif raw_name not in raw_names:
            raw_names.append(raw_name)

    if invalid_names:
        raise ValueError("Địa điểm không hợp lệ: " + ", ".join(invalid_names))
    return raw_names


def _apply_filters(df: pd.DataFrame, filters: dict[str, object] | None = None) -> pd.DataFrame:
    active_filters = filters or {}
    start_year, end_year = _parse_period(active_filters, df)
    scoped = df[df["year"].between(start_year, end_year)]

    selected_region = str(active_filters.get("region", ALL_REGIONS_LABEL))
    if selected_region != ALL_REGIONS_LABEL:
        if selected_region not in REGION_ORDER:
            raise ValueError(f"Vùng không hợp lệ: {selected_region}")
        scoped = scoped[scoped["region"] == selected_region]

    raw_names = _raw_location_names(active_filters.get("locations", []), df)
    if raw_names:
        available_locations = set(scoped["location_name"].astype(str).unique())
        unavailable = [name for name in raw_names if name not in available_locations]
        if unavailable:
            display_names = [_display_location(name) for name in unavailable]
            raise ValueError("Địa điểm không thuộc phạm vi vùng đã chọn: " + ", ".join(display_names))
        scoped = scoped[scoped["location_name"].isin(raw_names)]

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


def _region_ranking_chart(region_period: pd.DataFrame) -> alt.Chart:
    tooltip = [
        alt.Tooltip("region:N", title="Vùng"),
        alt.Tooltip("mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_tmax:Q", title="T2M_MAX trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_tmin:Q", title="T2M_MIN trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_daily_range:Q", title="Biên độ ngày-đêm TB (°C)", format=".2f"),
        alt.Tooltip("n_locations:Q", title="Số điểm đang dùng", format=".0f"),
        alt.Tooltip("hottest_location:N", title="Điểm nóng nhất"),
        alt.Tooltip("coolest_location:N", title="Điểm mát nhất"),
        alt.Tooltip("within_region_spread:Q", title="Chênh lệch nội vùng (°C)", format=".2f"),
    ]
    region_rank_order = (
        region_period.sort_values("mean_t2m", ascending=False)["region"].tolist()
    )
    y = alt.Y(
        "region:N",
        title=None,
        sort=region_rank_order,
        axis=alt.Axis(labelLimit=245),
    )
    bars = (
        alt.Chart(region_period)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("mean_t2m:Q", title="Nhiệt độ trung bình (°C)"),
            y=y,
            color=_region_color_encoding(legend=None),
            tooltip=tooltip,
        )
    )
    labels = bars.mark_text(align="left", baseline="middle", dx=4, color=PRIMARY).encode(
        text=alt.Text("mean_t2m:Q", format=".2f")
    )
    reference_value = float(region_period["mean_t2m"].mean())
    reference_data = pd.DataFrame({"reference": [reference_value]})
    reference = (
        alt.Chart(reference_data)
        .mark_rule(color=MUTED, strokeDash=[5, 4], strokeWidth=1.5)
        .encode(
            x=alt.X("reference:Q"),
            tooltip=[alt.Tooltip("reference:Q", title="TB các vùng (°C)", format=".2f")],
        )
    )
    chart = (bars + reference + labels).properties(
        title="Xếp hạng nhiệt độ trung bình theo vùng",
        padding={"left": 5, "right": 45, "top": 5, "bottom": 5},
    )
    return _finish_chart(chart, 310)


def _region_scatter_chart(region_period: pd.DataFrame) -> alt.Chart:
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
        ),
        y=alt.Y(
            "mean_daily_range:Q",
            title="Biên độ nhiệt ngày-đêm trung bình (°C)",
            scale=alt.Scale(zero=False, padding=0.5),
        ),
    )
    points = base.mark_circle(size=135, opacity=0.9).encode(
        color=_region_color_encoding(legend=_short_region_legend()),
        tooltip=tooltip,
    )
    chart = points.properties(
        title="Mức nhiệt và biên độ ngày–đêm",
        padding={"left": 5, "right": 8, "top": 5, "bottom": 5},
    )
    return _finish_chart(chart, 310)


def _dumbbell_chart(location_period: pd.DataFrame, multi_region: bool) -> alt.Chart:
    tooltip = [
        alt.Tooltip("region:N", title="Vùng"),
        alt.Tooltip("location_label:N", title="Điểm tham chiếu"),
        alt.Tooltip("mean_tmin:Q", title="T2M_MIN trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_tmax:Q", title="T2M_MAX trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_daily_range:Q", title="Biên độ ngày-đêm TB (°C)", format=".2f"),
    ]
    y = alt.Y(
        "location_label:N",
        title=None,
        sort=alt.SortField(field="mean_t2m", order="descending"),
        axis=alt.Axis(labelLimit=210),
    )
    color = _region_color_encoding(
        legend=_short_region_legend() if multi_region else None
    )
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
    title = (
        "Khoảng Tmin–Tmax và vị trí Tmean"
        if multi_region
        else "Khoảng Tmin–Tmax theo địa điểm"
    )
    chart = (ranges + min_points + max_points + mean_points).properties(title=title)
    height = 460 if multi_region else 320
    return _finish_chart(chart, height)


def _location_ranking_chart(location_period: pd.DataFrame, region: str) -> alt.Chart:
    color = REGION_COLORS.get(region, TEMP_ACCENT)
    tooltip = [
        alt.Tooltip("location_label:N", title="Điểm tham chiếu"),
        alt.Tooltip("mean_t2m:Q", title="T2M trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_tmax:Q", title="T2M_MAX trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_tmin:Q", title="T2M_MIN trung bình (°C)", format=".2f"),
        alt.Tooltip("mean_daily_range:Q", title="Biên độ ngày-đêm TB (°C)", format=".2f"),
        alt.Tooltip("observation_days:Q", title="Số ngày quan sát", format=",.0f"),
    ]
    location_rank_order = (
        location_period.sort_values("mean_t2m", ascending=False)["location_label"].tolist()
    )
    y = alt.Y(
        "location_label:N",
        title=None,
        sort=location_rank_order,
        axis=alt.Axis(labelLimit=210),
    )
    bars = alt.Chart(location_period).mark_bar(color=color, cornerRadiusEnd=4).encode(
        x=alt.X("mean_t2m:Q", title="Nhiệt độ trung bình (°C)"),
        y=y,
        tooltip=tooltip,
    )
    labels = bars.mark_text(align="left", dx=4, color=PRIMARY).encode(
        text=alt.Text("mean_t2m:Q", format=".2f")
    )
    reference_value = float(location_period["mean_t2m"].mean())
    reference = (
        alt.Chart(pd.DataFrame({"reference": [reference_value]}))
        .mark_rule(color=MUTED, strokeDash=[5, 4])
        .encode(
            x="reference:Q",
            tooltip=[alt.Tooltip("reference:Q", title="TB các điểm (°C)", format=".2f")],
        )
    )
    chart = (bars + reference + labels).properties(
        title=f"Xếp hạng địa điểm trong {region}"
    )
    return _finish_chart(chart, 320)


def _heatmap_chart(
    data: pd.DataFrame,
    row_field: str,
    row_title: str,
    row_order: list[str],
    title: str,
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
                axis=alt.Axis(labelLimit=280 if row_field == "region" else 245),
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
        .properties(title=title)
    )
    chart_height = height if height is not None else max(260, len(row_order) * 45 + 45)
    return _finish_chart(chart, chart_height)


def _monthly_profile_chart(location_month: pd.DataFrame, location_label: str) -> alt.Chart:
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
        .properties(title=f"Chu kỳ nhiệt 12 tháng tại {location_label}")
    )
    return _finish_chart(chart, 320)


def _annual_distribution_chart(
    data: pd.DataFrame,
    category_field: str,
    category_title: str,
    category_order: list[str],
    title: str,
    region_colors: bool,
    height: int | None = None,
    show_category_axis_title: bool = True,
) -> tuple[alt.Chart, bool]:
    n_years = int(data["year"].nunique())
    y = alt.Y(
        f"{category_field}:N",
        title=category_title if show_category_axis_title else None,
        sort=category_order,
        axis=alt.Axis(labelLimit=245),
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
    color = _region_color_encoding(legend=None) if region_colors else alt.value(TEMP_ACCENT)
    base = alt.Chart(data).encode(x=x, y=y, color=color)

    if n_years < 3:
        points = base.mark_circle(size=95, opacity=0.9).encode(tooltip=tooltip)
        chart_height = height if height is not None else max(250, len(category_order) * 45)
        return _finish_chart(points.properties(title=title), chart_height), False

    boxes = base.mark_boxplot(size=24, extent="min-max", opacity=0.72)
    points = base.mark_circle(size=28, opacity=0.28).encode(tooltip=tooltip)
    chart = (boxes + points).properties(title=title)
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


def _annual_trend_chart(
    annual_data: pd.DataFrame,
    group_field: str,
    group_title: str,
    title: str,
    region_colors: bool,
) -> tuple[alt.Chart, bool]:
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

    if region_colors:
        color = _region_color_encoding(legend=_short_region_legend())
    else:
        color = alt.Color(
            f"{group_field}:N",
            title=group_title,
            legend=alt.Legend(orient="bottom", columns=3),
        )

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
            color=color,
            strokeDash=alt.StrokeDash(
                "series:N",
                legend=alt.Legend(title="Chuỗi", symbolType="stroke"),
                scale=alt.Scale(
                    domain=["Trung bình năm", "TB trượt 5 năm"],
                    range=[[1, 0], [7, 4]],
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{group_field}:N", title=group_title),
                alt.Tooltip("year:O", title="Năm"),
                alt.Tooltip("series:N", title="Chuỗi"),
                alt.Tooltip("plot_value:Q", title="T2M (°C)", format=".2f"),
            ],
        )
        .properties(title=title)
    )
    return _finish_chart(chart, 290), has_moving_average


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

    region_order = [region for region in REGION_ORDER if region in set(tables["region_month"]["region"])]

    left_col, right_col = st.columns([1, 1], gap="medium")
    with left_col:
        st.altair_chart(_region_ranking_chart(region_period), width="stretch")
    with right_col:
        st.altair_chart(_region_scatter_chart(region_period), width="stretch")

    st.altair_chart(
        _dumbbell_chart(location_period, multi_region=True),
        width="stretch",
    )

    heatmap_col, distribution_col = st.columns([1, 1], gap="medium")
    with heatmap_col:
        _warn_if_months_missing(tables["region_month"], "region")
        st.altair_chart(
            _heatmap_chart(
                tables["region_month"],
                row_field="region",
                row_title="Vùng",
                row_order=region_order,
                title="Nhiệt độ theo tháng và vùng",
                height=290,
                color_legend_bottom=True,
            ),
            width="stretch",
        )
    with distribution_col:
        distribution, is_boxplot = _annual_distribution_chart(
            tables["region_year"],
            category_field="region",
            category_title="Vùng",
            category_order=region_order,
            title="Phân bố nhiệt độ trung bình năm",
            region_colors=True,
            height=290,
            show_category_axis_title=False,
        )
        if not is_boxplot:
            st.info("Giai đoạn quá ngắn; hiển thị giá trị trung bình từng năm.")
        st.altair_chart(distribution, width="stretch")

    with st.expander("Xem diễn biến theo năm", expanded=False):
        trend, has_moving_average = _annual_trend_chart(
            tables["region_year"],
            group_field="region",
            group_title="Vùng",
            title="Trung bình năm và TB trượt 5 năm",
            region_colors=True,
        )
        if not has_moving_average:
            st.info("Giai đoạn đang chọn chưa đủ cửa sổ 5 năm; không tạo moving average giả.")
        st.altair_chart(trend, width="stretch")


def _render_single_region(tables: dict[str, pd.DataFrame]) -> None:
    location_period = tables["location_period"]
    region = str(location_period["region"].iloc[0])
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

    left_col, right_col = st.columns([1, 1], gap="medium")
    with left_col:
        st.altair_chart(_location_ranking_chart(location_period, region), width="stretch")
    with right_col:
        st.altair_chart(
            _dumbbell_chart(location_period, multi_region=False),
            width="stretch",
        )

    location_order = location_period.sort_values("mean_t2m", ascending=False)["location_label"].tolist()
    left_col, right_col = st.columns([1, 1], gap="medium")
    with left_col:
        _warn_if_months_missing(tables["location_month"], "location_id")
        st.altair_chart(
            _heatmap_chart(
                tables["location_month"],
                row_field="location_label",
                row_title="Điểm tham chiếu",
                row_order=location_order,
                title=f"Nhiệt độ theo tháng trong {region}",
                height=320,
            ),
            width="stretch",
        )
    with right_col:
        distribution, is_boxplot = _annual_distribution_chart(
            tables["location_year"],
            category_field="location_label",
            category_title="Điểm tham chiếu",
            category_order=location_order,
            title="Phân bố nhiệt độ trung bình năm theo địa điểm",
            region_colors=False,
            height=320,
        )
        if not is_boxplot:
            st.info("Giai đoạn quá ngắn; hiển thị giá trị trung bình từng năm.")
        st.altair_chart(distribution, width="stretch")

    with st.expander("Xem diễn biến theo năm", expanded=False):
        trend, has_moving_average = _annual_trend_chart(
            tables["location_year"],
            group_field="location_label",
            group_title="Điểm tham chiếu",
            title=f"Diễn biến nhiệt độ năm trong {region}",
            region_colors=False,
        )
        if not has_moving_average:
            st.info("Giai đoạn đang chọn chưa đủ cửa sổ 5 năm; không tạo moving average giả.")
        st.altair_chart(trend, width="stretch")


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

    left_col, right_col = st.columns([1, 1], gap="medium")
    with left_col:
        _warn_if_months_missing(tables["location_month"], "location_id")
        st.altair_chart(
            _monthly_profile_chart(tables["location_month"], location_label),
            width="stretch",
        )
        st.caption(f"Biên độ mùa: {_format_temperature(seasonality)}")
    with right_col:
        distribution, is_boxplot = _annual_distribution_chart(
            tables["location_year"],
            category_field="location_label",
            category_title="Điểm tham chiếu",
            category_order=[location_label],
            title="Phân bố nhiệt độ trung bình năm",
            region_colors=False,
            height=320,
        )
        if not is_boxplot:
            st.info("Giai đoạn quá ngắn; hiển thị giá trị trung bình từng năm.")
        st.altair_chart(distribution, width="stretch")

    with st.expander("Xem diễn biến theo năm", expanded=False):
        trend, has_moving_average = _annual_trend_chart(
            tables["location_year"],
            group_field="location_label",
            group_title="Điểm tham chiếu",
            title=f"Diễn biến nhiệt độ năm tại {location_label}",
            region_colors=False,
        )
        if not has_moving_average:
            st.info("Giai đoạn đang chọn chưa đủ cửa sổ 5 năm; không tạo moving average giả.")
        st.altair_chart(trend, width="stretch")


def render_temperature_comparison_tab(
    placeholder_box,
    filters: dict[str, object] | None = None,
) -> None:
    _ = placeholder_box
    st.markdown('<div class="section-title">So sánh đặc điểm nhiệt độ</div>', unsafe_allow_html=True)

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

    start_year, end_year = _parse_period(active_filters, daily)
    n_regions = int(scoped["region"].nunique())
    n_locations = int(scoped["location_id"].nunique())
    layout = _determine_layout(scoped)
    location_subset_active = bool(active_filters.get("locations", []))
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
