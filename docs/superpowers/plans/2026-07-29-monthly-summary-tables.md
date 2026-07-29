# Monthly Summary Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Section 3 display every field from the workbook's premium amount summary and add a matching full-field premium count table.

**Architecture:** `analysis.py` will locate each workbook summary by title, normalize its headers into stable JSON keys, and retain both month rows and the grand-total row. `app.js` will render the existing amount charts from the shared amount records and render two wide tables from those extracted datasets; `index.html` only adds the second table container.

**Tech Stack:** Python 3, pandas/openpyxl, static HTML/CSS, vanilla JavaScript, Chart.js, Playwright Core, Python `unittest`.

## Global Constraints

- Use `C:\Users\mOHAMED.tOLBA\Downloads\branches 29-7\Contact Branches.xlsx` as the updated source workbook.
- Preserve the current dashboard structure, charts, KPI cards, colors, and calculations outside the updated workbook fields.
- Include all workbook columns from both monthly summaries.
- Include `Grand Total` as the final row in both tables.
- Keep future month additions dynamic and calendar ordered.

---

### Task 1: Header-Driven Workbook Extraction

**Files:**
- Create: `tests/test_monthly_summaries.py`
- Modify: `analysis.py:305`

**Interfaces:**
- Produces: `extract_monthly(df) -> tuple[list[dict], dict]`
- Produces: `extract_monthly_counts(df) -> tuple[list[dict], dict]`
- Amount records expose `month`, `new_premium_2025`, `renewal_premium_2025`, `other_premium_2025`, `new_premium`, `renewal_premium`, `endorsement_premium`, `actual_2025`, `actual_2026`, `target_2026`, `target_achievement_pct`, `yoy_change`, `yoy_pct`, `motor_premium`, `non_motor_premium`, `motor_premium_2025`, `non_motor_premium_2025`, and `pending_finance`.
- Count records expose `month`, `new_policies_2025`, `renewal_policies_2025`, `other_policies_2025`, `new_policies_2026`, `renewal_policies_2026`, `other_policies_2026`, `total_policies_2025`, `total_policies_2026`, `yoy_change`, `motor_policies_2026`, `non_motor_policies_2026`, `motor_policies_2025`, `non_motor_policies_2025`, `motor_average_rate_2026`, and `motor_average_rate_2025`.

- [ ] **Step 1: Write failing extraction tests**

```python
import unittest
import pandas as pd
from analysis import extract_monthly, extract_monthly_counts


class MonthlySummaryExtractionTests(unittest.TestCase):
    def test_amount_summary_maps_every_new_header(self):
        df = build_amount_fixture()
        rows, total = extract_monthly(df)
        self.assertEqual(rows[0]["new_premium_2025"], 100.0)
        self.assertEqual(rows[0]["other_premium_2025"], 25.0)
        self.assertEqual(rows[0]["motor_premium_2025"], 90.0)
        self.assertEqual(total["month"], "Grand Total")

    def test_count_summary_maps_counts_and_rates(self):
        df = build_count_fixture()
        rows, total = extract_monthly_counts(df)
        self.assertEqual(rows[0]["new_policies_2026"], 12.0)
        self.assertEqual(rows[0]["non_motor_policies_2025"], 40.0)
        self.assertAlmostEqual(rows[0]["motor_average_rate_2026"], 0.019)
        self.assertEqual(total["month"], "Grand Total")
```

- [ ] **Step 2: Run tests and verify the missing count extractor and new amount keys fail**

Run: `python -m unittest tests.test_monthly_summaries -v`

Expected: FAIL because `extract_monthly_counts` and the new amount fields do not exist.

- [ ] **Step 3: Implement title/header-based extraction**

Add a normalized-header lookup that identifies the header row after each section title and maps workbook labels to the stable keys above. Parse amount/count fields with `parse_number`, percentage fields with `parse_percent`, preserve raw YoY amount/count difference, and derive `yoy_pct` only from raw 2025 and 2026 amount totals.

- [ ] **Step 4: Run extraction tests**

Run: `python -m unittest tests.test_monthly_summaries -v`

Expected: both tests PASS.

- [ ] **Step 5: Commit extraction changes**

```powershell
git add -- analysis.py tests/test_monthly_summaries.py
git commit -m "feat: extract monthly amount and count summaries"
```

### Task 2: Regenerate Source-Backed Dashboard Data

**Files:**
- Modify: `E:\Daily v3\Reports\Branch Report.xlsx`
- Modify: `analysis.py:719`
- Modify: `data/report-data.json`
- Modify: `data/report-data.js`
- Modify: `data/validation-summary.json`
- Test: `tests/test_monthly_summaries.py`

