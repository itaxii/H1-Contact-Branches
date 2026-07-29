# Monthly Summary Tables Design

## Goal

Update Section 3 from the new `Contact Branches.xlsx` workbook so the existing Monthly Performance Table exposes every field in `2025 vs 2026 By Premium Amount Summary`, and add `2025 vs 2026 By Premium Count Summary` as a second table with the same dashboard styling.

## Source And Reporting Period

- The supplied workbook is the single source of truth.
- The amount summary is identified by the section title `2025 vs 2026 By Premium Amount Summary`.
- The count summary is identified by the section title `2025 vs 2026 By Premium Count Summary`.
- Headers are mapped by normalized header text rather than fixed worksheet positions.
- Month rows remain in calendar order, and new months are included automatically.
- `Grand Total` is retained in the extracted data for reconciliation and displayed as the final table row.

## Amount Table

The existing `Monthly Performance Table` remains in Section 3 and keeps its current table-card, toolbar, CSV export, colors, and responsive behavior. It displays every workbook field:

- Month
- New Premiums 2025
- Renewal Premiums 2025
- Other Policies 2025
- New Premiums 2026
- Renewal Premiums 2026
- Other Policies 2026
- 2025 Total
- 2026 Total
- Target
- Target Achievement %
- 2025 vs 2026 YoY
- Motor Premiums 2026
- Non-Motor Premiums 2026
- Motor Premiums 2025
- Non-Motor Premiums 2025
- Pending Finance

Premium and variance amounts use the report's existing EGP formatting. Percentages use the existing percentage formatter. The current Section 3 charts continue to consume the same centralized monthly amount records and are not redesigned.

## Count Table

A second full-width table card is added immediately after the amount table and titled `Monthly Policy Count Performance Table`. It uses the same styling and CSV export behavior and displays every workbook field:

- Month
- New Policies 2025
- Renewal Policies 2025
- Other Policies 2025
- New Policies 2026
- Renewal Policies 2026
- Other Policies 2026
- 2025 Total
- 2026 Total
- YoY Count Difference
- Motor Policies 2026
- Non-Motor Policies 2026
- Motor Policies 2025
- Non-Motor Policies 2025
- Motor Average Rate 2026
- Motor Average Rate 2025

Policy values render as whole-number counts, and average rates render as percentages. No count chart is added.

## Layout And Printing

- Both wide tables remain full-width and horizontally scrollable on screen.
- Existing table styling is reused; no report sections, charts, KPI cards, or colors are redesigned.
- Print rules keep each table card together where possible and fit wide content using the report's existing landscape print behavior.
- Web-only CSV buttons remain hidden in PDF output.

## Validation

- Extraction tests verify the renamed amount block and all fields from both summaries.
- Reconciliation verifies that each summary's monthly values equal its workbook grand-total row for additive count and amount fields.
- Browser verification confirms both Section 3 tables render, include July and Grand Total, and expose the expected headers.
- Existing report generation and JavaScript syntax checks must continue to pass.

