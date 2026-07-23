from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .constants import OFFICIAL_REGIONS


HOT_DAY_THRESHOLD_C = 35.0
DRY_DAY_THRESHOLD_MM = 1.0

METRIC_SPECS = {
    "T2M": {
        "phrases": ("nhiet do trung binh", "t2m"),
        "label": "Nhiệt độ trung bình",
        "unit": "°C",
        "default_aggregation": "mean",
    },
    "T2M_MAX": {
        "phrases": (
            "nhiet do cao nhat",
            "nhiet do toi cao",
            "t2m max",
            "t2m_max",
        ),
        "label": "Nhiệt độ cực đại trung bình",
        "unit": "°C",
        "default_aggregation": "mean",
    },
    "T2M_MIN": {
        "phrases": (
            "nhiet do thap nhat",
            "nhiet do toi thap",
            "t2m min",
            "t2m_min",
        ),
        "label": "Nhiệt độ cực tiểu trung bình",
        "unit": "°C",
        "default_aggregation": "mean",
    },
    "RH2M": {
        "phrases": ("do am", "rh2m"),
        "label": "Độ ẩm trung bình",
        "unit": "%",
        "default_aggregation": "mean",
    },
    "PRECTOTCORR": {
        "phrases": ("luong mua", "prectotcorr"),
        "label": "Lượng mưa",
        "unit": "mm",
        "default_aggregation": None,
    },
    "HOT_LOCATION_DAY": {
        "phrases": ("ngay nong",),
        "label": "Lượt địa điểm-ngày nóng",
        "unit": "lượt địa điểm-ngày nóng",
        "default_aggregation": "count_location_days",
    },
    "DRY_STREAK": {
        "phrases": ("chuoi ngay kho",),
        "label": "Chuỗi ngày khô dài nhất",
        "unit": "ngày",
        "default_aggregation": "longest_consecutive_streak",
    },
}

EXPLICIT_LOCATION_ALIASES = {
    "ha noi": "Ha Noi",
    "tp hcm": "Ho Chi Minh City",
    "tphcm": "Ho Chi Minh City",
    "tp ho chi minh": "Ho Chi Minh City",
    "ho chi minh": "Ho Chi Minh City",
    "hue": "Hue",
    "da nang": "Da Nang",
}


@dataclass(frozen=True)
class ParsedDatasetQuery:
    metric: str | None
    aggregation: str | None
    locations: tuple[str, ...]
    region: str | None
    start_year: int | None
    end_year: int | None
    intent: str
    clarification_needed: bool = False
    clarification_message: str = ""


def _normalize(value: object) -> str:
    text = str(value).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_number(value: float) -> str:
    return f"{value:.2f}"


def _find_year_range(prompt_norm: str) -> tuple[int | None, int | None]:
    years = [
        int(match)
        for match in re.findall(r"\b(19\d{2}|20\d{2})\b", prompt_norm)
    ]
    if not years:
        return None, None
    return min(years), max(years)


def _location_alias_map(df: pd.DataFrame) -> dict[str, str]:
    aliases: dict[str, str] = {}
    if "location_name" not in df.columns:
        return aliases

    for location in df["location_name"].dropna().astype(str).unique():
        aliases[_normalize(location)] = location

    if "location_vn" in df.columns:
        pairs = df[["location_name", "location_vn"]].dropna().drop_duplicates()
        for row in pairs.itertuples(index=False):
            aliases[_normalize(row.location_vn)] = str(row.location_name)

    available = set(df["location_name"].dropna().astype(str))
    for alias, canonical in EXPLICIT_LOCATION_ALIASES.items():
        if canonical in available:
            aliases[_normalize(alias)] = canonical
    return aliases


def _find_locations(prompt_norm: str, df: pd.DataFrame) -> tuple[str, ...]:
    padded_prompt = f" {prompt_norm} "
    matches: list[tuple[int, int, str]] = []
    for alias, canonical in _location_alias_map(df).items():
        token = f" {alias} "
        position = padded_prompt.find(token)
        if position >= 0:
            matches.append((position, -len(alias), canonical))

    locations: list[str] = []
    for _, _, canonical in sorted(matches):
        if canonical not in locations:
            locations.append(canonical)
    return tuple(locations)


def _find_region(prompt_norm: str) -> str | None:
    for region in OFFICIAL_REGIONS:
        if f" {_normalize(region)} " in f" {prompt_norm} ":
            return region
    return None


