# Full PDF Download Design

## Goal

Replace the dashboard's unreliable in-app-browser print action with a direct download of the complete generated report PDF.

## Confirmed Cause

The existing Playwright PDF contains 25 pages and includes Sections 1 through 11. The same report also passes the browser rendering checks. Missing pages occur in the embedded browser's native print dialog, outside the dashboard's print CSS and content generation.

## User Experience

- Change the existing hero action label from `Print / Save as PDF` to `Download Full PDF`.
- Keep the same button position, styling, colors, and report layout.
- Clicking the action downloads `contact-branches-report.pdf` directly.
- Do not open the browser print dialog from this action.
- CSV downloads and all other dashboard controls remain unchanged.

## PDF Artifact

- `generate-pdf.js` writes the canonical artifact as `contact-branches-report.pdf`.
- The PDF is committed with the static dashboard so GitHub Pages and other static hosts can serve it.
- The existing A4 landscape format, print colors, chart labels, page margins, and page-break rules remain unchanged.
- The workbook refresh workflow is `python analysis.py` followed by `npm run pdf`, ensuring the downloadable PDF matches the generated dashboard data.

## Failure Handling

- The download control uses a normal static link so it works without application JavaScript after the page loads.
- Publishing validation fails if the PDF file is absent or if the link does not resolve with HTTP 200.
- The existing browser print preparation functions remain available for automated PDF generation and manual browser printing, but the hero action no longer depends on the native print dialog.

## Verification

- Browser test confirms the action is labeled `Download Full PDF`, references `contact-branches-report.pdf`, and has the `download` attribute.
- HTTP verification confirms the PDF URL returns 200.
- PDF text verification confirms 25 pages and Sections 1 through 11.
- Existing Python, JavaScript, Section 3, and PDF generation checks continue to pass.

