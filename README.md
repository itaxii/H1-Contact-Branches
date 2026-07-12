# Contact Branches Performance - H1 2026

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

Current generated checks:

- Overall approved gross premium: EGP 15,290,947
- Monthly 2026 sum difference: EGP 0
- Line of business 2026 sum difference: EGP 0
- Branch 2026 sum difference: EGP 2
- Insurer 2026 sum difference: EGP 3

The small branch and insurer differences are retained as reconciliation notes.

## Data Quality Notes

- Seller data is limited to the workbook's Top 20 sellers section.
- Pending amounts are reported separately and are not added to approved premium.
- Renewal analysis is based on aggregated monthly workbook counts.
- Workbook labels and spelling are retained as supplied.
