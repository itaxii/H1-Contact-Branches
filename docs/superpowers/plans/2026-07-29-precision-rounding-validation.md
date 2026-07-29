# Precision, Rounding, and Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recalculate every derived report percentage from raw workbook values, apply Excel-compatible display rounding once, validate every displayed percentage, and block PDF replacement when calculation or rendering validation fails.

**Architecture:** Add a focused Python `report_metrics.py` module that owns Decimal-based formulas, formatting, metric registration, and percentage validation. `analysis.py` will extract raw amounts/counts and register canonical metrics, while `app.js` will only render those canonical numeric results using a matching half-up formatter. `generate-pdf.js` will run data generation first, validate the rendered metric catalog, wait for chart completion, and atomically replace the canonical PDF only after all checks pass.

**Tech Stack:** Python 3, pandas/openpyxl, `decimal.Decimal`, JavaScript, Chart.js, Node.js, Playwright Core, Python `unittest`.

## Global Constraints

- Do not modify the source Excel workbook or business logic.
- Do not change report structure, charts, tables, KPI cards, text meaning, colors, or typography.
- Calculate derived metrics only from original raw amounts and counts.
- Keep all intermediate calculations unrounded and round once at final display.
- Use Excel-compatible `ROUND_HALF_UP` behavior.
- Display percentages with one decimal place, except Motor Average Rate with two decimal places.
- Display detailed currency as full values with thousand separators.
- Display chart and KPI currency in K/M notation with one decimal place.
- Display counts as whole numbers without decimals.
- Preserve undefined YoY values as `N/A`; do not turn New Base or No Current Production into ordinary growth percentages.
- Do not force rounded values or workbook source totals to reconcile.
- Block PDF replacement on canonical calculation or rendered percentage mismatch.

## File Structure

- Create `report_metrics.py`: Decimal conversion, raw formulas, Excel-style formatters, canonical metric registry, metric validation, and rounding-change records.
- Create `tests/test_report_metrics.py`: unit and regression coverage for formulas, rounding, undefined denominators, registry behavior, and validation failures.
- Modify `analysis.py`: replace workbook percentage inputs with raw formulas, register canonical metrics, reuse them in narratives, classify validation severity, and write audit artifacts.
- Modify `app.js`: replace `toFixed`/`Math.round` display paths, consume canonical aggregate percentages, expose browser validation, and signal chart completion.
- Create `tests/verify-rounding.js`: browser-side formatter and rendered-metric parity checks against generated data.
- Modify `generate-pdf.js`: run analysis, enforce validation gates, wait for charts, validate browser output, and write PDF atomically.
- Modify `package.json`: add repeatable data, validation, and full test commands used by PDF generation.
- Modify `tests/verify-pdf.py`: retain completeness checks and assert the corrected renewal display is present.
- Generate `data/rounding-changes.json`: before/after displayed-value audit.
- Regenerate `data/report-data.json`, `data/report-data.js`, `data/validation-summary.json`, and `contact-branches-report.pdf`.

---

### Task 1: Decimal Formula and Formatting Core

**Files:**
- Create: `report_metrics.py`
- Create: `tests/test_report_metrics.py`

**Interfaces:**
- Produces: `to_decimal(value) -> Decimal | None`
- Produces: `ratio(numerator, denominator) -> Decimal | None`
- Produces: `yoy_rate(current, previous) -> Decimal | None`
- Produces: `format_percent(value, decimals=1) -> str`
- Produces: `format_money(value, compact=False) -> str`
- Produces: `format_count(value) -> str`
- Produces: `MetricRegistry.register(metric_id, label, numerator, denominator, decimals=1, source_rate=None) -> Decimal | None`
- Produces: `MetricRegistry.to_json() -> dict[str, dict]`
- Produces: `MetricRegistry.validate() -> list[dict]`
- Produces: `MetricRegistry.rounding_changes() -> list[dict]`

- [ ] **Step 1: Write failing formula and rounding tests**

```python
from decimal import Decimal
import unittest

from report_metrics import format_count, format_money, format_percent, ratio, yoy_rate


class DecimalMetricTests(unittest.TestCase):
    def test_renewal_rate_uses_raw_counts_and_half_up_display(self):
        raw = ratio(64, 163)
        self.assertEqual(raw, Decimal(64) / Decimal(163))
        self.assertEqual(format_percent(raw), "39.3%")

    def test_half_up_rounding_matches_excel(self):
        self.assertEqual(format_percent(Decimal("0.3925")), "39.3%")
        self.assertEqual(format_percent(Decimal("0.3945")), "39.5%")

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
```

