from pathlib import Path
import html
import math
import re

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium


DATA_PATH = Path("data/nasa_power_vietnam_daily_clean.csv")
ALL_REGIONS_LABEL = "Tất cả 7 nhóm vùng"

REGION_VIETNAMESE = {
    "Central Highlands": "Tây Nguyên",
    "Mekong Delta": "Đồng bằng sông Cửu Long",
    "South Central Coast": "Duyên hải Nam Trung Bộ",
    "Central": "Miền Trung",
    "North": "Miền Bắc",
    "Southeast": "Đông Nam Bộ",
    "North Central": "Bắc Trung Bộ",
}
REGION_ENGLISH = {value: key for key, value in REGION_VIETNAMESE.items()}

# Colour palette for each region (used for chips + tooltip accent)
REGION_COLORS = {
    "Miền Bắc":                    "#3B82F6",
    "Bắc Trung Bộ":                "#8B5CF6",
    "Miền Trung":                  "#EC4899",
    "Duyên hải Nam Trung Bộ":      "#F59E0B",
    "Tây Nguyên":                  "#10B981",
    "Đông Nam Bộ":                 "#EF4444",
    "Đồng bằng sông Cửu Long":    "#06B6D4",
}

# Temperature bounds for colour mapping (°C)
TEMP_COLD = 20.0
TEMP_HOT  = 28.0

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
LOCATION_ENGLISH = {value: key for key, value in LOCATION_VIETNAMESE.items()}


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _temp_to_color(temp: float) -> str:
    """Map temperature (°C) to a hex colour: blue → teal → orange → red."""
    t = max(0.0, min(1.0, (temp - TEMP_COLD) / (TEMP_HOT - TEMP_COLD)))
    if t < 0.33:
        u = t / 0.33
        r = int(59  + (16  - 59)  * u)
        g = int(130 + (185 - 130) * u)
        b = int(246 + (129 - 246) * u)
    elif t < 0.66:
        u = (t - 0.33) / 0.33
        r = int(16  + (249 - 16)  * u)
        g = int(185 + (115 - 185) * u)
        b = int(129 + (22  - 129) * u)
    else:
        u = (t - 0.66) / 0.34
        r = int(249 + (220 - 249) * u)
        g = int(115 + (38  - 115) * u)
        b = int(22  + (38  - 22)  * u)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Extreme-weather thresholds ──────────────────────────────────────────────
# Thresholds are absolute annual-mean values (not statistical anomalies).
# hot_days / heavy_days are annual COUNTS (not consecutive streaks).
_EXTREME_CHECKS: list[tuple[str, str, float, str]] = [
    # (field, operator, threshold, label)
    # temp  = annual mean T2M (°C) — threshold: top ~10% of VN locations
    ("temp",       ">",  27.5,  "Nhiệt độ trung bình năm cao"),
    # rain  = annual total precipitation (mm/yr) — VN avg ~1 800 mm
    ("rain",       ">", 3000.0, "Lượng mưa năm rất cao"),
    # Low annual rain → arid/semi-arid climate (not a drought event per se)
    ("rain",       "<",  900.0, "Khí hậu khô hạn"),
    # hot_days = COUNT of days/yr with Tmax above threshold (e.g. 35 °C)
    # High count → frequently hot climate, NOT a single heat-wave event
    ("hot_days",   ">",   60.0, "Tần suất nắng nóng cao"),
    # heavy_days = COUNT of days/yr with heavy rain (e.g. ≥ 50 mm/day)
    # High count → high frequency, NOT necessarily consecutive days
    ("heavy_days", ">",   20.0, "Tần suất mưa lớn cao"),
]



def _extreme_labels(point: dict[str, object]) -> list[str]:
    """Return list of active extreme-weather condition labels for a point."""
    labels = []
    for field, op, threshold, label in _EXTREME_CHECKS:
        val = float(point.get(field, 0) or 0)
        if (op == ">" and val > threshold) or (op == "<" and val < threshold):
            labels.append(label)
    return labels


def _is_extreme(point: dict[str, object]) -> bool:
    """True when any extreme-weather condition is triggered."""
    return bool(_extreme_labels(point))


