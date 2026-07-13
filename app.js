const data = window.REPORT_DATA;
const COLORS = {
  navy: "#16324F",
  blue: "#2563EB",
  green: "#16A34A",
  red: "#DC2626",
  orange: "#F59E0B",
  grey: "#6B7280",
  lightBlue: "#BFDBFE",
  lightGreen: "#BBF7D0",
  lightOrange: "#FED7AA",
};

const tables = {};
const charts = [];

function value(n) {
  return Number.isFinite(Number(n)) ? Number(n) : 0;
}

function fmtMoney(n, compact = true) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "N/A";
  const num = Number(n);
  const abs = Math.abs(num);
  const signOpen = num < 0 ? "(" : "";
  const signClose = num < 0 ? ")" : "";
  if (compact) {
    if (abs >= 1_000_000) return `${signOpen}EGP ${(abs / 1_000_000).toFixed(1)}M${signClose}`;
    if (abs >= 1_000) return `${signOpen}EGP ${(abs / 1_000).toFixed(1)}K${signClose}`;
  }
  return `${signOpen}${Math.round(abs).toLocaleString("en-US")}${signClose}`;
}

function fmtPct(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "N/A";
  return `${(Number(n) * 100).toFixed(1)}%`;
}

function fmtNumber(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "N/A";
  return Math.round(Number(n)).toLocaleString("en-US");
}

function statusClass(n, inverse = false) {
  if (n === null || n === undefined) return "warning";
  const positive = inverse ? Number(n) < 0 : Number(n) >= 0;
  return positive ? "positive" : "negative";
}

function shortLabel(label, max = 24) {
  return label.length > max ? `${label.slice(0, max - 1)}...` : label;
}

function formatPremiumRange(start, end) {
  const compact = (amount) => {
    if (amount === 0) return "0";
    if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1).replace(".0", "")}M`;
    return `${Math.round(amount / 1_000)}K`;
  };
  return `EGP ${compact(start)}–${compact(end)}`;
}

function byDesc(key) {
  return (a, b) => value(b[key]) - value(a[key]);
}

function byAsc(key) {
  return (a, b) => value(a[key]) - value(b[key]);
}

function chartDefaults() {
  Chart.defaults.font.family = "Inter, Segoe UI, Arial, sans-serif";
  Chart.defaults.color = COLORS.grey;
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.tooltip.callbacks.label = (context) => {
    const raw = context.raw;
    if (typeof raw === "object" && raw !== null) {
      return `${context.dataset.label}: ${fmtMoney(raw.y || raw.value || 0)}`;
    }
    if (String(context.dataset.label || "").includes("%")) return `${context.dataset.label}: ${fmtPct(raw)}`;
    return `${context.dataset.label}: ${fmtMoney(raw)}`;
  };
  Chart.register(staticValueLabels);
}

const staticValueLabels = {
  id: "staticValueLabels",
  afterDatasetsDraw(chart) {
    const pluginOptions = chart.options.plugins?.staticValueLabels || {};
    if (!pluginOptions.display && !document.body.classList.contains("pdf-mode")) return;
    if (chart.config.type === "bubble" || chart.config.type === "scatter") return;

    const ctx = chart.ctx;
    ctx.save();
    ctx.font = `700 ${pluginOptions.fontSize || 10}px Inter, Segoe UI, Arial, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    chart.data.datasets.forEach((dataset, datasetIndex) => {
      if (dataset.hidden) return;
      const meta = chart.getDatasetMeta(datasetIndex);
      if (meta.hidden) return;
      const isPercent = String(dataset.label || "").includes("%") || String(dataset.label || "").includes("Contribution");
      const isPolicy = String(dataset.label || "").includes("Policies");
      const isCount = pluginOptions.valueType === "number" || String(dataset.label || "").includes("Branches");
      const isDoughnut = chart.config.type === "doughnut";
      const isHorizontal = chart.options.indexAxis === "y";
      const visiblePoints = meta.data.length;

      meta.data.forEach((element, index) => {
        const raw = Array.isArray(dataset.data) ? dataset.data[index] : null;
        if (raw === null || raw === undefined || Number.isNaN(Number(raw))) return;
        if (Math.abs(Number(raw)) < 0.0001 && !pluginOptions.showZero) return;
        const label = isPercent ? fmtPct(raw) : isPolicy || isCount ? fmtNumber(raw) : fmtMoney(raw);
        const props = element.tooltipPosition();

        ctx.fillStyle = "#111827";
        if (isDoughnut) {
          if (visiblePoints > 4 && Math.abs(Number(raw)) / dataset.data.reduce((s, v) => s + Math.abs(value(v)), 0) < 0.06) return;
          ctx.fillStyle = "#ffffff";
          ctx.fillText(label, props.x, props.y);
          return;
        }

        if (chart.config.type === "line" || dataset.type === "line") {
          if (index % 2 === 1 && visiblePoints > 6) return;
          ctx.fillText(label, props.x, props.y - 12);
          return;
        }

        if (isHorizontal) {
          const labelX = Math.min(Math.max(props.x + 8, chart.chartArea.left + 6), chart.chartArea.right - 6);
          ctx.textAlign = labelX >= chart.chartArea.right - 8 ? "right" : "left";
          ctx.fillText(label, labelX, props.y);
          ctx.textAlign = "center";
          return;
        }

        ctx.fillText(label, props.x, props.y - 10);
      });
    });
    ctx.restore();
  },
};

