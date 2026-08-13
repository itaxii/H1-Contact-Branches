import json
import unittest
from decimal import Decimal

from report_metrics import (
    MetricRegistry,
    format_count,
    format_money,
    format_percent,
    ratio,
    yoy_rate,
)
from analysis import DATA_DIR, main, validate_report


def build_valid_validation_data():
    return {
        "totals": {"approved_gross_premium": 100, "pending_total": 30},
        "monthly": [{"actual_2026": 100}],
        "monthly_total": {"actual_2026": 100},
        "monthly_count_summary": [{"total_policies_2026": 10}],
        "monthly_count_total": {"total_policies_2026": 10},
        "branches": [{"premium_2026": 100, "contribution_pct": 1}],
        "lines_of_business": [{"premium_2026": 100, "share_2026_pct": 1}],
        "insurers": [{"premium_2026": 100, "share_2026_pct": 1}],
        "pending_categories": [{"premium": 10}, {"premium": 10}, {"premium": 10}],
        "policy_type_mix": [{"premium": 40}, {"premium": 50}, {"premium": 10}],
        "premium_distribution_bins": [{"count": 1}],
        "branches_per_day_last_month": {
            "month": "August",
            "rows": [{"premium_2026": 100}],
            "total": 100,
        },
        "branches_per_day_this_month": {
            "month": "September",
            "daily_rows": [{
                "premium_2026": 100,
                "pending_operation_paid": 20,
                "pending_not_paid": 30,
                "pending_finance": 40,
            }],
            "totals": {
                "premium_2026": 100,
                "pending_operation_paid": 20,
                "pending_not_paid": 30,
                "pending_finance": 40,
            },
            "total": 100,
        },
        "renewals": [
            {
                "month": "Grand Total",
                "renewed_policies": 6,
                "not_renewed_policies": 4,
                "policies_up_for_renewal": 10,
            }
        ],
    }


class DecimalMetricTests(unittest.TestCase):
    def test_renewal_rate_uses_raw_counts_and_half_up_display(self):
        raw = ratio(64, 163)

        self.assertEqual(raw, Decimal(64) / Decimal(163))
        self.assertEqual(format_percent(raw), "39.3%")

    def test_half_up_rounding_matches_excel(self):
        self.assertEqual(format_percent(Decimal("0.3925")), "39.3%")
        self.assertEqual(format_percent(Decimal("0.3945")), "39.5%")
        self.assertEqual(format_percent(Decimal("-0.545")), "-54.5%")

    def test_motor_average_rate_uses_two_decimals(self):
        self.assertEqual(format_percent(Decimal("0.01945"), decimals=2), "1.95%")

    def test_undefined_denominators_remain_undefined(self):
        self.assertIsNone(ratio(10, 0))
        self.assertIsNone(yoy_rate(10, None))
        self.assertEqual(format_percent(None), "N/A")

    def test_numeric_display_formats(self):
        self.assertEqual(format_money(1_550_000, compact=True), "EGP 1.6M")
        self.assertEqual(format_money(15_500, compact=False), "15,500")
        self.assertEqual(format_count(Decimal("163")), "163")


class MetricRegistryTests(unittest.TestCase):
    def test_registry_keeps_raw_inputs_result_and_expected_display(self):
        registry = MetricRegistry()

        result = registry.register("renewal.june", "June Renewal Rate", 64, 163)
        metric = registry.to_json()["renewal.june"]

        self.assertEqual(result, Decimal(64) / Decimal(163))
        self.assertEqual(metric["numerator"], "64")
        self.assertEqual(metric["denominator"], "163")
        self.assertEqual(metric["display"], "39.3%")

    def test_registry_detects_calculation_mismatch(self):
        registry = MetricRegistry()
        registry.register("target.july", "July Target Achievement", 100, 300)
        registry._metrics["target.july"]["value"] = "0.34"

        failures = registry.validate()

        self.assertEqual(failures[0]["metric_id"], "target.july")
        self.assertEqual(failures[0]["expected_display"], "33.3%")

    def test_rounding_change_compares_source_display_to_raw_display(self):
        registry = MetricRegistry()
        registry.register(
            "kpi.premium_yoy",
            "Approved Gross Premiums YoY",
            16_073_207 - 35_350_000,
            35_350_000,
            source_rate="-0.54",
        )

        changes = registry.rounding_changes()

        self.assertEqual(changes[0]["previous_display"], "-54.0%")
        self.assertEqual(changes[0]["corrected_display"], "-54.5%")


class GeneratedMetricCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main()
        cls.data = json.loads((DATA_DIR / "report-data.json").read_text(encoding="utf-8"))

    def test_catalog_contains_raw_inputs_and_reusable_aggregates(self):
        catalog = self.data["calculated_metrics"]

        self.assertIn("totals.new_premium_mix", catalog)
        self.assertIn("insurers.top3_share", catalog)
        self.assertIn("seller_monthly", self.data)
        self.assertIn("renewals", self.data)
        self.assertEqual(
            self.data["totals"]["new_premium_mix_pct"],
            catalog["totals.new_premium_mix"]["value_numeric"],
        )

    def test_motor_average_rate_catalog_uses_two_decimals(self):
        metric = self.data["calculated_metrics"]["monthly-count.January.motor_average_rate_2026"]

        self.assertEqual(metric["decimals"], 2)


class ReportValidationTests(unittest.TestCase):
    def test_percentage_mismatch_is_blocking(self):
        registry = MetricRegistry()
        registry.register("renewal.total.rate", "Overall Renewal Rate", 64, 163)
        registry._metrics["renewal.total.rate"]["display"] = "39.5%"

        result = validate_report(build_valid_validation_data(), registry)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocking_failures"][0]["metric_id"], "renewal.total.rate")

    def test_small_source_reconciliation_difference_is_warning(self):
        data = build_valid_validation_data()
        data["insurers"][0]["premium_2026"] += 2

        result = validate_report(data, MetricRegistry())

        self.assertEqual(result["status"], "warning")
        warning = next(item for item in result["warnings"] if item["name"] == "Insurer totals = overall total")
        self.assertEqual(warning["difference"], 2)

    def test_internal_renewal_mismatch_is_blocking(self):
        data = build_valid_validation_data()
        data["renewals"][0]["not_renewed_policies"] = 3

        result = validate_report(data, MetricRegistry())

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("Renewal counts reconcile" in item["name"] for item in result["blocking_failures"]))

    def test_daily_reconciliation_uses_this_month_day_totals(self):
        data = build_valid_validation_data()
        data["branches_per_day_this_month"]["daily_rows"][0]["premium_2026"] = 90

        result = validate_report(data, MetricRegistry())

        warning = next(item for item in result["warnings"] if item["name"] == "Branches per day approved total")
        self.assertEqual(warning["expected"], 100)
        self.assertEqual(warning["actual"], 90)

    def test_daily_measures_reconcile_independently(self):
        cases = {
            "premium_2026": "Branches per day approved total",
            "pending_operation_paid": "Branches per day pending operation paid total",
            "pending_not_paid": "Branches per day pending not paid total",
            "pending_finance": "Branches per day pending finance total",
        }

        for key, check_name in cases.items():
            with self.subTest(key=key):
                data = build_valid_validation_data()
                data["branches_per_day_this_month"]["daily_rows"][0][key] -= 1

                result = validate_report(data, MetricRegistry())

                warning = next(item for item in result["checks"] if item["name"] == check_name)
                self.assertEqual(warning["expected"], data["branches_per_day_this_month"]["totals"][key])
                self.assertEqual(warning["actual"], data["branches_per_day_this_month"]["totals"][key] - 1)
                self.assertEqual(warning["difference"], -1)
                self.assertEqual(warning["severity"], "warning")
                self.assertEqual(warning["tolerance"], 1)
                self.assertEqual(warning["source"], "workbook")


if __name__ == "__main__":
    unittest.main()
