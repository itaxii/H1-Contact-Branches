# Insight-First Tables and Grand Totals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder the two monthly tables around current performance insights and add correct, fixed Grand Total rows to every dashboard table and both heatmaps.

**Architecture:** Expose the workbook's existing entity total records through `analysis.py`, with raw-value aggregation only as a fallback. Extend the reusable browser table renderer with a separate non-sortable `totalRow`, and share one heatmap-total helper between the branch and line-of-business heatmaps. Keep total calculations on raw values and preserve the existing Decimal formatting, validation, PDF layout, and visual language.

**Tech Stack:** Python 3, pandas/openpyxl, Decimal metric registry, JavaScript, Chart.js, HTML/CSS, Node.js, Playwright Core, Python `unittest`.

## Global Constraints

- Preserve all current report data, columns, charts, sections, calculations, colors, and business definitions.
- Keep monthly rows in chronological order.
- Do not remove any existing table column.
- Use raw aggregate values for total currency, counts, percentages, averages, and mix metrics.
- Keep Motor Average Rate at two decimal places.
- Keep Grand Total fixed at the bottom during sorting and Branch Breakdown filtering.
- Include Grand Total as the last row of CSV exports.
- Heatmap totals describe only the rows currently displayed: top 25 branches and top 10 lines of business.
- Heatmap total cells must not affect detail-cell color intensity.
- Do not change chart types, chart data, report sections, or business logic.
- Preserve the existing 25-page PDF with Sections 1 through 11.

## File Structure

- Modify `analysis.py`: serialize branch, seller, insurer, and line-of-business total records; create fallback raw totals only when workbook totals are unavailable; register derived total rates.
- Modify `tests/test_monthly_summaries.py`: verify total records are exposed and reconcile with detail rows.
- Modify `app.js`: reorder monthly columns, support separate total rows in tables and CSV, add nested branch totals, and render heatmap total rows/columns.
- Modify `styles.css`: extend existing summary-total styling to table footers and heatmap total cells without changing the design palette.
- Create `tests/verify-table-totals.js`: browser verification for column order, total placement, sorting/filtering, nested totals, CSV state, and heatmap sums.
- Modify `package.json`: include the new browser test in `test:browser`.
- Regenerate `data/report-data.json`, `data/report-data.js`, `data/validation-summary.json`, `data/rounding-changes.json`, and `contact-branches-report.pdf`.

---

### Task 1: Expose Canonical Table Total Records

**Files:**
- Modify: `analysis.py`
- Modify: `tests/test_monthly_summaries.py`

**Interfaces:**
- Produces: `aggregate_entity_total(records: list[dict], name_key: str) -> dict`
- Produces: `data["table_totals"]` with keys `branches`, `sellers`, `insurers`, and `lines_of_business`.
- Preserves: existing `monthly_total` and `monthly_count_total` keys.

- [ ] **Step 1: Write failing workbook-total serialization tests**

Add imports for `json`, `DATA_DIR`, and `main`, then add:

```python
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
                self.assertLessEqual(abs(total - detail_sum), 2)
```

- [ ] **Step 2: Run the tests and verify the total catalog is missing**

Run: `python -m unittest tests.test_monthly_summaries.DashboardTableTotalTests -v`

Expected: FAIL with `KeyError: 'table_totals'`.

- [ ] **Step 3: Implement raw fallback aggregation**

Add a focused helper near the extraction functions:

```python
def aggregate_entity_total(records, name_key):
    total = {name_key: "Grand Total"}
    numeric_keys = {
        key
        for record in records
        for key, value in record.items()
        if key != name_key and isinstance(value, (int, float)) and not key.endswith("_pct")
    }
    for key in numeric_keys:
        total[key] = sum(money(record.get(key)) for record in records)
    total["yoy_change"] = money(total.get("premium_2026")) - money(total.get("premium_2025"))
    total["yoy_change_pct"] = safe_yoy(total.get("premium_2026"), total.get("premium_2025"))
    total["contribution_pct"] = 1 if records else None
    total["avg_premium_per_policy"] = safe_div(total.get("premium_2026"), total.get("approved_policies"))
    total["renewal_mix_pct"] = safe_div(total.get("renewal_premium"), total.get("premium_2026"))
    total["motor_mix_pct"] = safe_div(total.get("motor_premium"), total.get("premium_2026"))
    total["growth_class"] = "Grand Total"
    return total
```

