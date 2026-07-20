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
                padding-top: 1.6rem;
                padding-bottom: 2.5rem;
            }}

            h1, h2, h3 {{
                color: var(--primary);
                letter-spacing: 0;
            }}

            .dashboard-hero {{
                background: linear-gradient(135deg, #ffffff 0%, #eef8f7 54%, #fdf4eb 100%);
                border: 1px solid var(--border);
                border-radius: 7px;
                padding: 24px 28px;
                margin-bottom: 18px;
            }}

            .eyebrow {{
                color: var(--secondary);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 8px;
            }}

            .hero-title {{
                color: var(--primary);
                font-size: 2rem;
                font-weight: 760;
                line-height: 1.2;
                margin: 0 0 10px;
            }}

            .hero-subtitle {{
                color: var(--muted);
                font-size: 1rem;
                line-height: 1.55;
                max-width: 960px;
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
                margin-bottom: 8px;
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


def render_header() -> None:
    st.markdown(
        """
        <section class="dashboard-hero">
            <div class="eyebrow">Khí hậu Việt Nam | 1991-2025</div>
            <div class="hero-title">Phân tích và so sánh đặc điểm khí hậu giữa 7 nhóm vùng và 20 điểm tham chiếu</div>
            <p class="hero-subtitle">
                Sườn dashboard học thuật cho phân tích nhiệt độ, mưa, độ ẩm, các yếu tố khí tượng và thời tiết cực đoan.
                Các vùng trực quan hóa đang để placeholder để có thể gắn biểu đồ thật ở bước tiếp theo.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metric_row() -> None:
    cols = st.columns(4)
    with cols[0]:
        metric_card("Nhóm vùng", "7", "Vùng khí hậu chính")
    with cols[1]:
        metric_card("Địa điểm", "20", "Điểm đại diện")
    with cols[2]:
        metric_card("Giai đoạn", "1991-2025", "Khung phân tích")
    with cols[3]:
        metric_card("Trạng thái dữ liệu", "Chưa nạp", "Dashboard vẫn chạy độc lập")


def render_active_tab(selected_tab: str) -> None:
    if selected_tab == "Tổng quan":
        render_overview_regions_tab(placeholder_box)
    elif selected_tab == "Nhiệt độ":
        render_temperature_comparison_tab(placeholder_box)
    elif selected_tab == "Mưa và độ ẩm":
        render_rainfall_humidity_tab(placeholder_box)
    elif selected_tab == "Yếu tố khí tượng":
        render_meteorological_factors_tab(placeholder_box)
    elif selected_tab == "Thời tiết cực đoan":
        render_extreme_weather_tab(placeholder_box)
    else:
        render_ai_assistant_tab(placeholder_box)


def main() -> None:
    configure_page()
    inject_css()
    inject_sidebar_css()
    selected_tab = render_sidebar()
    render_header()
    render_metric_row()
    render_active_tab(selected_tab)


if __name__ == "__main__":
    main()
