# Contact Branches Performance - YTD 2026

Single-page interactive executive dashboard generated from `H1 Contact Branches v2.xlsx`.

## Run

Open `index.html` directly in a browser.

Optional local server:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000` from inside this folder.

## Regenerate Data

```powershell
python analysis.py
```

The script reads the Excel workbook, cleans formatted currency and percentage values, excludes total rows from rankings, validates totals, and writes:

- `data/report-data.json`
- `data/report-data.js`

The JavaScript dashboard uses `report-data.js` so it can work when `index.html` is opened directly.

## Reconciliation

Review `data/validation-summary.json` for current totals, blocking failures, and source reconciliation warnings. Source differences are retained as warnings and are never hidden or adjusted to force agreement.

## Validated Report Generation

Run `npm test` to validate extraction, formulas, display rounding, and browser rendering.

Run `npm run pdf` to regenerate data, enforce all blocking checks, wait for chart rendering, and replace the PDF only after the temporary artifact passes completeness checks.

Review `data/rounding-changes.json` for every corrected displayed percentage after each workbook update.

## Data Quality Notes

- Seller data is limited to the workbook's Top 20 sellers section.
- Pending amounts are reported separately and are not added to approved premium.
- Renewal analysis is based on aggregated monthly workbook counts.
- Workbook labels and spelling are retained as supplied.
