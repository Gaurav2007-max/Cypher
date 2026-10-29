#!/usr/bin/env python3
"""Patch base.html: add Chart.js CDN, crowd_chart.js, and Crowd Forecast Modal."""
import pathlib

root = pathlib.Path(r"c:\Users\Gaurav\Desktop\Cypher 2.0")
tmpl = root / "app" / "templates" / "base.html"

content = tmpl.read_text(encoding="utf-8")

# ── 1. Add Chart.js + crowd_chart.js before {% block extra_scripts %} ──────────
old_block = "    {% block extra_scripts %}{% endblock %}\n</body>"
new_block = (
    "    <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js\"></script>\n"
    "    <script src=\"{{ url_for('static', filename='js/crowd_chart.js') }}\"></script>\n"
    "    {% block extra_scripts %}{% endblock %}\n"
    "</body>"
)
if old_block not in content:
    print("WARNING: could not find extra_scripts block — trying \\r\\n variant")
    old_block = "    {% block extra_scripts %}{% endblock %}\r\n</body>"
    new_block = new_block.replace("\n", "\r\n")

content = content.replace(old_block, new_block, 1)

# ── 2. Insert the Crowd Forecast Modal just before </body> ─────────────────────
modal = """
<!-- ============================================================
     Crowd Forecast Modal  (ML Predictions)
     ============================================================ -->
<div class="modal fade" id="crowdForecastModal" tabindex="-1"
     aria-labelledby="crowdForecastModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content border-0 shadow-lg">

      <!-- Header -->
      <div class="modal-header"
           style="background:linear-gradient(135deg,#e8f4fd,#f0e8fd);border-bottom:1px solid #dee2e6">
        <h5 class="modal-title fw-bold" id="crowdForecastModalLabel">
          <i class="bi bi-graph-up-arrow text-primary me-2"></i>Predicted Crowd Forecast
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>

      <!-- Body -->
      <div class="modal-body p-3 p-lg-4">

        <!-- Loading spinner -->
        <div id="crowdChartSpinner" class="text-center py-5">
          <div class="spinner-border text-primary" role="status"></div>
          <p class="mt-2 text-muted small">Loading crowd predictions&hellip;</p>
        </div>

        <!-- Error state -->
        <div id="crowdForecastError" class="alert alert-danger d-none"></div>

        <!-- Chart wrapper (hidden while loading) -->
        <div id="crowdChartWrapper" class="d-none">

          <!-- Authority status comparison banner -->
          <div id="authorityCrowdBanner" class="alert alert-secondary py-2 small mb-3"></div>

          <!-- 24-hour bar chart -->
          <div class="card border-0 shadow-sm mb-4">
            <div class="card-header bg-white py-2">
              <h6 class="mb-0 fw-semibold">
                <i class="bi bi-clock-history text-primary me-1"></i>
                Today&rsquo;s Hourly Crowd Forecast
              </h6>
              <small class="text-muted">Predicted crowd level (0&nbsp;=&nbsp;None &rarr; 4&nbsp;=&nbsp;Overcrowded) for each hour</small>
            </div>
            <div class="card-body p-3">
              <div style="height:220px;position:relative">
                <canvas id="crowdForecastCanvas"></canvas>
              </div>
            </div>
          </div>

          <!-- 7-day heatmap -->
          <div class="card border-0 shadow-sm mb-3">
            <div class="card-header bg-white py-2">
              <h6 class="mb-0 fw-semibold">
                <i class="bi bi-calendar-week text-success me-1"></i>
                7-Day Crowd Heatmap
              </h6>
              <small class="text-muted">Each cell = 3-hour window. Colour = max predicted crowd level in that window.</small>
            </div>
            <div class="card-body p-2">
              <div id="weeklyHeatmap">
                <div class="text-center py-3">
                  <div class="spinner-border spinner-border-sm text-secondary"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Model meta badges -->
          <div id="crowdForecastMeta" class="d-flex flex-wrap gap-1 mb-2"></div>

        </div><!-- /crowdChartWrapper -->
      </div><!-- /modal-body -->

      <!-- Footer disclaimer -->
      <div class="modal-footer flex-column align-items-start bg-light" style="font-size:0.78rem">
        <div class="text-muted">
          <i class="bi bi-info-circle-fill text-warning me-1"></i>
          <strong>Disclaimer:</strong> These predictions are <em>ML model estimates</em> based on
          historical tourism patterns, typical monthly weather, and city traffic indices &mdash;
          <strong>not live crowd counts</strong>.
          Authority-verified crowd status always takes precedence.
        </div>
        <div class="text-muted mt-1">
          <i class="bi bi-cpu me-1"></i>
          <strong>Features used:</strong> Hour of day &bull; Day of week &bull; Month &bull;
          Day of year &bull; Public holidays &bull; Festival season &bull; Historical weather &bull;
          City traffic index &bull; Destination type &bull; Base popularity
        </div>
      </div>

    </div>
  </div>
</div><!-- /crowdForecastModal -->
"""

# Insert before the closing </body> tag
if "\n</body>" in content:
    content = content.replace("\n</body>", modal + "\n</body>", 1)
elif "\r\n</body>" in content:
    content = content.replace("\r\n</body>", modal + "\r\n</body>", 1)
else:
    print("ERROR: could not find </body> tag — manual edit required")
    exit(1)

tmpl.write_text(content, encoding="utf-8")
print(f"base.html patched successfully ({len(content)} bytes)")

