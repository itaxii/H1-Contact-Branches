# Remove Status Mix and Renewal Card Design

## Scope

- Remove the `Status Mix by Year` panel from Section 4.
- Remove the `Motor Renewal Rate` card from the KPI grid.
- Remove only the JavaScript rendering paths made unused by those two removals.
- Preserve all other sections, cards, charts, data, calculations, and styling.

## Verification

- Assert that neither removed title appears in the rendered dashboard.
- Assert that the `statusStacked` canvas and chart instance do not exist.
- Run the complete Python and browser test suites.

