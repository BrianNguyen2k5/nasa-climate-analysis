import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
from pathlib import Path
import html

# --- Cấu hình hằng số ---
DATA_PATH = Path("data/nasa_power_vietnam_daily_clean.csv")

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
    "Bắc Trung Bộ": "#8B5CF6",
    "Nam Trung Bộ": "#F59E0B",
    "Trung du và miền núi phía Bắc": "#3B82F6",
    "Đông Nam Bộ": "#EF4444",
    "Đồng bằng sông Cửu Long": "#06B6D4",
    "Đồng bằng sông Hồng": "#10B981",
}


# --- Hàm hỗ trợ ---
def _escape(val: object) -> str:
    return html.escape(str(val), quote=True)


@st.cache_data(show_spinner=False)
def load_rainfall_humidity_data() -> pd.DataFrame:
    usecols = [
        "location_name",
        "region",
        "latitude",
        "longitude",
        "year",
        "month",
        "PRECTOTCORR",
        "RH2M",
        "heavy_rain_day"
    ]
    df = pd.read_csv(DATA_PATH, usecols=usecols)
    df["region_vn"] = df["region"].map(REGION_VIETNAMESE).fillna(df["region"])
    df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE).fillna(df["location_name"])
    return df


def filter_data(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    # Đồng bộ logic lấy period với Tab 4 để đảm bảo bộ lọc năm hoạt động
    period = filters.get("year_range") or filters.get("period") or (1991, 2025)
    start_year, end_year = period
    filtered = df[df["year"].between(int(start_year), int(end_year))]

    regions = filters.get("selected_regions") or filters.get("selected_region_keys")
    if regions:
        filtered = filtered[filtered["region_vn"].isin(regions)]

    locations = filters.get("selected_reference_points") or filters.get("locations")
    if locations:
        filtered = filtered[filtered["location_name"].isin(locations) | filtered["location_vn"].isin(locations)]

    return filtered


# --- Chú thích vùng ---
def render_region_legend():
    items_html = "".join([
        f'<div class="tab3-legend-item">'
        f'<span class="tab3-legend-dot" style="background:{color};"></span>'
        f'<span>{_escape(name)}</span></div>'
        for name, color in REGION_COLORS.items()
    ])
    st.markdown(f"""
        <style>
        .tab3-legend-box {{ 
            background: #ffffff; 
            border: 1px solid #e2e8f0; 
            border-radius: 8px; 
            padding: 16px 20px; 
            margin-top: 34px; 
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04); 
            height: 310px; 
            display: flex; 
            flex-direction: column; 
            justify-content: center; 
        }}
        .tab3-legend-header {{ 
            font-size: 14px; 
            font-weight: 750; 
            color: #1e3a5f; 
            margin-bottom: 12px; 
            padding-bottom: 8px; 
            border-bottom: 1px dashed #e2e8f0; 
        }}
        .tab3-legend-item {{ display: flex; align-items: center; gap: 10px; font-size: 12px; color: #334155; margin-bottom: 8px; }}
        .tab3-legend-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; flex-shrink: 0; }}
        </style>
        <div class="tab3-legend-box">
            <div class="tab3-legend-header">Nhóm các vùng</div>
            {items_html}
        </div>
    """, unsafe_allow_html=True)


# --- Biểu đồ Altair ---
def draw_line_chart(df, y_col, y_label):
    df_monthly = df.groupby(["month", "region_vn"])[y_col].mean().reset_index()
    chart = (
        alt.Chart(df_monthly).mark_line(point=True).encode(
            x=alt.X("month:O", title="Tháng", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{y_col}:Q", title=y_label, scale=alt.Scale(zero=False)),
            color=alt.Color("region_vn:N",
                            scale=alt.Scale(domain=list(REGION_COLORS.keys()), range=list(REGION_COLORS.values())),
                            legend=None),
            tooltip=[alt.Tooltip("month:O", title="Tháng"), alt.Tooltip("region_vn:N", title="Vùng"),
                     alt.Tooltip(f"{y_col}:Q", title=y_label, format=".2f")]
        )
        .properties(height=300, background="#FFFFFF", padding={"left": 10, "right": 10, "top": 10, "bottom": 10})
        .configure_view(fill="#FFFFFF", stroke="transparent")
        .configure_axis(labelFont="Plus Jakarta Sans", titleFont="Plus Jakarta Sans", labelColor="#475569",
                        titleColor="#1E3A5F", gridColor="#F1F5F9")
    )
    st.altair_chart(chart, use_container_width=True)


def draw_heatmap(df):
    df_hm = df.groupby(["month", "region_vn"])["PRECTOTCORR"].mean().reset_index()
    chart = (
        alt.Chart(df_hm).mark_rect().encode(
            x=alt.X("month:O", title="Tháng", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("region_vn:N", title="Vùng", axis=alt.Axis(labelLimit=300)),
            color=alt.Color("PRECTOTCORR:Q", title="Lượng mưa (mm)", scale=alt.Scale(scheme="blues")),
            tooltip=[alt.Tooltip("month:O", title="Tháng"), alt.Tooltip("region_vn:N", title="Vùng"),
                     alt.Tooltip("PRECTOTCORR:Q", title="Lượng mưa trung bình (mm)", format=".2f")]
        )
        .properties(height=310, background="#FFFFFF", padding={"left": 10, "right": 10, "top": 10, "bottom": 10})
        .configure_view(fill="#FFFFFF", stroke="transparent")
        .configure_axis(labelFont="Plus Jakarta Sans", titleFont="Plus Jakarta Sans", gridColor="#F1F5F9")
    )
    st.altair_chart(chart, use_container_width=True)


def draw_map(df):
    df_map = df.groupby(["location_vn", "latitude", "longitude"])["heavy_rain_day"].sum().reset_index()
    fig = px.scatter_mapbox(
        df_map, lat="latitude", lon="longitude", size="heavy_rain_day", color="heavy_rain_day",
        hover_name="location_vn", color_continuous_scale="Tealgrn",
        zoom=3.75, center={"lat": 16.1, "lon": 108.3},
        mapbox_style="carto-positron",
        labels={"heavy_rain_day": "Số ngày mưa lớn"},
        hover_data={"latitude": False, "longitude": False, "heavy_rain_day": True}
    )
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=310, paper_bgcolor="white",
                      coloraxis_colorbar_title="Số ngày")
    st.plotly_chart(fig, use_container_width=True)


# --- Hàm render chính ---
def render_rainfall_humidity_tab(placeholder_box, filters: dict | None = None) -> None:
    # CSS ẩn KPI hàng trên của app.py
    st.markdown("""
        <style>
        div[data-testid="stVerticalBlock"] > div:has(div.metric-card):not(:has(span.kpi-number)) {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Đảm bảo lấy filter đúng cách
    active_filters = filters or {
        "selected_regions": st.session_state.get("selected_regions", []),
        "selected_reference_points": st.session_state.get("selected_reference_points", []),
        "year_range": st.session_state.get("year_range", (1991, 2025)),
    }

    df = filter_data(load_rainfall_humidity_data(), active_filters)
    if df.empty:
        st.info("Không có dữ liệu phù hợp.")
        return

    # 1. KPIs
    loc_stats = df.groupby("location_vn").agg(
        {"PRECTOTCORR": "mean", "RH2M": "mean", "heavy_rain_day": "sum"}).reset_index()
    max_rain = loc_stats.loc[loc_stats["PRECTOTCORR"].idxmax()]
    max_hum = loc_stats.loc[loc_stats["RH2M"].idxmax()]
    max_heavy_days = loc_stats.loc[loc_stats["heavy_rain_day"].idxmax()]

    kcols = st.columns(4)
    kpis = [
        {"t": "Lượng mưa trung bình cao nhất", "v": f"{max_rain['PRECTOTCORR']:.2f} mm", "s": max_rain["location_vn"]},
        {"t": "Độ ẩm trung bình cao nhất", "v": f"{max_hum['RH2M']:.1f} %", "s": max_hum["location_vn"]},
        {"t": "Số ngày mưa lớn nhiều nhất", "v": f"{int(max_heavy_days['heavy_rain_day'])} ngày",
         "s": max_heavy_days["location_vn"]},
        {"t": "Độ ẩm trung bình toàn khu vực", "v": f"{df['RH2M'].mean():.1f} %", "s": "Dữ liệu tổng hợp"}
    ]
    for col, k in zip(kcols, kpis):
        with col:
            st.markdown(f"""
                <div class="metric-card overview-kpi-card">
                    <div class="metric-label">{k['t']}</div>
                    <div class="kpi-value-row"><span class="kpi-number">{k['v']}</span></div>
                    <div class="overview-kpi-subject">{k['s']}</div>
                </div>
            """, unsafe_allow_html=True)

    # 2. Hàng 1
    col1, col2, col3 = st.columns([1, 1, 0.5])
    with col1:
        st.markdown(
            '<div class="section-title" style="margin-top: 8px; margin-bottom: 6px; font-size: 15px; font-weight: 750; color: #1E3A5F;">Xu thế lượng mưa trung bình theo tháng</div>',
            unsafe_allow_html=True)
        draw_line_chart(df, "PRECTOTCORR", "Lượng mưa (mm)")
    with col2:
        st.markdown(
            '<div class="section-title" style="margin-top: 8px; margin-bottom: 6px; font-size: 15px; font-weight: 750; color: #1E3A5F;">Xu thế độ ẩm tương đối trung bình</div>',
            unsafe_allow_html=True)
        draw_line_chart(df, "RH2M", "Độ ẩm (%)")
    with col3:
        render_region_legend()

    # 3. Hàng 2
    col4, col5 = st.columns([1.3, 1])
    with col4:
        st.markdown(
            '<div class="section-title" style="margin-top: 8px; margin-bottom: 6px; font-size: 15px; font-weight: 750; color: #1E3A5F;">Cường độ mưa theo vùng (Heatmap)</div>',
            unsafe_allow_html=True)
        draw_heatmap(df)
    with col5:
        st.markdown(
            '<div class="section-title" style="margin-top: 8px; margin-bottom: 6px; font-size: 15px; font-weight: 750; color: #1E3A5F;">Số ngày mưa lớn theo địa điểm</div>',
            unsafe_allow_html=True)
        draw_map(df)