- [ ] **Step 2: Run the tests and verify the module is missing**

Run: `python -m unittest tests.test_report_metrics.DecimalMetricTests -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'report_metrics'`.

- [ ] **Step 3: Implement Decimal conversion, formulas, and formatters**

```python
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def to_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def ratio(numerator, denominator):
    numerator = to_decimal(numerator)
    denominator = to_decimal(denominator)
    if numerator is None or denominator in (None, Decimal("0")):
        return None
    return numerator / denominator


def yoy_rate(current, previous):
    current = to_decimal(current)
    previous = to_decimal(previous)
    if current is None or previous in (None, Decimal("0")):
        return None
    return (current - previous) / previous


def quantize_half_up(value, decimals):
    value = to_decimal(value)
    if value is None:
        return None
    quantum = Decimal("1").scaleb(-decimals)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)
```

Implement `format_percent`, `format_money`, and `format_count` using `quantize_half_up`; keep compact currency at exactly one decimal and detailed currency at zero decimals with separators.

- [ ] **Step 4: Write failing canonical registry tests**

```python
from report_metrics import MetricRegistry


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
        registry.register("kpi.premium_yoy", "Approved Gross Premiums YoY", 16_073_207 - 35_350_000, 35_350_000, source_rate="-0.54")
        changes = registry.rounding_changes()
        self.assertEqual(changes[0]["previous_display"], "-54.0%")
        self.assertEqual(changes[0]["corrected_display"], "-54.5%")
```

- [ ] **Step 5: Implement `MetricRegistry`**

Store Decimal values internally as decimal strings in `to_json()` so validation is deterministic. Include `value_numeric` as a JSON-safe float for charts, `display`, `decimals`, and optional `source_display`. Independently recalculate every registered metric in `validate()` rather than trusting the stored result.

- [ ] **Step 6: Run the focused tests**

Run: `python -m unittest tests.test_report_metrics -v`

Expected: all Task 1 tests PASS.

- [ ] **Step 7: Commit the metric core**

```powershell
git add report_metrics.py tests/test_report_metrics.py
git commit -m "feat: add decimal metric and formatting core"
```

---

### Task 2: Raw Workbook Calculations and Canonical Metric Catalog

**Files:**
- Modify: `analysis.py:1-919`
- Modify: `tests/test_monthly_summaries.py`
- Modify: `tests/test_report_metrics.py`

**Interfaces:**
- Consumes: `MetricRegistry`, `ratio`, `yoy_rate`, and display formatters from Task 1.
- Produces: `build_metric_catalog(data, source_rates) -> MetricRegistry`
- Produces: `data["calculated_metrics"]` keyed by stable metric IDs.
- Produces: raw-derived rate fields at their existing paths, preserving the current JSON contract for `app.js`.

- [ ] **Step 1: Add failing extraction regressions for raw percentages**

Extend the monthly fixture so its stored target percentage is deliberately wrong, then assert extraction ignores it:

```python
def build_kpi_fixture(previous, current, source_rate):
    rows = [[None] * 7 for _ in range(20)]
    rows[12][2] = "Approved Gross Premiums"
    rows[12][3] = previous
    rows[12][4] = current
    rows[12][5] = current - previous
    rows[12][6] = source_rate
    return pd.DataFrame(rows)


def build_entity_row(previous, current):
    values = ["Sample Branch", previous, current, 999, 0.99]
    values.extend([0] * 14)
    return pd.Series(values)


def test_amount_summary_recalculates_target_achievement_from_raw_values(self):
    fixture = build_amount_fixture()
    fixture.iat[2, 12] = 0.99
    rows, _ = extract_monthly(fixture)
    self.assertAlmostEqual(rows[0]["target_achievement_pct"], 370 / 406.25)

def test_kpi_yoy_recalculates_from_raw_values(self):
    fixture = build_kpi_fixture(previous=200, current=91, source_rate=-0.54)
    result = extract_kpis(fixture)["Approved Gross Premiums"]
    self.assertAlmostEqual(result["change_pct"], (91 - 200) / 200)

def test_entity_missing_prior_year_keeps_yoy_undefined(self):
    record = row_to_record(build_entity_row(previous=None, current=100), list(range(19)), "branch")
    self.assertIsNone(record["yoy_change_pct"])
    self.assertEqual(record["growth_class"], "New Base")
```

