/**
 * crowd_chart.js — TravelTech ML Crowd Forecast Visualizer
 * ==========================================================
 * Renders a 24-hour crowd prediction chart and a 7-day weekly heatmap
 * for any destination, powered by the backend ML model.
 *
 * Requires: Chart.js 4.x  (loaded in base.html)
 * Exports:  openCrowdForecastModal(destId, destName)
 */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────────
const CROWD_COLORS = {
  0: { bg: "rgba(40, 167, 69, 0.75)",  border: "#28a745", text: "None"        },
  1: { bg: "rgba(92, 184, 92, 0.75)",  border: "#5cb85c", text: "Low"         },
  2: { bg: "rgba(240, 173, 78, 0.82)", border: "#f0ad4e", text: "Moderate"    },
  3: { bg: "rgba(253, 126, 20, 0.82)", border: "#fd7e14", text: "High"        },
  4: { bg: "rgba(220, 53, 69, 0.85)",  border: "#dc3545", text: "Overcrowded" },
};

// Authority status → crowd level mapping (for comparison banner)
const AUTH_STATUS_LEVEL = {
  "normal":      1,
  "moderate":    2,
  "crowded":     3,
  "overcrowded": 4,
  "unknown":     null,
};

let _dailyChart  = null;
let _weeklyChart = null;
let _currentDestId = null;

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Fetch forecast data and open the Bootstrap modal.
 * @param {number} destId   - Destination DB id
 * @param {string} destName - Human-readable name
 */
window.openCrowdForecastModal = function (destId, destName) {
  _currentDestId = destId;

  // Update modal title
  const titleEl = document.getElementById("crowdForecastModalLabel");
  if (titleEl) titleEl.textContent = `📊 Predicted Crowd Forecast — ${destName}`;

  // Show loading states
  _setLoadingState(true);

  // Open modal first for responsive feel
  const modalEl = document.getElementById("crowdForecastModal");
  const modal   = bootstrap.Modal.getOrCreate(modalEl);
  modal.show();

  // Parallel fetch: daily + weekly
  Promise.all([
    fetch(`/api/ml/crowd-forecast/${destId}`).then((r) => r.json()),
    fetch(`/api/ml/crowd-weekly/${destId}`).then((r) => r.json()),
  ])
    .then(([daily, weekly]) => {
      _renderDailyChart(daily);
      _renderWeeklyHeatmap(weekly);
      _renderMetaBadges(daily, weekly);
      _setLoadingState(false);
    })
    .catch((err) => {
      console.error("Crowd forecast fetch error:", err);
      _showError("Failed to load crowd forecast. Please try again.");
    });
};

// ── Rendering ─────────────────────────────────────────────────────────────────

function _renderDailyChart(data) {
  const canvas = document.getElementById("crowdForecastCanvas");
  if (!canvas) return;

  const ctx    = canvas.getContext("2d");
  const levels = data.crowd_levels || [];
  const labels = levels.map((h) => h.hour_label);
  const values = levels.map((h) => h.level);
  const bgs    = values.map((v) => CROWD_COLORS[v]?.bg    || CROWD_COLORS[2].bg);
  const bords  = values.map((v) => CROWD_COLORS[v]?.border || CROWD_COLORS[2].border);

  if (_dailyChart) {
    _dailyChart.destroy();
    _dailyChart = null;
  }

  _dailyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Predicted Crowd Level (0–4)",
        data: values,
        backgroundColor: bgs,
        borderColor: bords,
        borderWidth: 1.5,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      scales: {
        y: {
          min: 0,
          max: 4,
          ticks: {
            stepSize: 1,
            callback: (v) => ["None", "Low", "Moderate", "High", "Overcrowded"][v] || v,
            font: { size: 11 },
          },
          grid: { color: "rgba(0,0,0,0.06)" },
        },
        x: {
          ticks: {
            maxRotation: 45,
            font: { size: 10 },
            callback: function (val, idx) {
              // Show every 3rd hour to avoid clutter
              return idx % 3 === 0 ? this.getLabelForValue(val) : "";
            },
          },
          grid: { display: false },
        },
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const lvl = ctx.raw;
              const info = CROWD_COLORS[lvl];
              return ` ${info?.text || "Unknown"}  (level ${lvl})`;
            },
          },
        },
        legend: { display: false },
      },
    },
  });

  // Authority comparison banner
  _renderAuthorityBanner(data);
}

function _renderAuthorityBanner(data) {
  const banner = document.getElementById("authorityCrowdBanner");
  if (!banner) return;

  const authStatus = (data.authority_crowd_status || "unknown").toLowerCase();
  const authLevel  = AUTH_STATUS_LEVEL[authStatus];

  if (authStatus === "unknown" || authLevel === null) {
    banner.className = "alert alert-secondary py-2 small mb-2";
    banner.innerHTML = `<i class="bi bi-shield-exclamation me-1"></i>
      No authority-verified crowd status set for this destination.
      Showing ML-predicted estimates only.`;
    return;
  }

  const col = authLevel <= 1 ? "success" : authLevel === 2 ? "warning" : "danger";
  const icon = authLevel <= 1 ? "shield-check" : authLevel <= 3 ? "shield-exclamation" : "shield-x";
  banner.className = `alert alert-${col} py-2 small mb-2`;
  banner.innerHTML = `<i class="bi bi-${icon} me-1"></i>
    <strong>Authority-verified status:</strong> ${data.authority_crowd_status}
    <span class="ms-2 text-muted fst-italic">(Always takes precedence over ML predictions)</span>`;
}

