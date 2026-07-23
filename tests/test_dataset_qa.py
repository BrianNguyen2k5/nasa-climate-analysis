from __future__ import annotations

import re
import unittest

import pandas as pd

from ai_assistant.data_context import DATA_PATH, load_dataset
from ai_assistant.dataset_qa import (
    answer_dataset_question,
    query_dataset_question,
)


METRIC_COLUMNS = {
    "mean_temperature": "T2M",
    "maximum_temperature": "T2M_MAX",
    "rainfall": "PRECTOTCORR",
    "humidity": "RH2M",
    "wind_speed": "WS10M",
    "pressure": "PS",
    "solar_radiation": "ALLSKY_SFC_SW_DWN",
}

# Definitions documented in EDA.ipynb and verified against every dataset row.
HOT_DAY_THRESHOLD_C = 35.0
DRY_DAY_THRESHOLD_MM = 1.0


def _extract_number_before_unit(answer: str, unit: str) -> float:
    match = re.search(
        rf"(-?\d+(?:[.,]\d+)?)\s*{re.escape(unit)}",
        answer,
        flags=re.IGNORECASE,
    )
    if not match:
        raise AssertionError(
            f"Không tìm thấy số đứng trước đơn vị {unit!r} trong answer={answer!r}"
        )
    return float(match.group(1).replace(",", "."))


def _longest_dry_streak_by_location(df: pd.DataFrame) -> pd.Series:
    streaks: dict[str, int] = {}
    ordered = df.sort_values(["location_name", "date"])

    for location, group in ordered.groupby("location_name", sort=False):
        longest = 0
        current = 0
        previous_date: pd.Timestamp | None = None

        for row in group[["date", "dry_day"]].itertuples(index=False):
            date = row.date
            is_consecutive = (
                previous_date is not None
                and date - previous_date == pd.Timedelta(days=1)
            )
            if int(row.dry_day) == 1:
                current = current + 1 if is_consecutive else 1
                longest = max(longest, current)
            else:
                current = 0
            previous_date = date

        streaks[str(location)] = longest

    return pd.Series(streaks, dtype="int64")


class DatasetQARealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.df = load_dataset().copy()
        cls.df["date"] = pd.to_datetime(cls.df["date"], errors="raise")

    def test_00_real_dataset_contract_and_metric_columns(self) -> None:
        required_columns = {
            "date",
            "year",
            "location_name",
            "location_vn",
            "region_vn",
            "hot_day",
            "dry_day",
            *METRIC_COLUMNS.values(),
        }

        self.assertTrue(DATA_PATH.is_file(), f"Dataset local không tồn tại: {DATA_PATH}")
        self.assertEqual(
            required_columns - set(self.df.columns),
            set(),
            f"Thiếu cột thật trong DataFrame: {required_columns - set(self.df.columns)}",
        )
        self.assertEqual(self.df["location_name"].nunique(), 20)
        self.assertEqual(self.df["region_vn"].nunique(), 6)
        self.assertEqual(int(self.df["year"].min()), 1991)
        self.assertEqual(int(self.df["year"].max()), 2025)
        self.assertTrue(
            self.df["hot_day"].eq(
                self.df["T2M_MAX"].ge(HOT_DAY_THRESHOLD_C).astype(int)
            ).all(),
            "hot_day không khớp định nghĩa T2M_MAX >= 35°C",
        )
        self.assertTrue(
            self.df["dry_day"].eq(
                self.df["PRECTOTCORR"].lt(DRY_DAY_THRESHOLD_MM).astype(int)
            ).all(),
            "dry_day không khớp định nghĩa PRECTOTCORR < 1 mm/ngày",
        )

    def test_01_dataset_region_count(self) -> None:
        expected = int(self.df["region_vn"].nunique())

        answer = answer_dataset_question("Dataset có bao nhiêu vùng?", self.df)

        self.assertIsNotNone(answer)
        self.assertIn(
            f"{expected} vùng",
            answer,
            f"expected={expected}; actual={answer!r}; metric=region_vn.nunique()",
        )

    def test_02_locations_in_southeast_region(self) -> None:
        region = "Đông Nam Bộ"
        expected = sorted(
            self.df.loc[
                self.df["region_vn"].eq(region),
                "location_vn",
            ].dropna().unique()
        )

        answer = answer_dataset_question(
            "Liệt kê địa điểm thuộc Đông Nam Bộ.",
            self.df,
        )

        self.assertIsNotNone(answer)
        for location in expected:
            self.assertIn(
                location,
                answer,
                f"expected location={location!r}; region={region}; actual={answer!r}",
            )

    def test_03_ha_noi_mean_temperature_2020(self) -> None:
        location = "Ha Noi"
        year = 2020
        subset = self.df[
            self.df["location_name"].eq(location) & self.df["year"].eq(year)
        ]
        expected = float(subset["T2M"].mean())

        answer = answer_dataset_question(
            "Nhiệt độ trung bình Hà Nội năm 2020.",
            self.df,
        )

        self.assertIsNotNone(answer)
        actual = _extract_number_before_unit(answer, "°C")
        self.assertAlmostEqual(
            actual,
            round(expected, 2),
            places=2,
            msg=(
                f"expected={expected}; actual={actual}; "
                f"filter=location_name={location}, year={year}; metric=T2M.mean()"
            ),
        )
        self.assertIn(f"{len(subset)} bản ghi", answer)

    def test_04_hue_maximum_temperature_2024(self) -> None:
        location = "Hue"
        year = 2024
        subset = self.df[
            self.df["location_name"].eq(location) & self.df["year"].eq(year)
        ]
        expected = float(subset["T2M_MAX"].mean())

        answer = answer_dataset_question(
            "Nhiệt độ cao nhất Huế năm 2024.",
            self.df,
        )

        self.assertIsNotNone(answer)
        actual = _extract_number_before_unit(answer, "°C")
        self.assertAlmostEqual(
            actual,
            round(expected, 2),
            places=2,
            msg=(
                f"expected={expected}; actual={actual}; "
                f"filter=location_name={location}, year={year}; "
                "metric=T2M_MAX.mean()"
            ),
        )

    def test_05_hottest_region_by_mean_temperature(self) -> None:
        ranking = self.df.groupby("region_vn")["T2M"].mean().sort_values(
            ascending=False
        )
        expected_region = str(ranking.index[0])
        expected_value = float(ranking.iloc[0])

        answer = answer_dataset_question(
            "Vùng có nhiệt độ trung bình cao nhất là vùng nào?",
            self.df,
        )

        self.assertIsNotNone(
            answer,
            "Dataset QA chưa hỗ trợ ranking vùng theo T2M.mean().",
        )
        self.assertIn(expected_region, answer)
        self.assertIn(f"{expected_value:.2f}", answer)

    def test_06_rainiest_location_by_daily_mean_2020_2025(self) -> None:
        start_year = 2020
        end_year = 2025
        subset = self.df[self.df["year"].between(start_year, end_year)]
        ranking = (
            subset.groupby("location_name")["PRECTOTCORR"]
            .mean()
            .sort_values(ascending=False)
        )
        expected_location = str(ranking.index[0])
        expected_value = float(ranking.iloc[0])

        answer = answer_dataset_question(
            (
                "Địa điểm có lượng mưa trung bình ngày cao nhất "
                "giai đoạn 2020–2025 là đâu?"
            ),
            self.df,
        )

        self.assertIsNotNone(answer)
        self.assertIn(expected_location, answer)
        self.assertIn(f"{expected_value:.2f}", answer)
        self.assertIn("mm/ngày", answer.lower())

    def test_07_da_nang_humidity_2023(self) -> None:
        location = "Da Nang"
        year = 2023
        subset = self.df[
            self.df["location_name"].eq(location) & self.df["year"].eq(year)
        ]
        expected = float(subset["RH2M"].mean())

        answer = answer_dataset_question(
            "Độ ẩm Đà Nẵng năm 2023 là bao nhiêu?",
            self.df,
        )

        self.assertIsNotNone(answer)
        actual = _extract_number_before_unit(answer, "%")
        self.assertAlmostEqual(actual, round(expected, 2), places=2)

        result = query_dataset_question(
            "Độ ẩm Đà Nẵng năm 2023 là bao nhiêu?",
            self.df,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metric"], "RH2M")
        self.assertEqual(result["aggregation"], "mean")
        self.assertEqual(
            result["filters"],
            {
                "start_year": year,
                "end_year": year,
                "location_name": location,
            },
        )
        self.assertAlmostEqual(
            float(result["rows"][0]["value"]),
            expected,
            places=9,
        )

    @unittest.expectedFailure
    def test_08_expected_gap_region_with_most_hot_days(self) -> None:
        ranking = self.df.groupby("region_vn")["hot_day"].sum().sort_values(
            ascending=False
        )
        expected_region = str(ranking.index[0])
        expected_count = int(ranking.iloc[0])

        answer = answer_dataset_question(
            "Vùng có nhiều ngày nóng nhất là vùng nào?",
            self.df,
        )

        self.assertIsNotNone(
            answer,
            "Dataset QA chưa hỗ trợ tổng hot_day theo region_vn.",
        )
        self.assertIn(expected_region, answer)
        self.assertIn(str(expected_count), answer)

    @unittest.expectedFailure
    def test_09_expected_gap_location_with_longest_dry_streak(self) -> None:
        streaks = _longest_dry_streak_by_location(self.df)
        expected_location = str(streaks.idxmax())
        expected_days = int(streaks.max())

        answer = answer_dataset_question(
            "Địa điểm có chuỗi ngày khô dài nhất là đâu?",
            self.df,
        )

        self.assertIsNotNone(
            answer,
            (
                "Dataset QA chưa hỗ trợ chuỗi dry_day liên tục theo location; "
                f"expected={expected_location}, {expected_days} ngày."
            ),
        )
        self.assertIn(expected_location, answer)
        self.assertIn(str(expected_days), answer)

    def test_10_compare_ha_noi_and_ho_chi_minh_city_2020_2025(
        self,
    ) -> None:
        locations = ["Ha Noi", "Ho Chi Minh City"]
        subset = self.df[
            self.df["location_name"].isin(locations)
            & self.df["year"].between(2020, 2025)
        ]
        expected = subset.groupby("location_name")["T2M"].mean()

        answer = answer_dataset_question(
            "So sánh nhiệt độ trung bình Hà Nội và TP.HCM giai đoạn 2020–2025.",
            self.df,
        )

        self.assertIsNotNone(answer)
        for location, value in expected.items():
            self.assertIn(str(location), answer)
            self.assertIn(f"{float(value):.2f}", answer)

    def test_11_unknown_location_requests_structured_clarification(self) -> None:
        answer = answer_dataset_question(
            "Nhiệt độ trung bình Atlantis năm 2020 là bao nhiêu?",
            self.df,
        )

        self.assertIsNotNone(
            answer,
            "Location không tồn tại đang trả None thay vì yêu cầu làm rõ.",
        )
        self.assertRegex(
            answer.lower(),
            r"không (tìm thấy|có)|địa điểm|vui lòng",
        )
        self.assertNotRegex(answer, r"\d+(?:[.,]\d+)?\s*°C")

        result = query_dataset_question(
            "Nhiệt độ trung bình Atlantis năm 2020 là bao nhiêu?",
            self.df,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result["handled"])
        self.assertEqual(result["status"], "clarification")
        self.assertTrue(result["clarification_needed"])
        self.assertEqual(result["rows"], [])

    def test_12_year_outside_dataset_range_does_not_fabricate_value(self) -> None:
        outside_year = int(self.df["year"].min()) - 1

        answer = answer_dataset_question(
            f"Nhiệt độ trung bình Hà Nội năm {outside_year}.",
            self.df,
        )

        self.assertIsNotNone(answer)
        self.assertIn(str(outside_year), answer)
        self.assertIn("Không có dữ liệu", answer)
        self.assertNotRegex(answer, r"\d+(?:[.,]\d+)?\s*°C")

    def test_13_missing_year_requests_clarification(self) -> None:
        answer = answer_dataset_question(
            "Nhiệt độ trung bình Hà Nội là bao nhiêu?",
            self.df,
        )

        self.assertIsNotNone(
            answer,
            "Câu hỏi cần năm đang trả None thay vì yêu cầu làm rõ.",
        )
        self.assertRegex(answer.lower(), r"năm|thời gian|vui lòng")
        self.assertNotRegex(answer, r"\d+(?:[.,]\d+)?\s*°C")

    def test_15_total_rainfall_uses_sum_for_explicit_year(self) -> None:
        location = "Da Nang"
        year = 2023
        subset = self.df[
            self.df["location_name"].eq(location) & self.df["year"].eq(year)
        ]
        expected = float(subset["PRECTOTCORR"].sum())

        result = query_dataset_question(
            "Tổng lượng mưa Đà Nẵng năm 2023 là bao nhiêu?",
            self.df,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["metric"], "PRECTOTCORR")
        self.assertEqual(result["aggregation"], "sum")
        self.assertEqual(result["unit"], "mm")
        self.assertAlmostEqual(
            float(result["rows"][0]["value"]),
            expected,
            places=9,
        )

    def test_16_ambiguous_rainfall_query_requests_clarification(self) -> None:
        result = query_dataset_question(
            "Địa điểm có lượng mưa cao nhất là đâu?",
            self.df,
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["status"], "clarification")
        self.assertTrue(result["clarification_needed"])
        self.assertIsNone(result["aggregation"])
        self.assertEqual(result["rows"], [])
        self.assertRegex(
            result["answer"].lower(),
            r"tổng lượng mưa|lượng mưa trung bình ngày",
        )

    def test_14_accented_and_canonical_names_resolve_to_same_location(self) -> None:
        year = 2020
        display_name = "Hà Nội"
        canonical = str(
            self.df.loc[
                self.df["location_vn"].eq(display_name),
                "location_name",
            ].iloc[0]
        )

        accented_answer = answer_dataset_question(
            f"Nhiệt độ trung bình {display_name} năm {year}.",
            self.df,
        )
        canonical_answer = answer_dataset_question(
            f"Nhiệt độ trung bình {canonical} năm {year}.",
            self.df,
        )

        self.assertIsNotNone(accented_answer)
        self.assertIsNotNone(canonical_answer)
        self.assertIn(canonical, accented_answer)
        self.assertIn(canonical, canonical_answer)
        self.assertAlmostEqual(
            _extract_number_before_unit(accented_answer, "°C"),
            _extract_number_before_unit(canonical_answer, "°C"),
            places=2,
        )


if __name__ == "__main__":
    unittest.main()