function makeChart(id, config) {
  const el = document.getElementById(id);
  if (!el) return null;
  config.options = config.options || {};
  config.options.plugins = config.options.plugins || {};
  config.options.plugins.staticValueLabels = config.options.plugins.staticValueLabels || { display: false };
  const chart = new Chart(el, config);
  charts.push(chart);
  return chart;
}

function renderMeta() {
  document.getElementById("reportingPeriod").textContent = data.meta.reporting_period;
  document.getElementById("lastUpdated").textContent = `Last updated ${data.meta.last_updated}`;
  document.getElementById("sourceName").textContent = data.meta.source;
  document.getElementById("heroPremium").textContent = fmtMoney(data.totals.approved_gross_premium);
  document.getElementById("heroYoy").textContent = fmtPct(data.kpis["Approved Gross Premiums"].change_pct);
  document.getElementById("heroTarget").textContent = fmtPct(data.totals.target_achievement_pct);
  document.getElementById("heroHeadline").textContent =
    `Approved gross premium reached ${fmtMoney(data.totals.approved_gross_premium)} in H1 2026, down ${fmtPct(Math.abs(data.kpis["Approved Gross Premiums"].change_pct))} versus H1 2025 and at ${fmtPct(data.totals.target_achievement_pct)} of target.`;
}

function kpiCard(label, current, comparison, delta, context, options = {}) {
  const cls = options.status || statusClass(delta);
  const direction = delta === null ? "N/A" : `${Number(delta) >= 0 ? "up" : "down"} ${fmtPct(Math.abs(delta))}`;
  return `<article class="kpi-card">
    <span>${label}</span>
    <strong>${current}</strong>
    <div class="delta ${cls}">${direction} ${comparison}</div>
    <p class="context">${context}</p>
  </article>`;
}

function renderKpis() {
  const k = data.kpis;
  const t = data.totals;
  const renewalTotal = data.renewals.find((r) => r.month === "Grand Total");
  const cards = [
    kpiCard("Approved Gross Premiums", fmtMoney(t.approved_gross_premium), "vs H1 2025", k["Approved Gross Premiums"].change_pct, "Below target", { status: "negative" }),
    kpiCard("Target Achievement", fmtPct(t.target_achievement_pct), "of 2026 target", t.target_achievement_pct - 1, `${fmtMoney(t.target_gap)} target gap`, { status: "warning" }),
    kpiCard("YoY Growth %", fmtPct(k["Approved Gross Premiums"].change_pct), "premium change", k["Approved Gross Premiums"].change_pct, `${fmtMoney(k["Approved Gross Premiums"].change)} absolute movement`, { status: "negative" }),
    kpiCard("Total Policies", fmtNumber(t.total_policies), "vs H1 2025", k["Total Policies"].change_pct, "Total issued policies", { status: "negative" }),
    kpiCard("Approved Policies", fmtNumber(t.approved_policies), "vs H1 2025", k["Total Approved Policies"].change_pct, "Approved-policy base", { status: "negative" }),
    kpiCard("Average Premium per Policy", fmtMoney(t.avg_premium_per_policy), "vs H1 2025", k["Avg Premium per policy"].change_pct, "Higher ticket size offset lower volume"),
    kpiCard("New Premiums", fmtMoney(t.new_premium), "share of approved", t.new_premium / t.approved_gross_premium, "New production mix", { status: "positive" }),
    kpiCard("Renewal Premiums", fmtMoney(t.renewal_premium), "share of approved", t.renewal_premium / t.approved_gross_premium, "Renewal production mix", { status: "positive" }),
    kpiCard("Motor Renewal Rate", fmtPct(renewalTotal.renewal_rate), "H1 aggregate", renewalTotal.renewal_rate - 0.5, `${fmtNumber(renewalTotal.not_renewed_policies)} not renewed`, { status: renewalTotal.renewal_rate >= 0.5 ? "positive" : "warning" }),
    kpiCard("Pending Pipeline", fmtMoney(t.pending_total), "of approved premium", t.pending_as_pct_approved, "Separate from approved premium", { status: "warning" }),
  ];
  document.getElementById("kpiGrid").innerHTML = cards.join("");
}

function renderInsights() {
  const groups = [
    ["Positive Highlights", data.insights.positive_highlights],
    ["Key Concerns", data.insights.key_concerns],
    ["Opportunities", data.insights.opportunities],
  ];
  document.getElementById("insightGrid").innerHTML = groups
    .map(([title, rows]) => `<article class="insight-card"><h3>${title}</h3><ul>${rows.map((r) => `<li>${r}</li>`).join("")}</ul></article>`)
    .join("");
}

function renderTable(id, columns, rows, options = {}) {
  const table = document.getElementById(id);
  tables[id] = { columns, rows, filteredRows: rows.slice(), sortKey: null, sortDir: 1, options };
  drawTable(id);
}

