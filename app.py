import streamlit as st

from sidebar import inject_sidebar_css, render_sidebar
from tabs.tab_1_overview_regions import render_overview_regions_tab
from tabs.tab_2_temperature_comparison import render_temperature_comparison_tab
from tabs.tab_3_rainfall_humidity import render_rainfall_humidity_tab
from tabs.tab_4_meteorological_factors import render_meteorological_factors_tab
from tabs.tab_5_extreme_weather import render_extreme_weather_tab
from tabs.tab_6_ai_assistant import render_ai_assistant_tab


PRIMARY = "#1E3A5F"
SECONDARY = "#2A9D8F"
TEMP_ACCENT = "#F4A261"
EXTREME_ACCENT = "#E76F51"
BACKGROUND = "#F5F7FA"
CARD = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#64748B"
BORDER = "#E2E8F0"


def configure_page() -> None:
    st.set_page_config(
        page_title="Vietnam Climate Explorer",
        page_icon="🌦️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

            /* Force Plus Jakarta Sans globally on text elements, Streamlit widgets & BaseWeb popovers/menus */
            html, body, .stApp, .stApp *,
            [data-baseweb="popover"] *,
            [data-baseweb="menu"] *,
            [data-baseweb="select"] *,
            [data-testid="stPopoverBody"] *,
            div[role="listbox"] *,
            div[role="option"] * {{
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            }}

            /* Preserve Material Icons font for all Streamlit icons (popover arrows, expanders, collapse button, etc.) */
            [data-testid*="stIcon"],
            [data-testid*="stIcon"] *,
            [data-testid*="Icon"],
            [data-testid*="Icon"] *,
            [data-testid="stSidebarCollapseButton"],
            [data-testid="stSidebarCollapseButton"] *,
            [data-testid="stHeader"] *,
            .material-icons,
            [class*="MaterialSymbols"],
            [class*="material-symbols"] {{
                font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
                color: #334155 !important;
            }}

            :root {{
                --primary: {PRIMARY};
                --secondary: {SECONDARY};
                --temp: {TEMP_ACCENT};
                --extreme: {EXTREME_ACCENT};
                --background: {BACKGROUND};
                --card: {CARD};
                --text: {TEXT};
                --muted: {MUTED};
                --border: {BORDER};
            }}

            .stApp {{
                background: var(--background);
                color: var(--text);
            }}

            .block-container {{
                padding-top: 0.4rem;
                padding-bottom: 2.5rem;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 98% !important;
            }}

            h1, h2, h3 {{
                color: var(--primary);
                letter-spacing: 0;
            }}

            .dashboard-hero {{
                background: linear-gradient(135deg, #ffffff 0%, #eef8f7 54%, #fdf4eb 100%);
                border: 1px solid var(--border);
                border-radius: 7px;
                padding: 10px 18px;
                margin-bottom: 6px;
            }}

            .eyebrow {{
                color: var(--secondary);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 4px;
            }}

            .hero-title {{
                color: var(--primary);
                font-size: 1.25rem;
                font-weight: 750;
                line-height: 1.25;
                margin: 0;
            }}

            .section-title {{
                color: var(--primary);
                font-size: 1.14rem;
                font-weight: 720;
                margin: 8px 0 10px;
            }}

            .small-note {{
                color: var(--muted);
                font-size: 0.88rem;
                line-height: 1.45;
            }}

            .metric-card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 7px;
                padding: 16px 18px;
                min-height: 110px;
            }}

            .metric-label {{
                color: var(--muted);
                font-size: 0.82rem;
                font-weight: 650;
                margin-bottom: 6px;
            }}

            .metric-value {{
                color: var(--primary);
                font-size: 1.7rem;
                font-weight: 760;
                margin-bottom: 4px;
            }}

            .metric-caption {{
                color: var(--muted);
                font-size: 0.82rem;
            }}
            .overview-kpi-card {{
                min-height: 132px;
                height: 132px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start;
                text-align: center;
                padding: 14px 12px;
            }}

            .overview-kpi-card .metric-label {{
                width: 100%;
                min-height: 28px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 8px;
                text-align: center;
            }}

            .kpi-value-row {{
                display: flex;
                align-items: baseline;
                justify-content: center;
                gap: 4px;
                color: var(--primary);
                margin-bottom: 10px;
                white-space: nowrap;
            }}

            .kpi-number {{
                font-size: 1.58rem;
                font-weight: 780;
                line-height: 1;
            }}

            .kpi-unit {{
                font-size: 0.9rem;
                font-weight: 720;
                line-height: 1;
            }}

            .overview-kpi-subject {{
                width: 100%;
                color: var(--muted);
                font-size: 0.8rem;
                font-weight: 700;
                text-align: center;
                line-height: 1.25;
            }}

            .placeholder-box {{
                background: var(--card);
                border: 1px dashed #cbd5e1;
                border-radius: 7px;
                min-height: 280px;
                padding: 18px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                gap: 8px;
            }}

            .placeholder-box.tall {{
                min-height: 420px;
            }}

            .placeholder-kicker {{
                color: var(--secondary);
                font-size: 0.78rem;
                font-weight: 740;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }}

            .placeholder-title {{
                color: var(--primary);
                font-size: 1.05rem;
                font-weight: 720;
            }}

            .placeholder-copy {{
                color: var(--muted);
                font-size: 0.84rem;
                line-height: 1.45;
            }}

            .region-chip {{
                display: inline-block;
                background: #eef8f7;
                color: var(--primary);
                border: 1px solid #cdecea;
                border-radius: 999px;
                padding: 5px 10px;
                margin: 0 6px 8px 0;
                font-size: 0.82rem;
                font-weight: 650;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def placeholder_box(title: str, description: str, kicker: str = "Placeholder", tall: bool = False) -> None:
    css_class = "placeholder-box tall" if tall else "placeholder-box"
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="placeholder-kicker">{kicker}</div>
            <div class="placeholder-title">{title}</div>
            <div class="placeholder-copy">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str = "Phân tích đặc điểm khí hậu giữa 6 nhóm vùng và 20 điểm tham chiếu") -> None:
    st.markdown(
        f"""
        <section class="dashboard-hero">
            <div class="hero-title">{title}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metric_row() -> None:
    cols = st.columns(4)
    with cols[0]:
        metric_card("Nhóm vùng", "6", "Vùng khí hậu chính")
    with cols[1]:
        metric_card("Địa điểm", "20", "Điểm đại diện")
    with cols[2]:
        metric_card("Giai đoạn", "1991-2025", "Khung phân tích")
    with cols[3]:
        metric_card("Trạng thái dữ liệu", "Chưa nạp", "Dashboard vẫn chạy độc lập")


def render_active_tab(filters: dict[str, object]) -> None:
    selected_tab = str(filters.get("selected_tab", "Tổng quan"))

    if selected_tab == "Tổng quan":
        render_overview_regions_tab(placeholder_box, filters)
    elif selected_tab == "Nhiệt độ":
        render_temperature_comparison_tab(placeholder_box)
    elif selected_tab == "Mưa và độ ẩm":
        render_rainfall_humidity_tab(placeholder_box)
    elif selected_tab == "Yếu tố khí tượng":
        render_meteorological_factors_tab(placeholder_box, filters)
    elif selected_tab == "Thời tiết cực đoan":
        render_extreme_weather_tab(placeholder_box)
    else:
        render_ai_assistant_tab(placeholder_box)


def main() -> None:
    configure_page()
    inject_css()
    inject_sidebar_css()
    filters = render_sidebar()

    selected_tab = str(filters.get("selected_tab", "Tổng quan"))

    if selected_tab == "Tổng quan":
        render_header("Phân tích đặc điểm khí hậu giữa 6 nhóm vùng và 20 điểm tham chiếu")
    elif selected_tab == "Nhiệt độ":
        render_header("Phân tích đặc điểm nhiệt độ")
        render_metric_row()
    elif selected_tab == "Mưa và độ ẩm":
        render_header("Phân tích đặc điểm mưa và độ ẩm")
        render_metric_row()
    elif selected_tab == "Yếu tố khí tượng":
        render_header("Phân tích đặc điểm gió, áp suất và bức xạ mặt trời")
    elif selected_tab == "Thời tiết cực đoan":
        render_header("Phân tích các khu vực liên quan đến thời tiết cực đoan")
        render_metric_row()
    else:
        # Tab AI Assistant
        render_header("Phân tích đặc điểm khí hậu giữa 6 nhóm vùng và 20 điểm tham chiếu")
        render_metric_row()

    render_active_tab(filters)


if __name__ == "__main__":
    main()