@st.cache_data(show_spinner=False)
def load_climate_data() -> pd.DataFrame:
    usecols = [
        "location_name",
        "region",
        "latitude",
        "longitude",
        "year",
        "T2M",
        "RH2M",
        "PRECTOTCORR",
        "hot_day",
        "heavy_rain_day",
    ]
    df = pd.read_csv(DATA_PATH, usecols=usecols)
    df["region_vn"] = df["region"].map(REGION_VIETNAMESE).fillna(df["region"])
    df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE).fillna(df["location_name"])
    return df


def filter_data(df: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    start_year, end_year = filters.get("period", (1991, 2025))
    filtered = df[df["year"].between(int(start_year), int(end_year))]

    region = str(filters.get("region", ALL_REGIONS_LABEL))
    if region != ALL_REGIONS_LABEL:
        filtered = filtered[filtered["region_vn"] == region]

    locations = filters.get("locations", [])
    if isinstance(locations, list) and locations:
        filtered = filtered[filtered["location_vn"].isin(locations)]

    return filtered


def _format_decimal(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _format_int(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def _annual_location_metrics(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["region_vn", "location_vn", "year"], as_index=False)
        .agg(
            annual_rain=("PRECTOTCORR", "sum"),
            hot_days=("hot_day", "sum"),
            heavy_rain_days=("heavy_rain_day", "sum"),
        )
    )


def _scope_label(filters: dict[str, object]) -> str:
    region = str(filters.get("region", ALL_REGIONS_LABEL))
    locations = filters.get("locations", [])

    if isinstance(locations, list) and len(locations) == 1:
        return locations[0]
    if isinstance(locations, list) and len(locations) > 1:
        return f"{len(locations)} điểm tham chiếu"
    if region != ALL_REGIONS_LABEL:
        return region
    return "Toàn quốc"


def _kpi_mode(filters: dict[str, object]) -> str:
    region = str(filters.get("region", ALL_REGIONS_LABEL))
    locations = filters.get("locations", [])

    if isinstance(locations, list) and locations:
        return "location"
    if region != ALL_REGIONS_LABEL:
        return "region"
    return "national"


def build_kpis(df: pd.DataFrame, filters: dict[str, object]) -> list[dict[str, str]]:
    if df.empty:
        return [
            {"title": "Nhiệt độ trung bình", "value": "Không có dữ liệu", "subject": ""},
            {"title": "Tổng lượng mưa trung bình năm", "value": "Không có dữ liệu", "subject": ""},
            {"title": "Độ ẩm trung bình", "value": "Không có dữ liệu", "subject": ""},
            {"title": "Số ngày nóng trung bình", "value": "Không có dữ liệu", "subject": ""},
            {"title": "Số ngày mưa lớn trung bình", "value": "Không có dữ liệu", "subject": ""},
        ]

    mode = _kpi_mode(filters)
    annual = _annual_location_metrics(df)

    if mode == "national":
        temp = df.groupby("region_vn")["T2M"].mean().idxmax()
        temp_value = df.groupby("region_vn")["T2M"].mean().max()
        rain = annual.groupby("region_vn")["annual_rain"].mean()
        humidity = df.groupby("region_vn")["RH2M"].mean()
        hot = annual.groupby("region_vn")["hot_days"].mean()
        heavy = annual.groupby("region_vn")["heavy_rain_days"].mean()

        return [
            {"title": "Nhiệt độ trung bình cao nhất", "value": f"{_format_decimal(temp_value)}°C", "subject": temp},
            {"title": "Lượng mưa cao nhất", "value": f"{_format_int(rain.max())} mm/năm", "subject": rain.idxmax()},
            {"title": "Độ ẩm trung bình cao nhất", "value": f"{_format_decimal(humidity.max())}%", "subject": humidity.idxmax()},
            {"title": "Số ngày nóng nhiều nhất", "value": f"{_format_decimal(hot.max())} ngày/năm", "subject": hot.idxmax()},
            {"title": "Số ngày mưa lớn nhiều nhất", "value": f"{_format_decimal(heavy.max())} ngày/năm", "subject": heavy.idxmax()},
        ]

    scope = _scope_label(filters)
    annual_rain = annual["annual_rain"].mean()
    hot_days = annual["hot_days"].mean()
    heavy_days = annual["heavy_rain_days"].mean()

    return [
        {"title": "Nhiệt độ trung bình", "value": f"{_format_decimal(df['T2M'].mean())}°C", "subject": scope},
        {"title": "Tổng lượng mưa trung bình năm", "value": f"{_format_int(annual_rain)} mm/năm", "subject": scope},
        {"title": "Độ ẩm trung bình", "value": f"{_format_decimal(df['RH2M'].mean())}%", "subject": scope},
        {"title": "Số ngày nóng trung bình", "value": f"{_format_decimal(hot_days)} ngày/năm", "subject": scope},
        {"title": "Số ngày mưa lớn trung bình", "value": f"{_format_decimal(heavy_days)} ngày/năm", "subject": scope},
    ]


def _split_value(value: str) -> tuple[str, str]:
    match = re.match(r"^([\d.,]+)\s*(.*)$", value)
    if not match:
        return value, ""
    return match.group(1), match.group(2).strip()


def _render_kpi_card(title: str, subject: str, value: str) -> None:
    number, unit = _split_value(value)
    unit_html = f'<span class="kpi-unit">{_escape(unit)}</span>' if unit else ""

    st.markdown(
        f"""
        <div class="metric-card overview-kpi-card">
            <div class="metric-label">{_escape(title)}</div>
            <div class="kpi-value-row">
                <span class="kpi-number">{_escape(number)}</span>{unit_html}
            </div>
            <div class="overview-kpi-subject">{_escape(subject)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_contextual_kpis(df: pd.DataFrame, filters: dict[str, object]) -> None:
    cols = st.columns(5)
    for col, kpi in zip(cols, build_kpis(df, filters)):
        with col:
            _render_kpi_card(kpi["title"], kpi["subject"], kpi["value"])


def build_location_summary(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []

    annual = _annual_location_metrics(df)
    daily_metrics = (
        df.groupby(["location_name", "location_vn", "region_vn", "latitude", "longitude"], as_index=False)
        .agg(temp=("T2M", "mean"), humidity=("RH2M", "mean"))
    )
    annual_metrics = (
        annual.groupby(["location_vn", "region_vn"], as_index=False)
        .agg(rain=("annual_rain", "mean"), hot_days=("hot_days", "mean"), heavy_days=("heavy_rain_days", "mean"))
    )
    summary = daily_metrics.merge(annual_metrics, on=["location_vn", "region_vn"], how="left")
    return summary.to_dict("records")


def _bubble_tooltip_html(point: dict[str, object]) -> str:
    """Build a rich HTML popup for a Folium CircleMarker."""
    temp_val  = float(point["temp"])
    rain_val  = float(point["rain"])
    hum_val   = float(point["humidity"])
    hot_val   = float(point["hot_days"])
    heavy_val = float(point["heavy_days"])
    region_vn = str(point["region_vn"])

    dot_color  = _temp_to_color(temp_val)
    region_col = REGION_COLORS.get(region_vn, "#1E3A5F")
    extreme_labels = _extreme_labels(point)
    extreme        = bool(extreme_labels)

    temp_bar  = max(2, min(100, int((temp_val - 15) / (32 - 15) * 100)))
    rain_bar  = max(2, min(100, int(rain_val / 3500 * 100)))
    hum_bar   = max(2, min(100, int(hum_val / 100 * 100)))

    extreme_badge = (
        '<span style="margin-left:auto;background:#FEE2E2;color:#DC2626;'
        'border-radius:4px;font-size:9px;font-weight:700;padding:1px 5px;">'
        '&#9888; C&#7921;c &#273;oan</span>'
    ) if extreme else ""

    # Build extreme-condition tag list
    extreme_tags = ""
    if extreme_labels:
        tags_html = "".join(
            f'<span style="display:inline-block;background:#FEF2F2;color:#991B1B;'
            f'border:1px solid #FECACA;border-radius:4px;font-size:9px;'
            f'font-weight:600;padding:1px 6px;margin:1px 2px 1px 0;">'
            f'{_escape(lbl)}</span>'
            for lbl in extreme_labels
        )
        extreme_tags = (
            f'<div style="margin-top:6px;padding-top:5px;'
            f'border-top:1px dashed #FECACA;">'
            f'<div style="color:#991B1B;font-size:9.5px;font-weight:700;margin-bottom:3px;">'
            f'&#9888; C&#7843;nh b&#225;o kh&#237; h&#7853;u c&#7921;c &#273;oan:</div>'
            f'{tags_html}</div>'
        )

    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif; width:240px;
                border-left:4px solid {dot_color}; padding:10px 12px;
                border-radius:0 8px 8px 0; font-size:11px; line-height:1.45;">
        <div style="display:flex;align-items:center;gap:7px;margin-bottom:4px;">
            <span style="width:11px;height:11px;border-radius:50%;background:{dot_color};flex-shrink:0;"></span>
            <strong style="font-size:13px;color:#1E3A5F;">{_escape(point['location_vn'])}</strong>
            {extreme_badge}
        </div>
        <div style="color:{region_col};font-weight:700;font-size:10px;margin-bottom:6px;">&#9616; {_escape(region_vn)}</div>
        <hr style="border:none;border-top:1px solid #F1F5F9;margin:5px 0;"/>

        <div style="display:flex;justify-content:space-between;margin-top:3px;">
            <span style="color:#475569;">&#127777; Nhi&#7879;t &#273;&#7897; TB</span>
            <strong style="color:#1E3A5F;">{_format_decimal(temp_val)}&#176;C</strong>
        </div>
        <div style="background:#F1F5F9;border-radius:3px;height:4px;margin:2px 0 5px;">
            <div style="width:{temp_bar}%;height:4px;border-radius:3px;background:{dot_color};"></div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-top:3px;">
            <span style="color:#475569;">&#127783; L&#432;&#7907;ng m&#432;a TB</span>
            <strong style="color:#1E3A5F;">{_format_int(rain_val)} mm</strong>
        </div>
        <div style="background:#F1F5F9;border-radius:3px;height:4px;margin:2px 0 5px;">
            <div style="width:{rain_bar}%;height:4px;border-radius:3px;background:#3B82F6;"></div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-top:3px;">
            <span style="color:#475569;">&#128167; &#272;&#7897; &#7849;m TB</span>
            <strong style="color:#1E3A5F;">{_format_decimal(hum_val)}%</strong>
        </div>
        <div style="background:#F1F5F9;border-radius:3px;height:4px;margin:2px 0 5px;">
            <div style="width:{hum_bar}%;height:4px;border-radius:3px;background:#06B6D4;"></div>
        </div>

        <div style="display:flex;justify-content:space-between;margin-top:4px;">
            <span style="color:#475569;">&#9728; Ng&#224;y n&#243;ng</span>
            <strong style="color:#1E3A5F;">{_format_decimal(hot_val)} ng&#224;y/n&#259;m</strong>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:3px;">
            <span style="color:#475569;">&#9928; M&#432;a l&#7899;n</span>
            <strong style="color:#1E3A5F;">{_format_decimal(heavy_val)} ng&#224;y/n&#259;m</strong>
        </div>
        {extreme_tags}
    </div>
    """


def render_vietnam_reference_map(df: pd.DataFrame) -> None:
    """Render a Folium bubble map locked to Vietnam.
    Circles are coloured by temperature (yellow→red) and sized by hot days.
    """
    from branca.element import MacroElement
    from jinja2 import Template

    # ── Hard bounds: SW corner → NE corner of Vietnam ──────────────────────
    VN_SW = [8.0,  101.5]
    VN_NE = [24.0, 110.5]

    points = build_location_summary(df)
    if not points:
        st.info("Không có dữ liệu để hiển thị bản đồ.")
        return

    # ── Base map ─────────────────────────────────────────────────────────────
    m = folium.Map(
        location=[16.2, 106.5],
        zoom_start=5,
        min_zoom=5,          # can't zoom out past full-Vietnam view
        max_zoom=10,
        tiles="CartoDB positron",
        zoom_control=True,
        scrollWheelZoom=True,
        dragging=True,
        max_bounds=True,     # Leaflet native bounds restriction
    )

    # ── Inject JS that calls setMaxBounds on the actual Leaflet map object ──
    # MacroElement runs inside the Jinja context of the parent map, so
    # {{ this._parent.get_name() }} resolves to the correct Leaflet variable.
    class _LockBounds(MacroElement):
        def __init__(self, sw, ne, min_zoom):
            super().__init__()
            self._template = Template("""
                {% macro script(this, kwargs) %}
                (function() {
                    var map = {{ this._parent.get_name() }};
                    var sw = L.latLng({{ this.sw[0] }}, {{ this.sw[1] }});
                    var ne = L.latLng({{ this.ne[0] }}, {{ this.ne[1] }});
                    var bounds = L.latLngBounds(sw, ne);
                    map.setMaxBounds(bounds);
                    map.options.minZoom = {{ this.min_zoom }};
                    map.fitBounds(bounds, {padding: [10, 10]});
                    map.on('drag', function() { map.panInsideBounds(bounds, {animate: false}); });
                })();
                {% endmacro %}
            """)
            self.sw       = sw
            self.ne       = ne
            self.min_zoom = min_zoom

    _LockBounds(VN_SW, VN_NE, min_zoom=5).add_to(m)

    # ── Mask "South China Sea" tile label with ocean-coloured rectangle ───────
    # CartoDB Positron ocean background ≈ #d4dbe3
    folium.Rectangle(
        bounds=[[8.0, 110.8], [19.5, 121.0]],
        color=None,
        weight=0,
        fill=True,
        fill_color="#d4dbe3",
        fill_opacity=1.0,
    ).add_to(m)

    # ── Bubble sizing by hot_days ─────────────────────────────────────────
    hot_vals = [float(p["hot_days"]) for p in points]
    hot_min  = min(hot_vals) if hot_vals else 0
    hot_max  = max(hot_vals) if hot_vals else 1
    hot_rng  = max(hot_max - hot_min, 1)

    # ── Top-right legend overlay ──────────────────────────────────────────
    legend_html = """
    <div style="
        position:fixed; top:10px; right:10px; z-index:9999;
        background:rgba(255,255,255,0.96);
        border:1px solid #E2E8F0;
        border-radius:10px;
        box-shadow:0 4px 16px rgba(30,58,95,0.14);
        padding:12px 14px;
        font-family:'Segoe UI',Arial,sans-serif;
        font-size:11px;
        min-width:170px;
        pointer-events:none;
    ">
        <div style="font-weight:800;color:#1E3A5F;font-size:12px;margin-bottom:8px;">
            &#128200; Ch&uacute; th&iacute;ch
        </div>

        <div style="font-weight:700;color:#475569;font-size:10px;
                    letter-spacing:.05em;text-transform:uppercase;margin-bottom:5px;">
            M&agrave;u s&#7855;c &mdash; Nhi&#7879;t &#273;&#7897; TB
        </div>
        <div style="display:flex;align-items:center;gap:5px;margin-bottom:2px;">
            <span style="width:12px;height:12px;border-radius:50%;background:#3b82f6;display:inline-block;"></span>
            &lt; 20&deg;C &nbsp;&mdash;&nbsp; M&aacute;t
        </div>
        <div style="display:flex;align-items:center;gap:5px;margin-bottom:2px;">
            <span style="width:12px;height:12px;border-radius:50%;background:#10b981;display:inline-block;"></span>
            20&ndash;24&deg;C &nbsp;&mdash;&nbsp; &Ocirc;n h&ograve;a
        </div>
        <div style="display:flex;align-items:center;gap:5px;margin-bottom:2px;">
            <span style="width:12px;height:12px;border-radius:50%;background:#f97316;display:inline-block;"></span>
            24&ndash;26&deg;C &nbsp;&mdash;&nbsp; &Acirc;m &aacute;p
        </div>
        <div style="display:flex;align-items:center;gap:5px;margin-bottom:10px;">
            <span style="width:12px;height:12px;border-radius:50%;background:#dc2626;display:inline-block;"></span>
            &gt; 26&deg;C &nbsp;&mdash;&nbsp; N&oacute;ng
        </div>

        <div style="font-weight:700;color:#475569;font-size:10px;
                    letter-spacing:.05em;text-transform:uppercase;margin-bottom:5px;">
            K&iacute;ch th&#432;&#7899;c &mdash; Ng&agrave;y n&oacute;ng/n&#259;m
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">
            <span style="width:8px;height:8px;border-radius:50%;background:#94a3b8;
                         display:inline-block;border:1.5px solid white;"></span>
            &Iacute;t ng&agrave;y n&oacute;ng
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
            <span style="width:16px;height:16px;border-radius:50%;background:#94a3b8;
                         display:inline-block;border:1.5px solid white;"></span>
            Nhi&#7873;u ng&agrave;y n&oacute;ng
        </div>

        <div style="font-weight:700;color:#475569;font-size:10px;
                    letter-spacing:.05em;text-transform:uppercase;margin-bottom:5px;">
            C&#7843;nh b&aacute;o c&#7921;c &#273;oan
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:2px;">
            <span style="width:14px;height:14px;border-radius:50%;border:2px dashed #ef4444;
                         display:inline-block;"></span>
            &nbsp;&#9888; V&ograve;ng &#273;&#7887; nh&#7845;p nh&aacute;y
        </div>
        <div style="color:#6b7280;font-size:9.5px;margin-top:2px;line-height:1.4;">
            Nhi&#7879;t &#273;&#7897; cao &#124; M&#432;a b&#7845;t th&#432;&#7901;ng<br/>
            H&#7841;n h&aacute;n &#124; N&#7855;ng n&oacute;ng k&eacute;o d&agrave;i<br/>
            Nhi&#7873;u ng&agrave;y m&#432;a l&#7899;n li&ecirc;n ti&#7871;p
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    for point in points:
        temp_val = float(point["temp"])
        hot_val  = float(point["hot_days"])
        color    = _temp_to_color(temp_val)
        extreme  = _is_extreme(point)

        # Radius: 10–26 px scaled by hot days
        radius = 10 + (hot_val - hot_min) / hot_rng * 16

        folium.CircleMarker(
            location=[float(point["latitude"]), float(point["longitude"])],
            radius=radius,
            color="white",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.82,
            tooltip=folium.Tooltip(
                _bubble_tooltip_html(point),
                sticky=True,
                style=(
                    "background:white;"
                    "border:1px solid #E2E8F0;"
                    "border-radius:8px;"
                    "box-shadow:0 8px 24px rgba(30,58,95,0.15);"
                    "padding:0;"
                    "font-size:11px;"
                ),
            ),
        ).add_to(m)

        if extreme:
            folium.CircleMarker(
                location=[float(point["latitude"]), float(point["longitude"])],
                radius=radius + 5,
                color="#EF4444",
                weight=1.5,
                fill=False,
                opacity=0.6,
                dash_array="4 4",
            ).add_to(m)

    st_folium(m, height=560, use_container_width=True, returned_objects=[])



def render_overview_regions_tab(placeholder_box, filters: dict[str, object] | None = None) -> None:
    active_filters = filters or {
        "region": ALL_REGIONS_LABEL,
        "locations": [],
        "period": (1991, 2025),
    }

    try:
        df = load_climate_data()
        filtered_df = filter_data(df, active_filters)
    except Exception as exc:
        st.error(f"Không đọc được dữ liệu khí hậu: {exc}")
        return

    render_contextual_kpis(filtered_df, active_filters)

    left, right = st.columns([1.35, 1])
    with left:
        render_vietnam_reference_map(filtered_df)
    with right:
        placeholder_box(
            "Hồ sơ khí hậu theo vùng",
            "Biểu đồ sẽ được bổ sung: bảng tóm tắt đặc trưng nhiệt, mưa, ẩm và mùa khí hậu.",
            kicker="Tổng hợp",
        )
        st.write("")
        placeholder_box(
            "Xếp hạng khác biệt vùng",
            "Biểu đồ sẽ được bổ sung: mức tương phản giữa các vùng trong giai đoạn được chọn.",
            kicker="So sánh",
        )

    st.markdown('<div class="section-title">Khung phân tích vùng</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        placeholder_box("Phân bố điểm tham chiếu", "Biểu đồ sẽ được bổ sung.")
    with cols[1]:
        placeholder_box("Tín hiệu khí hậu nổi bật", "Biểu đồ sẽ được bổ sung.")
    with cols[2]:
        placeholder_box("Ghi chú học thuật", "Container dành cho nhận xét và diễn giải sau khi có dữ liệu.")