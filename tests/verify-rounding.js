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
    await page.addInitScript(() => sessionStorage.setItem("contactReportAuthed", "true"));
    await page.goto(`file://${path.join(root, "index.html").replace(/\\/g, "/")}`, { waitUntil: "load" });
    await page.waitForFunction(() => window.dashboardFormatting);

    assert.equal(
      await page.evaluate(() => window.dashboardFormatting.formatPercent(64 / 163, 1)),
      "39.3%"
    );
    assert.equal(
      await page.evaluate(() => window.dashboardFormatting.formatPercent(0.01945, 2)),
      "1.95%"
    );

    const result = await page.evaluate(() => window.validateDashboardMetrics());
    assert.equal(result.status, "pass", JSON.stringify(result.failures, null, 2));
    assert.ok(result.checked > 1000, `Expected full metric catalog, received ${result.checked}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
