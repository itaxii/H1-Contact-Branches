# Policy Count Columns Design

## Scope

Update the dashboard using `8-9.xlsx` as the latest source workbook. Preserve the existing report structure, styling, charts, calculations, and interactions.

## Insurance Company Data

- Locate the `2025 vs 2026 By Insurance Company Summary` table by its title and normalized header names.
- Read `New Policies 2026`, `Renewal Policies 2026`, and `Other Policies 2026` as raw whole-number counts.
- Carry the three fields through insurer records and the insurer grand-total record.
- Display the fields in the existing Insurance Company table without changing its current sorting behavior.

Header-name detection is preferred over fixed Excel coordinates so future monthly workbook updates remain compatible when columns move.

## Seller Data

- Reuse the existing `new_policies` and `renewal_policies` fields already extracted from the seller source table.
- Display both fields in each main seller row.
- Display both fields in each seller's expanded monthly detail rows.
- Include the fields in seller grand totals using the existing raw-value aggregation path.

## Presentation

- Label the columns `New Policies 2026` and `Renewal Policies 2026`.
- Label the additional insurer column `Other Policies 2026`.
- Format all policy counts as integers with thousands separators and no decimals.
- Retain the existing responsive table behavior and horizontal scrolling.

## Validation

- Add parser tests proving insurer counts are mapped from header names rather than hard-coded positions.
- Add tests proving seller summary counts equal the sum of seller monthly rows.
- Add browser verification for the new insurer and seller headers and displayed values.
- Run the complete Python and browser verification suites against data generated from `8-9.xlsx`.

## Non-Goals

- No chart, KPI, layout, color, typography, sorting, or business-logic changes.
- No recalculation or modification of workbook values.
- No GitHub publication unless requested after local verification.
