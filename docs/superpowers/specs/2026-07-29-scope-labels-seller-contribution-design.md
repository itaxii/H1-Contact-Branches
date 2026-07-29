# Scope Labels and Seller Contribution Design

## Goal

Correct three presentation and metric-definition issues without changing report structure, source data, or unrelated calculations.

## Changes

### PDF Download Control

Hide the `Download Full PDF` action from the report interface. Keep the internal Playwright PDF-generation workflow and existing PDF artifact available for development and validation.

### Heatmap Scope

Rename the heatmaps to describe the rows they display:

- `Top 25 Branches Monthly Premium Heatmap`
- `Top 10 Lines of Business Monthly Premium Heatmap`

Update each heatmap note to state that its row, column, and Grand Total values cover only the displayed Top 25 branches or Top 10 lines of business. The ranking remains dynamic and based on 2026 premium from the current workbook.

### Seller Contribution

Calculate each seller's contribution dynamically as:

`seller 2026 premium / overall Approved Gross Premium`

Use the centralized raw Approved Gross Premium value extracted from the current workbook. Do not use the sum of displayed seller rows, formatted values, or a hard-coded denominator. Apply rounding only through the existing final-display formatter.

The seller table's Grand Total contribution must use the same overall denominator and the aggregate seller premium numerator.

## Data Flow

1. `analysis.py` reads the current workbook and obtains overall Approved Gross Premium.
2. Seller records and the seller total record calculate contribution from raw premium values and that centralized denominator.
3. The existing metric catalog serializes the same raw calculation for display validation.
4. `app.js` renders the calculated contribution without recomputing it from visible table rows.

## Validation

- Assert each seller contribution equals seller premium divided by overall Approved Gross Premium.
- Assert the seller total contribution uses aggregate seller premium divided by the same denominator.
- Assert no contribution calculation uses a formatted or rounded input.
- Assert the PDF download action is not visible.
- Assert both heatmap titles and explanatory notes identify their displayed scope.
- Run all Python and browser tests after implementation.

## Non-Goals

- Removing internal PDF generation or the generated PDF artifact.
- Changing heatmap membership, sorting, totals, colors, or layout.
- Changing report sections, charts, tables, or other contribution metrics.
