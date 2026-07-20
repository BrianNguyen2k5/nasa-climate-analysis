import streamlit as st

REGIONS = [
    "Tất cả 7 nhóm vùng",
    "Tây Bắc",
    "Đông Bắc",
    "Đồng bằng Bắc Bộ",
    "Bắc Trung Bộ",
    "Nam Trung Bộ",
    "Tây Nguyên",
    "Nam Bộ",
]

REFERENCE_POINTS = [
    "Hà Nội",
    "Lào Cai",
    "Điện Biên",
    "Lạng Sơn",
    "Hải Phòng",
    "Thanh Hóa",
    "Nghệ An",
    "Huế",
    "Đà Nẵng",
    "Quảng Ngãi",
    "Nha Trang",
    "Phan Thiết",
    "Kon Tum",
    "Pleiku",
    "Buôn Ma Thuột",
    "Đà Lạt",
    "TP. Hồ Chí Minh",
    "Cần Thơ",
    "Cà Mau",
    "Phú Quốc",
]

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
            /* Sidebar Container - Fixed Width 280px, No Resizing */
            [data-testid="stSidebar"] {
                background-color: #ffffff !important;
                border-right: 1px solid #e2e8f0 !important;
                width: 280px !important;
                min-width: 280px !important;
                max-width: 280px !important;
            }

            /* Disable Sidebar Resizer Handle (Prevent user drag resizing) */
            [data-testid="stSidebarResizer"],
            div[class*="stSidebarResizer"] {
                display: none !important;
                pointer-events: none !important;
                cursor: default !important;
            }

            [data-testid="stSidebar"] > div:first-child {
                padding: 0 !important;
            }

            [data-testid="stSidebarUserContent"] {
                padding-left: 1.1rem !important;
                padding-right: 1.1rem !important;
            }

            /* Fix Sidebar Collapse/Expand Icon Color (default visible in dark slate) */
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarCollapseButton"] button,
            [data-testid="stSidebarCollapseButton"] span,
            [data-testid="stSidebarCollapseButton"] svg {
                color: #334155 !important;
            }

            [data-testid="stSidebarCollapseButton"]:hover button,
            [data-testid="stSidebarCollapseButton"]:hover span {
                color: #1e3a5f !important;
            }

            /* Header Branding - Larger VietNam / CLIMATE EXPLORER */
            .sidebar-brand-container {
                padding-bottom: 0.9rem;
                margin-bottom: 0.9rem;
                border-bottom: 2px solid #bbb;
            }

            .sidebar-brand-title {
                color: #1e3a5f;
                font-size: 40px;
                font-weight: 800;
                letter-spacing: -0.025em;
                margin: 0;
                line-height: 1.1;
            }

            .sidebar-brand-main {
                color: #2a9d8f;
                font-size: 20px;
                font-weight: 750;
                letter-spacing: 0.05em;
                line-height: 1.25;
                margin: 2px 0 6px 0;
                text-transform: uppercase;
            }

            .sidebar-brand-subtitle {
                color: #64748b;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.02em;
            }

            /* Section Divider & Titles */
            .sidebar-section-label {
                color: #64748b;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                margin: 1.1rem 0 0.55rem 0;
            }

            /* Navigation Items - Stretch 100% Full Width of Sidebar */
            [data-testid="stSidebar"] [data-testid="stRadio"],
            [data-testid="stSidebar"] [data-testid="stRadio"] > div,
            [data-testid="stSidebar"] [data-testid="stRadio"] div,
            [data-testid="stSidebar"] [role="radiogroup"],
            [data-testid="stSidebar"] [role="radiogroup"] > div {
                width: 110% !important;
                box-sizing: border-box !important;
            }

            [data-testid="stSidebar"] [role="radiogroup"] {
                gap: 6px !important;
                display: flex !important;
                flex-direction: column !important;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label {
                width: 100% !important;
                max-width: 100% !important;
                flex: 1 1 100% !important;
                box-sizing: border-box !important;
                min-height: 40px !important;
                background: #f8fafc !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 8px !important;
                padding: 8px 14px !important;
                margin: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                cursor: pointer !important;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
                transition: all 160ms cubic-bezier(0.4, 0, 0.2, 1) !important;
            }

            /* Hide default radio circle */
            [data-testid="stSidebar"] [role="radiogroup"] label input[type="radio"],
            [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
                display: none !important;
            }

            /* Inactive Text */
            [data-testid="stSidebar"] [role="radiogroup"] label p {
                color: #334155 !important;
                font-weight: 500 !important;
                font-size: 15px !important;
                line-height: 1.2 !important;
                margin: 0 !important;
                transition: color 160ms ease !important;
            }

            /* Hover state for unselected buttons: subtle background + border highlight */
            [data-testid="stSidebar"] [role="radiogroup"] label:hover {
                background: #f1f5f9 !important;
                border-color: #cbd5e1 !important;
                transform: translateX(2px);
            }

            [data-testid="stSidebar"] [role="radiogroup"] label:hover p {
                color: #0f172a !important;
            }

            /* Active State: Primary Navy Pill with pure white text and soft elevation */
            [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
                background: #1e3a5f !important;
                border-color: #1e3a5f !important;
                box-shadow: 0 4px 12px -2px rgba(30, 58, 95, 0.28) !important;
                transform: none !important;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
                color: #ffffff !important;
                font-weight: 650 !important;
            }

            /* Form Inputs & Selects - Enforce Minimum 14px */
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] p {
                color: #1e3a5f;
                font-size: 14px !important;
                font-weight: 600;
            }

            [data-testid="stSidebar"] [data-baseweb="select"] > div {
                background-color: #ffffff !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 8px !important;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04) !important;
                min-height: 38px !important;
                transition: border-color 150ms ease, box-shadow 150ms ease !important;
            }

            [data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
                border-color: #cbd5e1 !important;
            }

            [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
                border-color: #1e3a5f !important;
                box-shadow: 0 0 0 3px rgba(30, 58, 95, 0.12) !important;
            }

            /* Popover Dropdown Checkbox Styling */
            [data-testid="stSidebar"] [data-testid="stPopover"] {
                width: 100% !important;
                margin-bottom: 0.5rem;
            }

            [data-testid="stSidebar"] [data-testid="stPopover"] > button {
                width: 100% !important;
                background-color: #ffffff !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 8px !important;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04) !important;
                min-height: 38px !important;
                color: #1e3a5f !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                padding: 6px 12px !important;
                transition: border-color 150ms ease, box-shadow 150ms ease !important;
            }

            [data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
                border-color: #cbd5e1 !important;
                background-color: #f8fafc !important;
            }

            [data-testid="stSidebar"] [data-testid="stPopover"] > button:focus {
                border-color: #1e3a5f !important;
                box-shadow: 0 0 0 3px rgba(30, 58, 95, 0.12) !important;
            }

            [data-testid="stPopoverBody"] {
                max-height: 320px !important;
                border-radius: 8px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
                padding: 10px 12px !important;
            }

            /* Slider Styling */
            [data-testid="stSidebar"] [data-testid="stSlider"] {
                padding-top: 0.2rem;
                padding-bottom: 0.2rem;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
                background-color: #1e3a5f !important;
                border: 2px solid #ffffff !important;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.15) !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {
                background-color: #1e3a5f !important;
            }

            [data-testid="stSidebar"] [data-testid="stSlider"] label p {
                color: #1e3a5f !important;
                font-weight: 600 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    with st.sidebar:
        # Branding Header (VietNam \n CLIMATE EXPLORER)
        st.markdown(
            """
            <div class="sidebar-brand-container">
                <div class="sidebar-brand-title">VietNam</div>
                <div class="sidebar-brand-main">CLIMATE EXPLORER</div>
                <div class="sidebar-brand-subtitle">Dữ liệu khí hậu 1991 - 2025</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Section 1: Navigation
        st.markdown('<div class="sidebar-section-label">Điều hướng Dashboard</div>', unsafe_allow_html=True)
        selected_tab = st.radio("Dashboard", NAV_ITEMS, label_visibility="collapsed")

        # Section 2: Filters
        st.markdown('<div class="sidebar-section-label">Bộ lọc dữ liệu</div>', unsafe_allow_html=True)
        st.selectbox("Vùng khí hậu", REGIONS)

        # Dropdown List with Checkboxes for "Địa điểm tham chiếu"
        st.markdown(
            '<div style="color: #1e3a5f; font-size: 14px; font-weight: 600; margin-bottom: 4px;">Địa điểm tham chiếu</div>',
            unsafe_allow_html=True,
        )

        if "selected_reference_points" not in st.session_state:
            st.session_state.selected_reference_points = []

        count = len(st.session_state.selected_reference_points)
        if count == len(REFERENCE_POINTS):
            popover_label = "Tất cả 20 địa điểm"
        else:
            popover_label = f"Đã chọn {count}/20 địa điểm"

        with st.popover(popover_label, use_container_width=True):
            select_all = st.checkbox("Chọn tất cả", key="chk_select_all")
            st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

            current_selected = []
            if select_all:
                current_selected = REFERENCE_POINTS.copy()
                st.caption("Đã chọn tất cả 20 địa điểm")
            else:
                for idx, point in enumerate(REFERENCE_POINTS):
                    checked = st.checkbox(point, key=f"chk_point_{idx}")
                    if checked:
                        current_selected.append(point)

            st.session_state.selected_reference_points = current_selected

        st.slider(
            "Khung thời gian",
            min_value=1991,
            max_value=2025,
            value=(1991, 2025),
        )

        return selected_tab