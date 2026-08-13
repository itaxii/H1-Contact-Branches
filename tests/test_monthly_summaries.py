import json
import unittest

import pandas as pd

import analysis
from analysis import (
    DATA_DIR,
    WORKBOOK,
    extract_kpis,
    extract_lob_totals,
    extract_monthly,
    extract_monthly_counts,
    extract_renewals,
    extract_insurers,
    extract_sellers,
    extract_branches_per_day_this_month,
    row_to_record,
    main,
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


def build_seller_fixture():
    rows = [[None] * 21 for _ in range(10)]
    rows[0][2] = "TOP 20 Sellers"
    rows[1][2] = "Branch"
    rows[1][3:21] = [
        "Premiums 2025 (Approved)", "Premiums 2026 (Approved)", "Gross YoY Change",
        "Gross YoY Change %", "Pending Operation (Paid)", "Pending Finance",
        "Pending (Not Paid Yet)", "New Premiums 2026", "Renewal Premiums 2026",
        "Approved Policies", "Total Policies", "Total Policies LY", "New Policies",
        "Renewal Policies", "Retail Approved Gross", "Corporate Approved Gross",
        "Motor Premiums 2026", "Non-Motor Premiums 2026",
    ]
    rows[2][2] = "Seller A"
    rows[3][2:21] = ["January", 100, 120, 20, 0.2, 0, 0, 0, 40, 80, 2, 2, 2, 1, 1, 120, 0, 90, 30]
    rows[4][2:21] = ["August", 50, 180, 130, 2.6, 0, 0, 0, 160, 20, 3, 3, 1, 2, 1, 180, 0, 140, 40]
    rows[5][2] = "Seller B"
    rows[6][2:21] = ["August", 100, 250, 150, 1.5, 0, 0, 0, 20, 230, 4, 4, 2, 1, 3, 250, 0, 240, 10]
    rows[7][2:21] = ["Grand Total", 250, 550, 300, 1.2, 0, 0, 0, 220, 330, 9, 9, 5, 4, 5, 550, 0, 470, 80]
    return pd.DataFrame(rows)


def build_flat_seller_fixture():
    rows = [[None] * 21 for _ in range(6)]
    rows[0][2] = "TOP 20 Sellers"
    rows[1][2:21] = [
        "Branch", "Premiums 2025 (Approved)", "Premiums 2026 (Approved)",
        "Gross YoY Change", "Gross YoY Change %", "Pending Operation (Paid)",
        "Pending Finance", "Pending (Not Paid Yet)", "New Premiums 2026",
        "Renewal Premiums 2026", "Approved Policies", "Total Policies",
        "Total Policies LY", "New Policies", "Renewal Policies",
        "Retail Approved Gross", "Corporate Approved Gross", "Motor Premiums 2026",
        "Non-Motor Premiums 2026",
    ]
    rows[2][2:21] = ["Seller A", 100, 300, 200, 2, 0, 0, 0, 120, 180, 3, 3, 1, 2, 1, 300, 0, 250, 50]
    rows[3][2:21] = ["Seller B", 200, 400, 200, 1, 0, 0, 0, 50, 350, 4, 4, 2, 1, 3, 400, 0, 390, 10]
    rows[4][2:21] = ["Grand Total", 300, 700, 400, 4 / 3, 0, 0, 0, 170, 530, 7, 7, 3, 3, 4, 700, 0, 640, 60]
    return pd.DataFrame(rows)


def build_insurer_fixture():
    rows = [[None] * 18 for _ in range(6)]
    rows[0][1] = "2025 vs 2026 By Insurance Company Summary"
    rows[1][2:16] = [
        "Insurance Company", "2025", "2026", "New Premiums 2025",
        "Renewal Premiums 2025", "Other Policies 2025", "New Premiums 2026",
        "Renewal Premuims 2026", "Other Policies 2026", "2025 VS 2026 YOY",
        "Gross YoY Change %", "New Policies 2026", "Renewal Policies 2026",
        "Other Policies 2026",
    ]
    rows[2][2:16] = ["Insurer A", 100, 200, 0, 0, 0, 0, 0, 0, 100, 1, 4, 3, 2]
    rows[3][2:16] = ["Grand Total", 100, 200, 0, 0, 0, 0, 0, 0, 100, 1, 4, 3, 2]
    return pd.DataFrame(rows)


def build_daily_fixture():
    rows = [[None] * 6 for _ in range(12)]
    rows[0][2] = "Branches Per Day last month"
    rows[2][2], rows[2][3] = "Month", "August"
    rows[4][2], rows[4][3] = "Branch", "Premiums 2026 ( Approved )"
    rows[5][2], rows[5][3] = 46236, 51600
    rows[6][2], rows[6][3] = 46238, 100
    rows[7][2], rows[7][3] = "Grand Total", 51700
    return pd.DataFrame(rows)


def build_status_summary_fixture():
    rows = [[None] * 15 for _ in range(21)]
    rows[8][9:15] = ["Month", "Collection", "Endorsement", "New", "Renewal", "Grand Total"]
    rows[13][9:15] = ["April", None, 125850, 1611092, 2730565, 4467507]
    return pd.DataFrame(rows)


def build_this_month_daily_seller_fixture():
    rows = [[None] * 8 for _ in range(16)]
    rows[0][2] = "Branches Per Day this month"
    rows[2][2], rows[2][3] = "Month", "September"
    rows[4][2:8] = [
        "Day of Month", "Seller", "Premiums 2026 ( Approved )",
        "Pending Operation ( Paid )", "Pending ( Not Paid Yet )", "Pending Finance",
    ]
    rows[5][2:8] = [46267, "(blank)", "(10) EGP", None, None, None]
    rows[6][3:8] = ["Seller A", "100 EGP", "20 EGP", None, None]
    rows[7][3:8] = ["Seller B", "50 EGP", None, "30 EGP", None]
    rows[8][2:8] = ["September 02 Total", None, "140 EGP", "20 EGP", "30 EGP", None]
    rows[9][2:8] = [46268, "(blank)", None, None, None, None]
    rows[10][3:8] = ["Seller A", "200 EGP", None, None, None]
    rows[11][3:8] = ["Seller C", "25 EGP", None, None, None]
    rows[12][3:8] = ["Seller D", None, None, None, "40 EGP"]
    rows[13][2:8] = ["September 03 Total", None, "225 EGP", None, None, "40 EGP"]
    rows[15][2:8] = ["Grand Total", None, "365 EGP", "20 EGP", "30 EGP", "40 EGP"]
    return pd.DataFrame(rows)


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

    def test_seller_months_are_aggregated_under_parent(self):
        sellers, total, monthly = extract_sellers(build_seller_fixture())

        self.assertEqual([row["seller"] for row in sellers], ["Seller A", "Seller B"])
        self.assertEqual(sellers[0]["premium_2026"], 300)
        self.assertEqual(
            [row["month"] for row in monthly if row["seller"] == "Seller A"],
            ["January", "August"],
        )
        self.assertEqual(total["premium_2026"], 550)

    def test_flat_seller_rows_keep_their_aggregate_metrics(self):
        sellers, total, monthly = extract_sellers(build_flat_seller_fixture())

        self.assertEqual([row["seller"] for row in sellers], ["Seller A", "Seller B"])
        self.assertEqual([row["premium_2026"] for row in sellers], [300, 400])
        self.assertEqual(total["premium_2026"], 700)
        self.assertEqual(monthly, [])

    def test_insurer_policy_counts_are_mapped_by_header(self):
        rows, total = extract_insurers(build_insurer_fixture())

        self.assertEqual(rows[0]["new_policies_2026"], 4)
        self.assertEqual(rows[0]["renewal_policies_2026"], 3)
        self.assertEqual(rows[0]["other_policies_2026"], 2)
        self.assertEqual(total["other_policies_2026"], 2)

    def test_status_summary_is_not_parsed_as_renewal_policy_data(self):
        self.assertEqual(extract_renewals(build_status_summary_fixture()), [])

    def test_daily_block_uses_august_and_reconciles(self):
        daily = analysis.extract_branches_per_day(build_daily_fixture())

        self.assertEqual(daily["month"], "August")
        self.assertEqual(daily["rows"][0]["date"], "2026-08-02")
        self.assertNotIn("Grand Total", [row["label"] for row in daily["rows"]])
        self.assertEqual(sum(row["premium_2026"] for row in daily["rows"]), daily["total"])

    def test_seller_mvps_use_raw_metric_values_and_august(self):
        sellers, _, monthly = extract_sellers(build_seller_fixture())
        this_month = analysis.extract_branches_per_day_this_month(build_this_month_daily_seller_fixture())
        mvps = analysis.build_seller_mvps(sellers, this_month)

        self.assertEqual(mvps["overall"]["seller"], "Seller A")
        self.assertEqual(mvps["overall"]["value"], 300)
        self.assertEqual(mvps["non_motor"]["metric"], "non_motor_premium")
        self.assertEqual(mvps["non_motor"]["seller"], "Seller A")
        self.assertEqual(mvps["motor"]["seller"], "Seller B")
        self.assertEqual(mvps["this_month"]["seller"], "Seller A")
        self.assertEqual(mvps["this_month"]["value"], 300)
        self.assertEqual(mvps["this_month"]["month"], "September")

    def test_this_month_daily_sellers_aggregate_days_and_exclude_totals(self):
        result = analysis.extract_branches_per_day_this_month(build_this_month_daily_seller_fixture())

        self.assertEqual(result["month"], "September")
        self.assertEqual(
            result["seller_totals"],
            [
                {"seller": "Seller A", "premium_2026": 300.0},
                {"seller": "Seller B", "premium_2026": 50.0},
                {"seller": "Seller C", "premium_2026": 25.0},
            ],
        )
        self.assertEqual([row["seller"] for row in result["rows"]], ["Seller A", "Seller B", "Seller A", "Seller C", "Seller D"])
        self.assertNotIn("(blank)", [row["seller"] for row in result["rows"]])
        self.assertEqual(
            result["rows"][-1],
            {
                "date": "2026-09-03",
                "seller": "Seller D",
                "premium_2026": None,
                "pending_operation_paid": None,
                "pending_not_paid": None,
                "pending_finance": 40.0,
            },
        )
        self.assertEqual(result["total"], 365.0)
        self.assertEqual(
            result["daily_rows"],
            [
                {
                    "date": "2026-09-02",
                    "label": "Sep 2",
                    "premium_2026": 140.0,
                    "pending_operation_paid": 20.0,
                    "pending_not_paid": 30.0,
                    "pending_finance": 0.0,
                },
                {
                    "date": "2026-09-03",
                    "label": "Sep 3",
                    "premium_2026": 225.0,
                    "pending_operation_paid": 0.0,
                    "pending_not_paid": 0.0,
                    "pending_finance": 40.0,
                },
            ],
        )
        self.assertEqual(
            result["totals"],
            {
                "premium_2026": 365.0,
                "pending_operation_paid": 20.0,
                "pending_not_paid": 30.0,
                "pending_finance": 40.0,
            },
        )
        self.assertEqual(result["seller_totals"][0], {"seller": "Seller A", "premium_2026": 300.0})

    def test_this_month_daily_requires_all_measure_headers(self):
        fixture = build_this_month_daily_seller_fixture()
        fixture.iat[4, 5] = None
        fixture.iat[4, 7] = None

        with self.assertRaisesRegex(
            ValueError,
            r"Missing required Branches Per Day this month header\(s\): "
            r"Pending Operation \( Paid \), Pending Finance",
        ):
            analysis.extract_branches_per_day_this_month(fixture)

    def test_this_month_daily_requires_measure_headers_when_header_row_is_missing(self):
        fixture = build_this_month_daily_seller_fixture()
        fixture.iat[4, 2] = None

        with self.assertRaisesRegex(
            ValueError,
            r"Missing required Branches Per Day this month header\(s\): "
            r"Premiums 2026 \( Approved \), Pending Operation \( Paid \), "
            r"Pending \( Not Paid Yet \), Pending Finance",
        ):
            analysis.extract_branches_per_day_this_month(fixture)

    def test_this_month_daily_skips_empty_subtotals_but_keeps_explicit_zero(self):
        fixture = build_this_month_daily_seller_fixture()
        fixture.loc[14, 2] = 46269
        fixture.loc[15, 2:7] = ["September 04 Total", None, None, None, None, None]
        fixture.loc[16, 2] = 46270
        fixture.loc[17, 2:7] = ["September 05 Total", None, "0 EGP", None, None, None]
        fixture.loc[18, 2:7] = ["Grand Total", None, "365 EGP", "20 EGP", "30 EGP", "40 EGP"]

        result = analysis.extract_branches_per_day_this_month(fixture)

        self.assertNotIn("Sep 4", [row["label"] for row in result["daily_rows"]])
        self.assertIn("Sep 5", [row["label"] for row in result["daily_rows"]])


class MonthlySummaryWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overview = pd.read_excel(WORKBOOK, sheet_name="overview", header=None, engine="openpyxl")

    def test_updated_workbook_contains_august_and_reconciled_totals(self):
        amount_rows, amount_total = extract_monthly(self.overview)
        count_rows, count_total = extract_monthly_counts(self.overview)

        self.assertEqual(amount_rows[-1]["month"], "August")
        self.assertEqual(count_rows[-1]["month"], "August")
        self.assertLessEqual(
            abs(sum(r["actual_2026"] for r in amount_rows) - amount_total["actual_2026"]),
            1,
        )
        self.assertEqual(
            sum(r["total_policies_2026"] for r in count_rows),
            count_total["total_policies_2026"],
        )

    def test_updated_workbook_contains_usable_seller_data(self):
        branches = pd.read_excel(WORKBOOK, sheet_name="Branches", header=None, engine="openpyxl")
        sellers, _, monthly = extract_sellers(branches)

        self.assertLessEqual(len(sellers), 20)
        self.assertTrue(all(row["premium_2026"] is not None for row in sellers))
        if monthly:
            self.assertIn("August", {row["month"] for row in monthly})

    def test_latest_daily_approved_and_pending_totals(self):
        branches = pd.read_excel(WORKBOOK, sheet_name="Branches", header=None, engine="openpyxl")
        result = extract_branches_per_day_this_month(branches)

        self.assertEqual(result["month"], "August")
        self.assertEqual(
            result["totals"],
            {
                "premium_2026": 273294.0,
                "pending_operation_paid": 44200.0,
                "pending_not_paid": 94702.0,
                "pending_finance": 111332.0,
            },
        )
        self.assertEqual(len(result["daily_rows"]), 9)
        self.assertEqual(result["daily_rows"][0]["premium_2026"], 51600.0)
        self.assertEqual(result["daily_rows"][-1]["pending_finance"], -32403.0)

    def test_line_of_business_extraction_starts_after_real_header(self):
        rows, total = extract_lob_totals(self.overview)

        self.assertNotIn("Line of Business", [r["line_of_business"] for r in rows])
        self.assertNotIn("Month", [r["line_of_business"] for r in rows])
        self.assertLessEqual(
            abs(sum((r["premium_2026"] or 0) for r in rows) - total["premium_2026"]),
            1,
        )


class DashboardTableTotalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main()
        cls.data = json.loads((DATA_DIR / "report-data.json").read_text(encoding="utf-8"))

    def test_every_entity_table_has_a_serialized_total(self):
        totals = self.data["table_totals"]

        self.assertEqual(set(totals), {"branches", "sellers", "insurers", "lines_of_business"})
        self.assertEqual(totals["branches"]["branch"], "Grand Total")
        self.assertEqual(totals["sellers"]["seller"], "Grand Total")
        self.assertEqual(totals["insurers"]["insurance_company"], "Grand Total")
        self.assertEqual(totals["lines_of_business"]["line_of_business"], "Grand Total")

    def test_entity_total_amounts_reconcile_to_displayed_rows(self):
        cases = (
            ("branches", "branches"),
            ("sellers", "sellers"),
            ("insurers", "insurers"),
            ("lines_of_business", "lines_of_business"),
        )
        for total_key, rows_key in cases:
            with self.subTest(total_key=total_key):
                detail_sum = sum((row.get("premium_2026") or 0) for row in self.data[rows_key])
                total = self.data["table_totals"][total_key]["premium_2026"]
                tolerance = max(2, len(self.data[rows_key]) * 0.5) if total_key == "sellers" else 2
                self.assertLessEqual(abs(total - detail_sum), tolerance)

    def test_seller_contribution_uses_overall_approved_premium(self):
        approved = self.data["totals"]["approved_gross_premium"]
        for seller in self.data["sellers"]:
            with self.subTest(seller=seller["seller"]):
                self.assertAlmostEqual(
                    seller["contribution_pct"],
                    seller["premium_2026"] / approved,
                    places=12,
                )

    def test_seller_total_contribution_uses_overall_approved_premium(self):
        approved = self.data["totals"]["approved_gross_premium"]
        total = self.data["table_totals"]["sellers"]

        self.assertAlmostEqual(
            total["contribution_pct"],
            total["premium_2026"] / approved,
            places=12,
        )

    def test_latest_workbook_policy_counts_are_serialized_and_reconciled(self):
        for insurer in self.data["insurers"]:
            self.assertIn("new_policies_2026", insurer)
            self.assertIn("renewal_policies_2026", insurer)
            self.assertIn("other_policies_2026", insurer)

        for seller in self.data["sellers"]:
            months = [row for row in self.data["seller_monthly"] if row["seller"] == seller["seller"]]
            if months:
                self.assertEqual(seller["new_policies"], sum((row["new_policies"] or 0) for row in months))
                self.assertEqual(seller["renewal_policies"], sum((row["renewal_policies"] or 0) for row in months))

    def test_missing_renewal_table_has_unavailable_data_quality_note(self):
        self.assertEqual(self.data["renewals"], [])
        self.assertIn(
            "Workbook has no dedicated renewal-policy table; renewal-rate analysis is unavailable.",
            self.data["data_quality_notes"],
        )

if __name__ == "__main__":
    unittest.main()
