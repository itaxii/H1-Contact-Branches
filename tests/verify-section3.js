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
    await page.waitForFunction(() => window.Chart && document.querySelector("#monthlyTable tbody"));

    assert.equal(await page.locator("#monthlyTable thead th").count(), 17);
    assert.equal(await page.locator("#monthlyCountTable thead th").count(), 16);
    assert.match(await page.locator("#monthlyTable").innerText(), /Grand Total/);
    assert.match(await page.locator("#monthlyTable").innerText(), /Pending Finance/);
    assert.match(await page.locator("#monthlyCountTable").innerText(), /Motor Average Rate 2026/);
    assert.match(await page.locator("#monthlyCountTable").innerText(), /July/);

    await page.emulateMedia({ media: "print" });
    const dataCellWhiteSpace = await page.locator("#monthlyTable tbody td").first().evaluate((cell) => getComputedStyle(cell).whiteSpace);
    assert.equal(dataCellWhiteSpace, "nowrap");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
