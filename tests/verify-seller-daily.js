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
    for (const title of ["MVP Seller - Overall", "MVP Seller - Non-Motor", "MVP Seller - Motor", "MVP Seller - This Month"]) {
      assert.match(mvpText, new RegExp(title, "i"));
    }
    assert.doesNotMatch(mvpText, /MVP Seller - Last Month/i);
    const thisMonthCard = page.locator("#sellerMvpGrid .kpi-card").nth(3);
    const expectedThisMonth = await page.evaluate(() => data.seller_mvps.this_month);
    assert.match(await thisMonthCard.innerText(), new RegExp(expectedThisMonth.seller, "i"));
    assert.match(await thisMonthCard.innerText(), new RegExp(`${expectedThisMonth.month} approved premium`, "i"));
    const sellerSpacing = await page.evaluate(() => {
      const mvpGrid = document.getElementById("sellerMvpGrid");
      const cardsBottom = Math.max(...Array.from(mvpGrid.children).map((card) => card.getBoundingClientRect().bottom));
      const chartTop = mvpGrid.nextElementSibling.getBoundingClientRect().top;
      return {
        paddingBottom: getComputedStyle(mvpGrid).paddingBottom,
        visibleGap: chartTop - cardsBottom,
      };
    });
    assert.equal(sellerSpacing.paddingBottom, "24px");
    assert.ok(sellerSpacing.visibleGap >= 23, `Expected at least 23px visible gap, received ${sellerSpacing.visibleGap}px`);

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

    const sellerMixOrder = await page.evaluate(() => {
      const chart = Chart.getChart("sellerMix");
      const expected = data.sellers.slice().sort((a, b) => Number(b.premium_2026) - Number(a.premium_2026)).slice(0, 12);
      return {
        labels: chart.data.labels,
        expectedLabels: expected.map((row) => shortLabel(row.seller, 18)),
        totals: chart.data.datasets[0].data.map((value, index) => Number(value) + Number(chart.data.datasets[1].data[index])),
      };
    });
    assert.deepEqual(sellerMixOrder.labels, sellerMixOrder.expectedLabels);
    assert.deepEqual(sellerMixOrder.totals, sellerMixOrder.totals.slice().sort((a, b) => b - a));

    assert.ok(await page.locator("#sellerTable > tbody > tr:not(.child-row)").count() <= 20);
    assert.equal(await page.locator("#sellerTable > tbody > tr.child-row").count(), 0);
    const sellerHeaders = await page.locator("#sellerTable thead th").allTextContents();
    assert.ok(sellerHeaders.includes("New Policies 2026"));
    assert.ok(sellerHeaders.includes("Renewal Policies 2026"));
    const sellerWithMonthlyDetail = await page.evaluate(() => data.sellers
      .slice(0, 20)
      .findIndex((seller) => data.seller_monthly.some((row) => row.seller === seller.seller)));
    assert.ok(sellerWithMonthlyDetail >= 0, "Expected at least one displayed seller with monthly detail");
    await page.locator("#sellerTable .row-toggle").first().click();
    assert.equal(await page.locator("#sellerTable > tbody > tr.child-row").count(), 1);
    const firstSellerMonths = await page.evaluate(() => {
      const seller = data.sellers[0].seller;
      return data.seller_monthly.filter((row) => row.seller === seller).map((row) => row.month);
    });
    const childText = await page.locator("#sellerTable > tbody > tr.child-row").innerText();
    if (firstSellerMonths.length) firstSellerMonths.forEach((month) => assert.match(childText, new RegExp(month, "i")));
    else {
      assert.match(childText, /No monthly seller detail is available/i);
      await page.locator("#sellerTable .row-toggle").first().click();
    }
    if (sellerWithMonthlyDetail !== 0) await page.locator("#sellerTable .row-toggle").nth(sellerWithMonthlyDetail).click();
    const displayedSellerMonths = await page
      .locator("#sellerTable > tbody > tr.child-row .nested-table tbody tr td:first-child")
      .allTextContents();
    const expectedSellerMonths = await page.evaluate(() => {
      const seller = data.sellers
        .slice(0, 20)
        .find((item) => data.seller_monthly.some((row) => row.seller === item.seller)).seller;
      return data.seller_monthly
        .filter((row) => row.seller === seller)
        .map((row) => row.month)
        .sort((a, b) => MONTHS.indexOf(a) - MONTHS.indexOf(b));
    });
    assert.deepEqual(displayedSellerMonths, expectedSellerMonths);
    const nestedHeaders = await page.locator("#sellerTable > tbody > tr.child-row .nested-table thead th").allTextContents();
    assert.ok(nestedHeaders.includes("New Policies 2026"));
    assert.ok(nestedHeaders.includes("Renewal Policies 2026"));
    const firstMonthlyPolicyCounts = await page.locator("#sellerTable > tbody > tr.child-row .nested-table tbody tr").first().locator("td").evaluateAll((cells) => ({
      newPolicies: cells[7].textContent,
      renewalPolicies: cells[8].textContent,
    }));
    const expectedFirstMonthlyPolicyCounts = await page.evaluate(() => {
      const seller = window.REPORT_DATA.sellers
        .slice(0, 20)
        .find((item) => window.REPORT_DATA.seller_monthly.some((row) => row.seller === item.seller)).seller;
      const row = window.REPORT_DATA.seller_monthly
        .filter((item) => item.seller === seller)
        .sort((a, b) => MONTHS.indexOf(a.month) - MONTHS.indexOf(b.month))[0];
      const format = (number) => number === null || number === undefined
        ? "N/A"
        : new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(number);
      return {
        newPolicies: format(row.new_policies),
        renewalPolicies: format(row.renewal_policies),
      };
    });
    assert.deepEqual(firstMonthlyPolicyCounts, expectedFirstMonthlyPolicyCounts);

    assert.equal(await page.locator("#renewals, #renewalStrip, #renewalLine, #renewalFunnel").count(), 0);
    assert.equal(await page.locator("#branchesPerDay").count(), 1);
    assert.equal(
      await page.getByRole("heading", { name: "Daily Approved and Pending Premiums", exact: true }).count(),
      1
    );
    const thisMonth = await page.evaluate(() => data.branches_per_day_this_month.month);
    assert.match(await page.locator("#branchesPerDay").innerText(), new RegExp(thisMonth, "i"));
    assert.equal(await page.locator('nav a[href="#branchesPerDay"]').count(), 1);
    const dailyChart = await page.evaluate(() => {
      const chart = Chart.getChart("branchesPerDayChart");
      const dailyRows = window.REPORT_DATA.branches_per_day_this_month.daily_rows;
      return {
        labels: chart.data.labels,
        sourceLabels: dailyRows.map((row) => row.label),
        datasetLabels: chart.data.datasets.map((item) => item.label),
        values: chart.data.datasets.map((item) => item.data),
        expectedValues: [
          dailyRows.map((row) => row.premium_2026),
          dailyRows.map((row) => row.pending_operation_paid),
          dailyRows.map((row) => row.pending_not_paid),
          dailyRows.map((row) => row.pending_finance),
        ],
        legendVisible: chart.options.plugins.legend.display,
        stackedX: Boolean(chart.options.scales.x.stacked),
        stackedY: Boolean(chart.options.scales.y.stacked),
      };
    });
    assert.deepEqual(dailyChart.labels, dailyChart.sourceLabels);
    assert.deepEqual(dailyChart.datasetLabels, [
      "Approved Premium", "Pending Operation Paid", "Pending Not Paid Yet", "Pending Finance",
    ]);
    assert.deepEqual(dailyChart.values, dailyChart.expectedValues);
    assert.equal(dailyChart.legendVisible, true);
    assert.equal(dailyChart.stackedX, false);
    assert.equal(dailyChart.stackedY, false);

    assert.equal(await page.locator("#kpiGrid .kpi-card").filter({ hasText: "Motor Renewal Rate" }).count(), 0);
    assert.equal(await page.getByRole("heading", { name: "Status Mix by Year", exact: true }).count(), 0);
    assert.equal(await page.locator("#statusStacked, #mixInterpretation").count(), 0);
    assert.equal(await page.evaluate(() => Chart.getChart("statusStacked") === undefined), true);
    assert.deepEqual(pageErrors, []);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
