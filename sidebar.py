import streamlit as st

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
    "Trung du và miền núi phía Bắc": ["Dien Bien Phu", "Lao Cai"],
    "Đồng bằng sông Hồng": ["Ha Noi", "Hai Phong"],
    "Bắc Trung Bộ": ["Dong Hoi", "Hue", "Vinh"],
    "Nam Trung Bộ": [
        "Buon Ma Thuot",
        "Da Lat",
        "Da Nang",
        "Nha Trang",
        "Phan Rang-Thap Cham",
        "Pleiku",
        "Quy Nhon",
    ],
    "Đông Nam Bộ": ["Ho Chi Minh City", "Vung Tau"],
    "Đồng bằng sông Cửu Long": [
        "Ca Mau",
        "Can Tho",
        "Chau Doc",
        "Phu Quoc",
    ],
}

REGION_ORDER = list(LOCATIONS_BY_REGION.keys())

REGION_KEYS = list(REGION_ORDER)
REGION_VIETNAMESE = {region: region for region in REGION_ORDER}
REFERENCE_POINTS = LOCATIONS_BY_REGION

LOCATIONS_BY_REGION_VN = {
    region: [
        LOCATION_VIETNAMESE.get(location, location)
        for location in locations
    ]
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
            /* Sidebar Container */
            [data-testid="stSidebar"] {
                background-color: #ffffff !important;
                border-right: 1px solid #e2e8f0 !important;
            }

            /* Keep the Sidebar Resizer Hidden */
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

            /* Navigation Items - Full Width Without Affecting Inner Wrappers */
            [data-testid="stSidebar"] [data-testid="stRadio"],
            [data-testid="stSidebar"] [role="radiogroup"],
            [data-testid="stSidebar"] [role="radiogroup"] > div {
                width: 100% !important;
                max-width: 100% !important;
                box-sizing: border-box !important;
            }

            /* Stack Navigation Items Vertically */
            [data-testid="stSidebar"] [role="radiogroup"] {
                display: flex !important;
                flex-direction: column !important;
                gap: 6px !important;
            }

            /* Navigation Button */
            [data-testid="stSidebar"] [role="radiogroup"] label {
                position: relative !important;
                width: 120% !important;
                min-height: 42px !important;
                box-sizing: border-box !important;
                border: 1px solid #bbb !important;
                border-radius: 8px !important;
                padding: 9px 14px !important;
                margin: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
                background-color: #ffffff !important;
                cursor: pointer !important;
                overflow: hidden !important;
                box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
                transition:
                    background-color 160ms ease,
                    border-color 160ms ease,
                    box-shadow 160ms ease,
                    transform 160ms ease !important;
            }

            /* Hide the Radio Circle Indicator Completely */
            [data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] {
                position: absolute !important;
                width: 0 !important;
                height: 0 !important;
                opacity: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                pointer-events: none !important;
                overflow: hidden !important;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] * {
                display: none !important;
            }

            /* Keep the Text Container Inside the Button */
            [data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] {
                width: 100% !important;
                min-width: 0 !important;
                display: block !important;
            }

            /* Inactive Navigation Text */
            [data-testid="stSidebar"] [role="radiogroup"] label p {
                color: #334155 !important;
                font-size: 15px !important;
                font-weight: 500 !important;
                line-height: 1.25 !important;
                margin: 0 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                transition: color 160ms ease !important;
            }

            /* Hover State */
            [data-testid="stSidebar"] [role="radiogroup"] label:hover {
                background-color: #f1f5f9 !important;
                border-color: #cbd5e1 !important;
                transform: translateX(2px) !important;
            }

            [data-testid="stSidebar"] [role="radiogroup"] label:hover p {
                color: #0f172a !important;
            }

            /* Active Navigation Item */
            [data-testid="stSidebar"] [role="radiogroup"] label:has(input[type="radio"]:checked) {
                background-color: #1e3a5f !important;
                border-color: #1e3a5f !important;
                box-shadow: 0 4px 12px -2px rgba(30, 58, 95, 0.28) !important;
                transform: none !important;
            }

            /* Active Navigation Text */
            [data-testid="stSidebar"] [role="radiogroup"] label:has(input[type="radio"]:checked) p {
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

            [data-testid="stSidebar"] [data-testid="stPopover"] [data-testid*="stIcon"],
            [data-testid="stSidebar"] [data-testid="stPopover"] [data-testid*="stIcon"] *,
            [data-testid="stSidebar"] [data-testid="stPopover"] span[data-testid*="Icon"] {
                font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
                font-size: 20px !important;
                line-height: 1 !important;
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


def _selected_region_keys_from_state() -> list[str]:
    return [
        region
        for region in REGION_KEYS
        if st.session_state.get(f"chk_region_{region}", False)
    ]


def _get_available_locations() -> list[str]:
    selected_r_keys = _selected_region_keys_from_state()
    locs = []
    for r_key in selected_r_keys:
        locs.extend(LOCATIONS_BY_REGION.get(r_key, []))
    return locs


def _sync_locations_after_region_change(
    previous_regions: set[str],
    selected_regions: set[str],
) -> None:
    added_regions = selected_regions - previous_regions
    removed_regions = previous_regions - selected_regions

    for region in REGION_KEYS:
        if region in added_regions:
            for location in LOCATIONS_BY_REGION[region]:
                st.session_state[f"chk_loc_{location}"] = True
        elif region in removed_regions:
            for location in LOCATIONS_BY_REGION[region]:
                st.session_state[f"chk_loc_{location}"] = False

    available_locations = _get_available_locations()
    st.session_state.chk_loc_select_all = bool(available_locations) and all(
        st.session_state.get(f"chk_loc_{location}", False)
        for location in available_locations
    )


def _on_region_select_all_change() -> None:
    new_val = st.session_state.get("chk_region_select_all", False)
    for r_key in REGION_KEYS:
        st.session_state[f"chk_region_{r_key}"] = new_val
        for loc_key in LOCATIONS_BY_REGION[r_key]:
            st.session_state[f"chk_loc_{loc_key}"] = new_val
    st.session_state.previous_selected_regions = list(REGION_KEYS) if new_val else []
    st.session_state.chk_loc_select_all = new_val


def _on_region_individual_change() -> None:
    previous_regions = set(st.session_state.get("previous_selected_regions", []))
    selected_region_keys = _selected_region_keys_from_state()
    selected_regions = set(selected_region_keys)
    _sync_locations_after_region_change(previous_regions, selected_regions)
    st.session_state.chk_region_select_all = len(selected_region_keys) == len(REGION_KEYS)
    st.session_state.previous_selected_regions = selected_region_keys


def _on_location_select_all_change() -> None:
    new_val = st.session_state.get("chk_loc_select_all", False)
    for loc_key in _get_available_locations():
        st.session_state[f"chk_loc_{loc_key}"] = new_val


def _on_location_individual_change() -> None:
    avail_locs = _get_available_locations()
    all_checked = (
        all(st.session_state.get(f"chk_loc_{loc_key}", False) for loc_key in avail_locs)
        if avail_locs
        else False
    )
    st.session_state.chk_loc_select_all = all_checked


def render_sidebar() -> dict[str, object]:
    with st.sidebar:
        # Branding Header (VietNam \n CLIMATE EXPLORER)
        st.markdown(
            """
            <div class="sidebar-brand-container">
                <div class="sidebar-brand-title">VietNam</div>
                <div class="sidebar-brand-main">CLIMATE EXPLORER</div>
                <div class="sidebar-brand-subtitle">
									Dữ liệu khí hậu 1991 - 2025
									<br>
									Nguồn: NASA
								</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Section 1: Navigation
        selected_tab = st.radio("Dashboard", NAV_ITEMS, label_visibility="collapsed")
        st.markdown("<hr style='margin: 6px 0; border: none; border-top: 2px solid #bbb;'>", unsafe_allow_html=True)

        # Section 2: Filters
        # --- Filter Vùng (Region Filter) ---
        st.markdown(
            '<div style="color: #1e3a5f; font-size: 14px; font-weight: 600; margin-bottom: 4px;">Vùng</div>',
            unsafe_allow_html=True,
        )

        if "chk_region_select_all" not in st.session_state:
            st.session_state.chk_region_select_all = True
            for r_key in REGION_KEYS:
                st.session_state[f"chk_region_{r_key}"] = True

            # Mặc định chọn tất cả các địa điểm/tỉnh khi mới mở dashboard
            st.session_state.chk_loc_select_all = True
            for r_key in REGION_KEYS:
                for loc_key in LOCATIONS_BY_REGION[r_key]:
                    st.session_state[f"chk_loc_{loc_key}"] = True

            st.session_state.previous_selected_regions = list(REGION_KEYS)
        elif "previous_selected_regions" not in st.session_state:
            st.session_state.previous_selected_regions = _selected_region_keys_from_state()

        selected_region_keys = [
            r_key
            for r_key in REGION_KEYS
            if st.session_state.get(f"chk_region_{r_key}", False)
        ]
        st.session_state.selected_regions = selected_region_keys
        st.session_state.selected_region_keys = selected_region_keys

        region_count = len(selected_region_keys)
        total_regions = len(REGION_KEYS)
        region_popover_label = f"Đã chọn {region_count}/{total_regions} vùng"

        with st.popover(region_popover_label, use_container_width=True):
            st.checkbox(
                "Chọn tất cả",
                key="chk_region_select_all",
                on_change=_on_region_select_all_change,
            )
            st.markdown(
                "<hr style='margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;'>",
                unsafe_allow_html=True,
            )

            for r_key in REGION_KEYS:
                st.checkbox(
                    REGION_VIETNAMESE.get(r_key, r_key),
                    key=f"chk_region_{r_key}",
                    on_change=_on_region_individual_change,
                )

        # --- Filter Địa điểm - Tỉnh (Location Filter dependent on Vùng) ---
        st.markdown(
            '<div style="color: #1e3a5f; font-size: 14px; font-weight: 600; margin-bottom: 4px;">Tỉnh/Thành phố</div>',
            unsafe_allow_html=True,
        )

        available_locations = _get_available_locations()
        total_avail = len(available_locations)

        # Sync location select_all state
        if total_avail > 0:
            st.session_state.chk_loc_select_all = all(
                st.session_state.get(f"chk_loc_{loc_key}", False) for loc_key in available_locations
            )
        else:
            st.session_state.chk_loc_select_all = False

        selected_locations = [
            loc_key for loc_key in available_locations
            if st.session_state.get(f"chk_loc_{loc_key}", False)
        ]
        st.session_state.selected_reference_points = selected_locations

        loc_count = len(selected_locations)
        if total_avail == 0:
            loc_popover_label = "0 tỉnh/thành phố"
        else:
            loc_popover_label = f"Đã chọn {loc_count}/{total_avail} tỉnh"

        with st.popover(loc_popover_label, use_container_width=True):
            if total_avail == 0:
                st.caption("Vui lòng chọn ít nhất 1 vùng ở trên để hiển thị danh sách tỉnh/thành phố.")
            else:
                st.checkbox(
                    "Chọn tất cả",
                    key="chk_loc_select_all",
                    on_change=_on_location_select_all_change,
                )
                st.markdown(
                    "<hr style='margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;'>",
                    unsafe_allow_html=True,
                )

                for loc_key in available_locations:
                    st.checkbox(
                        LOCATION_VIETNAMESE.get(loc_key, loc_key),
                        key=f"chk_loc_{loc_key}",
                        on_change=_on_location_individual_change,
                    )

        # --- Filter Thời gian ---
        year_range = st.slider(
            "Thời gian",
            min_value=1991,
            max_value=2025,
            value=(1991, 2025),
        )

        return {
            "selected_tab": selected_tab,
            "selected_regions": st.session_state.get("selected_regions", []),
            "selected_region_keys": st.session_state.get("selected_region_keys", []),
            "selected_reference_points": st.session_state.get("selected_reference_points", []),
            "year_range": year_range,
        }
