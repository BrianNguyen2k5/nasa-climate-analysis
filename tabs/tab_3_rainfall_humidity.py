import streamlit as st
import plotly.express as px
import pandas as pd
import os

# Hàm bổ trợ để đọc dữ liệu (Nháp)
@st.cache_data
def load_data():
    path="data/nasa_power_vietnam_daily_clean.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return None

def render_rainfall_humidity_tab(placeholder_box) -> None:
    st.markdown('<div class="section-title">So sánh mưa và độ ẩm</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="small-note">Khu vực dành cho lượng mưa, mùa mưa, độ ẩm tương đối.</p>',
        unsafe_allow_html=True,
    )

    df_raw = load_data()

    # Kiểm tra nếu chưa có dữ liệu
    if df_raw is None:
        st.warning("Không tìm thấy dữ liệu")
        return

    # --- 1. MAPPING ĐỂ LỌC---
    REGION_MAP = {
        "Bắc Bộ": "North", "Bắc Trung Bộ": "North Central", "Nam Trung Bộ": "South Central Coast",
        "Tây Nguyên": "Central Highlands", "Đông Nam Bộ": "Southeast",
        "Tây Nam Bộ": "Mekong Delta", "Trung Bộ": "Central"
    }

    # Mapping ngược để Việt hóa tên trên biểu đồ
    REVERSE_MAP = {
        "North": "Bắc Bộ", "North Central": "Bắc Trung Bộ",
        "South Central Coast": "Nam Trung Bộ", "Central Highlands": "Tây Nguyên",
        "Southeast": "Đông Nam Bộ", "Mekong Delta": "Tây Nam Bộ", "Central": "Trung Bộ"
    }

    LOCATION_MAP = {
        "Hà Nội": "Ha Noi", "Lào Cai": "Lao Cai", "Điện Biên": "Dien Bien Phu",
        "Châu Đốc": "Chau Doc", "Hải Phòng": "Hai Phong", "Vũng Tàu": "Vung Tau",
        "Vinh": "Vinh", "Huế": "Hue", "Đà Nẵng": "Da Nang",
        "Quy Nhơn": "Quy Nhon", "Nha Trang": "Nha Trang", "Phan Rang - Tháp Chàm": "Phan Rang-Thap Cham",
        "Đồng Hới": "Dong Hoi", "Pleiku": "Pleiku", "Buôn Ma Thuột": "Buon Ma Thuot",
        "Đà Lạt": "Da Lat", "TP. Hồ Chí Minh": "Ho Chi Minh City",
        "Cần Thơ": "Can Tho", "Cà Mau": "Ca Mau", "Phú Quốc": "Phu Quoc"
    }

    # --- 2. LẤY FILTER ---
    raw_region = st.session_state.get("sb_regions", "Tất cả 7 nhóm vùng")
    raw_locations = st.session_state.get("sb_location", [])
    year_range = st.session_state.get("sb_year_range", (1991, 2025))

    df = df_raw.copy()
    df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

    if raw_region != "Tất cả 7 nhóm vùng":
        ds_val = REGION_MAP.get(raw_region)
        df = df[df['region'].isin(ds_val)] if isinstance(ds_val, list) else df[df['region'] == ds_val]

    if raw_locations:
        ds_locs = [LOCATION_MAP.get(loc, loc) for loc in raw_locations]
        df = df[df['location_name'].isin(ds_locs)]

    if df.empty:
        st.info("Không tìm thấy dữ liệu. Hãy chọn địa điểm thuộc vùng tương ứng.")
        return

    # Nhãn Việt hóa cho Plotly
    VN_LABELS = {'avg_rain': 'Lượng mưa', 'avg_hum': 'Độ ẩm (%)', 'month_name': 'Tháng', 'region': 'Vùng'}
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


    # --- 3. HÀNG 1: BIỂU ĐỒ ĐƯỜNG---
    r_col, h_col = st.columns(2)

    # Line Chart Xu thế lượng mưa TB
    with r_col:
        # Gom nhóm dữ liệu để vẽ
        df_r = df.groupby(['region', 'month', 'month_name'])['PRECTOTCORR'].mean().reset_index().sort_values('month')
        df_r.rename(columns={'PRECTOTCORR': 'avg_rain'}, inplace=True)

        fig_r = px.line(df_r, x='month_name', y='avg_rain', color='region',
                        title="Xu thế lượng mưa TB theo tháng (mm/ngày)", markers=True, labels=VN_LABELS)

        # Việt hóa tên vùng trong Legend
        fig_r.for_each_trace(lambda t: t.update(name=REVERSE_MAP.get(t.name, t.name)))
        fig_r.update_layout(xaxis_title="Tháng", yaxis_title="Lượng mưa (mm/ngày)",
                            legend=dict(orientation="h", y=-0.2), legend_title_text="Vùng")
        st.plotly_chart(fig_r, use_container_width=True)

    # Line Chart Xu thế độ ẩm tương đối TB
    with h_col:
        df_h = df.groupby(['region', 'month', 'month_name'])['RH2M'].mean().reset_index().sort_values('month')
        df_h.rename(columns={'RH2M': 'avg_hum'}, inplace=True)

        fig_h = px.line(df_h, x='month_name', y='avg_hum', color='region',
                        title="Xu thế độ ẩm tương đối TB (%)", markers=True, labels=VN_LABELS)

        fig_h.for_each_trace(lambda t: t.update(name=REVERSE_MAP.get(t.name, t.name)))
        fig_h.update_layout(xaxis_title="Tháng", yaxis_title="Độ ẩm (%)",
                            legend=dict(orientation="h", y=-0.2), legend_title_text="Vùng")
        st.plotly_chart(fig_h, use_container_width=True)

    # --- 4. HÀNG 2: HEATMAP, MAP, STACKED BAR ---
    c1, c2 = st.columns(2)

    # Heatmap Cường độ mưa
    with c1:
        # Heatmap: Việt hóa trục Y và Colobar
        fig_hm = px.density_heatmap(df_r, x='month_name', y='region', z='avg_rain',
                                    title="Cường độ mưa (Heatmap)", color_continuous_scale='Blues', height=450,
                                    labels={'avg_rain': 'Lượng mưa', 'month_name': 'Tháng', 'region': 'Vùng'},
                                    category_orders={"month_name": month_order})
        fig_hm.update_coloraxes(colorbar_title_text='Lượng mưa')

        # Việt hóa các nhãn vùng trên trục đứng
        fig_hm.update_yaxes(ticktext=[REVERSE_MAP.get(label, label) for label in df_r['region'].unique()],
                            tickvals=df_r['region'].unique())
        st.plotly_chart(fig_hm, use_container_width=True)

    # Bản đồ số ngày mưa lớn
    with c2:
        df_m = df.groupby(['location_name', 'latitude', 'longitude'])['heavy_rain_day'].sum().reset_index()
        fig_m = px.scatter_mapbox(df_m, lat="latitude", lon="longitude", size="heavy_rain_day",
                                  color="heavy_rain_day", hover_name="location_name",
                                  zoom=4.2, center={"lat": 16.4, "lon": 107.5},
                                  title="Số ngày mưa lớn (Lượng mưa > 50mm)", labels={'heavy_rain_day': 'Số ngày'},
                                  color_continuous_scale='Tealgrn', mapbox_style="carto-positron")

        fig_m.update_layout(margin=dict(t=30, b=0, l=0, r=0), coloraxis_colorbar_title_text='Số ngày')
        st.plotly_chart(fig_m, use_container_width=True)