- [ ] **Step 2: Run the extraction regressions and confirm they fail**

Run: `python -m unittest tests.test_monthly_summaries -v`

Expected: target/KPI tests FAIL because current code reads workbook percentage cells.

- [ ] **Step 3: Recalculate all extractable percentages from raw fields**

Modify these extraction paths:

- `extract_kpis`: calculate `change = value_2026 - value_2025` and `change_pct = yoy_rate(value_2026, value_2025)`; retain workbook values under `source_change` and `source_change_pct` only for the audit.
- `row_to_record`: calculate entity `yoy_change` and `yoy_change_pct` from `premium_2025` and `premium_2026`.
- `extract_monthly`: calculate `target_achievement_pct` from `actual_2026 / target_2026` and `yoy_pct` from raw actuals for every month and Grand Total.
- `extract_insurers`: calculate YoY amount and rate from raw premiums.
- `extract_lob_totals`: calculate target achievement and YoY from raw premiums/target.
- `extract_renewals`: retain raw `renewed_policies` and `policies_up_for_renewal`, derive `not_renewed_policies` and rate.
- Contribution, mix, pending share, and insurer/LOB shares: calculate once in Python from raw values.

Convert Decimal rates to JSON-safe unrounded floats only when assigning existing rate fields; preserve the exact decimal string in the metric catalog.

- [ ] **Step 4: Add failing catalog coverage and canonical aggregate assertions**

```python
import json

from analysis import DATA_DIR, main


def test_catalog_contains_raw_inputs_and_reusable_aggregates(self):
    main()
    data = json.loads((DATA_DIR / "report-data.json").read_text(encoding="utf-8"))
    catalog = data["calculated_metrics"]
    self.assertEqual(catalog["renewal.June.rate"]["display"], "39.3%")
    self.assertIn("totals.new_premium_mix", catalog)
    self.assertIn("insurers.top3_share", catalog)
    self.assertEqual(data["totals"]["new_premium_mix_pct"], catalog["totals.new_premium_mix"]["value_numeric"])
```

- [ ] **Step 5: Implement `build_metric_catalog` and stable IDs**

Register metrics using these ID families:

- `kpi.<normalized-name>.yoy`
- `monthly.<month>.target_achievement` and `monthly.<month>.yoy`
- `branch.<normalized-name>.yoy`, `.contribution`, `.renewal_mix`, `.motor_mix`
- `seller.<normalized-name>.*`
- `insurer.<normalized-name>.yoy` and `.share`
- `lob.<normalized-name>.target_achievement`, `.yoy`, and `.share`
- `renewal.<month>.rate`
- `totals.target_achievement`, `.pending_share`, `.new_premium_mix`, `.renewal_premium_mix`, and `.other_policy_type_mix`
- `insurers.top3_share`

Add canonical aggregate fields to `data["totals"]` and `data["summary_metrics"]` so `app.js` does not divide amounts itself.

- [ ] **Step 6: Replace Python narrative formatting with shared formatters**

Update `build_insights` and `build_recommendations` to call `format_percent`, `format_money`, and `format_count` on canonical values. Remove `.1%`, `.1f`, and `.0f` numeric display formatting from those functions.

- [ ] **Step 7: Run Python extraction and metric tests**

Run: `python -m unittest tests.test_monthly_summaries tests.test_report_metrics -v`

Expected: all tests PASS, including `64 / 163 -> 39.3%` and undefined YoY behavior.

- [ ] **Step 8: Commit raw calculation integration**

```powershell
git add analysis.py tests/test_monthly_summaries.py tests/test_report_metrics.py
git commit -m "fix: derive report percentages from raw values"
```

---

### Task 3: Browser Formatter Parity and Canonical Metric Reuse

**Files:**
- Modify: `app.js:46-970`
- Create: `tests/verify-rounding.js`
- Modify: `package.json`

**Interfaces:**
- Consumes: `data.calculated_metrics`, `data.totals.*_pct`, and `data.summary_metrics` from Task 2.
- Produces: `window.dashboardFormatting.formatPercent(value, decimals) -> str`
- Produces: `window.validateDashboardMetrics() -> {status, checked, failures}`
- Produces: `window.dashboardChartsReady === true` after all charts complete a no-animation update.

