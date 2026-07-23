from __future__ import annotations

from pathlib import Path

import pandas as pd

from .constants import (
    LOCATION_TO_REGION,
    LOCATION_VIETNAMESE,
    OFFICIAL_REGIONS,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "nasa_power_vietnam_daily_clean.csv"


def _validate_dataset_scope(df: pd.DataFrame) -> None:
    required = {"region", "location_name"}
    missing_columns = sorted(required - set(df.columns))
    if missing_columns:
        raise ValueError("Dataset thiếu cột phạm vi: " + ", ".join(missing_columns))

    actual_regions = set(df["region"].dropna().astype(str).unique())
    official_regions = set(OFFICIAL_REGIONS)
    if actual_regions != official_regions:
        missing = sorted(official_regions - actual_regions)
        unexpected = sorted(actual_regions - official_regions)
        raise ValueError(
            f"Danh sách vùng không khớp cấu hình AI; thiếu={missing}, "
            f"ngoài cấu hình={unexpected}."
        )

    pairs = df[["location_name", "region"]].drop_duplicates()
    actual_locations = set(pairs["location_name"].astype(str))
    expected_locations = set(LOCATION_TO_REGION)
    if actual_locations != expected_locations:
        missing = sorted(expected_locations - actual_locations)
        unexpected = sorted(actual_locations - expected_locations)
        raise ValueError(
            f"Danh sách địa điểm không khớp cấu hình AI; thiếu={missing}, "
            f"ngoài cấu hình={unexpected}."
        )

    mismatches = [
        f"{row.location_name}: {row.region}"
        for row in pairs.itertuples(index=False)
        if LOCATION_TO_REGION[str(row.location_name)] != str(row.region)
    ]
    if mismatches:
        raise ValueError("Mapping địa điểm-vùng không khớp dataset: " + "; ".join(mismatches))


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, low_memory=False)
    _validate_dataset_scope(df)
    df["region_vn"] = df["region"]
    df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE)
    return df


def dataset_context(df: pd.DataFrame) -> str:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = [col for col in df.columns if col not in numeric_cols]
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False).head(12).to_dict()
    numeric_summary = (
        df[numeric_cols]
        .describe()
        .loc[["mean", "min", "max"]]
        .round(3)
        .to_dict()
        if numeric_cols
        else {}
    )
    present_regions = set(df["region_vn"].dropna().astype(str)) if "region_vn" in df.columns else set()
    regions = [region for region in OFFICIAL_REGIONS if region in present_regions]
    locations = sorted(df["location_vn"].dropna().unique().tolist()) if "location_vn" in df.columns else []
    if {"region_vn", "location_vn"}.issubset(df.columns):
        region_location_map = {
            region: sorted(
                df.loc[df["region_vn"].eq(region), "location_vn"].dropna().unique().tolist()
            )
            for region in regions
        }
        region_location_counts = {
            region: len(items)
            for region, items in region_location_map.items()
        }
    else:
        region_location_map = {}
        region_location_counts = {}

    return (
        "Dataset: NASA POWER Vietnam daily climate data.\n"
        f"Shape: {df.shape[0]} rows x {df.shape[1]} columns.\n"
        f"Columns: {list(df.columns)}\n"
        f"Numeric columns: {numeric_cols}\n"
        f"Categorical/date columns: {categorical_cols}\n"
        f"Regions: {regions}\n"
        f"Locations: {locations}\n"
        f"Region location counts: {region_location_counts}\n"
        f"Region to locations: {region_location_map}\n"
        f"Missing values top: {missing}\n"
        f"Numeric summary mean/min/max: {numeric_summary}\n"
        "Important columns: T2M, T2M_MAX, T2M_MIN, RH2M, PRECTOTCORR, "
        "WS10M, PS, ALLSKY_SFC_SW_DWN, year, month, region_vn, location_vn."
    )
