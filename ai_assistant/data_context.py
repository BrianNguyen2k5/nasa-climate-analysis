from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "nasa_power_vietnam_daily_clean.csv"

REGION_VIETNAMESE = {
    "North West": "Tay Bac",
    "North East": "Dong Bac",
    "Red River Delta": "Dong bang song Hong",
    "North Central": "Bac Trung Bo",
    "South Central Coast": "Duyen hai Nam Trung Bo",
    "Central Highlands": "Tay Nguyen",
}

LOCATION_VIETNAMESE = {
    "Lai Chau": "Lai Chau",
    "Sapa": "Sa Pa",
    "Son La": "Son La",
    "Ha Giang": "Ha Giang",
    "Cao Bang": "Cao Bang",
    "Lang Son": "Lang Son",
    "Ha Noi": "Ha Noi",
    "Hai Phong": "Hai Phong",
    "Ninh Binh": "Ninh Binh",
    "Thanh Hoa": "Thanh Hoa",
    "Vinh": "Vinh",
    "Hue": "Hue",
    "Da Nang": "Da Nang",
    "Quy Nhon": "Quy Nhon",
    "Nha Trang": "Nha Trang",
    "Da Lat": "Da Lat",
    "Pleiku": "Pleiku",
    "Buon Ma Thuot": "Buon Ma Thuot",
}


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, low_memory=False)
    if "region" in df.columns and "region_vn" not in df.columns:
        df["region_vn"] = df["region"].map(REGION_VIETNAMESE).fillna(df["region"])
    if "location_name" in df.columns and "location_vn" not in df.columns:
        df["location_vn"] = df["location_name"].map(LOCATION_VIETNAMESE).fillna(df["location_name"])
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
    regions = sorted(df["region_vn"].dropna().unique().tolist()) if "region_vn" in df.columns else []
    locations = sorted(df["location_vn"].dropna().unique().tolist()) if "location_vn" in df.columns else []
    if {"region_vn", "location_vn"}.issubset(df.columns):
        region_location_map = {
            region: sorted(group["location_vn"].dropna().unique().tolist())
            for region, group in df.groupby("region_vn")
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

