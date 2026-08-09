# Remove Status Mix and Renewal Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Status Mix by Year chart and Motor Renewal Rate card without changing any other dashboard content.

**Architecture:** Delete the two presentation elements at their existing HTML and JavaScript ownership points, then lock the removal with a browser regression check.

**Tech Stack:** Vanilla JavaScript, HTML, Playwright Core.

## Global Constraints

- Preserve every unrelated card, chart, section, calculation, style, and dataset.
- Do not change the latest generated workbook data.

---

### Task 1: Remove Both Presentation Elements

**Files:**
- Modify: `tests/verify-seller-daily.js`
- Modify: `index.html`
- Modify: `app.js`

**Interfaces:**
- Consumes: the existing dashboard DOM and `renderKpis` / `renderMix` entry points.
- Produces: the same dashboard without `Motor Renewal Rate`, `Status Mix by Year`, `statusStacked`, or `mixInterpretation`.

- [ ] **Step 1: Change the browser assertions to require both elements to be absent**

```javascript
assert.equal(await page.locator("#kpiGrid .kpi-card").filter({ hasText: "Motor Renewal Rate" }).count(), 0);
assert.equal(await page.getByRole("heading", { name: "Status Mix by Year", exact: true }).count(), 0);
assert.equal(await page.locator("#statusStacked, #mixInterpretation").count(), 0);
assert.equal(await page.evaluate(() => Chart.getChart("statusStacked") === undefined), true);
```

- [ ] **Step 2: Run the browser test and verify it fails**

Run: `node tests/verify-seller-daily.js`

Expected: FAIL because both presentation elements still exist.

- [ ] **Step 3: Remove the chart panel and unused rendering code**

Delete the `Status Mix by Year` article from `index.html`, remove `statusStacked` from `CHART_DESCRIPTIONS`, and remove the status aggregation, chart construction, and `mixInterpretation` assignment from `renderMix`.

- [ ] **Step 4: Remove the KPI card and unused variables**

Delete `renewalTotal`, `renewalRate`, and the `Motor Renewal Rate` `kpiCard` entry from `renderKpis`.

- [ ] **Step 5: Run focused and complete verification**

Run: `node tests/verify-seller-daily.js`

Expected: PASS.

Run: `npm test`

Expected: all Python and browser checks PASS.

- [ ] **Step 6: Commit and update the existing PR branch**

```bash
git add app.js index.html tests/verify-seller-daily.js docs/plans/2026-08-09-remove-status-renewal-card-design.md docs/superpowers/plans/2026-08-09-remove-status-renewal-card.md
git commit -m "ui: remove status mix and renewal card"
git push origin fix/trigger-pages
```