- [ ] **Step 1: Write a failing browser verification script**

```javascript
const assert = require("assert");
const path = require("path");
const { chromium } = require("playwright-core");

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH, headless: true });
  const page = await browser.newPage();
  await page.addInitScript(() => sessionStorage.setItem("contactReportAuthed", "true"));
  await page.goto(`file://${path.join(__dirname, "..", "index.html").replace(/\\/g, "/")}`);
  await page.waitForFunction(() => window.dashboardFormatting);
  assert.equal(await page.evaluate(() => window.dashboardFormatting.formatPercent(64 / 163, 1)), "39.3%");
  assert.equal(await page.evaluate(() => window.dashboardFormatting.formatPercent(0.01945, 2)), "1.95%");
  const result = await page.evaluate(() => window.validateDashboardMetrics());
  assert.equal(result.status, "pass", JSON.stringify(result.failures, null, 2));
  await browser.close();
})().catch((error) => { console.error(error); process.exit(1); });
```

Resolve Chrome/Edge with the same candidate logic as `generate-pdf.js` rather than requiring manual environment configuration in the final version.

- [ ] **Step 2: Run the browser verification and confirm it fails**

Run: `node tests/verify-rounding.js`

Expected: FAIL because `window.dashboardFormatting` and `window.validateDashboardMetrics` do not exist.

- [ ] **Step 3: Implement half-up browser formatting**

Replace `toFixed(1)` and display-facing `Math.round` calls in `fmtPct`, `fmtMoney`, and `fmtNumber`. Implement a formatter factory using `Intl.NumberFormat("en-US", { minimumFractionDigits, maximumFractionDigits, roundingMode: "halfExpand" })` and a tested half-up fallback.

Expose:

```javascript
window.dashboardFormatting = {
  formatPercent: fmtPct,
  formatMoney: fmtMoney,
  formatNumber: fmtNumber,
};
```

Pass `2` to `fmtPct` only for `motor_average_rate_2025` and `motor_average_rate_2026` table columns. Keep every other percentage at one decimal.

- [ ] **Step 4: Remove duplicate percentage calculations from rendering**

Replace these browser calculations with canonical fields:

- New Premium KPI share -> `data.totals.new_premium_mix_pct`
- Renewal Premium KPI share -> `data.totals.renewal_premium_mix_pct`
- Top-three insurer share -> `data.summary_metrics.top3_insurer_share_pct`
- Any narrative/card/chart percentage currently derived from formatted or display values -> its existing raw canonical rate field

Do not change chart datasets, chart types, labels, colors, or layout.

- [ ] **Step 5: Add browser metric validation and chart-ready signal**

Implement `window.validateDashboardMetrics()` to iterate `data.calculated_metrics`, independently divide decimal-string numerator by denominator, apply browser half-up formatting with each metric's `decimals`, and compare with the metric's expected `display`. Return every failure with metric ID, expected display, actual display, numerator, and denominator.

Set `window.dashboardChartsReady = true` only after `init()` has created all charts and `prepareForPrint()` has disabled animation, resized each chart, and completed `chart.update("none")`.

- [ ] **Step 6: Add repeatable package scripts**

```json
{
  "scripts": {
    "data": "python analysis.py",
    "test:python": "python -m unittest discover -s tests -p \"test_*.py\" -v",
    "test:browser": "node tests/verify-section3.js && node tests/verify-rounding.js",
    "test": "npm run test:python && npm run test:browser",
    "pdf": "node generate-pdf.js"
  }
}
```

- [ ] **Step 7: Run browser and syntax verification**

Run: `node --check app.js`

Run: `node tests/verify-rounding.js`

Run: `node tests/verify-section3.js`

Expected: all commands PASS.

- [ ] **Step 8: Commit browser parity**

```powershell
git add app.js tests/verify-rounding.js package.json package-lock.json
git commit -m "fix: align dashboard display rounding with Excel"
```

---

### Task 4: Blocking Validation and Reconciliation Audit

**Files:**
- Modify: `analysis.py:666-919`
- Modify: `report_metrics.py`
- Modify: `tests/test_report_metrics.py`
- Generate: `data/validation-summary.json`
- Generate: `data/rounding-changes.json`

**Interfaces:**
- Consumes: `MetricRegistry.validate()` and `MetricRegistry.rounding_changes()`.
- Produces: `validate_report(data, registry) -> {status, blocking_failures, warnings, checks, percentage_checks}`.
- Produces: process exit code 1 for blocking calculation failures.

- [ ] **Step 1: Write failing validation-severity tests**

```python
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
        "pending_categories": [
            {"premium": 10}, {"premium": 10}, {"premium": 10}
        ],
        "policy_type_mix": [
            {"premium": 40}, {"premium": 50}, {"premium": 10}
        ],
        "premium_distribution_bins": [{"count": 1}],
        "renewals": [{
            "month": "Grand Total",
            "renewed_policies": 6,
            "not_renewed_policies": 4,
            "policies_up_for_renewal": 10,
        }],
    }


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
    self.assertEqual(result["warnings"][0]["difference"], 2)