function drawTable(id) {
  const state = tables[id];
  const rows = state.filteredRows.slice();
  if (state.sortKey) {
    const col = state.columns.find((c) => c.key === state.sortKey);
    rows.sort((a, b) => {
      const av = col.raw ? col.raw(a) : a[col.key];
      const bv = col.raw ? col.raw(b) : b[col.key];
      if (typeof av === "number" || typeof bv === "number") return (value(av) - value(bv)) * state.sortDir;
      return String(av || "").localeCompare(String(bv || "")) * state.sortDir;
    });
  }
  const header = `<thead><tr>${state.columns.map((c) => `<th data-key="${c.key}">${c.label}</th>`).join("")}</tr></thead>`;
  const body = `<tbody>${rows
    .map((row) => {
      const rowClass = state.options.rowClass ? state.options.rowClass(row) : "";
      return `<tr class="${rowClass}">${state.columns.map((c) => `<td>${c.format ? c.format(row) : row[c.key] ?? ""}</td>`).join("")}</tr>`;
    })
    .join("")}</tbody>`;
  document.getElementById(id).innerHTML = header + body;
  document.querySelectorAll(`#${id} th`).forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.key;
      state.sortDir = state.sortKey === key ? state.sortDir * -1 : 1;
      state.sortKey = key;
      drawTable(id);
    });
  });
}

function filterTable(id, predicate) {
  tables[id].filteredRows = tables[id].rows.filter(predicate);
  drawTable(id);
}

function exportTable(id) {
  const state = tables[id];
  const rows = state.filteredRows;
  const csv = [
    state.columns.map((c) => `"${c.label.replaceAll('"', '""')}"`).join(","),
    ...rows.map((row) =>
      state.columns
        .map((c) => {
          const val = c.export ? c.export(row) : c.raw ? c.raw(row) : row[c.key] ?? "";
          return `"${String(val).replaceAll('"', '""')}"`;
        })
        .join(",")
    ),
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${id}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function moneyCol(key) {
  return { raw: (r) => r[key], format: (r) => fmtMoney(r[key], false), export: (r) => Math.round(value(r[key])) };
}

function pctCol(key) {
  return { raw: (r) => r[key], format: (r) => fmtPct(r[key]), export: (r) => r[key] };
}

function renderMonthly() {
  const m = data.monthly;
  makeChart("monthlyCombo", {
    data: {
      labels: m.map((r) => r.month),
      datasets: [
        { type: "bar", label: "H1 2025 Actual", data: m.map((r) => r.actual_2025), backgroundColor: COLORS.lightBlue, yAxisID: "y" },
        { type: "bar", label: "H1 2026 Actual", data: m.map((r) => r.actual_2026), backgroundColor: COLORS.blue, yAxisID: "y" },
        { type: "line", label: "2026 Target", data: m.map((r) => r.target_2026), borderColor: COLORS.orange, backgroundColor: COLORS.orange, tension: 0.25, yAxisID: "y" },
        { type: "line", label: "Target Achievement %", data: m.map((r) => r.target_achievement_pct), borderColor: COLORS.green, backgroundColor: COLORS.green, tension: 0.25, yAxisID: "pct" },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) } },
        pct: { position: "right", min: 0, max: 1, ticks: { callback: (v) => fmtPct(v) }, grid: { drawOnChartArea: false } },
      },
    },
  });
  makeChart("monthlyMix", {
    type: "bar",
    data: {
      labels: m.map((r) => r.month),
      datasets: [
        { label: "New Premium", data: m.map((r) => r.new_premium), backgroundColor: COLORS.blue },
        { label: "Renewal Premium", data: m.map((r) => r.renewal_premium), backgroundColor: COLORS.green },
        { label: "Motor Premium", data: m.map((r) => r.motor_premium), backgroundColor: COLORS.orange },
        { label: "Non-Motor Premium", data: m.map((r) => r.non_motor_premium), backgroundColor: COLORS.lightBlue },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) } } } },
  });
  const best = Math.max(...m.map((r) => value(r.actual_2026)));
  const weakest = Math.min(...m.map((r) => value(r.target_achievement_pct)));
  renderTable(
    "monthlyTable",
    [
      { key: "month", label: "Month" },
      { key: "actual_2025", label: "2025 Actual", ...moneyCol("actual_2025") },
      { key: "actual_2026", label: "2026 Actual", ...moneyCol("actual_2026") },
      { key: "target_2026", label: "Target", ...moneyCol("target_2026") },
      { key: "target_achievement_pct", label: "Achievement %", ...pctCol("target_achievement_pct") },
      { key: "yoy_pct", label: "YoY %", ...pctCol("yoy_pct") },
      { key: "new_premium", label: "New", ...moneyCol("new_premium") },
      { key: "renewal_premium", label: "Renewal", ...moneyCol("renewal_premium") },
    ],
    m,
    { rowClass: (r) => (value(r.actual_2026) === best ? "highlight-best" : value(r.target_achievement_pct) === weakest ? "highlight-risk" : "") }
  );
}