**Interfaces:**
- Adds: `report["monthly_count_summary"]: list[dict]`
- Keeps: `report["monthly"]: list[dict]` for month-only chart input.
- Adds: `report["monthly_total"]` and `report["monthly_count_total"]` for table grand totals and reconciliation.

- [ ] **Step 1: Add a failing real-workbook contract test**

```python
def test_updated_workbook_contains_july_and_reconciled_totals(self):
    amount_rows, amount_total = extract_monthly(self.overview)
    count_rows, count_total = extract_monthly_counts(self.overview)
    self.assertEqual(amount_rows[-1]["month"], "July")
    self.assertEqual(count_rows[-1]["month"], "July")
    self.assertEqual(sum(r["actual_2026"] for r in amount_rows), amount_total["actual_2026"])
    self.assertEqual(sum(r["total_policies_2026"] for r in count_rows), count_total["total_policies_2026"])
```

- [ ] **Step 2: Run the test against the old canonical workbook**

Run: `python -m unittest tests.test_monthly_summaries.MonthlySummaryWorkbookTests -v`

Expected: FAIL because the canonical workbook does not yet match the supplied workbook contract.

- [ ] **Step 3: Replace the canonical workbook with the supplied workbook and wire count data into `main()`**

Use a verified copy from the supplied path to `E:\Daily v3\Reports\Branch Report.xlsx`, then add count extraction, grand totals, and additive-field reconciliation checks. Validation messages must report expected, actual, and difference when a summary does not reconcile.

- [ ] **Step 4: Regenerate data and run tests**

Run: `python analysis.py`

Run: `python -m unittest discover -s tests -v`

Expected: generation exits 0 and all tests PASS.

- [ ] **Step 5: Commit generated data and workbook extractor wiring**

```powershell
git add -- analysis.py data/report-data.json data/report-data.js data/validation-summary.json tests/test_monthly_summaries.py
git commit -m "data: refresh contact branches through July"
```

### Task 3: Render Both Full-Field Section 3 Tables

**Files:**
- Create: `tests/verify-section3.js`
- Modify: `index.html:100`
- Modify: `app.js:351`
- Modify: `styles.css`

**Interfaces:**
- Adds DOM table: `#monthlyCountTable`
- Reuses existing `renderTable`, `moneyCol`, and `pctCol` helpers.
- Adds a whole-number count formatter for policy-count columns.

- [ ] **Step 1: Write a failing browser verification**

```javascript
const assert = require("node:assert/strict");
assert.equal(await page.locator("#monthlyTable thead th").count(), 17);
assert.equal(await page.locator("#monthlyCountTable thead th").count(), 16);
assert.match(await page.locator("#monthlyTable").innerText(), /Grand Total/);
assert.match(await page.locator("#monthlyCountTable").innerText(), /Motor Average Rate 2026/);
```

- [ ] **Step 2: Run the browser test and verify it fails**

Run: `node tests/verify-section3.js`

Expected: FAIL because `#monthlyCountTable` is absent and the existing amount table has only eight headers.

- [ ] **Step 3: Add the second table and expand the amount table**

Add a second `table-card` after the existing amount table with title `Monthly Policy Count Performance Table`, CSV button, and `monthlyCountTable`. Render all 17 amount columns and all 16 count columns, append each summary's grand-total record, and retain current highlight behavior only for month rows. Use compact non-wrapping cells with horizontal scrolling and no new colors or chart changes.

- [ ] **Step 4: Run syntax and browser verification**

Run: `node --check app.js`

Run: `node tests/verify-section3.js`

Expected: both commands exit 0.

- [ ] **Step 5: Commit the Section 3 UI**

```powershell
git add -- index.html app.js styles.css tests/verify-section3.js
git commit -m "feat: show complete monthly summary tables"
```

### Task 4: Full Report Verification

**Files:**
- Modify only if verification exposes a scoped issue in the files above.

**Interfaces:**
- Verifies the generated JSON, JavaScript runtime, browser layout, and PDF generation path.

- [ ] **Step 1: Run the full verification suite**

Run: `python analysis.py`

Run: `python -m unittest discover -s tests -v`

Run: `node --check app.js`

Run: `node tests/verify-section3.js`

Run: `npm run pdf`

Expected: all commands exit 0.

- [ ] **Step 2: Review reconciliation output**

Confirm amount monthly total equals workbook amount grand total, count monthly total equals workbook count grand total, reporting period ends in July 2026, and any unrelated workbook validation differences remain explicitly logged.

- [ ] **Step 3: Inspect final changes**

Run: `git diff --check`

Run: `git status --short`

Expected: no whitespace errors and only intended generated/report files are modified.