```

- [ ] **Step 2: Run validation tests and confirm failure**

Run: `python -m unittest tests.test_report_metrics -v`

Expected: FAIL because `validate_report` has no registry argument or severity split.

- [ ] **Step 3: Implement blocking versus source-warning validation**

Keep exact count and calculation mismatches blocking. Mark workbook cross-summary differences within the existing EGP tolerance as pass and differences just outside tolerance as explicit source warnings. Include `name`, `expected`, `actual`, `difference`, `tolerance`, `severity`, and `source` on every reconciliation result.

Percentage catalog failures are always blocking. Do not write refreshed report data or replace the PDF when they exist; write the validation summary first so the failure remains reviewable.

- [ ] **Step 4: Add raw share and component reconciliations**

Validate:

- monthly amount rows against workbook Grand Total and overall approved premium
- monthly count rows against workbook Grand Total
- branch, LOB, and insurer totals against overall approved premium
- pending categories against total pending
- renewal counts for each month and Grand Total
- policy-type mix against approved gross premium
- raw branch, LOB, insurer, policy-type, and pending shares against their denominators

Use raw Decimal values and never sum formatted percentages.

- [ ] **Step 5: Write audit artifacts**

Write `data/validation-summary.json` with blocking failures and warnings. Write `data/rounding-changes.json` from `registry.rounding_changes()`, sorted by report area then metric label, with:

```json
{
  "metric_id": "kpi.approved-gross-premiums.yoy",
  "label": "Approved Gross Premiums YoY",
  "previous_display": "-54.0%",
  "corrected_display": "-54.5%",
  "numerator": "-19276793",
  "denominator": "35350000"
}
```

- [ ] **Step 6: Run analysis and inspect audit output**

Run: `python analysis.py`

Expected: exit 0; percentage checks pass; known small source differences appear as warnings; June `64 / 163` is cataloged as `39.3%`; Motor Average Rate catalog entries use two decimals.

- [ ] **Step 7: Run all Python tests**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

Expected: all tests PASS.

- [ ] **Step 8: Commit validation and audit output**

```powershell
git add analysis.py report_metrics.py tests/test_report_metrics.py data/report-data.json data/report-data.js data/validation-summary.json data/rounding-changes.json
git commit -m "feat: block invalid percentages and log rounding changes"
```

---

### Task 5: Atomic PDF Validation Gate

**Files:**
- Modify: `generate-pdf.js:1-75`
- Modify: `tests/verify-pdf.py`
- Modify: `.gitignore` only if a temporary PDF pattern is not already ignored
- Regenerate: `contact-branches-report.pdf`

**Interfaces:**
- Consumes: `python analysis.py`, `window.dashboardChartsReady`, and `window.validateDashboardMetrics()`.
- Produces: canonical `contact-branches-report.pdf` only after all validations pass.

- [ ] **Step 1: Add a failing PDF content regression**

Extend `tests/verify-pdf.py`:

```python
from pypdf import PdfReader