Do not aggregate `*_pct` fields. Recalculate them from aggregate numerators and denominators.

- [ ] **Step 4: Serialize workbook totals with fallbacks**

After extraction and before `build_metric_catalog(data)`, add:

```python
"table_totals": {
    "branches": branch_total or aggregate_entity_total(branches, "branch"),
    "sellers": seller_total or aggregate_entity_total(sellers, "seller"),
    "insurers": insurer_total or aggregate_entity_total(insurers, "insurance_company"),
    "lines_of_business": lob_total or aggregate_entity_total(lobs, "line_of_business"),
},
```

Normalize each total's name field to `Grand Total` and growth classification to `Grand Total`.

- [ ] **Step 5: Register total percentages through the Decimal metric layer**

Extend `build_metric_catalog(data)` so each `table_totals` record receives canonical YoY, contribution/share, renewal mix, motor mix, average, and target achievement values where its underlying fields exist. Use IDs such as `table-total.branches.yoy` and `table-total.lines-of-business.target-achievement`.

- [ ] **Step 6: Run Python tests**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

Expected: all tests PASS and existing reconciliation warnings remain unchanged.

- [ ] **Step 7: Commit total serialization**

```powershell
git add analysis.py tests/test_monthly_summaries.py
git commit -m "feat: expose canonical dashboard table totals"
```

---

### Task 2: Insight-First Monthly Columns and Fixed Table Footers

**Files:**
- Modify: `app.js`
- Modify: `styles.css`
- Create: `tests/verify-table-totals.js`

**Interfaces:**
- Consumes: `data.table_totals`, `data.monthly_total`, and `data.monthly_count_total` from Task 1.
- Extends: `renderTable(id, columns, rows, options)` with `options.totalRow`.
- Extends: table state with `totalRow: object | null`.
- Produces: a `<tfoot>` Grand Total row that is independent of detail-row sorting/filtering.
- Produces: `tableRowsForExport(state) -> object[]`.

- [ ] **Step 1: Write a failing browser test for monthly column order and six main totals**

Create `tests/verify-table-totals.js` using the same browser discovery and authentication setup as `tests/verify-section3.js`, then assert:

```javascript
const expectedAmountHeaders = [
  "Month", "2026 Total", "Target", "Achievement %", "2025 Total",
  "2025 vs 2026 YoY", "New Premiums 2026", "Renewal Premiums 2026",
  "Other Policies 2026", "Motor Premiums 2026", "Non-Motor Premiums 2026",
  "Pending Finance", "New Premiums 2025", "Renewal Premiums 2025",
  "Other Policies 2025", "Motor Premiums 2025", "Non-Motor Premiums 2025",
];
const expectedCountHeaders = [
  "Month", "2026 Total", "YoY Count Difference", "2025 Total",
  "New Policies 2026", "Renewal Policies 2026", "Other Policies 2026",
  "Motor Policies 2026", "Non-Motor Policies 2026", "Motor Average Rate 2026",
  "New Policies 2025", "Renewal Policies 2025", "Other Policies 2025",
  "Motor Policies 2025", "Non-Motor Policies 2025", "Motor Average Rate 2025",
];

assert.deepEqual(await page.locator("#monthlyTable thead th").allTextContents(), expectedAmountHeaders);
assert.deepEqual(await page.locator("#monthlyCountTable thead th").allTextContents(), expectedCountHeaders);
for (const id of ["monthlyTable", "monthlyCountTable", "branchTable", "sellerTable", "insurerTable", "lobTable"]) {
  assert.equal(await page.locator(`#${id} tfoot tr`).count(), 1, `${id} needs one total row`);
  assert.match(await page.locator(`#${id} tfoot`).innerText(), /Grand Total/);
}
```

- [ ] **Step 2: Run the browser test and verify failure**

Run: `node tests/verify-table-totals.js`

Expected: FAIL because current column order differs and tables do not render `<tfoot>` totals.

- [ ] **Step 3: Reorder the two monthly column arrays**

Move existing column objects into the exact approved order from the test. Do not add, remove, rename, or reformat any column.

- [ ] **Step 4: Extend the reusable table renderer**

In `renderTable`, store the total separately:

```javascript
tables[id] = {
  columns,
  rows,
  filteredRows: rows.slice(),
  sortKey: null,
  sortDir: 1,
  options,
  totalRow: options.totalRow || null,
};
```

Extract cell rendering into `renderTableCells(id, row, state, allowChildren)` so detail and total rows use identical formatters. In `drawTable`, append:

```javascript
const footer = state.totalRow
  ? `<tfoot><tr class="summary-total">${renderTableCells(id, state.totalRow, state, false)}</tr></tfoot>`
  : "";