function _renderWeeklyHeatmap(data) {
  const container = document.getElementById("weeklyHeatmap");
  if (!container) return;

  const weekly = data.weekly_forecast;
  if (!weekly || !weekly.days) {
    container.innerHTML = '<p class="text-muted small">Weekly data unavailable.</p>';
    return;
  }

  const days    = weekly.days;
  const summary = weekly.summary || {};

  // Build heatmap table
  let html = `
    <div class="table-responsive">
      <table class="table table-sm table-bordered crowd-heatmap-table mb-1" style="font-size:0.65rem;">
        <thead>
          <tr>
            <th class="text-center" style="width:60px">Day</th>`;

  // Hour columns (show 0,3,6,9,...21)
  for (let h = 0; h < 24; h += 3) {
    html += `<th class="text-center" style="min-width:28px">${String(h).padStart(2,"0")}</th>`;
  }
  html += `</tr></thead><tbody>`;

  for (const day of days) {
    html += `<tr><td class="fw-semibold text-nowrap">${day.day_short}<br><small class="text-muted">${day.date.slice(5)}</small></td>`;
    // Group hourly data into 3-hour buckets (take the max level in each bucket)
    for (let h = 0; h < 24; h += 3) {
      const bucket = day.hours.slice(h, h + 3);
      const maxLvl = Math.max(...bucket.map((x) => x.level));
      const c      = CROWD_COLORS[maxLvl];
      const label  = c?.text || "?";
      html += `<td style="background:${c?.bg || "#eee"};border-color:${c?.border || "#ccc"}" 
                   title="${day.day_short} ${String(h).padStart(2,"0")}:00 — ${label}"
                   class="text-center">&nbsp;</td>`;
    }
    html += `</tr>`;
  }
  html += `</tbody></table></div>`;

  // Legend
  html += `<div class="d-flex flex-wrap gap-2 mb-2 ps-1">`;
  for (const [lvl, info] of Object.entries(CROWD_COLORS)) {
    html += `<span class="badge" style="background:${info.bg};color:#333;border:1px solid ${info.border};font-size:0.68rem">${info.text}</span>`;
  }
  html += `</div>`;

  // Summary
  if (summary.peak_day) {
    html += `<p class="small text-muted mb-0">
      📈 <strong>Busiest time this week:</strong> ${summary.peak_day} around ${summary.peak_hour_label}
      &nbsp;|&nbsp; Avg crowd level: <strong>${summary.avg_label}</strong>
    </p>`;
  }

  container.innerHTML = html;
}

function _renderMetaBadges(daily, weekly) {
  const metaEl = document.getElementById("crowdForecastMeta");
  if (!metaEl) return;

  const ds  = daily.crowd_levels?.[0]?.data_source || "unknown";
  const acc = daily.crowd_levels?.[0]?.model_accuracy;
  const cv  = daily.crowd_levels?.[0]?.model_cv_accuracy;

  let sourceLabel, sourceCls;
  if (ds === "ml_model") {
    sourceLabel = `ML Model (acc ≈ ${acc ? Math.round(acc * 100) : "?"}%, CV ${cv ? Math.round(cv * 100) : "?"}%)`;
    sourceCls   = "bg-info text-dark";
  } else {
    sourceLabel = "Heuristic Estimate (model not yet available)";
    sourceCls   = "bg-secondary text-white";
  }

  metaEl.innerHTML = `
    <span class="badge ${sourceCls} me-1"><i class="bi bi-cpu me-1"></i>${sourceLabel}</span>
    <span class="badge bg-warning text-dark me-1"><i class="bi bi-thermometer-half me-1"></i>Weather: Historical monthly avg</span>
    <span class="badge bg-light text-dark border"><i class="bi bi-info-circle me-1"></i>Estimate — not live data</span>
  `;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _setLoadingState(loading) {
  const spinner   = document.getElementById("crowdChartSpinner");
  const chartWrap = document.getElementById("crowdChartWrapper");
  if (spinner)   spinner.classList.toggle("d-none", !loading);
  if (chartWrap) chartWrap.classList.toggle("d-none", loading);

  const errEl = document.getElementById("crowdForecastError");
  if (errEl) errEl.classList.add("d-none");
}

function _showError(msg) {
  _setLoadingState(false);
  const errEl = document.getElementById("crowdForecastError");
  if (errEl) {
    errEl.textContent = msg;
    errEl.classList.remove("d-none");
  }
}

// Clean up charts when modal closes to free memory
document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("crowdForecastModal");
  if (!modalEl) return;
  modalEl.addEventListener("hidden.bs.modal", () => {
    if (_dailyChart)  { _dailyChart.destroy();  _dailyChart  = null; }
    if (_weeklyChart) { _weeklyChart.destroy(); _weeklyChart = null; }
    _currentDestId = null;
  });
});

