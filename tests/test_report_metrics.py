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


if __name__ == "__main__":
    unittest.main()
