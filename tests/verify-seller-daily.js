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

async function main() {
  const executablePath = candidates.find((candidate) => fs.existsSync(candidate));
  if (!executablePath) throw new Error("Chrome or Edge executable was not found.");

  const browser = await chromium.launch({ executablePath, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    await page.addInitScript(() => sessionStorage.setItem("contactReportAuthed", "true"));
    await page.goto(`file://${path.join(root, "index.html").replace(/\\/g, "/")}`, { waitUntil: "load" });

    assert.equal(await page.locator("#sellerMvpGrid .kpi-card").count(), 4);
    const mvpText = await page.locator("#sellerMvpGrid").innerText();
    for (const title of ["MVP Seller - Overall", "MVP Seller - Non-Motor", "MVP Seller - Motor", "MVP Seller - Last Month"]) {
      assert.match(mvpText, new RegExp(title, "i"));
    }

    const chartChecks = await page.evaluate(() => {
      const expected = (metric) => data.sellers
        .filter((row) => Number(row[metric]) > 0)
        .sort((a, b) => Number(b[metric]) - Number(a[metric]))
        .slice(0, 10);
      const newChart = Chart.getChart("sellerNewTop");
      const renewalChart = Chart.getChart("sellerRenewalTop");
      return {
        newCount: newChart.data.labels.length,
        renewalCount: renewalChart.data.labels.length,
        newValues: newChart.data.datasets[0].data,
        renewalValues: renewalChart.data.datasets[0].data,
        expectedNew: expected("new_premium").map((row) => row.new_premium),
        expectedRenewal: expected("renewal_premium").map((row) => row.renewal_premium),
      };
    });
    assert.ok(chartChecks.newCount <= 10);
    assert.ok(chartChecks.renewalCount <= 10);
    assert.deepEqual(chartChecks.newValues, chartChecks.expectedNew);
    assert.deepEqual(chartChecks.renewalValues, chartChecks.expectedRenewal);

    assert.ok(await page.locator("#sellerTable > tbody > tr:not(.child-row)").count() <= 20);
    assert.equal(await page.locator("#sellerTable > tbody > tr.child-row").count(), 0);
    await page.locator("#sellerTable .row-toggle").first().click();
    assert.equal(await page.locator("#sellerTable > tbody > tr.child-row").count(), 1);
    assert.match(await page.locator("#sellerTable > tbody > tr.child-row").innerText(), /August/);

    assert.equal(await page.locator("#renewals, #renewalStrip, #renewalLine, #renewalFunnel").count(), 0);
    assert.equal(await page.locator("#branchesPerDay").count(), 1);
    assert.match(await page.locator("#branchesPerDay").innerText(), /Branches Per Day - Last Month/);
    assert.match(await page.locator("#branchesPerDay").innerText(), /August/);
    assert.equal(await page.locator('nav a[href="#branchesPerDay"]').count(), 1);
    const dailyCounts = await page.evaluate(() => ({
      chart: Chart.getChart("branchesPerDayChart").data.labels.length,
      source: data.branches_per_day_last_month.rows.length,
    }));
    assert.equal(dailyCounts.chart, dailyCounts.source);

    const renewalCard = page.locator("#kpiGrid .kpi-card").filter({ hasText: "Motor Renewal Rate" });
    assert.equal(await renewalCard.count(), 1);
    assert.match(await renewalCard.innerText(), /N\/A/);
    assert.deepEqual(pageErrors, []);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
