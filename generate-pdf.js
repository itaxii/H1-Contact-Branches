const path = require("path");
const fs = require("fs");
const fsp = require("fs/promises");
const { spawnSync } = require("child_process");
const { chromium } = require("playwright-core");

const root = __dirname;
const output = path.join(root, "contact-branches-report.pdf");
const temporaryOutput = path.join(root, "contact-branches-report.tmp.pdf");
const chromeCandidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

async function fileExists(file) {
  try {
    await fsp.access(file);
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

function runCommand(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit", ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}.`);
  }
}

async function main() {
  runCommand("python", ["analysis.py"]);
  const validation = JSON.parse(await fsp.readFile(path.join(root, "data", "validation-summary.json"), "utf8"));
  if (validation.status === "blocked") {
    throw new Error(`Data validation blocked PDF generation: ${JSON.stringify(validation.blocking_failures)}`);
  }

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

  try {
    await page.goto(`file://${path.join(root, "index.html").replace(/\\/g, "/")}?pdf=1`, {
      waitUntil: "load",
    });
    await page.emulateMedia({ media: "print" });
    await page.waitForFunction(() => window.Chart && document.querySelectorAll("canvas").length >= 20);
    await page.evaluate(async () => {
      if (document.fonts?.ready) await document.fonts.ready;
      if (typeof window.prepareDashboardForPrint === "function") window.prepareDashboardForPrint();
    });
    await page.waitForFunction(() => window.dashboardChartsReady === true);
    await page.waitForFunction(() =>
      [...document.querySelectorAll("canvas")].every((canvas) => canvas.width > 0 && canvas.height > 0)
    );

    const renderedValidation = await page.evaluate(() => window.validateDashboardMetrics());
    if (renderedValidation.status !== "pass") {
      throw new Error(`Rendered percentage validation failed: ${JSON.stringify(renderedValidation.failures)}`);
    }
    const juneRenewalDisplay = await page.evaluate(
      () => window.REPORT_DATA.calculated_metrics["renewal.June.rate"].display
    );
    if (juneRenewalDisplay !== "39.3%") {
      throw new Error(`June renewal display expected 39.3%, received ${juneRenewalDisplay}.`);
    }

    await page.pdf({
      path: temporaryOutput,
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
  } finally {
    await browser.close();
  }

  runCommand("python", ["tests/verify-pdf.py"], {
    env: { ...process.env, PDF_PATH: temporaryOutput },
  });
  await fsp.rename(temporaryOutput, output);
  console.log(output);
}

main().catch(async (error) => {
  if (fs.existsSync(temporaryOutput)) await fsp.rm(temporaryOutput, { force: true });
  console.error(error);
  process.exitCode = 1;
});
