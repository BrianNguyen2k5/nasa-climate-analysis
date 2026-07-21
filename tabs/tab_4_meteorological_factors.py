from pathlib import Path
import html
import re
import altair as alt
import pandas as pd
import streamlit as st

DATA_PATH = Path("data/nasa_power_vietnam_daily_clean.csv")
ALL_REGIONS_LABEL = "Tất cả 6 nhóm vùng"

REGION_VIETNAMESE = {
    "Bắc Trung Bộ": "Bắc Trung Bộ",
    "Nam Trung Bộ": "Nam Trung Bộ",
    "Trung du và miền núi phía Bắc": "Trung du và miền núi phía Bắc",
    "Đông Nam Bộ": "Đông Nam Bộ",
    "Đồng bằng sông Cửu Long": "Đồng bằng sông Cửu Long",
    "Đồng bằng sông Hồng": "Đồng bằng sông Hồng",
}

LOCATION_VIETNAMESE = {
    "Buon Ma Thuot": "Buôn Ma Thuột",
    "Ca Mau": "Cà Mau",
    "Can Tho": "Cần Thơ",
    "Chau Doc": "Châu Đốc",
    "Da Lat": "Đà Lạt",
    "Da Nang": "Đà Nẵng",
    "Dien Bien Phu": "Điện Biên Phủ",
    "Dong Hoi": "Đồng Hới",
    "Ha Noi": "Hà Nội",
    "Hai Phong": "Hải Phòng",
    "Ho Chi Minh City": "TP. Hồ Chí Minh",
    "Hue": "Huế",
    "Lao Cai": "Lào Cai",
    "Nha Trang": "Nha Trang",
    "Phan Rang-Thap Cham": "Phan Rang - Tháp Chàm",
    "Phu Quoc": "Phú Quốc",
    "Pleiku": "Pleiku",
    "Quy Nhon": "Quy Nhơn",
    "Vinh": "Vinh",
    "Vung Tau": "Vũng Tàu",
}

REGION_COLORS = {
    "Bắc Trung Bộ": "#8B5CF6",                   # Tím
    "Nam Trung Bộ": "#F59E0B",                   # Cam
    "Trung du và miền núi phía Bắc": "#3B82F6",   # Xanh dương
    "Đông Nam Bộ": "#EF4444",                     # Đỏ
    "Đồng bằng sông Cửu Long": "#06B6D4",         # Xanh ngọc
    "Đồng bằng sông Hồng": "#10B981",             # Xanh lá
}


def _escape(val: object) -> str:
    return html.escape(str(val), quote=True)


def _format_num(val: float, digits: int = 1) -> str:
    return f"{val:.{digits}f}".replace(".", ",")


def _split_value(value: str) -> tuple[str, str]:
    match = re.match(r"^([\d.,]+)\s*(.*)$", value)
    if not match:
        return value, ""
    return match.group(1), match.group(2).strip()


@st.cache_data(show_spinner=False)
def load_meteorological_data() -> pd.DataFrame:
    usecols = [
        "location_name",
        "region",
        "latitude",
        "longitude",
        "year",
        "month",
        "WS10M",
        "PS",
        "ALLSKY_SFC_SW_DWN",
    ]
    df = pd.read_csv(DATA_PATH, usecols=usecols)
    df["region_vn"] = df["region"].map(REGION_VIETNAMESE).fillna(df["region"])
    df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE).fillna(df["location_name"])
    return df


def filter_meteorological_data(df: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    period = filters.get("year_range") or filters.get("period") or (1991, 2025)
    start_year, end_year = period
    filtered = df[df["year"].between(int(start_year), int(end_year))]

    regions = filters.get("selected_regions") or filters.get("selected_region_keys") or filters.get("region")
    if isinstance(regions, str):
        regions = [regions] if regions != ALL_REGIONS_LABEL else []

    if isinstance(regions, list) and regions and len(regions) < len(REGION_VIETNAMESE):
        filtered = filtered[
            filtered["region_vn"].isin(regions) | filtered["region"].isin(regions)
        ]

    locations = filters.get("selected_reference_points") or filters.get("locations")
    if isinstance(locations, str):
        locations = [locations]

    if isinstance(locations, list) and locations:
        filtered = filtered[
            filtered["location_name"].isin(locations) | filtered["location_vn"].isin(locations)
        ]

    return filtered


def _calc_location_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["location_vn", "region_vn", "wind_mean", "solar_mean", "pressure_mean", "potential_score"]
        )

    summary = (
        df.groupby(["location_name", "location_vn", "region_vn"], as_index=False)
        .agg(
            wind_mean=("WS10M", "mean"),
            solar_mean=("ALLSKY_SFC_SW_DWN", "mean"),
            pressure_mean=("PS", "mean"),
        )
    )
    summary["wind_mean"] = summary["wind_mean"].round(2)
    summary["solar_mean"] = summary["solar_mean"].round(2)
    summary["pressure_mean"] = summary["pressure_mean"].round(1)
    summary["potential_score"] = (summary["solar_mean"] * summary["wind_mean"]).round(1)

    return summary.sort_values("potential_score", ascending=False)


