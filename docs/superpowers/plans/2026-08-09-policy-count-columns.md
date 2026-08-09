# Policy Count Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display the newly supplied 2026 policy counts in the insurer table and in both levels of the seller table using `8-9.xlsx`.

**Architecture:** Extend the existing workbook extraction pipeline rather than calculating counts in the browser. Insurance columns will be resolved from normalized header names; seller counts will continue through the established entity aggregation path and only gain presentation columns.

**Tech Stack:** Python 3, pandas, openpyxl, vanilla JavaScript, Playwright Core, unittest.

## Global Constraints

- Use `C:\Users\mOHAMED.tOLBA\Downloads\Contact Branches\8-9.xlsx` as the latest source workbook.
- Preserve existing charts, KPIs, calculations, sorting, styling, and responsive layout.
- Show whole-number policy counts with thousands separators and no decimals.
- Do not modify source workbook values.

---

### Task 1: Header-Driven Insurance Policy Count Extraction

**Files:**
- Modify: `analysis.py:679`
- Test: `tests/test_monthly_summaries.py`

**Interfaces:**
- Consumes: a pandas `DataFrame` containing the `2025 vs 2026 By Insurance Company Summary` section.
- Produces: `extract_insurers(df) -> tuple[list[dict], dict | None]`, with `new_policies_2026`, `renewal_policies_2026`, and `other_policies_2026` on detail and total records.

- [ ] **Step 1: Add an insurer fixture with moved columns and policy counts**

```python
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
```

- [ ] **Step 2: Add a failing mapping assertion**

```python
def test_insurer_policy_counts_are_mapped_by_header(self):
    rows, total = extract_insurers(build_insurer_fixture())
    self.assertEqual(rows[0]["new_policies_2026"], 4)
    self.assertEqual(rows[0]["renewal_policies_2026"], 3)
    self.assertEqual(rows[0]["other_policies_2026"], 2)
    self.assertEqual(total["other_policies_2026"], 2)
```

- [ ] **Step 3: Run the focused test and confirm it fails**

Run: `python -m unittest tests.test_monthly_summaries.MonthlySummaryExtractionTests.test_insurer_policy_counts_are_mapped_by_header -v`

Expected: FAIL because the current extractor assumes fixed columns and does not serialize the new count fields.

- [ ] **Step 4: Implement normalized header lookup in `extract_insurers`**

Resolve the section title, locate the following header row, normalize header text with the repository's existing normalization helper, and map these output fields:

```python
field_aliases = {
    "insurance_company": ("Insurance Company",),
    "premium_2025": ("2025",),
    "premium_2026": ("2026",),
    "source_yoy_change": ("2025 VS 2026 YOY",),
    "source_yoy_change_pct": ("Gross YoY Change %",),
    "new_policies_2026": ("New Policies 2026",),
    "renewal_policies_2026": ("Renewal Policies 2026",),
    "other_policies_2026": ("Other Policies 2026",),
}
```

Use `parse_number` for count and amount fields, `parse_percent` for the source percentage, and preserve the existing raw-value YoY, share, and growth-class calculations.

- [ ] **Step 5: Run the focused test and the Python suite**

Run: `python -m unittest tests.test_monthly_summaries.MonthlySummaryExtractionTests.test_insurer_policy_counts_are_mapped_by_header -v`

Expected: PASS.

Run: `npm run test:python`

Expected: all Python tests PASS.

- [ ] **Step 6: Commit the parser change**

```bash
git add analysis.py tests/test_monthly_summaries.py
git commit -m "feat: extract insurer policy counts"
```

---

### Task 2: Seller and Insurer Table Columns

**Files:**
- Modify: `app.js:814`
- Modify: `app.js:874`
- Modify: `app.js:941`
- Test: `tests/verify-seller-daily.js`
- Test: `tests/verify-table-totals.js`

**Interfaces:**
- Consumes: insurer records with `*_policies_2026`, seller records with `new_policies` and `renewal_policies`, and monthly seller records with the same seller field names.
- Produces: visible integer-formatted policy columns in insurer summary, seller summary, seller expanded monthly rows, and their grand-total rows.

- [ ] **Step 1: Add failing browser assertions for summary headers**

```javascript
assert.ok((await page.locator("#sellerTable thead th").allTextContents()).includes("New Policies 2026"));
assert.ok((await page.locator("#sellerTable thead th").allTextContents()).includes("Renewal Policies 2026"));
assert.ok((await page.locator("#insurerTable thead th").allTextContents()).includes("Other Policies 2026"));
```

- [ ] **Step 2: Add failing assertions for expanded seller rows**