def _find_metric(prompt_norm: str) -> str | None:
    candidates: list[tuple[int, str]] = []
    for metric, spec in METRIC_SPECS.items():
        for phrase in spec["phrases"]:
            normalized_phrase = _normalize(phrase)
            if normalized_phrase in prompt_norm:
                candidates.append((len(normalized_phrase), metric))
    if not candidates:
        return None
    return max(candidates)[1]


def _rainfall_aggregation(prompt_norm: str) -> str | None:
    if "tong luong mua" in prompt_norm:
        return "sum"
    if (
        "luong mua trung binh" in prompt_norm
        or "trung binh ngay" in prompt_norm
    ):
        return "mean"
    return None


def _is_highest_query(prompt_norm: str) -> bool:
    return any(
        phrase in prompt_norm
        for phrase in ("cao nhat", "lon nhat", "nhieu nhat")
    )


def _parse_query(prompt_norm: str, df: pd.DataFrame) -> ParsedDatasetQuery | None:
    metric = _find_metric(prompt_norm)
    if metric is None:
        return None

    spec = METRIC_SPECS[metric]
    aggregation = (
        _rainfall_aggregation(prompt_norm)
        if metric == "PRECTOTCORR"
        else str(spec["default_aggregation"])
    )
    locations = _find_locations(prompt_norm, df)
    region = _find_region(prompt_norm)
    start_year, end_year = _find_year_range(prompt_norm)

    if metric == "HOT_LOCATION_DAY":
        intent = "rank_hot_regions"
    elif metric == "DRY_STREAK":
        intent = "longest_dry_streak"
    elif "so sanh" in prompt_norm:
        intent = "compare_locations"
    elif "vung" in prompt_norm and _is_highest_query(prompt_norm):
        intent = "rank_regions"
    elif "dia diem" in prompt_norm and _is_highest_query(prompt_norm):
        intent = "rank_locations"
    else:
        intent = "location_metric"

    clarification = ""
    if metric == "PRECTOTCORR" and aggregation is None:
        clarification = (
            "Vui lòng cho biết cần tổng lượng mưa hay lượng mưa trung bình ngày."
        )
        if start_year is None or end_year is None:
            clarification += " Đồng thời, hãy cung cấp năm hoặc khoảng năm."
    elif metric == "PRECTOTCORR" and (
        start_year is None or end_year is None
    ):
        clarification = (
            "Vui lòng cung cấp năm hoặc khoảng năm cho truy vấn lượng mưa; "
            "Dataset QA không tự dùng toàn bộ giai đoạn."
        )
    elif metric in {"HOT_LOCATION_DAY", "DRY_STREAK"} and (
        start_year is None or end_year is None
    ):
        clarification = (
            "Vui lòng cung cấp năm hoặc khoảng năm cho chỉ số dẫn xuất; "
            "Dataset QA không tự chọn giai đoạn mặc định."
        )
    elif intent == "compare_locations" and len(locations) < 2:
        clarification = (
            "Không tìm thấy đủ hai địa điểm để so sánh. "
            "Vui lòng dùng tên địa điểm canonical hoặc tên tiếng Việt."
        )
    elif intent == "location_metric" and not locations:
        valid_locations = ", ".join(
            sorted(df["location_name"].dropna().astype(str).unique())
        )
        clarification = (
            "Không tìm thấy địa điểm trong dataset. "
            f"Vui lòng chọn một trong các location_name: {valid_locations}."
        )
    elif intent in {"location_metric", "compare_locations", "rank_locations"} and (
        start_year is None or end_year is None
    ):
        clarification = (
            "Vui lòng cung cấp năm hoặc khoảng năm cần phân tích; "
            "Dataset QA không tự chọn năm mặc định."
        )

    return ParsedDatasetQuery(
        metric=metric,
        aggregation=aggregation,
        locations=locations,
        region=region,
        start_year=start_year,
        end_year=end_year,
        intent=intent,
        clarification_needed=bool(clarification),
        clarification_message=clarification,
    )


def _filters_for_query(query: ParsedDatasetQuery) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "start_year": query.start_year,
        "end_year": query.end_year,
    }
    if len(query.locations) == 1:
        filters["location_name"] = query.locations[0]
    elif query.locations:
        filters["location_names"] = list(query.locations)
    if query.region:
        filters["region_vn"] = query.region
    return filters


