# Contact Branches Data Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate the unchanged Contact Branches dashboard from the supplied July workbook and present a validated local preview.

**Architecture:** Preserve the generator and dashboard code. Back up the stable source workbook, replace it with the supplied workbook, then use the existing extraction, metric catalog, validation, browser, and PDF pipelines to regenerate all data-backed artifacts. Stop after local preview so GitHub publication remains a separate approved action.

**Tech Stack:** Excel/openpyxl, pandas, Python 3, JavaScript, Playwright Core, Chart.js, Git.

## Global Constraints

- Do not change report design, structure, chart types, tables, KPI cards, titles, colors, or business logic.
- Use `C:\Users\mOHAMED.tOLBA\Downloads\Branches\Contact Branches.xlsx` as the new source.
- Keep `E:\Daily v3\Reports\Branch Report.xlsx` as the stable generator input path.
- Do not publish to GitHub before the user approves the local preview.
- Stop generation if any blocking validation fails.

---

### Task 1: Install and Validate the Updated Workbook

**Files:**
- Source: `C:\Users\mOHAMED.tOLBA\Downloads\Branches\Contact Branches.xlsx`
- Replace: `E:\Daily v3\Reports\Branch Report.xlsx`
- Create backup: `E:\Daily v3\Reports\Branch Report.pre-refresh-20260730.xlsx`

**Interfaces:**
- Consumes: the supplied workbook with `overview` and `Branches` sheets.
- Produces: the stable `WORKBOOK` input consumed by `analysis.py`.

- [ ] **Step 1: Verify source and destination paths**

Run:

```powershell
Get-Item -LiteralPath 'C:\Users\mOHAMED.tOLBA\Downloads\Branches\Contact Branches.xlsx'
Get-Item -LiteralPath 'E:\Daily v3\Reports\Branch Report.xlsx'
```

Expected: both files exist and are regular `.xlsx` workbooks.

- [ ] **Step 2: Back up and replace the stable source**

Run:

```powershell
Copy-Item -LiteralPath 'E:\Daily v3\Reports\Branch Report.xlsx' -Destination 'E:\Daily v3\Reports\Branch Report.pre-refresh-20260730.xlsx' -Force
Copy-Item -LiteralPath 'C:\Users\mOHAMED.tOLBA\Downloads\Branches\Contact Branches.xlsx' -Destination 'E:\Daily v3\Reports\Branch Report.xlsx' -Force
```

Expected: the stable source hash equals the supplied workbook hash, while the backup retains the prior hash.

- [ ] **Step 3: Run extraction and data tests**

Run: `npm run test:python`

Expected: all Python tests pass; generated validation has no blocking failures.

- [ ] **Step 4: Verify expected refresh values**

Read `data/report-data.json` and assert:

```python
assert data["totals"]["approved_gross_premium"] == 16095001
assert data["monthly_total"]["actual_2026"] == 16095001
assert data["table_totals"]["branches"]["premium_2026"] == 16095001
assert data["table_totals"]["insurers"]["premium_2026"] == 16095001
assert data["table_totals"]["lines_of_business"]["premium_2026"] == 16095001
assert data["meta"]["latest_reporting_month"] == "July"
```

Expected: every assertion passes.

---

### Task 2: Regenerate Artifacts and Start Local Preview

**Files:**
- Modify: `data/report-data.json`
- Modify: `data/report-data.js`
- Modify: `data/validation-summary.json`
- Modify: `data/rounding-changes.json` if the audit changes
- Modify: `contact-branches-report.pdf`

**Interfaces:**
- Consumes: the validated stable workbook from Task 1.
- Produces: refreshed dashboard data, validation log, PDF, and a local preview URL.

- [ ] **Step 1: Run the complete automated suite**

Run: `npm test`

Expected: all Python and browser tests pass.

- [ ] **Step 2: Regenerate and validate the PDF**

Run: `npm run pdf`

Expected: PDF generation completes without blocking validation failures.

Run: `python tests/verify-pdf.py`

Expected: the PDF contains 25 pages and Sections 1 through 11.

- [ ] **Step 3: Verify reconciliation and source hygiene**

Run: `git diff --check`

Expected: no whitespace errors.

Review `data/validation-summary.json` and report every warning with expected, actual, and difference.

- [ ] **Step 4: Commit refreshed artifacts**

```powershell
git add data/report-data.json data/report-data.js data/validation-summary.json data/rounding-changes.json contact-branches-report.pdf
git commit -m "data: refresh Contact Branches dashboard"
```

Only stage `data/rounding-changes.json` when it changed.

- [ ] **Step 5: Start the local preview**

Start a static HTTP server from the worktree on an available local port and provide the URL plus login credentials.

Expected: the dashboard loads, the PDF action remains hidden, and refreshed values appear throughout the report.

- [ ] **Step 6: Wait for preview approval**

Do not push to GitHub in this task. After the user approves the preview, publish the committed branch to `main` in a separate step.