table.innerHTML = header + body + footer;
```

Do not insert `totalRow` into `filteredRows`; this guarantees sorting and filtering cannot move or remove it.

- [ ] **Step 5: Pass totals to all six main tables**

Use:

```javascript
{ ...existingOptions, totalRow: data.monthly_total }
{ totalRow: data.monthly_count_total }
{ ...existingBranchOptions, totalRow: data.table_totals.branches }
{ totalRow: data.table_totals.sellers }
{ totalRow: data.table_totals.insurers }
{ totalRow: data.table_totals.lines_of_business }
```

Remove the monthly pattern that appends totals directly into `amountRows` and `countRows`; pass only detail rows to `renderTable`.

- [ ] **Step 6: Keep totals last in CSV exports**

Add:

```javascript
function tableRowsForExport(state) {
  return state.totalRow ? [...state.filteredRows, state.totalRow] : state.filteredRows.slice();
}
```

Use this function in `exportTable`. Detail exports respect the active filter, and Grand Total remains the final row. Expose a read-only browser-test interface:

```javascript
window.dashboardTables = {
  rowsForExport: (id) => tableRowsForExport(tables[id]),
};
```

- [ ] **Step 7: Add nested branch monthly totals**

In `branchMonthlyTable(branch)`, find the matching branch aggregate:

```javascript
const total = data.branches.find((row) => row.branch === branch);
```

Append a `<tfoot>` row using the same eight nested columns: Month, 2025 Premium, 2026 Premium, YoY Change, YoY %, New, Renewal, and Approved Policies. The first cell displays `Grand Total`.

- [ ] **Step 8: Extend browser tests for sorting, filtering, nested totals, and CSV state**

Add assertions that click a sortable Branch header, fill `#branchSearch`, and confirm `#branchTable tfoot` remains exactly one row. Expand the first visible branch and assert `.nested-table tfoot tr` exists and contains `Grand Total`. Assert the exported monthly state ends with its total:

```javascript
const exportedRows = await page.evaluate(() => window.dashboardTables.rowsForExport("monthlyTable"));
assert.equal(exportedRows.at(-1).month, "Grand Total");
```

- [ ] **Step 9: Style table footers with the existing total language**

Extend the existing `.summary-total` selectors to `tfoot .summary-total` and ensure footer cells use the current summary background, bold weight, and top border. Do not introduce new colors.

- [ ] **Step 10: Run table browser checks**

Run: `node --check app.js`

Run: `node tests/verify-table-totals.js`

Run: `node tests/verify-section3.js`

Expected: all commands PASS.

- [ ] **Step 11: Commit table presentation and totals**

```powershell
git add app.js styles.css tests/verify-table-totals.js
git commit -m "feat: prioritize monthly insights and add table totals"
```

---

### Task 3: Heatmap Grand Total Rows and Columns

**Files:**
- Modify: `app.js`
- Modify: `styles.css`
- Modify: `tests/verify-table-totals.js`

**Interfaces:**
- Produces: `buildHeatmapHtml({ rows, rowNames, rowKey, valueKey, months, note }) -> string`.
- Produces: `.heatmap-total` cells with `data-raw-value` attributes for verification.
- Preserves: detail-cell intensity based only on detail values.