function renderMix() {
  donut("newRenewalDonut", ["New", "Renewal"], [data.totals.new_premium, data.totals.renewal_premium], [COLORS.blue, COLORS.green]);
  donut("motorDonut", ["Motor", "Non-Motor"], [data.totals.motor_premium, data.totals.non_motor_premium], [COLORS.orange, COLORS.blue]);
  const retail = data.kpis["Retail Approved Gross"].value_2026;
  const corporate = data.kpis["Corporate Approved Gross"].value_2026;
  donut("retailDonut", ["Retail", "Corporate"], [retail, corporate], [COLORS.blue, COLORS.green]);
  const totals = Object.entries(data.status_mix).map(([year, rows]) => ({
    year,
    collection: rows.reduce((s, r) => s + value(r.collection), 0),
    endorsement: rows.reduce((s, r) => s + value(r.endorsement), 0),
    new: rows.reduce((s, r) => s + value(r.new), 0),
    renewal: rows.reduce((s, r) => s + value(r.renewal), 0),
  }));
  makeChart("statusStacked", {
    type: "bar",
    data: {
      labels: totals.map((r) => r.year),
      datasets: [
        { label: "Collection", data: totals.map((r) => r.collection), backgroundColor: COLORS.grey },
        { label: "Endorsement", data: totals.map((r) => r.endorsement), backgroundColor: COLORS.orange },
        { label: "New", data: totals.map((r) => r.new), backgroundColor: COLORS.blue },
        { label: "Renewal", data: totals.map((r) => r.renewal), backgroundColor: COLORS.green },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", scales: { x: { stacked: true, ticks: { callback: (v) => fmtMoney(v) } }, y: { stacked: true } } },
  });
  document.getElementById("mixInterpretation").textContent =
    `Motor premium represents ${fmtPct(data.totals.motor_premium / data.totals.approved_gross_premium)} of approved premium, while non-motor contributes ${fmtPct(data.totals.non_motor_premium / data.totals.approved_gross_premium)}. This creates concentration risk in motor-led production and a clear cross-sell opportunity.`;
}

function donut(id, labels, values, colors) {
  makeChart(id, {
    type: "doughnut",
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderColor: "#fff", borderWidth: 3 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const sum = ctx.dataset.data.reduce((a, b) => a + value(b), 0);
              return `${ctx.label}: ${fmtMoney(ctx.raw)} (${fmtPct(ctx.raw / sum)})`;
            },
          },
        },
      },
    },
  });
}

function bar(id, rows, labelKey, valueKey, color = COLORS.blue, indexAxis = "y") {
  makeChart(id, {
    type: "bar",
    data: { labels: rows.map((r) => shortLabel(r[labelKey])), datasets: [{ label: "Premium", data: rows.map((r) => r[valueKey]), backgroundColor: color }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis, scales: { x: { beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) } }, y: { ticks: { autoSkip: false } } } },
  });
}