text = "\n".join(page.extract_text() or "" for page in PdfReader(PDF).pages)
assert "39.3%" in text, "Corrected renewal rate is missing from PDF"
assert "39.5%" not in text, "Stale renewal rate remains in PDF"
```

- [ ] **Step 2: Run the PDF test against the current artifact**

Run: `python tests/verify-pdf.py`

Expected: FAIL if the stale renewal display remains, establishing the regression.

- [ ] **Step 3: Run analysis as a required PDF preflight**

Use `child_process.spawnSync` before launching Chromium:

```javascript
const analysis = spawnSync("python", ["analysis.py"], { cwd: root, stdio: "inherit" });
if (analysis.status !== 0) process.exit(analysis.status || 1);
```

Read `data/validation-summary.json` and abort when `status === "blocked"`.

- [ ] **Step 4: Validate the rendered dashboard before printing**

After page load and `prepareDashboardForPrint()`, wait for:

```javascript
await page.waitForFunction(() => window.dashboardChartsReady === true);
const renderedValidation = await page.evaluate(() => window.validateDashboardMetrics());
if (renderedValidation.status !== "pass") {
  throw new Error(`Rendered percentage validation failed: ${JSON.stringify(renderedValidation.failures)}`);
}
```

Retain the existing font and nonzero-canvas checks.

- [ ] **Step 5: Write PDF to a temporary path and replace atomically**

Generate `contact-branches-report.tmp.pdf`, run the PDF completeness test against that path through an optional `PDF_PATH` environment variable, then rename it to `contact-branches-report.pdf`. On failure, delete only the temporary file and leave the last valid canonical PDF intact.

- [ ] **Step 6: Generate and verify the corrected PDF**

Run: `npm run pdf`

Run: `python tests/verify-pdf.py`

Expected: PDF generation succeeds; the PDF remains complete; all Sections 1-11 are present; `39.3%` appears and stale `39.5%` does not.

- [ ] **Step 7: Commit the gated PDF pipeline and artifact**

```powershell
git add generate-pdf.js tests/verify-pdf.py .gitignore contact-branches-report.pdf data/report-data.json data/report-data.js data/validation-summary.json data/rounding-changes.json
git commit -m "feat: gate PDF generation on metric validation"
```

---

### Task 6: Full Regression Verification and Delivery Audit

**Files:**
- Verify: all modified files and generated artifacts
- Modify: `README.md` only to document the validated generation commands and audit files

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: a reproducible final verification record and user-facing list of changed displayed metrics.

- [ ] **Step 1: Document the validated generation workflow**

Add to `README.md`:

```markdown
## Validated report generation

Run `npm test` to validate extraction, formulas, display rounding, and browser rendering.
Run `npm run pdf` to regenerate data, enforce all blocking checks, wait for chart rendering, and atomically replace the PDF.

Review `data/validation-summary.json` for reconciliation results and `data/rounding-changes.json` for corrected displayed percentages after each workbook update.
```

- [ ] **Step 2: Run the complete automated suite**

Run: `npm test`

Run: `npm run pdf`

Run: `python tests/verify-pdf.py`

Run: `git diff --check`

Expected: every command exits 0 and no whitespace errors are reported.

- [ ] **Step 3: Confirm no forbidden calculation paths remain**

Run:

```powershell
Select-String -Path analysis.py,app.js -Pattern '\.1%|\.1f|toFixed\(|change_pct.: parse_percent|target_achievement_pct.: parse_percent|premium_2026\s*\/\s*data\.totals'
```

Expected: no derived-percentage display or recalculation matches remain. Any remaining `parse_percent` is limited to Motor Average Rate source values, which have no numerator/denominator in the workbook and are display-only at two decimals.

- [ ] **Step 4: Review the generated rounding-change list**

Run:

```powershell
$changes = Get-Content -Raw data\rounding-changes.json | ConvertFrom-Json
$changes | Format-Table label,previous_display,corrected_display -AutoSize
```

Expected: every changed value has a metric label and before/after display; undefined prior-period YoY values do not appear as `0.0%`.

- [ ] **Step 5: Review reconciliation and data-quality results**

Run:

```powershell
$validation = Get-Content -Raw data\validation-summary.json | ConvertFrom-Json
$validation.status
$validation.blocking_failures | Format-Table -AutoSize
$validation.warnings | Format-Table name,expected,actual,difference -AutoSize
```

Expected: no blocking failures; known source-level EGP differences remain explicit warnings.

- [ ] **Step 6: Commit workflow documentation**

```powershell
git add README.md
git commit -m "docs: document validated report generation"
```

- [ ] **Step 7: Prepare the delivery summary**

Report:

- files changed
- generated PDF location and page completeness
- full validation/reconciliation status
- remaining Excel data-quality warnings
- every entry from `data/rounding-changes.json`
- explicit confirmation that no calculation uses previously rounded values
