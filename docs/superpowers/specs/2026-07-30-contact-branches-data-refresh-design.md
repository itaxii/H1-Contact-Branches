# Contact Branches Data Refresh Design

## Goal

Refresh the existing Contact Branches dashboard from `C:\Users\mOHAMED.tOLBA\Downloads\Branches\Contact Branches.xlsx` without changing report design, structure, calculations, or business logic.

## Source Handling

The new workbook replaces the current dashboard source workbook at `E:\Daily v3\Reports\Branch Report.xlsx`. The dashboard generator continues reading that stable source path, while report metadata identifies the workbook used for generation.

The workbook must retain the required `overview` and `Branches` sheets. The validated update contains January through July 2026 data, 61 branches, 20 sellers, 14 insurers, and 29 lines of business.

## Refresh Workflow

1. Back up the current source workbook before replacement.
2. Copy the supplied workbook to the stable source path.
3. Regenerate `data/report-data.json`, `data/report-data.js`, validation output, and the PDF.
4. Keep all dashboard sections, chart types, tables, titles, calculations, colors, and layout unchanged.
5. Run data, percentage, browser, and PDF validation.
6. Start a local preview and wait for user approval before publishing to GitHub.

## Reconciliation Baseline

The pre-refresh structural check produced these expected raw values from the supplied workbook:

- Approved Gross Premium: EGP 16,095,001
- Monthly total: EGP 16,095,001
- Branch total: EGP 16,095,001
- Insurer total: EGP 16,095,001
- Line-of-business total: EGP 16,095,001
- Reporting months: January through July 2026

The seller table remains the workbook's Top 20 seller extract. Seller contribution continues to use overall Approved Gross Premium as its dynamic denominator.

## Validation

- All required workbook extractors must complete without errors.
- Monthly, branch, insurer, and line-of-business totals must equal Approved Gross Premium within configured tolerance.
- Renewal and policy-type checks must reconcile.
- Every calculated percentage must pass centralized raw-value validation.
- Python and browser test suites must pass.
- The generated PDF must contain all expected report sections and the required page count.

If a blocking validation fails, generated artifacts must not be published.

## Non-Goals

- Redesigning the dashboard.
- Changing charts, tables, sections, KPI cards, titles, colors, or layout.
- Changing formulas or metric definitions.
- Publishing to GitHub before local preview approval.
