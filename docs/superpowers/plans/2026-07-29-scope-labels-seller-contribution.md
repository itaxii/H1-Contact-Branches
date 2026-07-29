# Scope Labels and Seller Contribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide the PDF download action, identify the displayed Top 25/Top 10 heatmap scope, and calculate seller contribution against dynamic overall Approved Gross Premium.

**Architecture:** Keep the report structure and PDF pipeline unchanged. Move seller contribution ownership fully into `build_metric_catalog`, where the workbook-derived overall approved premium already exists, and render the resulting serialized values without browser-side recalculation. Limit UI work to exact copy changes and removal of the public PDF action.

**Tech Stack:** Python 3, Decimal metric registry, JavaScript, HTML, Playwright Core, Python `unittest`.

## Global Constraints

- The overall Approved Gross Premium denominator must come from the current workbook.
- No calculation may use formatted, rounded, or hard-coded inputs.
- Keep internal PDF generation and the generated PDF artifact.
- Do not change heatmap membership, sorting, totals, colors, or layout.
- Do not change report sections, charts, tables, or unrelated metrics.

---

### Task 1: Dynamic Seller Contribution

**Files:**
- Modify: `analysis.py`
- Test: `tests/test_monthly_summaries.py`

**Interfaces:**
- Consumes: `data["totals"]["approved_gross_premium"]`, seller `premium_2026`, and `MetricRegistry.register_rate` through `register_rate`.
- Produces: seller row and seller Grand Total `contribution_pct` values with overall Approved Gross Premium as denominator.

- [ ] **Step 1: Write failing seller contribution tests**

Add tests to `DashboardTableTotalTests`:

```python
def test_seller_contribution_uses_overall_approved_premium(self):
    approved = self.data["totals"]["approved_gross_premium"]
    for seller in self.data["sellers"]:
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
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m unittest tests.test_monthly_summaries.DashboardTableTotalTests -v`

Expected: seller contribution assertions fail because current seller rows divide by seller-table premium and the total displays 100%.

- [ ] **Step 3: Centralize the dynamic calculation**

In `extract_sellers`, stop calculating contribution against the seller table total and leave `contribution_pct` unset until catalog registration.

In `build_metric_catalog`, change seller registration to:

```python
register_entity(data["sellers"], "seller", "seller", approved)
```

In the table-total loop, use `approved` only for the seller total contribution:

```python
if area == "sellers":
    denominator = approved
elif area == "branches":
    denominator = total.get("premium_2026")
else:
    denominator = None

if denominator is not None:
    total["contribution_pct"] = register_rate(
        registry,
        f"{prefix}.contribution",
        f"{area.title()} Grand Total Contribution",
        total.get("premium_2026"),
        denominator,
    )
```

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_monthly_summaries.DashboardTableTotalTests -v`

Expected: all dashboard table total tests pass.

- [ ] **Step 5: Commit the metric change**

```powershell
git add analysis.py tests/test_monthly_summaries.py
git commit -m "fix: calculate seller contribution from total premium"
```

---

### Task 2: Public Controls and Scope Copy

**Files:**
- Modify: `index.html`
- Modify: `app.js`
- Test: `tests/verify-section3.js`
- Test: `tests/verify-table-totals.js`

**Interfaces:**
- Consumes: existing heatmap IDs `branchesPerMonthHeatmap` and `lobHeatmap`.
- Produces: no public PDF action, exact scoped heatmap titles, and explanatory scope notes.

- [ ] **Step 1: Write failing browser assertions**

Replace the PDF-link assertions in `tests/verify-section3.js` with:

```javascript
assert.equal(await page.locator("#pdfDownload").count(), 0);
```

Add to `tests/verify-table-totals.js`:

```javascript
assert.equal(
  await page.locator("#branches h3").filter({ hasText: "Top 25 Branches Monthly Premium Heatmap" }).count(),
  1
);
assert.equal(
  await page.locator("#lob h3").filter({ hasText: "Top 10 Lines of Business Monthly Premium Heatmap" }).count(),
  1
);
assert.match(await page.locator("#branchesPerMonthHeatmap .source-note").innerText(), /displayed Top 25 branches/);
assert.match(await page.locator("#lobHeatmap .source-note").innerText(), /displayed Top 10 lines of business/);
```

- [ ] **Step 2: Run browser tests and confirm failure**

Run: `npm run test:browser`

Expected: assertions fail against the current PDF link and unscoped titles and notes.

- [ ] **Step 3: Apply the exact presentation changes**

Remove the `#pdfDownload` anchor from `index.html` while leaving the Reset Filters button and PDF generator untouched.

Change the heatmap headings in `index.html` to:

```html
<h3>Top 25 Branches Monthly Premium Heatmap</h3>
<h3>Top 10 Lines of Business Monthly Premium Heatmap</h3>
```

Change the heatmap notes in `app.js` to:

```javascript
"Shows monthly 2026 premium for the displayed Top 25 branches. Heatmap and Grand Total values cover only these displayed branches."
"Shows monthly 2026 premium for the displayed Top 10 lines of business. Heatmap and Grand Total values cover only these displayed lines of business."
```

- [ ] **Step 4: Run browser tests**

Run: `npm run test:browser`

Expected: all three browser suites pass.

- [ ] **Step 5: Commit UI copy and control changes**

```powershell
git add index.html app.js tests/verify-section3.js tests/verify-table-totals.js
git commit -m "fix: clarify scoped heatmaps and hide PDF action"
```

---

### Task 3: Regenerate and Verify Report Artifacts

**Files:**
- Modify: `data/report-data.json`
- Modify: `data/report-data.js`
- Modify: `data/validation-summary.json`
- Modify: `contact-branches-report.pdf`

**Interfaces:**
- Consumes: Tasks 1 and 2 outputs.
- Produces: validated serialized dashboard data and a complete 25-page PDF.

- [ ] **Step 1: Run the full test suite**

Run: `npm test`

Expected: all Python and browser tests pass, including centralized percentage validation.

- [ ] **Step 2: Regenerate the PDF**

Run: `npm run pdf`

Expected: validation has no blockers and PDF generation completes.

- [ ] **Step 3: Verify PDF and source hygiene**

Run: `python tests/verify-pdf.py`

Expected: the PDF contains 25 pages and Sections 1 through 11.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 4: Commit generated artifacts**

```powershell
git add data/report-data.json data/report-data.js data/validation-summary.json contact-branches-report.pdf
git commit -m "test: regenerate report with corrected seller shares"
```

- [ ] **Step 5: Run final post-commit verification**

Run: `npm test && python tests/verify-pdf.py && git status --short`

Expected: all tests pass, PDF validation passes, and the worktree is clean.
