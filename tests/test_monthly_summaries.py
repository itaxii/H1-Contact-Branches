import unittest

import pandas as pd

from analysis import extract_monthly, extract_monthly_counts


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


if __name__ == "__main__":
    unittest.main()
