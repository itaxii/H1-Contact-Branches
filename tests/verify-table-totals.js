const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

const root = path.resolve(__dirname, "..");
const candidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

const expectedAmountHeaders = [
  "Month",
  "2026 Total",
  "Target",
  "Achievement %",
  "2025 Total",
  "2025 vs 2026 YoY",
  "New Premiums 2026",
  "Renewal Premiums 2026",
  "Other Policies 2026",
  "Motor Premiums 2026",
  "Non-Motor Premiums 2026",
  "Pending Finance",
  "New Premiums 2025",
  "Renewal Premiums 2025",
  "Other Policies 2025",
  "Motor Premiums 2025",
  "Non-Motor Premiums 2025",
];

const expectedCountHeaders = [
  "Month",
  "2026 Total",
  "YoY Count Difference",
  "2025 Total",
  "New Policies 2026",
  "Renewal Policies 2026",
  "Other Policies 2026",
  "Motor Policies 2026",
  "Non-Motor Policies 2026",
  "Motor Average Rate 2026",
  "New Policies 2025",
  "Renewal Policies 2025",
  "Other Policies 2025",
  "Motor Policies 2025",
  "Non-Motor Policies 2025",
  "Motor Average Rate 2025",
];

async function main() {
  const executablePath = candidates.find((candidate) => fs.existsSync(candidate));
  if (!executablePath) throw new Error("Chrome or Edge executable was not found.");

  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
    await page.addInitScript(() => sessionStorage.setItem("contactReportAuthed", "true"));
    await page.goto(`file://${path.join(root, "index.html").replace(/\\/g, "/")}`, { waitUntil: "load" });
    await page.waitForFunction(() => document.querySelector("#branchTable tbody tr"));

    assert.deepEqual(await page.locator("#monthlyTable thead th").allTextContents(), expectedAmountHeaders);
    assert.deepEqual(await page.locator("#monthlyCountTable thead th").allTextContents(), expectedCountHeaders);

    for (const id of ["monthlyTable", "monthlyCountTable", "branchTable", "sellerTable", "insurerTable", "lobTable"]) {
      assert.equal(await page.locator(`#${id} tfoot tr`).count(), 1, `${id} needs one total row`);
      assert.match(await page.locator(`#${id} tfoot`).innerText(), /Grand Total/);
    }

    await page.locator("#branchTable thead th").nth(2).click();
    assert.equal(await page.locator("#branchTable tfoot tr").count(), 1);
    await page.locator("#branchSearch").fill("Nasr");
    assert.equal(await page.locator("#branchTable tfoot tr").count(), 1);
    await page.locator("#branchSearch").fill("");

    await page.locator("#branchTable .row-toggle").first().click();
    assert.equal(await page.locator("#branchTable .nested-table tfoot tr").count(), 1);
    assert.match(await page.locator("#branchTable .nested-table tfoot").innerText(), /Grand Total/);

    const exportedRows = await page.evaluate(() => window.dashboardTables.rowsForExport("monthlyTable"));
    assert.equal(exportedRows.at(-1).month, "Grand Total");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