def _calc_yearly_region_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["year", "region_vn", "wind_mean", "solar_mean", "pressure_mean"])

    df_yearly = (
        df.groupby(["year", "region_vn"], as_index=False)
        .agg(
            wind_mean=("WS10M", "mean"),
            solar_mean=("ALLSKY_SFC_SW_DWN", "mean"),
            pressure_mean=("PS", "mean"),
        )
    )
    df_yearly["wind_mean"] = df_yearly["wind_mean"].round(2)
    df_yearly["solar_mean"] = df_yearly["solar_mean"].round(2)
    df_yearly["pressure_mean"] = df_yearly["pressure_mean"].round(1)
    return df_yearly.sort_values(["year", "region_vn"])


def _calc_monthly_complementarity_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["month", "month_label", "solar_mean", "wind_mean", "solar_norm", "wind_norm"])

    df_monthly = (
        df.groupby("month", as_index=False)
        .agg(
            solar_mean=("ALLSKY_SFC_SW_DWN", "mean"),
            wind_mean=("WS10M", "mean"),
        )
    )
    df_monthly["solar_mean"] = df_monthly["solar_mean"].round(2)
    df_monthly["wind_mean"] = df_monthly["wind_mean"].round(2)
    df_monthly["month_label"] = df_monthly["month"].astype(str)

    # Min-Max Normalization (0% to 100%) for single Y-axis comparison
    solar_min, solar_max = df_monthly["solar_mean"].min(), df_monthly["solar_mean"].max()
    wind_min, wind_max = df_monthly["wind_mean"].min(), df_monthly["wind_mean"].max()

    if solar_max != solar_min:
        df_monthly["solar_norm"] = ((df_monthly["solar_mean"] - solar_min) / (solar_max - solar_min) * 100).round(1)
    else:
        df_monthly["solar_norm"] = 100.0

    if wind_max != wind_min:
        df_monthly["wind_norm"] = ((df_monthly["wind_mean"] - wind_min) / (wind_max - wind_min) * 100).round(1)
    else:
        df_monthly["wind_norm"] = 100.0

    return df_monthly.sort_values("month")


