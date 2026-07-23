from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .constants import OFFICIAL_REGIONS


TEMPERATURE_ALIASES = {
    "nhiet do trung binh": "T2M",
    "t2m": "T2M",
    "nhiet do cao nhat": "T2M_MAX",
    "t2m max": "T2M_MAX",
    "t2m_max": "T2M_MAX",
    "nhiet do thap nhat": "T2M_MIN",
    "t2m min": "T2M_MIN",
    "t2m_min": "T2M_MIN",
}


def _normalize(value: object) -> str:
    text = str(value).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_number(value: float) -> str:
    return f"{value:.2f}"


def _find_year(prompt_norm: str, df: pd.DataFrame) -> int | None:
    years = [int(match) for match in re.findall(r"\b(19\d{2}|20\d{2})\b", prompt_norm)]
    if not years or "year" not in df.columns:
        return None
    available_years = set(int(year) for year in df["year"].dropna().unique())
    for year in years:
        if year in available_years:
            return year
    return years[0]


def _find_location(prompt_norm: str, df: pd.DataFrame) -> tuple[str, pd.Series] | None:
    if "location_name" not in df.columns:
        return None

    candidates: list[tuple[int, str, pd.Series]] = []
    location_columns = ["location_name"]
    if "location_vn" in df.columns:
        location_columns.append("location_vn")

    for column in location_columns:
        for location in sorted(df[column].dropna().unique(), key=lambda item: len(str(item)), reverse=True):
            location_norm = _normalize(location)
            if location_norm and location_norm in prompt_norm:
                mask = df[column].eq(location)
                display = str(df.loc[mask, "location_name"].iloc[0])
                candidates.append((len(location_norm), display, mask))

    if not candidates:
        return None
    _, display, mask = max(candidates, key=lambda item: item[0])
    return display, mask


def _region_location_answer(df: pd.DataFrame) -> str | None:
    if not {"region_vn", "location_vn"}.issubset(df.columns):
        return None
    lines = []
    for region in OFFICIAL_REGIONS:
        group = df[df["region_vn"].eq(region)]
        if group.empty:
            continue
        locations = sorted(group["location_vn"].dropna().unique().tolist())
        lines.append(f"- {region}: {len(locations)} điểm, gồm {', '.join(locations)}")
    total_regions = sum(df["region_vn"].eq(region).any() for region in OFFICIAL_REGIONS)
    total_locations = df["location_vn"].nunique()
    return f"Dataset hiện có {total_regions} vùng và {total_locations} điểm tham chiếu:\n" + "\n".join(lines)


def _single_region_location_answer(prompt_norm: str, df: pd.DataFrame) -> str | None:
    if not {"region_vn", "location_vn"}.issubset(df.columns):
        return None
    for region in OFFICIAL_REGIONS:
        if _normalize(region) not in prompt_norm:
            continue
        locations = sorted(
            df.loc[df["region_vn"].eq(region), "location_vn"].dropna().unique().tolist()
        )
        return f"{region} có {len(locations)} điểm tham chiếu: {', '.join(locations)}."
    return None


def answer_dataset_question(prompt: str, df: pd.DataFrame) -> str | None:
    prompt_norm = _normalize(prompt)

    if (
        "bao nhieu vung" in prompt_norm
        or "cac tinh thanh cua moi vung" in prompt_norm
        or "cac diem cua moi vung" in prompt_norm
    ):
        return _region_location_answer(df)

    if "dia diem" in prompt_norm or "tinh thanh" in prompt_norm:
        region_answer = _single_region_location_answer(prompt_norm, df)
        if region_answer:
            return region_answer

    metric_col = None
    metric_label = None
    for phrase, column in TEMPERATURE_ALIASES.items():
        if phrase in prompt_norm:
            metric_col = column
            metric_label = phrase
            break

    if metric_col is None or metric_col not in df.columns:
        return None

    location_match = _find_location(prompt_norm, df)
    year = _find_year(prompt_norm, df)
    if location_match is None or year is None:
        return None

    location_name, location_mask = location_match
    subset = df[location_mask & df["year"].eq(year)]
    if subset.empty:
        return f"Không có dữ liệu {location_name} trong năm {year} trong dataset hiện tại."

    value = float(subset[metric_col].mean())
    count = int(subset[metric_col].count())
    label = {
        "T2M": "nhiệt độ trung bình",
        "T2M_MAX": "nhiệt độ cực đại trung bình",
        "T2M_MIN": "nhiệt độ cực tiểu trung bình",
    }.get(metric_col, metric_label or metric_col)

    return (
        f"{label.capitalize()} của {location_name} năm {year} là {_display_number(value)}°C "
        f"(tính từ {count} bản ghi ngày trong dataset hiện tại)."
    )
