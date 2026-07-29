# Precision, Rounding, and Validation Design

## Objective

Eliminate percentage and numerical rounding inconsistencies in the Contact Branches dashboard and generated PDF without changing the source workbook, business definitions, report structure, or visual design. All derived values will be calculated from raw numeric inputs, retained at full precision, and rounded only for final display.

## Scope

This change applies to every displayed numeric value in:

- KPI cards
- charts and chart labels
- detailed and summary tables
- executive-summary text
- captions, commentary, and recommendations
- the generated PDF

The source Excel workbook remains read-only. Existing business logic and source amounts/counts remain unchanged.

## Canonical Metric Layer

Python report generation will own a centralized derived-metric layer. Each calculated percentage will be represented once with:

- metric identifier and display label
- raw numerator
- raw denominator
- unrounded result
- display precision
- expected displayed value
- locations that consume the metric

Cards, tables, chart datasets, narratives, captions, and recommendations will consume the same canonical raw result instead of recalculating it independently.

When raw numerator and denominator values are available, workbook percentage cells will not be used as calculation inputs. A workbook percentage may be retained only as source metadata for diagnostics.

## Calculation Rules

All calculations will use the original parsed numeric amounts and counts:

- Renewal Rate = Renewed Policies / Policies Up for Renewal * 100
- Target Achievement = Actual Premium / Target Premium * 100
- YoY Change = (Current Value - Previous Value) / Previous Value * 100
- Contribution = Item Premium / Total Premium * 100
- Mix = Component Premium / Total Premium * 100

The internal representation may use a ratio such as `0.392638...` or a percent such as `39.2638...`, but the representation must be consistent within the metric layer and converted only at the formatting boundary.

Undefined percentages remain undefined. A missing or zero prior-period denominator must not be converted into `0.0%`; it will retain the report's existing `N/A`/classification behavior. In particular, New Base and No Current Production records must not be treated as ordinary YoY percentages.

Raw values remain unrounded through every calculation chain. No formatted string, compact K/M value, chart label, previously rounded percentage, or previously rounded intermediate result may be used as an input.

## Excel-Compatible Display Rounding

Python will use `Decimal` with `ROUND_HALF_UP` at the final formatting boundary. Float conversion must use a decimal-safe path, such as converting through a string, so binary floating-point artifacts do not change the displayed result.

Display rules:

- Percentages: one decimal place
- Motor Average Rate: two decimal places, as explicitly requested
- Detailed-table currency: full values with thousand separators
- Chart and KPI currency: K/M notation with one decimal place
- Counts: whole numbers with no decimal places

JavaScript formatting will match the Python output. Where browser support permits, `Intl.NumberFormat` will use `roundingMode: "halfExpand"`; otherwise a small decimal-safe half-up formatter will provide equivalent output. JavaScript must not independently recompute canonical percentages.

The renewal example `64 / 163 * 100 = 39.263803...` must display as `39.3%`.

## Data Flow

1. Parse raw amounts and counts from the workbook.
2. Build reusable canonical metrics from raw inputs.
3. Run calculation and reconciliation validation.
4. Serialize raw metric results plus display metadata into report data.
5. Render all report surfaces from those shared results.
6. Validate rendered percentage text against canonical expected display values.
7. Generate the PDF only after all blocking validations pass and charts finish rendering.
8. Write a validation summary and rounding-change log for review.

## Validation

### Percentage Validation

Every calculated percentage will be independently recalculated from its registered raw numerator and denominator. Validation will compare:

- canonical unrounded result
- independently recalculated result
- expected `ROUND_HALF_UP` display text
- displayed report value

A mismatch in calculation or displayed rounding is a blocking error. PDF generation must stop with a clear message containing the metric name, numerator, denominator, expected value, actual value, and difference where applicable.

### Reconciliation Checks

The existing reconciliation suite will continue and will cover:

- monthly totals versus overall total
- grand totals versus monthly values
- branch totals versus overall total
- line-of-business totals versus overall total
- insurer totals versus overall total
- pending categories versus total pending
- renewal counts
- policy-type premiums versus approved gross premium
- contribution and mix shares versus 100%

Normal final-display percentage rounding differences are allowed when displayed component percentages sum near 100%. Raw shares must reconcile independently; rounded values must never be manually adjusted to force a displayed total.

Known source-level EGP 1-2 differences among monthly, branch, and insurer summaries will remain visible in the validation log. They will not be hidden, altered, or forced to match. These source reconciliation warnings do not block PDF generation unless an existing business threshold is exceeded or the difference is introduced by report calculation logic.

## PDF Generation Gate

The PDF command will run the pipeline in this order:

1. regenerate report data from the current workbook
2. run raw calculation validations
3. load the report and wait for all chart-render completion signals
4. run rendered-display validations in the browser
5. create the PDF
6. run final PDF completeness checks

Any blocking calculation or display validation failure will terminate the command with a nonzero exit code before replacing the canonical PDF.

## Audit Outputs

Each generation will produce a machine-readable validation result and a human-readable summary containing:

- passed checks
- blocking failures
- non-blocking source reconciliation warnings
- metric name, expected value, actual value, and difference for failures

The implementation will also generate a before/after rounding-change log by comparing the previous displayed values with corrected canonical displays. This log will support the requested final list of every metric whose displayed value changed.

## Expected Corrected Displays

Initial analysis identified likely corrections in KPI YoY values, July target achievement, one branch YoY display, and multiple line-of-business target-achievement values. The final list will be generated from the completed pipeline rather than hard-coded from the audit. Undefined YoY values will remain undefined instead of being reported as zero.

## Testing

Tests will cover:

- Excel-style half-up rounding boundaries
- one-decimal percentage formatting
- two-decimal Motor Average Rate formatting
- K/M currency formatting
- integer count formatting
- raw renewal, target-achievement, YoY, contribution, and mix formulas
- zero and missing denominator behavior
- canonical metric reuse in serialized report data
- blocking percentage validation failures
- non-blocking source reconciliation warnings
- rendered text parity between HTML and PDF inputs
- successful complete PDF generation after all validations pass

The explicit renewal regression test will assert that 64 renewed policies out of 163 policies up for renewal displays as `39.3%`.

## Non-Goals

- Modifying workbook values or formulas
- Changing metric definitions or business logic
- Redesigning report pages, charts, tables, cards, colors, or typography
- Manually modifying rounded components to force totals
- Treating missing prior-period production as zero growth

## Acceptance Criteria

- Every derived metric uses raw numeric inputs.
- Intermediate calculation results remain unrounded.
- Rounding occurs once, at display time, using Excel-compatible half-up behavior.
- Percentages display with one decimal, except Motor Average Rate with two decimals.
- Detailed currency, compact currency, and counts follow the agreed formats.
- The same canonical result is reused across all report surfaces.
- Every displayed calculated percentage passes independent validation.
- PDF generation stops on calculation or display mismatch.
- Reconciliation warnings are logged without modifying source totals.
- A new complete PDF is generated successfully.
- The final delivery lists changed files, reconciliation results, data-quality issues, and every corrected displayed metric.