def render_meteorological_kpis(df_summary: pd.DataFrame) -> None:
    if df_summary.empty:
        return

    top_wind = df_summary.loc[df_summary["wind_mean"].idxmax()]
    min_wind = df_summary.loc[df_summary["wind_mean"].idxmin()]
    top_solar = df_summary.loc[df_summary["solar_mean"].idxmax()]
    top_pressure = df_summary.loc[df_summary["pressure_mean"].idxmax()]
    kpis = [
        {
            "title": "Tốc độ gió TB cao nhất",
            "value": f"{_format_num(top_wind['wind_mean'])} m/s",
            "subject": top_wind["location_vn"],
        },
        {
            "title": "Bức xạ mặt trời cao nhất",
            "value": f"{_format_num(top_solar['solar_mean'])} MJ/m²/ngày",
            "subject": top_solar["location_vn"],
        },
        {
            "title": "Áp suất khí quyển cao nhất",
            "value": f"{_format_num(top_pressure['pressure_mean'], 1)} kPa",
            "subject": top_pressure["location_vn"],
        },
        {
            "title": "Khu vực lặng gió nhất",
            "value": f"{_format_num(min_wind['wind_mean'])} m/s",
            "subject": min_wind["location_vn"],
        },
    ]

    cols = st.columns(4)
    for col, kpi in zip(cols, kpis):
        with col:
            number, unit = _split_value(kpi["value"])
            unit_html = f'<span class="kpi-unit">{_escape(unit)}</span>' if unit else ""
            st.markdown(
                f"""
                <div class="metric-card overview-kpi-card">
                    <div class="metric-label">{_escape(kpi['title'])}</div>
                    <div class="kpi-value-row">
                        <span class="kpi-number">{_escape(number)}</span>{unit_html}
                    </div>
                    <div class="overview-kpi-subject">{_escape(kpi['subject'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_shared_region_legend() -> None:
    items_html = "".join([
        f'<div class="tab4-legend-item-v">'
        f'<span class="tab4-legend-dot" style="background:{color};"></span>'
        f'<span>{_escape(reg_name)}</span>'
        f'</div>'
        for reg_name, color in REGION_COLORS.items()
    ])

    html_content = (
        f'<style>'
        f'.tab4-legend-box-vertical {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 20px; margin-top: 14px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04); height: 310px; display: flex; flex-direction: column; justify-content: center; }}'
        f'.tab4-legend-header {{ font-size: 14px; font-weight: 750; color: #1e3a5f; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed #e2e8f0; }}'
        f'.tab4-legend-list-vertical {{ display: flex; flex-direction: column; gap: 12px; }}'
        f'.tab4-legend-item-v {{ display: flex; align-items: center; gap: 10px; font-size: 12px; color: #334155; }}'
        f'.tab4-legend-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; flex-shrink: 0; }}'
        f'</style>'
        f'<div class="tab4-legend-box-vertical">'
        f'<div class="tab4-legend-header">Nhóm các vùng</div>'
        f'<div class="tab4-legend-list-vertical">{items_html}</div>'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)


def render_green_energy_scatter_chart(df_summary: pd.DataFrame) -> None:
    domain = list(REGION_COLORS.keys())
    range_colors = list(REGION_COLORS.values())

    solar_avg = df_summary["solar_mean"].mean()
    wind_avg = df_summary["wind_mean"].mean()

    # Interactive selection parameter on region_vn
    highlight = alt.selection_point(fields=["region_vn"], on="click", clear="dblclick")

    scatter = (
        alt.Chart(df_summary)
        .mark_circle(size=180, opacity=0.88, stroke="#FFFFFF", strokeWidth=1.5)
        .encode(
            x=alt.X(
                "solar_mean:Q",
                title="Bức xạ mặt trời trung bình (MJ/m²/ngày)",
                scale=alt.Scale(zero=False, padding=20),
            ),
            y=alt.Y(
                "wind_mean:Q",
                title="Tốc độ gió trung bình 10m (m/s)",
                scale=alt.Scale(zero=False, padding=20),
            ),
            color=alt.Color(
                "region_vn:N",
                title="Vùng khí hậu",
                scale=alt.Scale(domain=domain, range=range_colors),
                legend=None,
            ),
            opacity=alt.condition(highlight, alt.value(0.95), alt.value(0.20)),
            tooltip=[
                alt.Tooltip("location_vn:N", title="Tỉnh/Thành phố"),
                alt.Tooltip("region_vn:N", title="Vùng"),
                alt.Tooltip("solar_mean:Q", title="Bức xạ mặt trời (MJ/m²/ngày)", format=".2f"),
                alt.Tooltip("wind_mean:Q", title="Tốc độ gió (m/s)", format=".2f"),
                alt.Tooltip("pressure_mean:Q", title="Áp suất (kPa)", format=".1f"),
                alt.Tooltip("potential_score:Q", title="Điểm Tiềm năng Xanh", format=".1f"),
            ],
        )
        .add_params(highlight)
    )

    labels = (
        alt.Chart(df_summary)
        .mark_text(align="left", baseline="middle", dx=12, fontSize=12, color="#1E3A5F")
        .encode(
            x="solar_mean:Q",
            y="wind_mean:Q",
            text="location_vn:N",
            opacity=alt.condition(highlight, alt.value(1.0), alt.value(0.20)),
        )
    )

    x_rule = (
        alt.Chart(pd.DataFrame({"solar_avg": [solar_avg]}))
        .mark_rule(color="#94A3B8", strokeDash=[4, 4], strokeWidth=1.2)
        .encode(x="solar_avg:Q")
    )

    y_rule = (
        alt.Chart(pd.DataFrame({"wind_avg": [wind_avg]}))
        .mark_rule(color="#94A3B8", strokeDash=[4, 4], strokeWidth=1.2)
        .encode(y="wind_avg:Q")
    )

    chart = (
        (scatter + labels + x_rule + y_rule)
        .properties(
					height=330, 
					background="#FFFFFF",
					padding={"left": 0, "right": 0, "top": 10, "bottom": 10}	
				)
        .configure_view(fill="#FFFFFF", stroke="transparent")
        .configure_axis(
            labelFont="Plus Jakarta Sans",
            titleFont="Plus Jakarta Sans",
            labelColor="#475569",
            titleColor="#1E3A5F",
            labelFontSize=12,
            titleFontSize=13,
            gridColor="#F1F5F9",
        )
    )

    st.altair_chart(chart, use_container_width=True)


def render_region_yearly_trend_chart(df_yearly: pd.DataFrame) -> None:
    domain = list(REGION_COLORS.keys())
    range_colors = list(REGION_COLORS.values())

    var_option = st.selectbox(
        "Biến khí tượng theo năm",
        ["Bức xạ mặt trời", "Tốc độ gió", "Áp suất khí quyển"],
        key="tab4_yearly_var_select",
        label_visibility="collapsed",
    )

    if var_option == "Bức xạ mặt trời":
        y_col = "solar_mean"
        y_title = "Bức xạ (MJ/m²/ngày)"
    elif var_option == "Tốc độ gió":
        y_col = "wind_mean"
        y_title = "Tốc độ gió (m/s)"
    else:
        y_col = "pressure_mean"
        y_title = "Áp suất (kPa)"

    # Interactive selection parameter on region_vn
    highlight = alt.selection_point(fields=["region_vn"], on="click", clear="dblclick")

    chart = (
        alt.Chart(df_yearly)
        .mark_line(strokeWidth=2.2, point=False)
        .encode(
            x=alt.X("year:O", title="Năm", axis=alt.Axis(labelAngle=0, tickCount=6)),
            y=alt.Y(f"{y_col}:Q", title=y_title, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "region_vn:N",
                title="Vùng khí hậu",
                scale=alt.Scale(domain=domain, range=range_colors),
                legend=None,
            ),
            opacity=alt.condition(highlight, alt.value(1.0), alt.value(0.20)),
            tooltip=[
                alt.Tooltip("year:O", title="Năm"),
                alt.Tooltip("region_vn:N", title="Vùng"),
                alt.Tooltip(f"{y_col}:Q", title=y_title, format=".2f"),
            ],
        )
        .add_params(highlight)
        .properties(
					height=280, 
					background="#FFFFFF",
					padding={"left": 10, "right": 0, "top": 10, "bottom": 10}
				)
        .configure_view(fill="#FFFFFF", stroke="transparent")
        .configure_axis(
            labelFont="Plus Jakarta Sans",
            titleFont="Plus Jakarta Sans",
            labelColor="#475569",
            titleColor="#1E3A5F",
            labelFontSize=12,
            titleFontSize=13,
            gridColor="#F1F5F9",
        )
    )

    st.altair_chart(chart, use_container_width=True)


def render_seasonal_complementarity_chart(df: pd.DataFrame) -> None:
    df_monthly = _calc_monthly_complementarity_summary(df)

    if df_monthly.empty:
        st.info("Không có dữ liệu tháng.")
        return

    # Melt data for single chart with normalized % Y-axis
    df_melted = df_monthly.melt(
        id_vars=["month_label", "solar_mean", "wind_mean"],
        value_vars=["solar_norm", "wind_norm"],
        var_name="indicator",
        value_name="norm_percent",
    )
    df_melted["indicator_name"] = df_melted["indicator"].map({
        "solar_norm": "Bức xạ mặt trời (%)",
        "wind_norm": "Tốc độ gió (%)",
    })

    chart = (
        alt.Chart(df_melted)
        .mark_line(strokeWidth=2.8, point=alt.OverlayMarkDef(size=50))
        .encode(
            x=alt.X("month_label:O", title="Tháng trong năm", sort=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "norm_percent:Q",
                title="Mức độ hoạt động (%)",
                scale=alt.Scale(domain=[0, 105]),
            ),
            color=alt.Color(
                "indicator_name:N",
                title="Chỉ số khí tượng:",
                scale=alt.Scale(
                    domain=["Bức xạ mặt trời (%)", "Tốc độ gió (%)"],
                    range=["#F59E0B", "#06B6D4"],
                ),
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    titleOrient="left",
                    labelFontSize=13,
                    titleFontSize=13,
                    titlePadding=16,
                    columnPadding=32,
                    labelOffset=6,
                ),
            ),
            tooltip=[
                alt.Tooltip("month_label:O", title="Tháng"),
                alt.Tooltip("indicator_name:N", title="Chỉ số"),
                alt.Tooltip("norm_percent:Q", title="Mức độ so với Đỉnh", format=".1f"),
                alt.Tooltip("solar_mean:Q", title="Bức xạ thực tế (MJ/m²)", format=".2f"),
                alt.Tooltip("wind_mean:Q", title="Gió thực tế (m/s)", format=".2f"),
            ],
        )
        .properties(
					height=310, 
					background="#FFFFFF",
					padding={"left": 10, "right": 0, "top": 10, "bottom": 10}  # Padding 20px ở đáy
				)
        .configure_view(fill="#FFFFFF", stroke="transparent")
        .configure_axis(
            labelFont="Plus Jakarta Sans",
            titleFont="Plus Jakarta Sans",
            labelColor="#475569",
            titleColor="#1E3A5F",
            labelFontSize=12,
            titleFontSize=13,
            gridColor="#F1F5F9",
        )
    )

    st.altair_chart(chart, use_container_width=True)


def render_meteorological_factors_tab(placeholder_box, filters: dict[str, object] | None = None) -> None:
    active_filters = filters or {
        "selected_regions": list(REGION_VIETNAMESE.keys()),
        "selected_reference_points": list(LOCATION_VIETNAMESE.keys()),
        "year_range": (1991, 2025),
    }

    try:
        df = load_meteorological_data()
        filtered_df = filter_meteorological_data(df, active_filters)
    except Exception as exc:
        st.error(f"Lỗi nạp dữ liệu khí tượng: {exc}")
        return



    df_summary = _calc_location_summary(filtered_df)
    df_yearly = _calc_yearly_region_summary(filtered_df)

    # Render top 4 Meteorological KPI Cards
    render_meteorological_kpis(df_summary)

    # Row 1: 2 columns layout: Left (Scatter) vs Right (Yearly Trend Line Chart)
    col1_left, col1_right = st.columns([1.15, 1])

    with col1_left:
        st.markdown(
            '<div class="section-title" style="margin-top: 8px; margin-bottom: 6px; font-size: 15px; font-weight: 750; color: #1E3A5F;">'
            'Biểu đồ mối quan hệ giữa Bức xạ và Gió ở mỗi Địa điểm của 6 Vùng'
            '</div>',
            unsafe_allow_html=True,
        )
        if not df_summary.empty:
            render_green_energy_scatter_chart(df_summary)
        else:
            st.info("Không có dữ liệu phù hợp với bộ lọc hiện tại.")

    with col1_right:
        st.markdown(
            '<div class="section-title" style="margin-top: 8px; margin-bottom: 4px; font-size: 14px; font-weight: 750; color: #1E3A5F;">'
            'Biểu đồ biến thiên Khí tượng theo năm của 6 Vùng'
            '</div>',
            unsafe_allow_html=True,
        )
        if not df_yearly.empty:
            render_region_yearly_trend_chart(df_yearly)
        else:
            st.info("Không có dữ liệu.")

    # Row 2: 2 columns layout: Left (Seasonal Complementarity) vs Right (Shared Region Legend Box)
    col2_left, col2_right = st.columns([1.2, 0.8])

    with col2_left:
        st.markdown(
            '<div class="section-title" style="margin-top: -12px; margin-bottom: 4px; font-size: 15px; font-weight: 750; color: #1E3A5F;">'
            'Biểu đồ mối quan hệ bổ trợ của Bức xạ và Gió theo từng tháng'
            '</div>',
            unsafe_allow_html=True,
        )
        if not filtered_df.empty:
            render_seasonal_complementarity_chart(filtered_df)
        else:
            st.info("Không có dữ liệu phù hợp với bộ lọc hiện tại.")

    with col2_right:
        render_shared_region_legend()
