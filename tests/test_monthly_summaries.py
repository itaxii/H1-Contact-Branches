import unittest

import pandas as pd

from analysis import (
    WORKBOOK,
    extract_kpis,
    extract_lob_totals,
    extract_monthly,
    extract_monthly_counts,
    row_to_record,
)


def build_summary_fixture(title, headers, january, total):
    width = max(19, len(headers) + 2)
    rows = [[None] * width for _ in range(4)]
    rows[0][2] = title
    rows[1][2 : 2 + len(headers)] = headers
    rows[2][2 : 2 + len(january)] = january
    rows[3][2 : 2 + len(total)] = total
    return pd.DataFrame(rows)


def build_amount_fixture():
    headers = [
        "Month",
        "New Premiums 2025",
        "Renewal Premiums 2025",
        "Other Policies (Endorsement + Collection ) 2025",
        "New Premiums 2026",
        "Renewal Premuims 2026",
        "Other Policies (Endorsement + Collection ) 2026",
        "2025",
        "2026",
        "Target ( 2025 + 25%)",
        "Target Achievement %",
        "2025 VS 2026 YOY",
        "Motor Premiums 2026",
        "Non-Motor Premiums 2026",
        "Motor Premium 2025",
        "Non-Motor Premium 2025",
        "Pending Finance",
    ]
    january = [
        "January",
        100,
        200,
        25,
        120,
        220,
        30,
        325,
        370,
        406.25,
        370 / 406.25,
        45,
        300,
        70,
        250,
        75,
        10,
    ]
    return build_summary_fixture(
        "2025 vs 2026 By Premium Amount Summary", headers, january, ["Grand Total", *january[1:]]
    )


def build_count_fixture():
    headers = [
        "Month",
        "New Policies 2025",
        "Renewal Policies 2025",
        "Other Policies 2025",
        "New Policies 2026",
        "Renewal Policies 2026",
        "Other Policies 2026",
        "2025",
        "2026",
        "YoY",
        "Motor Policies 2026",
        "Non-Motor Policies 2026",
        "Motor Policies 2025",
        "Non-Motor Policies LY",
        "Motor Average Rate 2026",
        "Motor Average Rate 2025",
    ]
    january = ["January", 20, 10, 2, 12, 8, 1, 32, 21, 11, 9, 12, 7, 25, 0.019, 0.02]
    return build_summary_fixture(
        "2025 vs 2026 By Premium Count Summary", headers, january, ["Grand Total", *january[1:]]
    )


def build_kpi_fixture(previous, current, source_rate):
    rows = [[None] * 7 for _ in range(20)]
    rows[12][2] = "Approved Gross Premiums"
    rows[12][3] = previous
    rows[12][4] = current
    rows[12][5] = 999
    rows[12][6] = source_rate
    return pd.DataFrame(rows)


def build_entity_row(previous, current):
    values = ["Sample Branch", previous, current, 999, 0.99]
    values.extend([0] * 14)
    return pd.Series(values)


class MonthlySummaryExtractionTests(unittest.TestCase):
    def test_amount_summary_maps_every_new_header(self):
        rows, total = extract_monthly(build_amount_fixture())

        self.assertEqual(rows[0]["new_premium_2025"], 100.0)
        self.assertEqual(rows[0]["renewal_premium_2025"], 200.0)
        self.assertEqual(rows[0]["other_premium_2025"], 25.0)
        self.assertEqual(rows[0]["new_premium"], 120.0)
        self.assertEqual(rows[0]["endorsement_premium"], 30.0)
        self.assertEqual(rows[0]["motor_premium_2025"], 250.0)
        self.assertEqual(rows[0]["non_motor_premium_2025"], 75.0)
        self.assertEqual(total["month"], "Grand Total")

    def test_count_summary_maps_counts_and_rates(self):
        rows, total = extract_monthly_counts(build_count_fixture())

        self.assertEqual(rows[0]["new_policies_2026"], 12.0)
        self.assertEqual(rows[0]["non_motor_policies_2025"], 25.0)
        self.assertAlmostEqual(rows[0]["motor_average_rate_2026"], 0.019)
        self.assertEqual(total["month"], "Grand Total")

    def test_amount_summary_recalculates_target_achievement_from_raw_values(self):
        fixture = build_amount_fixture()
        fixture.iat[2, 12] = 0.99

        rows, _ = extract_monthly(fixture)

        self.assertAlmostEqual(rows[0]["target_achievement_pct"], 370 / 406.25)

    def test_kpi_yoy_recalculates_from_raw_values(self):
        result = extract_kpis(build_kpi_fixture(previous=200, current=91, source_rate=-0.54))

        self.assertEqual(result["Approved Gross Premiums"]["change"], -109)
        self.assertAlmostEqual(result["Approved Gross Premiums"]["change_pct"], -109 / 200)

    def test_entity_missing_prior_year_keeps_yoy_undefined(self):
        record = row_to_record(build_entity_row(previous=None, current=100), list(range(19)), "branch")

        self.assertIsNone(record["yoy_change_pct"])
        self.assertEqual(record["growth_class"], "New Base")


class MonthlySummaryWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overview = pd.read_excel(WORKBOOK, sheet_name="overview", header=None, engine="openpyxl")

    def test_updated_workbook_contains_july_and_reconciled_totals(self):
        amount_rows, amount_total = extract_monthly(self.overview)
        count_rows, count_total = extract_monthly_counts(self.overview)

        self.assertEqual(amount_rows[-1]["month"], "July")
        self.assertEqual(count_rows[-1]["month"], "July")
        self.assertLessEqual(
            abs(sum(r["actual_2026"] for r in amount_rows) - amount_total["actual_2026"]),
            1,
        )
        self.assertEqual(
            sum(r["total_policies_2026"] for r in count_rows),
            count_total["total_policies_2026"],
        )

    def test_line_of_business_extraction_starts_after_real_header(self):
        rows, total = extract_lob_totals(self.overview)

        self.assertNotIn("Line of Business", [r["line_of_business"] for r in rows])
        self.assertNotIn("Month", [r["line_of_business"] for r in rows])
        self.assertLessEqual(
            abs(sum((r["premium_2026"] or 0) for r in rows) - total["premium_2026"]),
            1,
        )

if __name__ == "__main__":
    unittest.main()
