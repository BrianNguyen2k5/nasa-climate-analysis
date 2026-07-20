import streamlit as st


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

LOCATIONS_BY_REGION = {
    "Bắc Trung Bộ": ["Dong Hoi", "Hue", "Vinh"],
    "Nam Trung Bộ": ["Buon Ma Thuot", "Da Lat", "Da Nang", "Nha Trang", "Phan Rang-Thap Cham", "Pleiku", "Quy Nhon"],
    "Trung du và miền núi phía Bắc": ["Dien Bien Phu", "Lao Cai"],
    "Đông Nam Bộ": ["Ho Chi Minh City", "Vung Tau"],
    "Đồng bằng sông Cửu Long": ["Ca Mau", "Can Tho", "Chau Doc", "Phu Quoc"],
    "Đồng bằng sông Hồng": ["Ha Noi", "Hai Phong"],
}

LOCATIONS_BY_REGION_VN = {
    REGION_VIETNAMESE.get(region, region): [LOCATION_VIETNAMESE.get(location, location) for location in locations]
    for region, locations in LOCATIONS_BY_REGION.items()
}

ALL_REGIONS_LABEL = "Tất cả 6 nhóm vùng"
NAV_ITEMS = [
    "Tổng quan",
    "Nhiệt độ",
    "Mưa và độ ẩm",
    "Yếu tố khí tượng",
    "Thời tiết cực đoan",
    "AI",
]


def inject_sidebar_css() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                background: #ffffff;
                border-right: 1px solid var(--border);
            }

            [data-testid="stSidebar"] > div:first-child,
            [data-testid="stSidebarUserContent"] {
                padding-top: 0;
            }

            [data-testid="stSidebar"] .element-container {
                margin-bottom: 0.14rem;
            }

            [data-testid="stSidebar"] h1 {
                color: var(--primary);
                font-size: 1.26rem;
                line-height: 1.05;
                margin-top: -0.8rem;
                margin-bottom: 0.14rem;
            }

            [data-testid="stSidebar"] label {
                color: var(--primary);
            }

            [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
                gap: 0.18rem;
            }

            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
                min-height: 1rem;
                margin-bottom: 0.04rem;
            }

            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
            [data-testid="stSidebar"] label p {
                font-size: 0.84rem;
                line-height: 1.1;
            }

            [data-testid="stSidebar"] [data-baseweb="select"] > div,
            [data-testid="stSidebar"] [data-baseweb="select"] input {
                min-height: 34px;
            }

            [data-testid="stSidebar"] [data-testid="stRadio"] {
                width: 100%;
                margin-bottom: 0.14rem;
            }

            [data-testid="stSidebar"] [role="radiogroup"] {
                width: 100%;
                gap: 0.18rem;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label {
                width: 100%;
                max-width: 100%;
                box-sizing: border-box;
                min-height: 32px;
                background: #f8fafc;
                border: 1px solid var(--border);
                border-radius: 7px;
                padding: 5px 10px;
                margin: 0;
                display: flex;
                align-items: center;
                box-shadow: 0 1px 2px rgba(30, 58, 95, 0.04);
                transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label input[type="radio"],
            [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
                display: none !important;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label:hover {
                background: #eef3f8;
                border-color: var(--primary);
                box-shadow: 0 4px 12px rgba(30, 58, 95, 0.10);
            }

            [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
                background: #eef3f8;
                border-color: var(--primary);
                box-shadow: inset 4px 0 0 var(--primary), 0 4px 12px rgba(30, 58, 95, 0.10);
            }

            [data-testid="stSidebar"] [role="radiogroup"] label p {
                color: var(--primary);
                font-weight: 660;
                font-size: 0.84rem;
                line-height: 1.06;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] {
                --primary-color: var(--text);
                padding-top: 0;
                padding-bottom: 0;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="color: rgb(255, 75, 75)"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="color:rgb(255,75,75)"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="color: #ff4b4b"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="color:#ff4b4b"] {
                color: var(--text) !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background: rgb(255, 75, 75)"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background:rgb(255,75,75)"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background-color: rgb(255, 75, 75)"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background-color:rgb(255,75,75)"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background: #ff4b4b"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background:#ff4b4b"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background-color: #ff4b4b"],
            [data-testid="stSidebar"] [data-testid="stSlider"] [style*="background-color:#ff4b4b"] {
                background-color: var(--text) !important;
                background: var(--text) !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {
                background-color: var(--text) !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
                background-color: var(--text) !important;
                border-color: var(--text) !important;
                box-shadow: 0 0 0 1px var(--text) !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"] div {
                background-color: var(--text) !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] label,
            [data-testid="stSidebar"] [data-testid="stSlider"] p,
            [data-testid="stSidebar"] [data-testid="stSlider"] span,
            [data-testid="stSidebar"] [data-testid="stSlider"] div[data-testid="stMarkdownContainer"] {
                color: var(--text) !important;
                background: transparent !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_locations_for_region(region: str) -> list[str]:
    if region == ALL_REGIONS_LABEL:
        return [location for locations in LOCATIONS_BY_REGION_VN.values() for location in locations]
    return LOCATIONS_BY_REGION_VN.get(region, [])


def render_sidebar() -> dict[str, object]:
    with st.sidebar:
        st.title("Vietnam Climate Explorer")
        selected_tab = st.radio("Dashboard", NAV_ITEMS, label_visibility="collapsed")

        selected_region = st.selectbox(
            "Vùng",
            [ALL_REGIONS_LABEL, *LOCATIONS_BY_REGION_VN.keys()],
        )
        selected_locations = st.multiselect(
            "Địa điểm",
            get_locations_for_region(selected_region),
            default=[],
        )
        selected_period = st.slider(
            "Giai đoạn phân tích",
            min_value=1991,
            max_value=2025,
            value=(1991, 2025),
            label_visibility="collapsed",
        )

        return {
            "selected_tab": selected_tab,
            "region": selected_region,
            "locations": selected_locations,
            "period": selected_period,
        }