After opening the first seller row, assert that the nested header contains `New Policies 2026` and `Renewal Policies 2026`, and compare the first monthly cells with `fmtNumber`-equivalent locale output from `window.REPORT_DATA.seller_monthly`.

- [ ] **Step 3: Run browser tests and confirm they fail**

Run: `node tests/verify-seller-daily.js`

Expected: FAIL because the seller summary and nested monthly headers do not expose policy counts.

Run: `node tests/verify-table-totals.js`

Expected: FAIL because the insurer table does not expose all three new fields.

- [ ] **Step 4: Add seller-only columns to `entityColumns`**

Build the shared columns first, then insert these only when `nameKey === "seller"`:

```javascript
{ key: "new_policies", label: "New Policies 2026", ...countCol("new_policies") },
{ key: "renewal_policies", label: "Renewal Policies 2026", ...countCol("renewal_policies") },
```

Do not expose these fields in the branch table.

- [ ] **Step 5: Extend the seller monthly nested table**

Add `New Policies 2026` and `Renewal Policies 2026` headers, use `fmtNumber(row.new_policies)` and `fmtNumber(row.renewal_policies)` for monthly rows, and use the same fields from the seller aggregate in the nested grand-total row.

- [ ] **Step 6: Extend the insurer table**

Add these columns after `Premium 2026`:

```javascript
{ key: "new_policies_2026", label: "New Policies 2026", ...countCol("new_policies_2026") },
{ key: "renewal_policies_2026", label: "Renewal Policies 2026", ...countCol("renewal_policies_2026") },
{ key: "other_policies_2026", label: "Other Policies 2026", ...countCol("other_policies_2026") },
```

- [ ] **Step 7: Run both browser checks**

Run: `node tests/verify-seller-daily.js && node tests/verify-table-totals.js`

Expected: both checks PASS with unchanged page errors and one grand-total row per table.

- [ ] **Step 8: Commit the presentation change**

```bash
git add app.js tests/verify-seller-daily.js tests/verify-table-totals.js
git commit -m "feat: show insurer and seller policy counts"
```

---

### Task 3: Latest Workbook and End-to-End Verification

**Files:**
- Replace: `../Branch Report.xlsx`
- Regenerate: `data/report-data.json`
- Test: `tests/test_monthly_summaries.py`

**Interfaces:**
- Consumes: the approved parser and UI changes plus `8-9.xlsx`.
- Produces: a locally viewable dashboard whose displayed insurer and seller counts match the latest workbook.

- [ ] **Step 1: Add workbook-backed reconciliation assertions**

Assert the generated insurer records contain all three count fields and that seller aggregates reconcile to their monthly rows:

```python
for insurer in self.data["insurers"]:
    self.assertIn("new_policies_2026", insurer)
    self.assertIn("renewal_policies_2026", insurer)
    self.assertIn("other_policies_2026", insurer)

for seller in self.data["sellers"]:
    months = [row for row in self.data["seller_monthly"] if row["seller"] == seller["seller"]]
    if months:
        self.assertEqual(seller["new_policies"], sum((row["new_policies"] or 0) for row in months))
        self.assertEqual(seller["renewal_policies"], sum((row["renewal_policies"] or 0) for row in months))
```

- [ ] **Step 2: Run the workbook-backed test before replacing the source**

Run: `npm run test:python`

Expected: the new workbook assertions fail or lack the newly added insurer fields in the current generated dataset.

- [ ] **Step 3: Replace the report source workbook**

Copy `C:\Users\mOHAMED.tOLBA\Downloads\Contact Branches\8-9.xlsx` to the repository's existing source path `E:\Daily v3\Reports\contact-branches-report\.worktrees\Branch Report.xlsx`, preserving the filename expected by `analysis.py`.

- [ ] **Step 4: Regenerate dashboard data**

Run: `npm run data`

Expected: `data/report-data.json` is generated successfully and contains the new insurer count fields and seller count values.

- [ ] **Step 5: Run all automated verification**

Run: `npm test`

Expected: all Python and Playwright checks PASS.

- [ ] **Step 6: Inspect the dashboard locally**

Start: `python -m http.server 8767 --bind 127.0.0.1`

Open `http://127.0.0.1:8767/index.html`, sign in with the existing credentials, and verify insurer policy counts, seller summary policy counts, expanded seller monthly counts, and all grand totals without altering any unrelated section.

- [ ] **Step 7: Commit the workbook-backed output and specification**

```bash
git add data/report-data.json docs/plans/2026-08-09-policy-count-columns-design.md docs/superpowers/plans/2026-08-09-policy-count-columns.md tests/test_monthly_summaries.py
git commit -m "data: refresh dashboard from 8-9 workbook"
```
