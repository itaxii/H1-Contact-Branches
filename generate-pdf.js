const path = require("path");
const { chromium } = require("playwright-core");

const root = __dirname;
const output = path.join(root, "contact-branches-report-sample.pdf");
const chromeCandidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

async function fileExists(file) {
  const fs = require("fs/promises");
  try {
    await fs.access(file);
    return true;
  } catch {
    return false;
  }
}

async function findBrowser() {
  for (const candidate of chromeCandidates) {
    if (await fileExists(candidate)) return candidate;
  }
  throw new Error("Chrome or Edge executable was not found.");
}

(async () => {
  const executablePath = await findBrowser();
  const browser = await chromium.launch({
    executablePath,
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1100 },
    deviceScaleFactor: 1,
  });
  await page.addInitScript(() => {
    sessionStorage.setItem("contactReportAuthed", "true");
  });

  await page.goto(`file://${path.join(root, "index.html").replace(/\\/g, "/")}?pdf=1`, {
    waitUntil: "load",
  });
  await page.emulateMedia({ media: "print" });
  await page.waitForFunction(() => window.Chart && document.querySelectorAll("canvas").length >= 20);
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    if (typeof window.prepareDashboardForPrint === "function") window.prepareDashboardForPrint();
  });
  await page.waitForTimeout(750);
  await page.waitForFunction(() =>
    [...document.querySelectorAll("canvas")].every((canvas) => canvas.width > 0 && canvas.height > 0)
  );

  await page.pdf({
    path: output,
    format: "A4",
    landscape: true,
    printBackground: true,
    preferCSSPageSize: true,
    margin: {
      top: "7mm",
      right: "7mm",
      bottom: "7mm",
      left: "7mm",
    },
    displayHeaderFooter: false,
  });

  await browser.close();
  console.log(output);
})();