function percentBar(id, rows, labelKey, valueKey, color = COLORS.green) {
  makeChart(id, {
    type: "bar",
    data: { labels: rows.map((r) => shortLabel(r[labelKey])), datasets: [{ label: "Contribution %", data: rows.map((r) => r[valueKey]), backgroundColor: color }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      scales: { x: { beginAtZero: true, ticks: { callback: (v) => fmtPct(v) } }, y: { ticks: { autoSkip: false } } },
      plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtPct(ctx.raw)}` } } },
    },
  });
}

function signedBar(id, rows, labelKey, valueKey) {
  makeChart(id, {
    type: "bar",
    data: { labels: rows.map((r) => shortLabel(r[labelKey])), datasets: [{ label: "YoY Change", data: rows.map((r) => r[valueKey]), backgroundColor: rows.map((r) => (value(r[valueKey]) >= 0 ? COLORS.green : COLORS.red)) }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", scales: { x: { ticks: { callback: (v) => fmtMoney(v) } } } },
  });
}

function renderBranches() {
  const rows = data.branches;
  bar("branchTop", rows.slice().sort(byDesc("premium_2026")).slice(0, 10), "branch", "premium_2026", COLORS.blue);
  signedBar("branchBottom", rows.slice().sort(byAsc("yoy_change")).slice(0, 10), "branch", "yoy_change");
  percentBar("branchContribution", rows.slice().sort(byDesc("contribution_pct")).slice(0, 10), "branch", "contribution_pct", COLORS.green);
  bar("branchPending", rows.slice().sort(byDesc("pending_total")).slice(0, 10), "branch", "pending_total", COLORS.orange);
  const medianPremium = rows.map((r) => value(r.premium_2026)).sort((a, b) => a - b)[Math.floor(rows.length / 2)];
  makeChart("branchScatter", {
    type: "bubble",
    data: {
      datasets: [
        {
          label: "Branches",
          data: rows.map((r) => ({ x: r.yoy_change_pct, y: r.premium_2026, r: Math.max(4, Math.min(22, Math.sqrt(value(r.approved_policies)) / 1.5)), label: r.branch })),
          backgroundColor: "rgba(37, 99, 235, 0.62)",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { ticks: { callback: (v) => fmtPct(v) }, title: { display: true, text: "YoY Growth %" } }, y: { ticks: { callback: (v) => fmtMoney(v) }, title: { display: true, text: "H1 2026 Premium" } } },
      plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.raw.label}: ${fmtPct(ctx.raw.x)}, ${fmtMoney(ctx.raw.y)}` } } },
    },
  });
  const branchPremiumRows = rows.slice().sort(byDesc("premium_2026"));
  makeChart("branchPremiumAll", {
    type: "bar",
    data: {
      labels: branchPremiumRows.map((r) => shortLabel(r.branch, 26)),
      datasets: [{ label: "2026 Premium", data: branchPremiumRows.map((r) => r.premium_2026), backgroundColor: COLORS.blue }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { autoSkip: false, maxRotation: 70, minRotation: 70, font: { size: 9 } } },
        y: { beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) } },
      },
    },
  });
  const branchPremiumTotals = Array.from(
    rows.reduce((map, row) => {
      const branch = row.branch;
      map.set(branch, (map.get(branch) || 0) + value(row.premium_2026));
      return map;
    }, new Map()).values()
  );
  const bins = [
    { label: "EGP 0–50K", min: 0, max: 50_000 },
    { label: "EGP 50K–100K", min: 50_000, max: 100_000 },
    { label: "EGP 100K–150K", min: 100_000, max: 150_000 },
    { label: "EGP 150K–200K", min: 150_000, max: 200_000 },
    { label: "EGP 200K–300K", min: 200_000, max: 300_000 },
    { label: "EGP 300K–600K", min: 300_000, max: 600_000 },
    { label: "EGP 600K–900K", min: 600_000, max: 900_000 },
    { label: "EGP 900K–1.2M", min: 900_000, max: 1_200_000 },
    { label: "EGP 1.2M–1.5M", min: 1_200_000, max: 1_500_000 },
    { label: "EGP 1.5M–1.8M", min: 1_500_000, max: 1_800_000 },
    { label: "EGP 1.8M–2.1M", min: 1_800_000, max: 2_100_000 },
    { label: "EGP 2.1M–2.4M", min: 2_100_000, max: 2_400_000 },
    { label: "EGP 2.4M–2.7M", min: 2_400_000, max: 2_700_000 },
    { label: "EGP 2.7M–3.0M", min: 2_700_000, max: 3_000_000, includeMax: true },
    { label: "More than EGP 3.0M", min: 3_000_000, max: Infinity, overflow: true },
  ].map((bin) => ({
    ...bin,
    count: branchPremiumTotals.filter((premium) =>
      bin.overflow
        ? premium > bin.min
        : premium >= bin.min && (bin.includeMax ? premium <= bin.max : premium < bin.max)
    ).length,
  }));
  makeChart("branchPremiumHistogram", {
    type: "bar",
    data: {
      labels: bins.map((bin) => bin.label),
      datasets: [{ label: "Number of Branches", data: bins.map((bin) => bin.count), backgroundColor: COLORS.green, borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { top: 18, right: 8, bottom: 4, left: 8 } },
      scales: {
        x: {
          title: { display: true, text: "2026 Premium Range", color: COLORS.navy, font: { weight: "700" } },
          grid: { display: false },
          ticks: { maxRotation: 35, minRotation: 25, autoSkip: false, font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          title: { display: true, text: "Number of Branches", color: COLORS.navy, font: { weight: "700" } },
          ticks: { precision: 0 },
          grid: { color: "#E5E7EB" },
        },
      },
      plugins: {
        legend: { display: false },
        staticValueLabels: { display: true, showZero: true, valueType: "number", fontSize: 11 },
        tooltip: { callbacks: { label: (ctx) => `${ctx.raw} branches` } },
      },
    },
  });
  const avg = data.totals.approved_gross_premium / rows.length;
  const highPending = rows.map((r) => value(r.pending_total)).sort((a, b) => a - b)[Math.floor(rows.length * 0.75)];
  renderTable("branchTable", entityColumns("branch"), rows);
  document.getElementById("branchSearch").addEventListener("input", applyBranchFilter);
  document.getElementById("branchFilter").addEventListener("change", applyBranchFilter);
  function applyBranchFilter() {
    const q = document.getElementById("branchSearch").value.toLowerCase();
    const f = document.getElementById("branchFilter").value;
    filterTable("branchTable", (r) => {
      const match = r.branch.toLowerCase().includes(q);
      const filter =
        f === "all" ||
        (f === "positive" && value(r.yoy_change) > 0) ||
        (f === "negative" && value(r.yoy_change) < 0) ||
        (f === "aboveAverage" && value(r.premium_2026) >= avg) ||
        (f === "belowAverage" && value(r.premium_2026) < avg) ||
        (f === "highPending" && value(r.pending_total) >= highPending);
      return match && filter;
    });
  }
}

function entityColumns(nameKey) {
  return [
    { key: nameKey, label: nameKey === "branch" ? "Branch" : "Seller" },
    { key: "premium_2025", label: "Premium 2025", ...moneyCol("premium_2025") },
    { key: "premium_2026", label: "Premium 2026", ...moneyCol("premium_2026") },
    { key: "yoy_change", label: "YoY Change", ...moneyCol("yoy_change") },
    { key: "yoy_change_pct", label: "YoY Change %", ...pctCol("yoy_change_pct") },
    { key: "contribution_pct", label: "Contribution %", ...pctCol("contribution_pct") },
    { key: "approved_policies", label: "Approved Policies", raw: (r) => r.approved_policies, format: (r) => fmtNumber(r.approved_policies) },
    { key: "avg_premium_per_policy", label: "Avg Premium / Policy", ...moneyCol("avg_premium_per_policy") },
    { key: "new_premium", label: "New Premium", ...moneyCol("new_premium") },
    { key: "renewal_premium", label: "Renewal Premium", ...moneyCol("renewal_premium") },
    { key: "renewal_mix_pct", label: "Renewal Mix %", ...pctCol("renewal_mix_pct") },
    { key: "motor_premium", label: "Motor Premium", ...moneyCol("motor_premium") },
    { key: "non_motor_premium", label: "Non-Motor Premium", ...moneyCol("non_motor_premium") },
    { key: "pending_finance", label: "Pending Finance", ...moneyCol("pending_finance") },
    { key: "pending_payment", label: "Pending Payment", ...moneyCol("pending_payment") },
  ];
}

function renderSellers() {
  const rows = data.sellers;
  bar("sellerTop", rows.slice().sort(byDesc("premium_2026")).slice(0, 10), "seller", "premium_2026", COLORS.blue);
  signedBar("sellerGrowth", rows.slice().sort(byDesc("yoy_change")).slice(0, 12), "seller", "yoy_change");
  makeChart("sellerMix", {
    type: "bar",
    data: {
      labels: rows.slice(0, 12).map((r) => shortLabel(r.seller, 18)),
      datasets: [
        { label: "New", data: rows.slice(0, 12).map((r) => r.new_premium), backgroundColor: COLORS.blue },
        { label: "Renewal", data: rows.slice(0, 12).map((r) => r.renewal_premium), backgroundColor: COLORS.green },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", scales: { x: { stacked: true, ticks: { callback: (v) => fmtMoney(v) } }, y: { stacked: true } } },
  });
  renderTable("sellerTable", entityColumns("seller"), rows);
  document.getElementById("sellerSearch").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    filterTable("sellerTable", (r) => r.seller.toLowerCase().includes(q));
  });
}

function renderInsurers() {
  const rows = data.insurers;
  const top3 = rows.slice().sort(byDesc("premium_2026")).slice(0, 3);
  const positive = rows.filter((r) => value(r.yoy_change) > 0).length;
  const noBase = rows.filter((r) => r.new_2026_base).length;
  document.getElementById("insurerStrip").innerHTML = [
    ["Top 3 Share", fmtPct(top3.reduce((s, r) => s + value(r.premium_2026), 0) / data.totals.approved_gross_premium)],
    ["Positive Growth", fmtNumber(positive)],
    ["Negative Growth", fmtNumber(rows.length - positive - noBase)],
    ["New 2026 Base", fmtNumber(noBase)],
  ].map(([a, b]) => `<div class="summary-item"><span>${a}</span><strong>${b}</strong></div>`).join("");
  bar("insurerTop", rows.slice().sort(byDesc("premium_2026")).slice(0, 10), "insurance_company", "premium_2026", COLORS.blue);
  signedBar("insurerGrowth", rows.slice().sort(byAsc("yoy_change")).slice(0, 10), "insurance_company", "yoy_change");
  renderTable("insurerTable", [
    { key: "insurance_company", label: "Insurance Company" },
    { key: "premium_2025", label: "Premium 2025", ...moneyCol("premium_2025") },
    { key: "premium_2026", label: "Premium 2026", ...moneyCol("premium_2026") },
    { key: "yoy_change", label: "YoY Change", ...moneyCol("yoy_change") },
    { key: "yoy_change_pct", label: "YoY Change %", ...pctCol("yoy_change_pct") },
    { key: "share_2026_pct", label: "2026 Share %", ...pctCol("share_2026_pct") },
    { key: "new_2026_base", label: "No Prior-Year Base", raw: (r) => r.new_2026_base, format: (r) => r.new_2026_base ? "Yes" : "No" },
  ], rows);
}

function renderLob() {
  const rows = data.lines_of_business;
  bar("lobTop", rows.slice().sort(byDesc("premium_2026")).slice(0, 12), "line_of_business", "premium_2026", COLORS.blue);
  signedBar("lobGrowth", rows.slice().filter((r) => r.yoy_change !== null).sort(byAsc("yoy_change")).slice(0, 12), "line_of_business", "yoy_change");
  makeChart("lobMix", {
    type: "bar",
    data: {
      labels: rows.slice().sort(byDesc("premium_2026")).slice(0, 12).map((r) => shortLabel(r.line_of_business, 24)),
      datasets: [
        { label: "New", data: rows.slice().sort(byDesc("premium_2026")).slice(0, 12).map((r) => r.new_premium), backgroundColor: COLORS.blue },
        { label: "Renewal", data: rows.slice().sort(byDesc("premium_2026")).slice(0, 12).map((r) => r.renewal_premium), backgroundColor: COLORS.green },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", scales: { x: { stacked: true, ticks: { callback: (v) => fmtMoney(v) } }, y: { stacked: true } } },
  });
  renderHeatmap();
  renderTable("lobTable", [
    { key: "line_of_business", label: "Line of Business" },
    { key: "premium_2025", label: "Premium 2025", ...moneyCol("premium_2025") },
    { key: "premium_2026", label: "Premium 2026", ...moneyCol("premium_2026") },
    { key: "yoy_change", label: "YoY Change", ...moneyCol("yoy_change") },
    { key: "yoy_change_pct", label: "YoY Change %", ...pctCol("yoy_change_pct") },
    { key: "target_2026", label: "Target", ...moneyCol("target_2026") },
    { key: "target_achievement_pct", label: "Target Achievement", ...pctCol("target_achievement_pct") },
    { key: "new_premium", label: "New Premium", ...moneyCol("new_premium") },
    { key: "renewal_premium", label: "Renewal Premium", ...moneyCol("renewal_premium") },
  ], rows);
}

function renderHeatmap() {
  const topLines = data.lines_of_business.slice().sort(byDesc("premium_2026")).slice(0, 10).map((r) => r.line_of_business);
  const vals = data.line_of_business_monthly.filter((r) => topLines.includes(r.line_of_business));
  const max = Math.max(...vals.map((r) => value(r.premium_2026)));
  let html = `<div class="heatmap-grid"><div class="heatmap-cell heatmap-head">Line of Business</div>${["January", "February", "March", "April", "May", "June"].map((m) => `<div class="heatmap-cell heatmap-head">${m}</div>`).join("")}`;
  topLines.forEach((line) => {
    html += `<div class="heatmap-cell heatmap-head">${shortLabel(line, 34)}</div>`;
    ["January", "February", "March", "April", "May", "June"].forEach((month) => {
      const rec = vals.find((r) => r.month === month && r.line_of_business === line);
      const intensity = rec ? value(rec.premium_2026) / max : 0;
      html += `<div class="heatmap-cell" style="background: rgba(37,99,235,${0.08 + intensity * 0.72}); color:${intensity > 0.5 ? "#fff" : "var(--text)"}">${rec ? fmtMoney(rec.premium_2026) : "N/A"}</div>`;
    });
  });
  html += "</div>";
  document.getElementById("lobHeatmap").innerHTML = html;
}

function renderRenewals() {
  const monthly = data.renewals.filter((r) => r.month !== "Grand Total");
  const total = data.renewals.find((r) => r.month === "Grand Total");
  const best = monthly.slice().sort(byDesc("renewal_rate"))[0];
  const weakest = monthly.slice().sort(byAsc("renewal_rate"))[0];
  document.getElementById("renewalStrip").innerHTML = [
    ["Policies Up for Renewal", fmtNumber(total.policies_up_for_renewal)],
    ["Renewed Policies", fmtNumber(total.renewed_policies)],
    ["Not Renewed Policies", fmtNumber(total.not_renewed_policies)],
    ["Overall H1 Renewal Rate", fmtPct(total.renewal_rate)],
  ].map(([a, b]) => `<div class="summary-item"><span>${a}</span><strong>${b}</strong></div>`).join("");
  makeChart("renewalLine", {
    type: "line",
    data: { labels: monthly.map((r) => r.month), datasets: [{ label: "Motor Renewal Rate %", data: monthly.map((r) => r.renewal_rate), borderColor: COLORS.blue, backgroundColor: COLORS.blue, tension: 0.25 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 0.7, ticks: { callback: (v) => fmtPct(v) } } } },
  });
  makeChart("renewalFunnel", {
    type: "bar",
    data: { labels: ["Up for Renewal", "Renewed", "Not Renewed"], datasets: [{ label: "Policies", data: [total.policies_up_for_renewal, total.renewed_policies, total.not_renewed_policies], backgroundColor: [COLORS.blue, COLORS.green, COLORS.orange] }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", scales: { x: { beginAtZero: true } } },
  });
}

function renderPending() {
  const t = data.totals;
  document.getElementById("pendingStrip").innerHTML = [
    ["Total Pending Value", fmtMoney(t.pending_total)],
    ["Pending Finance", fmtMoney(t.pending_finance)],
    ["Pending Payment", fmtMoney(t.pending_payment)],
    ["Pending as % of Approved", fmtPct(t.pending_as_pct_approved)],
  ].map(([a, b]) => `<div class="summary-item"><span>${a}</span><strong>${b}</strong></div>`).join("");
  bar("pendingBranch", data.branches.slice().sort(byDesc("pending_total")).slice(0, 12), "branch", "pending_total", COLORS.orange);
  donut("pendingMix", ["Operation Paid", "Finance", "Not Paid Yet"], [t.pending_operation_paid, t.pending_finance, t.pending_payment], [COLORS.blue, COLORS.green, COLORS.orange]);
  const top = data.branches.slice().sort(byDesc("pending_total"))[0];
  document.getElementById("pendingNote").textContent =
    `${top.branch} has the largest pending exposure at ${fmtMoney(top.pending_total)}. Pending amounts are treated as pipeline or risk exposure and are not included in approved gross premium unless explicitly shown as approved in the workbook.`;
}

function renderDrivers() {
  const positiveDrivers = [
    ["Top branch", fmtMoney(data.branches.slice().sort(byDesc("premium_2026"))[0].premium_2026), `${data.branches.slice().sort(byDesc("premium_2026"))[0].branch} led branch production.`, "Protect capacity and replicate its branch practices."],
    ["Best month", fmtMoney(data.monthly.slice().sort(byDesc("actual_2026"))[0].actual_2026), `${data.monthly.slice().sort(byDesc("actual_2026"))[0].month} had the highest 2026 premium.`, "Use as monthly run-rate benchmark."],
    ["Growth pockets", fmtNumber(data.branches.filter((r) => value(r.yoy_change) > 0).length), "Several smaller branches grew despite the aggregate decline.", "Study high-growth branches without overstating tiny bases."],
  ];
  const negativeDrivers = [
    ["Premium decline", fmtMoney(data.kpis["Approved Gross Premiums"].change), "Approved gross premium fell materially vs H1 2025.", "Launch recovery actions against target gap."],
    ["Target gap", fmtMoney(data.totals.target_gap), `Achievement is ${fmtPct(data.totals.target_achievement_pct)}.`, "Monitor weekly production against branch targets."],
    ["Motor concentration", fmtPct(data.totals.motor_premium / data.totals.approved_gross_premium), "Approved premium is heavily motor-led.", "Grow non-motor cross-sell and insurer breadth."],
  ];
  document.getElementById("driverGrid").innerHTML = [driverPanel("Positive Drivers", positiveDrivers), driverPanel("Negative Drivers", negativeDrivers)].join("");
}

function driverPanel(title, rows) {
  return `<article class="driver-panel"><h3>${title}</h3><div class="driver-row"><b>Driver</b><b>Impact</b><b>Evidence</b><b>Implication</b></div>${rows
    .map((r) => `<div class="driver-row"><b>${r[0]}</b><span>${r[1]}</span><span>${r[2]}</span><span>${r[3]}</span></div>`)
    .join("")}</article>`;
}

function initAuth() {
  const form = document.getElementById("loginForm");
  const error = document.getElementById("loginError");
  const unlock = () => document.body.classList.remove("auth-locked");
  if (sessionStorage.getItem("contactReportAuthed") === "true") {
    unlock();
  }
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const username = document.getElementById("loginUsername").value.trim().toLowerCase();
    const password = document.getElementById("loginPassword").value;
    if (username === "external user" && password === "1234") {
      sessionStorage.setItem("contactReportAuthed", "true");
      error.textContent = "";
      unlock();
      charts.forEach((chart) => {
        chart.resize();
        chart.update("none");
      });
      return;
    }
    error.textContent = "Invalid username or password.";
  });
}

function registerActions() {
  document.getElementById("printBtn").addEventListener("click", () => {
    prepareForPrint();
    setTimeout(() => window.print(), 150);
  });
  document.getElementById("resetBtn").addEventListener("click", () => {
    document.querySelectorAll(".filters input").forEach((el) => (el.value = ""));
    document.querySelectorAll(".filters select").forEach((el) => (el.value = "all"));
    filterTable("branchTable", () => true);
    filterTable("sellerTable", () => true);
  });
  document.querySelectorAll("[data-export]").forEach((btn) => btn.addEventListener("click", () => exportTable(btn.dataset.export)));
  window.addEventListener("beforeprint", prepareForPrint);
  window.addEventListener("afterprint", restoreAfterPrint);
}

function prepareForPrint() {
  document.body.classList.add("pdf-mode");
  charts.forEach((chart) => {
    chart.options.animation = false;
    chart.options.plugins.staticValueLabels =
      chart.canvas.id === "branchPremiumHistogram"
        ? { display: true, showZero: true, valueType: "number", fontSize: 11 }
        : { display: true, fontSize: 9 };
    chart.resize();
    chart.update("none");
  });
}

function restoreAfterPrint() {
  document.body.classList.remove("pdf-mode");
  charts.forEach((chart) => {
    chart.options.plugins.staticValueLabels =
      chart.canvas.id === "branchPremiumHistogram"
        ? { display: true, showZero: true, valueType: "number", fontSize: 11 }
        : { display: false };
    chart.resize();
    chart.update("none");
  });
}

window.prepareDashboardForPrint = prepareForPrint;
window.restoreDashboardAfterPrint = restoreAfterPrint;

function init() {
  initAuth();
  chartDefaults();
  renderMeta();
  renderKpis();
  renderInsights();
  renderMonthly();
  renderMix();
  renderBranches();
  renderSellers();
  renderInsurers();
  renderLob();
  renderRenewals();
  renderPending();
  renderDrivers();
  registerActions();
}

init();