def _structured_result(
    query: ParsedDatasetQuery,
    *,
    status: str,
    answer: str,
    rows: list[dict[str, Any]] | None = None,
    threshold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = METRIC_SPECS.get(query.metric or "", {})
    unit = str(spec.get("unit", ""))
    if query.metric == "PRECTOTCORR" and query.aggregation == "mean":
        unit = "mm/ngày"
    return {
        "handled": True,
        "status": status,
        "metric": query.metric,
        "metric_label": spec.get("label"),
        "unit": unit,
        "aggregation": query.aggregation,
        "threshold": threshold,
        "filters": _filters_for_query(query),
        "intent": query.intent,
        "clarification_needed": query.clarification_needed,
        "parsed_query": asdict(query),
        "rows": rows or [],
        "answer": answer,
    }


def _region_location_result(df: pd.DataFrame) -> dict[str, Any] | None:
    if not {"region_vn", "location_vn"}.issubset(df.columns):
        return None
    lines = []
    rows = []
    for region in OFFICIAL_REGIONS:
        group = df[df["region_vn"].eq(region)]
        if group.empty:
            continue
        locations = sorted(group["location_vn"].dropna().unique().tolist())
        rows.append({"region_vn": region, "locations": locations})
        lines.append(f"- {region}: {len(locations)} điểm, gồm {', '.join(locations)}")
    total_regions = sum(df["region_vn"].eq(region).any() for region in OFFICIAL_REGIONS)
    total_locations = int(df["location_vn"].nunique())
    answer = (
        f"Dataset hiện có {total_regions} vùng và {total_locations} điểm tham chiếu:\n"
        + "\n".join(lines)
    )
    return {
        "handled": True,
        "status": "ok",
        "metric": None,
        "metric_label": None,
        "unit": "",
        "aggregation": "count",
        "filters": {},
        "intent": "dataset_scope",
        "clarification_needed": False,
        "parsed_query": None,
        "rows": rows,
        "answer": answer,
    }


def _single_region_location_result(
    prompt_norm: str,
    df: pd.DataFrame,
) -> dict[str, Any] | None:
    if not {"region_vn", "location_vn"}.issubset(df.columns):
        return None
    for region in OFFICIAL_REGIONS:
        if _normalize(region) not in prompt_norm:
            continue
        locations = sorted(
            df.loc[df["region_vn"].eq(region), "location_vn"]
            .dropna()
            .unique()
            .tolist()
        )
        return {
            "handled": True,
            "status": "ok",
            "metric": None,
            "metric_label": None,
            "unit": "",
            "aggregation": "list",
            "filters": {"region_vn": region},
            "intent": "region_locations",
            "clarification_needed": False,
            "parsed_query": None,
            "rows": [{"region_vn": region, "locations": locations}],
            "answer": (
                f"{region} có {len(locations)} điểm tham chiếu: "
                f"{', '.join(locations)}."
            ),
        }
    return None


def _time_subset(df: pd.DataFrame, query: ParsedDatasetQuery) -> pd.DataFrame:
    subset = df
    if query.start_year is not None and query.end_year is not None:
        subset = subset[subset["year"].between(query.start_year, query.end_year)]
    if query.region is not None:
        subset = subset[subset["region_vn"].eq(query.region)]
    return subset


def _aggregate(series: pd.Series, aggregation: str) -> float:
    if aggregation == "sum":
        return float(series.sum())
    return float(series.mean())


def _period_label(query: ParsedDatasetQuery) -> str:
    if query.start_year == query.end_year:
        return f"năm {query.start_year}"
    return f"giai đoạn {query.start_year}–{query.end_year}"


def _single_location_result(
    query: ParsedDatasetQuery,
    df: pd.DataFrame,
) -> dict[str, Any]:
    assert query.metric is not None
    assert query.aggregation is not None
    location = query.locations[0]
    subset = _time_subset(df, query)
    subset = subset[subset["location_name"].eq(location)]
    if subset.empty:
        answer = (
            f"Không có dữ liệu {location} trong {_period_label(query)} "
            "trong dataset hiện tại."
        )
        return _structured_result(query, status="no_data", answer=answer)

    value = _aggregate(subset[query.metric], query.aggregation)
    count = int(subset[query.metric].count())
    spec = METRIC_SPECS[query.metric]
    unit = str(spec["unit"])
    label = str(spec["label"])
    if query.metric == "PRECTOTCORR":
        if query.aggregation == "sum":
            label = "Tổng lượng mưa"
        else:
            label = "Lượng mưa trung bình ngày"
            unit = "mm/ngày"
    answer = (
        f"{label} của {location} {_period_label(query)} là "
        f"{_display_number(value)}{unit} "
        f"(tính từ {count} bản ghi ngày trong dataset hiện tại)."
    )
    rows = [{"location_name": location, "value": value, "count": count}]
    return _structured_result(query, status="ok", answer=answer, rows=rows)


def _ranking_result(
    query: ParsedDatasetQuery,
    df: pd.DataFrame,
) -> dict[str, Any]:
    assert query.metric is not None
    assert query.aggregation is not None
    subset = _time_subset(df, query)
    group_column = "region_vn" if query.intent == "rank_regions" else "location_name"
    ranking = (
        subset.groupby(group_column)[query.metric]
        .agg(query.aggregation)
        .sort_values(ascending=False)
    )
    if ranking.empty:
        return _structured_result(
            query,
            status="no_data",
            answer="Không có dữ liệu phù hợp với bộ lọc đã cung cấp.",
        )

    subject = str(ranking.index[0])
    value = float(ranking.iloc[0])
    spec = METRIC_SPECS[query.metric]
    unit = str(spec["unit"])
    label = str(spec["label"]).lower()
    if query.metric == "PRECTOTCORR":
        if query.aggregation == "sum":
            label = "tổng lượng mưa"
        else:
            label = "lượng mưa trung bình ngày"
            unit = "mm/ngày"
    subject_label = "Vùng" if group_column == "region_vn" else "Địa điểm"
    period = f" {_period_label(query)}" if query.start_year is not None else ""
    answer = (
        f"{subject_label} có {label} cao nhất{period} là {subject}, "
        f"với {_display_number(value)}{unit}."
    )
    rows = [
        {group_column: str(name), "value": float(metric_value)}
        for name, metric_value in ranking.items()
    ]
    return _structured_result(query, status="ok", answer=answer, rows=rows)


def _comparison_result(
    query: ParsedDatasetQuery,
    df: pd.DataFrame,
) -> dict[str, Any]:
    assert query.metric is not None
    assert query.aggregation is not None
    subset = _time_subset(df, query)
    subset = subset[subset["location_name"].isin(query.locations)]
    grouped = subset.groupby("location_name")[query.metric].agg(query.aggregation)
    if grouped.empty:
        return _structured_result(
            query,
            status="no_data",
            answer="Không có dữ liệu phù hợp để so sánh.",
        )

    spec = METRIC_SPECS[query.metric]
    unit = str(spec["unit"])
    label = str(spec["label"]).lower()
    lines = []
    rows = []
    for location in query.locations:
        if location not in grouped:
            continue
        value = float(grouped.loc[location])
        rows.append({"location_name": location, "value": value})
        lines.append(f"- {location}: {_display_number(value)}{unit}")
    answer = (
        f"So sánh {label} {_period_label(query)}:\n" + "\n".join(lines)
    )
    return _structured_result(query, status="ok", answer=answer, rows=rows)


def _hot_location_day_result(
    query: ParsedDatasetQuery,
    df: pd.DataFrame,
) -> dict[str, Any]:
    subset = _time_subset(df, query).copy()
    threshold = {
        "column": "T2M_MAX",
        "operator": ">=",
        "value": HOT_DAY_THRESHOLD_C,
        "unit": "°C",
    }
    if subset.empty:
        return _structured_result(
            query,
            status="no_data",
            answer="Không có dữ liệu phù hợp với bộ lọc đã cung cấp.",
            threshold=threshold,
        )

    subset["is_hot_location_day"] = subset["T2M_MAX"].ge(
        HOT_DAY_THRESHOLD_C
    )
    ranking = (
        subset.groupby("region_vn")["is_hot_location_day"]
        .sum()
        .astype(int)
        .sort_values(ascending=False)
    )
    if ranking.empty:
        return _structured_result(
            query,
            status="no_data",
            answer="Không có dữ liệu vùng phù hợp với bộ lọc đã cung cấp.",
            threshold=threshold,
        )

    region = str(ranking.index[0])
    count = int(ranking.iloc[0])
    answer = (
        f"Vùng có nhiều lượt địa điểm-ngày nóng nhất {_period_label(query)} "
        f"là {region}, với {count} lượt. "
        "Một lượt được tính khi một địa điểm trong một ngày có "
        f"T2M_MAX ≥ {HOT_DAY_THRESHOLD_C:g}°C; đây không phải số ngày "
        "lịch duy nhất của toàn vùng."
    )
    rows = [
        {
            "region_vn": str(region_name),
            "hot_location_day_count": int(region_count),
        }
        for region_name, region_count in ranking.items()
    ]
    return _structured_result(
        query,
        status="ok",
        answer=answer,
        rows=rows,
        threshold=threshold,
    )


def _longest_dry_streak_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    working = df[["location_name", "date", "PRECTOTCORR"]].copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working = working.dropna(subset=["location_name", "date"]).sort_values(
        ["location_name", "date"]
    )

    rows: list[dict[str, Any]] = []
    for location, group in working.groupby("location_name", sort=True):
        longest = 0
        longest_start: pd.Timestamp | None = None
        longest_end: pd.Timestamp | None = None
        current = 0
        current_start: pd.Timestamp | None = None
        previous_date: pd.Timestamp | None = None

        for row in group[["date", "PRECTOTCORR"]].itertuples(index=False):
            date = row.date
            is_dry = bool(row.PRECTOTCORR < DRY_DAY_THRESHOLD_MM)
            is_consecutive = (
                previous_date is not None
                and date - previous_date == pd.Timedelta(days=1)
            )
            if is_dry:
                if current > 0 and is_consecutive:
                    current += 1
                else:
                    current = 1
                    current_start = date
                if current > longest:
                    longest = current
                    longest_start = current_start
                    longest_end = date
            else:
                current = 0
                current_start = None
            previous_date = date

        rows.append(
            {
                "location_name": str(location),
                "longest_streak_days": longest,
                "start_date": (
                    longest_start.date().isoformat()
                    if longest_start is not None
                    else None
                ),
                "end_date": (
                    longest_end.date().isoformat()
                    if longest_end is not None
                    else None
                ),
            }
        )

    return sorted(
        rows,
        key=lambda row: (-int(row["longest_streak_days"]), row["location_name"]),
    )


def _longest_dry_streak_result(
    query: ParsedDatasetQuery,
    df: pd.DataFrame,
) -> dict[str, Any]:
    subset = _time_subset(df, query)
    threshold = {
        "column": "PRECTOTCORR",
        "operator": "<",
        "value": DRY_DAY_THRESHOLD_MM,
        "unit": "mm/ngày",
    }
    rows = _longest_dry_streak_rows(subset)
    if not rows or int(rows[0]["longest_streak_days"]) == 0:
        return _structured_result(
            query,
            status="no_data",
            answer="Không có chuỗi ngày khô phù hợp với bộ lọc đã cung cấp.",
            rows=rows,
            threshold=threshold,
        )

    top = rows[0]
    answer = (
        f"Địa điểm có chuỗi ngày khô dài nhất {_period_label(query)} là "
        f"{top['location_name']}, kéo dài {top['longest_streak_days']} ngày "
        f"từ {top['start_date']} đến {top['end_date']}. "
        f"Ngày khô được xác định khi PRECTOTCORR < {DRY_DAY_THRESHOLD_MM:g} "
        "mm/ngày và chuỗi chỉ nối các ngày lịch liên tiếp."
    )
    return _structured_result(
        query,
        status="ok",
        answer=answer,
        rows=rows,
        threshold=threshold,
    )


def query_dataset_question(prompt: str, df: pd.DataFrame) -> dict[str, Any] | None:
    prompt_norm = _normalize(prompt)

    if (
        "bao nhieu vung" in prompt_norm
        or "cac tinh thanh cua moi vung" in prompt_norm
        or "cac diem cua moi vung" in prompt_norm
    ):
        return _region_location_result(df)

    if "dia diem" in prompt_norm or "tinh thanh" in prompt_norm:
        region_result = _single_region_location_result(prompt_norm, df)
        if region_result:
            return region_result

    query = _parse_query(prompt_norm, df)
    if query is None:
        return None
    if query.clarification_needed:
        return _structured_result(
            query,
            status="clarification",
            answer=query.clarification_message,
        )
    if query.intent == "location_metric":
        return _single_location_result(query, df)
    if query.intent in {"rank_regions", "rank_locations"}:
        return _ranking_result(query, df)
    if query.intent == "compare_locations":
        return _comparison_result(query, df)
    if query.intent == "rank_hot_regions":
        return _hot_location_day_result(query, df)
    if query.intent == "longest_dry_streak":
        return _longest_dry_streak_result(query, df)
    return None


def answer_dataset_question(prompt: str, df: pd.DataFrame) -> str | None:
    result = query_dataset_question(prompt, df)
    if result is None:
        return None
    return str(result["answer"])
