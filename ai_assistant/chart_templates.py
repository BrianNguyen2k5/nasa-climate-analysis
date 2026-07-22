from __future__ import annotations

import re
import unicodedata

import pandas as pd


LOCATION_ALIASES = {
    "buon ma thuot": "Buon Ma Thuot",
    "buon ma thuot": "Buon Ma Thuot",
    "buon ma thuat": "Buon Ma Thuot",
    "tp ho chi minh": "Ho Chi Minh City",
    "tp hcm": "Ho Chi Minh City",
    "ho chi minh": "Ho Chi Minh City",
    "thanh pho ho chi minh": "Ho Chi Minh City",
}


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFD", text.lower())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _find_year(prompt_norm: str, df: pd.DataFrame) -> int | None:
    matches = [int(item) for item in re.findall(r"\b(19\d{2}|20\d{2})\b", prompt_norm)]
    if not matches or "year" not in df.columns:
        return None
    years = set(int(year) for year in df["year"].dropna().unique())
    return next((year for year in matches if year in years), matches[0])


def _find_locations(prompt_norm: str, df: pd.DataFrame) -> list[str]:
    found: list[str] = []
    for alias, canonical in LOCATION_ALIASES.items():
        if alias in prompt_norm and canonical not in found:
            found.append(canonical)

    if "location_name" in df.columns:
        for location in sorted(df["location_name"].dropna().unique(), key=lambda item: len(str(item)), reverse=True):
            if _normalize(str(location)) in prompt_norm and str(location) not in found:
                found.append(str(location))

    return found


def build_chart_code_from_prompt(prompt: str, df: pd.DataFrame) -> tuple[str, str] | None:
    prompt_norm = _normalize(prompt)
    if "ve" not in prompt_norm and "bieu do" not in prompt_norm and "chart" not in prompt_norm:
        return None
    if "nhiet do" not in prompt_norm and "t2m" not in prompt_norm:
        return None

    year = _find_year(prompt_norm, df)
    locations = _find_locations(prompt_norm, df)
    if year is None or not locations:
        return None

    locations_repr = repr(locations)
    if "thang" in prompt_norm:
        code = f"""# Lọc dữ liệu theo năm và địa điểm từ dataset hiện tại
df_filtered = df[(df['year'] == {year}) & (df['location_name'].isin({locations_repr}))]

# Tính nhiệt độ trung bình theo tháng cho từng địa điểm
df_chart = df_filtered.groupby(['location_name', 'month'])['T2M'].mean().reset_index()

# Vẽ biểu đồ đường so sánh nhiệt độ trung bình theo tháng
fig = px.line(
    df_chart,
    x='month',
    y='T2M',
    color='location_name',
    markers=True,
    title='Nhiệt độ trung bình theo tháng năm {year}',
    labels={{'month': 'Tháng', 'T2M': 'Nhiệt độ trung bình (°C)', 'location_name': 'Địa điểm'}},
)
fig.update_xaxes(dtick=1)
"""
    else:
        code = f"""# Lọc dữ liệu theo năm và địa điểm từ dataset hiện tại
df_filtered = df[(df['year'] == {year}) & (df['location_name'].isin({locations_repr}))]

# Vẽ biểu đồ đường nhiệt độ trung bình ngày trong năm
fig = px.line(
    df_filtered,
    x='date',
    y='T2M',
    color='location_name',
    title='Nhiệt độ trung bình năm {year}',
    labels={{'date': 'Ngày', 'T2M': 'Nhiệt độ trung bình (°C)', 'location_name': 'Địa điểm'}},
)
"""
    answer = "Đã tạo code biểu đồ từ dataset hiện tại. Bạn có thể kiểm tra, chỉnh sửa rồi bấm Chấp nhận & chạy."
    return answer, code
