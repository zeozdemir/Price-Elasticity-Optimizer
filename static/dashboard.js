/* dashboard.js  –  Interactive Econometric & Plotly Engine */
(function () {
  "use strict";

  let uploadedFiles = [];
  let activeCurrency = "£";
  let activeProduct = null;
  let activeOptData = null;
  let simDebounce = null;

  /* ── Formatters ────────────────────────────────────────────────────────── */
  function fmt_currency(v, cur) {
    if (v == null || isNaN(v)) return "—";
    const c = cur || activeCurrency;
    const num = parseFloat(v);
    if (num >= 1_000_000) return c + (num / 1_000_000).toFixed(2) + "M";
    if (num >= 1_000)     return c + (num / 1_000).toFixed(1) + "K";
    return c + num.toFixed(2);
  }

  function fmt_pct(v) {
    if (v == null || isNaN(v)) return "—";
    const n = parseFloat(v);
    return (n >= 0 ? "+" : "") + n.toFixed(1) + "%";
  }

  function fmt_num(v, decimals = 2) {
    if (v == null || isNaN(v)) return "—";
    return parseFloat(v).toFixed(decimals);
  }

  function fmt_size(bytes) {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return (bytes / 1024).toFixed(0) + " KB";
  }

  function el(id) { return document.getElementById(id); }
  function setText(id, txt) { const e = el(id); if (e) e.textContent = txt; }

  /* ── Safe Fetch JSON ───────────────────────────────────────────────────── */
  async function fetchJSON(url) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error("fetchJSON error:", url, err);
      return null;
    }
  }

  /* ── Common Plotly Styling (Clean Light Amethyst) ───────────────────────── */
  const PLOTLY_FONT = { family: "Inter, -apple-system, sans-serif", color: "#475569", size: 11 };
  const PLOTLY_LAYOUT_BASE = {
    paper_bgcolor: "#FFFFFF",
    plot_bgcolor: "#F8FAFC",
    font: PLOTLY_FONT,
    margin: { l: 55, r: 25, t: 30, b: 40 },
    showlegend: true,
    legend: { orientation: "h", y: -0.22, x: 0.05, font: { size: 10 } },
    hovermode: "closest",
    xaxis: {
      gridcolor: "#E2E8F0",
      linecolor: "#CBD5E1",
      zerolinecolor: "#CBD5E1"
    },
    yaxis: {
      gridcolor: "#E2E8F0",
      linecolor: "#CBD5E1",
      zerolinecolor: "#CBD5E1"
    }
  };

  /* ── 1. KPI Summary ────────────────────────────────────────────────────── */
  async function loadSummary() {
    const data = await fetchJSON("/api/summary");
    if (!data) return;

    if (data.currency_symbol) {
      activeCurrency = data.currency_symbol;
      const cSel = el("dashboard-currency-select");
      if (cSel) cSel.value = activeCurrency;
    }

    setText("db-name", data.dataset_name || "Active Dataset");

    const revEl = el("kpi-revenue");
    if (revEl) {
      revEl.textContent = fmt_currency(data.total_revenue);
      revEl.classList.remove("spinner");
    }
    setText("kpi-date-range", data.date_range || "—");

    const boostEl = el("kpi-boost");
    if (boostEl) {
      boostEl.textContent = (data.best_revenue_boost_pct != null) ? fmt_pct(data.best_revenue_boost_pct) : "—";
    }
    setText("kpi-transactions", (data.total_transactions || 0).toLocaleString() + " transactions");

    setText("kpi-top-product", data.top_product || "—");
    setText("kpi-top-country", "Top Market: " + (data.top_country || "—"));

    const avgEl = el("kpi-avg-elasticity");
    if (avgEl) {
      avgEl.textContent = (data.avg_elasticity != null) ? fmt_num(data.avg_elasticity, 2) : "—";
    }
  }

  /* ── 2. Time Series & Price Distribution ───────────────────────────────── */
  async function loadMacroCharts() {
    const tsData = await fetchJSON("/api/time_series");
    if (tsData && tsData.dates) {
      Plotly.newPlot("plot-time-series", [
        {
          x: tsData.dates,
          y: tsData.revenues,
          type: "scatter",
          mode: "lines+markers",
          line: { color: "#7C3AED", width: 2.5, shape: "spline" },
          marker: { size: 5, color: "#6D28D9" },
          fill: "tozeroy",
          fillcolor: "rgba(124, 58, 237, 0.08)",
          name: "Monthly Revenue"
        }
      ], {
        ...PLOTLY_LAYOUT_BASE,
        margin: { l: 60, r: 25, t: 25, b: 45 },
        yaxis: {
          ...PLOTLY_LAYOUT_BASE.yaxis,
          tickprefix: activeCurrency,
          tickformat: ",.0f"
        }
      }, { responsive: true, displayModeBar: false });
    }

    const distData = await fetchJSON("/api/price_distribution");
    if (distData && distData.prices) {
      Plotly.newPlot("plot-price-dist", [
        {
          x: distData.prices,
          type: "histogram",
          nbinsx: 50,
          marker: { color: "#A78BFA", line: { color: "#7C3AED", width: 1 } },
          name: "Price Frequencies"
        }
      ], {
        ...PLOTLY_LAYOUT_BASE,
        margin: { l: 50, r: 25, t: 25, b: 45 },
        shapes: [
          {
            type: "line",
            x0: distData.mean,
            x1: distData.mean,
            y0: 0,
            y1: 1,
            yref: "paper",
            line: { color: "#D97706", width: 2, dash: "dash" }
          }
        ],
        annotations: [
          {
            x: distData.mean,
            y: 1,
            yref: "paper",
            text: `Mean: ${activeCurrency}${distData.mean}`,
            showarrow: false,
            font: { color: "#D97706", size: 10 }
          }
        ]
      }, { responsive: true, displayModeBar: false });
    }
  }

  /* ── 3. Elasticity Table & Bar Matrix ──────────────────────────────────── */
  async function loadElasticityMatrix() {
    const data = await fetchJSON("/api/elasticity");
    const tbody = el("elasticity-tbody");
    if (!tbody) return;

    if (!data || Object.keys(data).length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center">No reliable models found</td></tr>';
      return;
    }

    const items = Object.entries(data);

    // Populate Table
    tbody.innerHTML = items.map(([prod, info]) => {
      let badgeClass = "badge-inelastic";
      if (info.reliability_badge === "unreliable") badgeClass = "badge-elastic";
      else if (info.reliability_badge === "caution") badgeClass = "badge-unit";

      const ciText = (info.ci_lower != null && info.ci_upper != null)
        ? `[${info.ci_lower.toFixed(2)}, ${info.ci_upper.toFixed(2)}]`
        : "—";

      return `
        <tr>
          <td title="${prod}"><strong>${prod.length > 25 ? prod.slice(0, 25) + "…" : prod}</strong></td>
          <td>${fmt_num(info.elasticity, 2)}</td>
          <td><small>${ciText}</small></td>
          <td><small>${info.p_value != null ? (info.p_value < 0.001 ? "< 0.001" : info.p_value.toFixed(3)) : "—"}</small></td>
          <td>${fmt_num(info.r_squared, 2)}</td>
          <td><span class="${badgeClass}">${info.reliability || info.classification}</span></td>
        </tr>`;
    }).join("");

    // Horizontal Bar Chart
    const prods = items.slice(0, 10).map(x => x[0].slice(0, 20));
    const vals = items.slice(0, 10).map(x => x[1].elasticity);
    const colors = items.slice(0, 10).map(x => {
      if (x[1].reliability_badge === "reliable") return "#0D9488";
      if (x[1].reliability_badge === "caution") return "#D97706";
      return "#DC2626";
    });

    Plotly.newPlot("plot-elasticity-bars", [
      {
        y: prods,
        x: vals,
        type: "bar",
        orientation: "h",
        marker: { color: colors },
        name: "Elasticity (Ed)"
      }
    ], {
      ...PLOTLY_LAYOUT_BASE,
      margin: { l: 120, r: 25, t: 25, b: 40 },
      xaxis: {
        ...PLOTLY_LAYOUT_BASE.xaxis,
        title: "Elasticity Coefficient (Ed)",
        zeroline: true
      }
    }, { responsive: true, displayModeBar: false });
  }

  /* ── 4. Product-Specific Optimization & Curve Plotting ─────────────────── */
  async function loadProductOptimization(product) {
    activeProduct = product;
    const optLoading = el("opt-loading-state");
    const optContent = el("opt-result-content");

    if (optLoading) optLoading.classList.remove("hidden");
    if (optContent) optContent.classList.add("hidden");

    const marginSlider = el("margin-input");
    const marginFrac = marginSlider ? (parseFloat(marginSlider.value) / 100) : 0.65;
    const costMarginParam = (1.0 - marginFrac).toFixed(2); // cost fraction = 1 - margin

    const [optData, diagData, sdData] = await Promise.all([
      fetchJSON(`/api/optimize?product=${encodeURIComponent(product)}&cost_margin=${costMarginParam}`),
      fetchJSON(`/api/product_diagnostics?product=${encodeURIComponent(product)}`),
      fetchJSON(`/api/supply_demand?product=${encodeURIComponent(product)}`)
    ]);

    if (optLoading) optLoading.classList.add("hidden");
    if (optContent) optContent.classList.remove("hidden");

    if (!optData || optData.error) {
      setText("opt-banner-text", "Unable to fit concave optimization model for this item.");
      setText("opt-banner-sub", optData?.error || "Requires at least 2 distinct price levels.");
      setText("opt-current-price", "—");
      setText("opt-optimal-price", "—");
      setText("opt-profit-price", "—");
      setText("opt-revenue-boost", "—");
      setText("opt-reliability", "—");
      return;
    }

    activeOptData = optData;

    // Set Slider bounds around current price
    const pAvg = optData.current_avg_price;
    const slider = el("price-slider");
    if (slider) {
      const minP = Math.max(0.1, (pAvg * 0.2)).toFixed(2);
      const maxP = (pAvg * 3.0).toFixed(2);
      slider.min = minP;
      slider.max = maxP;
      slider.step = ((maxP - minP) / 100).toFixed(2);
      slider.value = optData.optimal_price.toFixed(2);
      setText("sim-slider-min", fmt_currency(minP));
      setText("sim-slider-max", fmt_currency(maxP));
      setText("sim-price-display", fmt_currency(optData.optimal_price));
    }

    // Banner Text
    const boostStr = fmt_pct(optData.revenue_increase_pct);
    setText(
      "opt-banner-text",
      `Optimal Price ${fmt_currency(optData.optimal_price)} (+${optData.revenue_increase_pct}% Projected Revenue)`
    );
    setText("opt-banner-sub", optData.methodology_note);

    setText("opt-current-price", fmt_currency(optData.current_avg_price));
    setText("opt-optimal-price", fmt_currency(optData.optimal_price));
    setText("opt-profit-price", fmt_currency(optData.profit_optimal_price));
    setText("opt-revenue-boost", boostStr);

    if (diagData) {
      const relEl = el("opt-reliability");
      if (relEl) {
        relEl.textContent = diagData.reliability_badge.toUpperCase();
        relEl.style.color = (diagData.reliability_badge === "reliable") ? "var(--teal)" : "var(--rose)";
      }
    }

    // ── Plot 1: Empirical Demand Curve ──────────────────────────────────────
    if (diagData && diagData.scatter_points) {
      const scatX = diagData.scatter_points.map(p => p.price);
      const scatY = diagData.scatter_points.map(p => p.qty);
      const fitX  = diagData.fitted_line.map(p => p.price);
      const fitY  = diagData.fitted_line.map(p => p.qty);

      Plotly.newPlot("plot-demand-curve", [
        {
          x: scatX,
          y: scatY,
          mode: "markers",
          type: "scatter",
          name: "Observations",
          marker: { color: "#7C3AED", size: 8, opacity: 0.6 }
        },
        {
          x: fitX,
          y: fitY,
          mode: "lines",
          type: "scatter",
          name: `OLS Fit (Ed = ${diagData.elasticity})`,
          line: { color: "#0D9488", width: 2.5 }
        }
      ], {
        ...PLOTLY_LAYOUT_BASE,
        xaxis: { ...PLOTLY_LAYOUT_BASE.xaxis, title: `Unit Price (${activeCurrency})` },
        yaxis: { ...PLOTLY_LAYOUT_BASE.yaxis, title: "Quantity Demanded" }
      }, { responsive: true, displayModeBar: false });
    }

    // ── Plot 2: Revenue & Profit Function Curves ────────────────────────────
    if (optData.curve_data && optData.curve_data.length > 0) {
      const cP = optData.curve_data.map(d => d.price);
      const cR = optData.curve_data.map(d => d.revenue);
      const cPi = optData.curve_data.map(d => d.profit);

      Plotly.newPlot("plot-revenue-curve", [
        {
          x: cP,
          y: cR,
          mode: "lines",
          name: "Revenue R(P)",
          line: { color: "#7C3AED", width: 3 }
        },
        {
          x: cP,
          y: cPi,
          mode: "lines",
          name: `Profit Π(P) [Cost=${activeCurrency}${optData.unit_cost}]`,
          line: { color: "#0D9488", width: 2.5, dash: "dot" }
        }
      ], {
        ...PLOTLY_LAYOUT_BASE,
        xaxis: { ...PLOTLY_LAYOUT_BASE.xaxis, title: `Unit Price (${activeCurrency})` },
        yaxis: { ...PLOTLY_LAYOUT_BASE.yaxis, title: `Financial Return (${activeCurrency})` },
        shapes: [
          {
            type: "line",
            x0: optData.optimal_price,
            x1: optData.optimal_price,
            y0: 0,
            y1: 1,
            yref: "paper",
            line: { color: "#7C3AED", width: 2, dash: "dash" }
          },
          {
            type: "line",
            x0: optData.profit_optimal_price,
            x1: optData.profit_optimal_price,
            y0: 0,
            y1: 1,
            yref: "paper",
            line: { color: "#0D9488", width: 2, dash: "dash" }
          }
        ]
      }, { responsive: true, displayModeBar: false });
    }

    // ── Plot 3: Market Clearing Simulation ──────────────────────────────────
    if (sdData && sdData.prices) {
      Plotly.newPlot("plot-supply-demand", [
        {
          x: sdData.prices,
          y: sdData.demand_curve,
          mode: "lines",
          name: "Empirical Demand D(P)",
          line: { color: "#7C3AED", width: 2.5 }
        },
        {
          x: sdData.prices,
          y: sdData.supply_curve,
          mode: "lines",
          name: "Calibrated Supply S(P) [εs=0.8]",
          line: { color: "#D97706", width: 2.5, dash: "dash" }
        }
      ], {
        ...PLOTLY_LAYOUT_BASE,
        margin: { l: 55, r: 25, t: 20, b: 35 },
        xaxis: { ...PLOTLY_LAYOUT_BASE.xaxis, title: `Price (${activeCurrency})` },
        yaxis: { ...PLOTLY_LAYOUT_BASE.yaxis, title: "Market Clearing Quantity" }
      }, { responsive: true, displayModeBar: false });
    }

    // Run initial simulation calculation
    runLiveSimulation(optData.optimal_price, product);
  }

  /* ── 5. Live Interactive Price Simulator ───────────────────────────────── */
  async function runLiveSimulation(price, product) {
    const url = `/api/simulate?price=${encodeURIComponent(price)}&product=${encodeURIComponent(product)}`;
    const data = await fetchJSON(url);

    if (!data || data.error) {
      setText("sim-qty", "—");
      setText("sim-rev", "—");
      setText("sim-profit", "—");
      setText("sim-vs-opt", "—");
      return;
    }

    setText("sim-qty", fmt_num(data.estimated_quantity, 1));
    setText("sim-rev", fmt_currency(data.estimated_revenue));
    setText("sim-profit", fmt_currency(data.estimated_profit));

    const vsOpt = el("sim-vs-opt");
    if (vsOpt) {
      const pct = parseFloat(data.vs_optimal_pct);
      if (isNaN(pct)) {
        vsOpt.textContent = "—";
        vsOpt.style.color = "";
      } else {
        vsOpt.textContent = fmt_pct(pct);
        vsOpt.style.color = (pct >= -3) ? "var(--teal)" : "var(--rose)";
      }
    }
  }

  function setupSlider() {
    const slider = el("price-slider");
    const display = el("sim-price-display");
    const select = el("product-select");
    if (!slider || !display || !select) return;

    slider.addEventListener("input", () => {
      const price = parseFloat(slider.value);
      display.textContent = fmt_currency(price);

      clearTimeout(simDebounce);
      simDebounce = setTimeout(() => {
        if (select.value) {
          runLiveSimulation(price, select.value);
        }
      }, 150);
    });
  }

  /* ── 6. File Upload & Sample Engine ────────────────────────────────────── */
  function setupUpload() {
    const dropZone = el("drop-zone");
    const fileInput = el("file-input");
    const fileList = el("file-list");
    const actions = el("upload-actions");
    const analyseBtn = el("analyse-btn");
    const clearBtn = el("clear-btn");
    const uploadError = el("upload-error");
    const curSelect = el("currency-select");
    const sampleBtn = el("load-sample-btn");

    function renderFileList() {
      if (uploadedFiles.length === 0) {
        fileList.innerHTML = "";
        actions.style.display = "none";
        analyseBtn.disabled = true;
        return;
      }
      actions.style.display = "flex";
      analyseBtn.disabled = false;
      uploadError.classList.add("hidden");

      fileList.innerHTML = uploadedFiles.map((f, idx) => `
        <div class="file-item">
          <span class="file-item-icon">${f.name.endsWith(".csv") ? "📄" : "📊"}</span>
          <span class="file-item-name" title="${f.name}">${f.name}</span>
          <span class="file-item-size">${fmt_size(f.size)}</span>
          <button class="file-item-remove" data-idx="${idx}" title="Remove file">✕</button>
        </div>
      `).join("");

      document.querySelectorAll(".file-item-remove").forEach(btn => {
        btn.addEventListener("click", e => {
          e.stopPropagation();
          const idx = parseInt(btn.dataset.idx, 10);
          uploadedFiles.splice(idx, 1);
          renderFileList();
        });
      });
    }

    function addFiles(newFiles) {
      const validExts = [".csv", ".xlsx", ".xls"];
      let hasError = false;

      Array.from(newFiles).forEach(f => {
        const ext = "." + f.name.split(".").pop().toLowerCase();
        if (!validExts.includes(ext)) {
          showError(`Unsupported file format: ${f.name}. Please upload CSV or Excel files.`);
          hasError = true;
          return;
        }
        if (uploadedFiles.length >= 10) {
          showError("Maximum upload batch is 10 files.");
          hasError = true;
          return;
        }
        if (!uploadedFiles.some(item => item.name === f.name && item.size === f.size)) {
          uploadedFiles.push(f);
        }
      });

      if (!hasError) uploadError.classList.add("hidden");
      renderFileList();
    }

    function showError(msg) {
      uploadError.textContent = msg;
      uploadError.classList.remove("hidden");
    }

    if (dropZone) {
      ["dragenter", "dragover"].forEach(evt => {
        dropZone.addEventListener(evt, e => {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.add("drag-over");
        });
      });
      ["dragleave", "drop"].forEach(evt => {
        dropZone.addEventListener(evt, e => {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.remove("drag-over");
        });
      });
      dropZone.addEventListener("drop", e => {
        if (e.dataTransfer && e.dataTransfer.files) {
          addFiles(e.dataTransfer.files);
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener("change", e => {
        if (e.target.files) {
          addFiles(e.target.files);
          fileInput.value = "";
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        uploadedFiles = [];
        renderFileList();
      });
    }

    if (analyseBtn) {
      analyseBtn.addEventListener("click", async () => {
        if (uploadedFiles.length === 0) return;

        const overlay = el("processing-overlay");
        const stepText = el("processing-step");
        const bar = el("processing-bar");

        overlay.classList.remove("hidden");
        bar.style.width = "25%";
        stepText.textContent = "Ingesting and cleaning transaction records...";

        const formData = new FormData();
        uploadedFiles.forEach(f => formData.append("files", f));
        formData.append("currency", curSelect ? curSelect.value : "£");

        try {
          setTimeout(() => {
            bar.style.width = "55%";
            stepText.textContent = "Estimating empirical elasticity coefficients & confidence intervals...";
          }, 800);

          setTimeout(() => {
            bar.style.width = "85%";
            stepText.textContent = "Fitting log-quadratic concave revenue curves & Lerner markup points...";
          }, 1600);

          const res = await fetch("/api/upload", { method: "POST", body: formData });
          const result = await res.json();

          if (!res.ok || result.error) {
            throw new Error(result.error || "Analysis pipeline failed.");
          }

          bar.style.width = "100%";
          stepText.textContent = "Calibration complete!";

          setTimeout(() => {
            activeCurrency = result.currency_symbol || "£";
            const cSel = el("dashboard-currency-select");
            if (cSel) cSel.value = activeCurrency;

            const select = el("product-select");
            if (select && result.top_products) {
              select.innerHTML = result.top_products
                .map(p => `<option value="${p}">${p}</option>`)
                .join("");
            }

            loadSummary();
            loadMacroCharts();
            loadElasticityMatrix();
            if (result.top_products && result.top_products.length > 0) {
              loadProductOptimization(result.top_products[0]);
            }

            overlay.classList.add("hidden");
            el("upload-screen").classList.add("hidden");
            el("dashboard").classList.remove("hidden");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }, 500);
        } catch (err) {
          overlay.classList.add("hidden");
          showError(err.message || "Failed to parse files.");
        }
      });
    }

    // Sample bypass button
    if (sampleBtn) {
      sampleBtn.addEventListener("click", () => {
        el("upload-screen").classList.add("hidden");
        el("dashboard").classList.remove("hidden");
        loadSummary();
        loadMacroCharts();
        loadElasticityMatrix();
        const sel = el("product-select");
        if (sel && sel.value) {
          loadProductOptimization(sel.value);
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    // New analysis switch
    const newAnBtn = el("new-analysis-btn");
    if (newAnBtn) {
      newAnBtn.addEventListener("click", () => {
        el("dashboard").classList.add("hidden");
        el("upload-screen").classList.remove("hidden");
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }
  }

  /* ── 7. Methodology Modal & Selectors ──────────────────────────────────── */
  function setupInteractions() {
    // Product select change
    const pSel = el("product-select");
    if (pSel) {
      pSel.addEventListener("change", () => {
        if (pSel.value) loadProductOptimization(pSel.value);
      });
    }

    // Margin slider change
    const mSlider = el("margin-input");
    const mDisplay = el("margin-display");
    if (mSlider && mDisplay) {
      mSlider.addEventListener("input", () => {
        mDisplay.textContent = mSlider.value + "%";
        if (pSel && pSel.value) {
          loadProductOptimization(pSel.value);
        }
      });
    }

    // Currency inline switch
    const curSel = el("dashboard-currency-select");
    if (curSel) {
      curSel.addEventListener("change", () => {
        activeCurrency = curSel.value;
        loadSummary();
        loadMacroCharts();
        if (pSel && pSel.value) {
          loadProductOptimization(pSel.value);
        }
      });
    }

    // Modal controls
    const openBtn = el("open-methodology-btn");
    const closeBtn = el("close-methodology-btn");
    const modal = el("methodology-modal");
    if (openBtn && modal) {
      openBtn.addEventListener("click", () => modal.classList.remove("hidden"));
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    }
    if (modal) {
      modal.addEventListener("click", e => {
        if (e.target === modal) modal.classList.add("hidden");
      });
    }
  }

  /* ── Initialization ────────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    setupUpload();
    setupSlider();
    setupInteractions();

    // Initial check: if summary has data, render dashboard directly
    fetchJSON("/api/summary").then(data => {
      if (data && data.total_rows && data.total_rows > 0) {
        el("upload-screen").classList.add("hidden");
        el("dashboard").classList.remove("hidden");
        loadSummary();
        loadMacroCharts();
        loadElasticityMatrix();
        const pSel = el("product-select");
        if (pSel && pSel.value) {
          loadProductOptimization(pSel.value);
        }
      }
    });
  });
})();
