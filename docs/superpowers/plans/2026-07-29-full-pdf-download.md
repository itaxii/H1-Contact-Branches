# Full PDF Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the embedded browser print action with a reliable static download of the complete 25-page dashboard PDF.

**Architecture:** Playwright continues to render the existing dashboard and print CSS, but writes one canonical `contact-branches-report.pdf` artifact. The hero control becomes a normal download link to that file, allowing GitHub Pages and local static servers to deliver the complete report without relying on the browser print dialog.

**Tech Stack:** Static HTML, vanilla JavaScript, Playwright Core, Python/PyMuPDF verification, GitHub Pages compatible static assets.

## Global Constraints

- Keep the current dashboard structure, report content, charts, tables, KPI cards, colors, print CSS, and PDF page settings unchanged.
- Keep the download action in the existing hero action position and style.
- The downloadable artifact must be named `contact-branches-report.pdf`.
- The complete artifact must include Sections 1 through 11.

---

### Task 1: Canonical Full PDF Download

**Files:**
- Modify: `.gitignore`
- Modify: `generate-pdf.js`
- Modify: `index.html:36`
- Modify: `app.js:907`
- Modify: `tests/verify-section3.js`
- Create: `tests/verify-pdf.py`
- Create: `contact-branches-report.pdf`

**Interfaces:**
- Produces static artifact: `contact-branches-report.pdf`
- Produces hero link: `#pdfDownload[href="contact-branches-report.pdf"][download]`
- Retains: `window.prepareDashboardForPrint()` for Playwright and manual browser printing.

- [ ] **Step 1: Write failing download and PDF contract tests**

Extend `tests/verify-section3.js`:

```javascript
const pdfDownload = page.locator("#pdfDownload");
assert.equal(await pdfDownload.innerText(), "Download Full PDF");
assert.equal(await pdfDownload.getAttribute("href"), "contact-branches-report.pdf");
assert.notEqual(await pdfDownload.getAttribute("download"), null);
```

Create `tests/verify-pdf.py`:

```python
import fitz

document = fitz.open("contact-branches-report.pdf")
text = "\n".join(page.get_text() for page in document).upper()
assert document.page_count == 25
for section in range(1, 12):
    assert f"SECTION {section}" in text
```

- [ ] **Step 2: Run tests and verify the new contract fails**

Run: `node tests/verify-section3.js`

Expected: FAIL because `#pdfDownload` does not exist.

Run: `python tests/verify-pdf.py`

Expected: FAIL because `contact-branches-report.pdf` does not exist.

- [ ] **Step 3: Implement the minimal download path**

Change `generate-pdf.js` output from `contact-branches-report-sample.pdf` to `contact-branches-report.pdf`. Replace the hero print button with:

```html
<a class="btn btn--light" id="pdfDownload" href="contact-branches-report.pdf" download>Download Full PDF</a>
```

Remove only the obsolete `printBtn` click registration from `registerActions()`; retain `beforeprint`, `afterprint`, `prepareForPrint`, and `restoreAfterPrint`. Add `!contact-branches-report.pdf` after `*.pdf` in `.gitignore`.

- [ ] **Step 4: Generate and verify the canonical PDF**

Run: `npm run pdf`

Run: `node tests/verify-section3.js`

Run: `python tests/verify-pdf.py`

Expected: PDF generation exits 0, browser test exits 0, and PDF verification confirms 25 pages with Sections 1–11.

- [ ] **Step 5: Verify static serving and regressions**

Run: `curl.exe -I http://127.0.0.1:8767/contact-branches-report.pdf`

Run: `python -m unittest discover -s tests -v`

Run: `node --check app.js`

Expected: PDF request returns HTTP 200, all Python tests pass, and JavaScript syntax check exits 0.

- [ ] **Step 6: Commit the feature**

```powershell
git add -- .gitignore generate-pdf.js index.html app.js tests/verify-section3.js tests/verify-pdf.py contact-branches-report.pdf
git commit -m "feat: add complete PDF download"
```