- [ ] **Step 1: Add failing heatmap-total browser assertions**

```javascript
for (const id of ["branchesPerMonthHeatmap", "lobHeatmap"]) {
  const heatmap = page.locator(`#${id}`);
  assert.equal(await heatmap.getByText("Grand Total", { exact: true }).count(), 2);
  assert.ok(await heatmap.locator(".heatmap-total").count() > 2);
  const overall = Number(await heatmap.locator(".heatmap-total--overall").getAttribute("data-raw-value"));
  const rowTotals = await heatmap.locator(".heatmap-total--row").evaluateAll((cells) =>
    cells.map((cell) => Number(cell.dataset.rawValue))
  );
  assert.equal(overall, rowTotals.reduce((sum, value) => sum + value, 0));
}
```

- [ ] **Step 2: Run the test and confirm heatmap totals are missing**

Run: `node tests/verify-table-totals.js`

Expected: FAIL because `.heatmap-total` cells do not exist.

- [ ] **Step 3: Implement the shared heatmap builder**

The helper will:

1. calculate `maxDetail` from detail values only
2. calculate one row total for each displayed row name
3. calculate one column total for each reporting month
4. calculate the overall displayed total from row totals
5. render the normal detail grid plus a rightmost Grand Total column and bottom Grand Total row

Use raw `value(row[valueKey])` inputs for every sum. Render totals with `fmtMoney`, and add exact raw totals through `data-raw-value`.

- [ ] **Step 4: Refactor both heatmaps to use the helper**

Pass the existing displayed branch list and filtered branch-month records to the helper. Pass the existing top-line list and filtered line-of-business records to the same helper. Preserve the current explanatory notes unchanged.

- [ ] **Step 5: Add neutral heatmap total styling**

Use the current table summary background/border variables for `.heatmap-total` and `.heatmap-total-label`. Do not apply inline blue opacity to these cells. Keep detail cells and their intensity calculations unchanged.

- [ ] **Step 6: Run browser verification**

Run: `node tests/verify-table-totals.js`

Run: `npm run test:browser`

Expected: totals reconcile exactly for both displayed heatmaps and all browser tests PASS.

- [ ] **Step 7: Commit heatmap totals**

```powershell
git add app.js styles.css tests/verify-table-totals.js
git commit -m "feat: add displayed totals to report heatmaps"
```

---

### Task 4: Full Validation and PDF Regeneration

**Files:**
- Modify: `package.json`
- Regenerate: `data/report-data.json`
- Regenerate: `data/report-data.js`
- Regenerate: `data/validation-summary.json`
- Regenerate: `data/rounding-changes.json`
- Regenerate: `contact-branches-report.pdf`

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: updated browser suite and validated 25-page PDF.

- [ ] **Step 1: Add the new browser test to the project suite**

Set:

```json
"test:browser": "node tests/verify-section3.js && node tests/verify-rounding.js && node tests/verify-table-totals.js"
```

- [ ] **Step 2: Run the complete automated suite**

Run: `npm test`

Expected: Python extraction/precision tests and all three Playwright browser checks PASS.

- [ ] **Step 3: Regenerate the validated PDF**

Run: `npm run pdf`

Expected: analysis validation has no blockers; browser metric validation passes; the temporary PDF passes completeness checks before replacing `contact-branches-report.pdf`.

- [ ] **Step 4: Verify final PDF and source hygiene**

Run: `python tests/verify-pdf.py`

Run: `git diff --check`

Run: `git status --short`

Expected: PDF has 25 pages and Sections 1-11; no whitespace errors; only expected generated artifacts and `package.json` remain uncommitted.

- [ ] **Step 5: Commit suite and generated artifacts**

```powershell
git add package.json data/report-data.json data/report-data.js data/validation-summary.json data/rounding-changes.json contact-branches-report.pdf
git commit -m "test: verify totals across dashboard and PDF"
```

- [ ] **Step 6: Prepare the delivery summary**

Report the approved monthly column orders, all tables receiving totals, heatmap displayed-scope totals, test results, PDF page count, and any unchanged workbook reconciliation warnings.
