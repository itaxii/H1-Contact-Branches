# Insight-First Tables and Grand Totals Design

## Objective

Improve table readability by placing the most decision-relevant fields first and add mathematically correct Grand Total rows to every dashboard table and both heatmaps. Preserve all current report data, columns, charts, sections, calculations, colors, and business definitions.

## Scope

This change covers:

- Monthly Performance Table
- Monthly Policy Count Performance Table
- Branch Breakdown table
- expanded branch monthly-detail tables
- Seller Performance table
- Insurance Company table
- Line of Business table
- Branches Per Month heatmap
- Monthly Line of Business heatmap

No table columns will be removed. The two monthly tables will only receive a more useful column order. Other table column orders remain unchanged unless required to place the Grand Total label correctly.

## Monthly Performance Column Order

The table will keep month rows in chronological order. Columns will be reordered as follows:

1. Month
2. 2026 Total
3. Target
4. Achievement %
5. 2025 Total
6. 2025 vs 2026 YoY
7. New Premiums 2026
8. Renewal Premiums 2026
9. Other Policies 2026
10. Motor Premiums 2026
11. Non-Motor Premiums 2026
12. Pending Finance
13. New Premiums 2025
14. Renewal Premiums 2025
15. Other Policies 2025
16. Motor Premiums 2025
17. Non-Motor Premiums 2025

This order puts current production, target performance, and year-over-year movement before composition details.

## Monthly Policy Count Column Order

The table will keep month rows in chronological order. Columns will be reordered as follows:

1. Month
2. 2026 Total
3. YoY Count Difference
4. 2025 Total
5. New Policies 2026
6. Renewal Policies 2026
7. Other Policies 2026
8. Motor Policies 2026
9. Non-Motor Policies 2026
10. Motor Average Rate 2026
11. New Policies 2025
12. Renewal Policies 2025
13. Other Policies 2025
14. Motor Policies 2025
15. Non-Motor Policies 2025
16. Motor Average Rate 2025

Motor Average Rate remains displayed with two decimal places.

## Table Total Model

The reusable table renderer will accept a separate `totalRow`. This row will not be part of the sortable or filterable detail rows and will always render last with the existing Grand Total visual treatment.

Grand Total behavior:

- Currency and count fields use raw aggregate values.
- YoY amount equals aggregate current value minus aggregate previous value.
- YoY percentage equals aggregate YoY amount divided by aggregate previous value.
- Target Achievement equals aggregate actual divided by aggregate target.
- Contribution totals equal 100% when the table represents the complete population shown by that contribution metric.
- Renewal and motor mix percentages use aggregate component premium divided by aggregate premium.
- Average premium per policy uses aggregate premium divided by aggregate approved-policy count.
- Motor Average Rate uses the workbook's provided Grand Total rate because no underlying numerator and denominator are available.
- Undefined percentages remain `N/A`.
- Growth Classification on a total row displays `Grand Total` rather than a misleading growth category.

Where the workbook provides a Grand Total record, that raw record is the source. If a displayed table is intentionally a subset, such as Top 20 Sellers, the total represents that displayed dataset and is labeled Grand Total without implying an all-seller total.

Sorting any main table changes only detail-row order. Filtering the Branch Breakdown table changes visible detail rows but does not replace or recalculate the full-dataset Grand Total. CSV exports include the Grand Total as the last row.

## Table-Specific Totals

- Monthly amount and count tables retain their existing workbook Grand Total records.
- Branch Breakdown uses the workbook branch Grand Total record.
- Expanded branch monthly detail uses the matching branch aggregate row.
- Seller Performance uses the Top 20 seller section's Grand Total record when available; otherwise it aggregates the displayed seller rows.
- Insurance Company uses the insurer section Grand Total record.
- Line of Business uses the line-of-business Grand Total record.

Raw total records will be serialized into report data where they are currently extracted but not exposed to the browser.

## Heatmap Totals

Both heatmaps will add:

- a rightmost Grand Total column containing each row's total across reporting months
- a bottom Grand Total row containing each month's total across displayed rows
- a bottom-right Grand Total containing all displayed heatmap values

Heatmap detail cells retain the current blue intensity scale. Grand Total headers and cells use the existing summary-total styling with a neutral background. Total cells do not participate in the maximum-value calculation, preventing large aggregate values from flattening the heatmap's useful color differences.

The Branches Per Month heatmap continues to show the current top 25 branches, so its total row and column describe those displayed branches. The Monthly Line of Business heatmap continues to show its current top 10 lines of business, so its totals describe those displayed lines.

## Data Flow

1. `analysis.py` extracts existing workbook total records and computes fallback totals only when a workbook total is unavailable.
2. All derived total percentages use raw values through the existing Decimal metric layer.
3. Total records are added to `report-data.json` and `report-data.js` under explicit total keys.
4. `app.js` passes detail rows and total rows separately to the reusable table renderer.
5. Heatmap rendering calculates displayed-row totals from the same unrounded raw values used in heatmap cells.
6. Existing PDF generation waits and validation continue unchanged, then the PDF is regenerated.

## Validation

Automated checks will confirm:

- monthly tables use the approved column order
- every main table renders exactly one Grand Total row at the bottom
- sorting does not move the Grand Total row
- Branch Breakdown filtering does not remove the Grand Total row
- every expanded branch monthly table includes a Grand Total row
- CSV exports append Grand Total after detail rows
- heatmaps include one Grand Total column and one Grand Total row
- heatmap row, column, and overall totals equal sums of the displayed raw values
- total percentages and averages are recalculated from aggregate raw values
- Motor Average Rate remains formatted to two decimal places
- the complete 25-page PDF still contains Sections 1 through 11

## Non-Goals

- Removing, renaming, or adding business-data columns
- Sorting month rows by performance
- Adding Summary/Detail view controls
- Changing chart types, chart data, report sections, colors, or visual design
- Recalculating heatmap totals from compact K/M display strings
- Making filtered Branch Breakdown totals replace the full Grand Total

## Acceptance Criteria

- The two monthly tables show insight fields first in the approved order.
- All existing columns remain available.
- Every dashboard table and expanded branch monthly table has one correct Grand Total row.
- Grand Total remains last during sorting and filtering.
- Both heatmaps have correct Grand Total rows and columns.
- Heatmap totals do not alter detail-cell intensity scaling.
- Derived totals use raw values and the centralized Decimal calculation rules.
- No report charts, sections, or business logic change.
- HTML and regenerated PDF checks pass.
