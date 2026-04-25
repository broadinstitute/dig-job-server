// frontend/composables/useFalconPlots.js
// Pure {data, layout} builders for Plotly. No DOM. Consumers mount via usePlotly().
//
// Scatter:    port of PEGS/src/dashboard/app.js:536-729 (renderScatterPlot).
// Histogram + bar: port of LogSummaryModule pieces (PEGS app.js:2511-2826).
import {
  getColorForClump,
  UNASSIGNED_CLUMP_ID,
  FALCON_PALETTE,
} from "~/utils/falcon/colorPalette";
import {
  STRICT_TOP_MIN_PROB,
  STRICT_TOP_MIN_NEGP,
} from "~/utils/falcon/config";
import { useFalconFilters } from "~/composables/useFalconFilters";

export function useFalconPlots(store) {
  const { getNegP, normalizedClumpId } = useFalconFilters(store);

  function buildScatterSpec(name /* 'genes' | 'variants' */) {
    const data = store.datasets[name].data;
    const isVariants = name === "variants";
    const keyName = isVariants ? "VARIANT" : "GENE";
    const keyLead = isVariants ? "LEAD_SNP" : "NEAREST_TO_LEAD";
    const region = name === "genes" ? store.plotFilters.genes : { chr: "All" };

    // Pass 1: top-per-clump under STRICT criteria (independent from user filter).
    const topPerClump = new Map();
    data.forEach((row, idx) => {
      const prob = parseFloat(row["PROBABILITY"]);
      const negP = getNegP(row, isVariants);
      if (isNaN(prob) || prob < STRICT_TOP_MIN_PROB) return;
      if (isNaN(negP) || negP < STRICT_TOP_MIN_NEGP) return;
      if (!isVariants && region.chr !== "All") {
        const rChr = row["CHR"] ? row["CHR"].toString().trim() : "";
        if (rChr !== region.chr) return;
        const rS = parseFloat(row["START"]);
        const rE = parseFloat(row["END"]);
        if (!isNaN(rS) && rS > region.maxEnd) return;
        if (!isNaN(rE) && rE < region.minStart) return;
      }
      const clumpId = normalizedClumpId(row);
      if (!topPerClump.has(clumpId) || prob > topPerClump.get(clumpId).prob) {
        topPerClump.set(clumpId, { index: idx, prob });
      }
    });

    // Pass 2: build per-clump traces, applying user globalFilter for display.
    const groups = new Map();
    const topData = { x: [], y: [], text: [] };

    data.forEach((row, idx) => {
      const prob = parseFloat(row["PROBABILITY"]);
      const negP = getNegP(row, isVariants);

      if (store.globalFilter.active) {
        if (isNaN(prob) || prob < store.globalFilter.minProb) return;
        if (isNaN(negP) || negP < store.globalFilter.minNegP) return;
      }
      if (!isVariants && region.chr !== "All") {
        const rChr = row["CHR"] ? row["CHR"].toString().trim() : "";
        if (rChr !== region.chr) return;
        const rS = parseFloat(row["START"]);
        const rE = parseFloat(row["END"]);
        if (!isNaN(rS) && rS > region.maxEnd) return;
        if (!isNaN(rE) && rE < region.minStart) return;
      }
      if (isNaN(prob) || isNaN(negP)) return;

      const clumpId = normalizedClumpId(row);
      if (!groups.has(clumpId)) {
        groups.set(clumpId, { x: [], y: [], text: [], symbols: [], sizes: [] });
      }
      const g = groups.get(clumpId);
      g.x.push(prob);
      g.y.push(negP);

      const leadRaw = String(row[keyLead] || "").toLowerCase().trim();
      const isLead = leadRaw === "true" || leadRaw === "1" || leadRaw === "yes";
      g.symbols.push(isLead ? "star" : "circle");
      g.sizes.push(isLead ? 14 : 8);

      const isTop = topPerClump.get(clumpId)?.index === idx;
      const typeLabel = isVariants ? "Variant" : "Gene";
      const itemName = row[keyName] || row["RSID"] || row["SNP"] || "Unknown";

      let badges = "";
      if (isLead) badges += `<br><b>⭐ Lead ${isVariants ? "SNP" : "Gene"}</b>`;
      if (isTop) badges += `<br><b style="color:#9333ea;">🏆 Top ${typeLabel}</b>`;

      const text = `${typeLabel}: ${itemName}${badges}<br>Clump: ${clumpId}<br>Prob: ${prob}<br>NegP: ${negP.toFixed(4)}`;
      g.text.push(text);

      if (isTop && clumpId !== UNASSIGNED_CLUMP_ID) {
        topData.x.push(prob);
        topData.y.push(negP);
        topData.text.push(text);
      }
    });

    const traces = [];
    Array.from(groups.keys()).sort().forEach((clumpId) => {
      const g = groups.get(clumpId);
      traces.push({
        x: g.x,
        y: g.y,
        text: g.text,
        name: clumpId,
        mode: "markers",
        type: "scattergl",
        hoverinfo: "text",
        marker: {
          symbol: g.symbols,
          size: g.sizes,
          opacity: 0.8,
          color: getColorForClump(store.caches.clumpColor, clumpId),
        },
      });
    });
    if (topData.x.length > 0) {
      traces.push({
        x: topData.x,
        y: topData.y,
        text: topData.text,
        name: isVariants ? "Top Variants" : "Top Genes",
        mode: "markers",
        type: "scattergl",
        hoverinfo: "text",
        marker: {
          symbol: "circle-open",
          size: 22,
          color: "#9333ea",
          line: { width: 3 },
        },
      });
    }

    // The CLUMP ID legend is only useful while it stays compact. Once the
    // dataset has more clumps than will visually fit alongside the plot
    // (~25), Plotly's external legend column eats most of the horizontal
    // space and makes the scatter unreadable. Hide it past that threshold;
    // the per-trace name is still in hover text + the data table.
    const LEGEND_TRACE_LIMIT = 25;
    const showLegend = traces.length <= LEGEND_TRACE_LIMIT;
    const layout = {
      xaxis: { title: "PROBABILITY" },
      yaxis: { title: "Negative Log10(P-Value)" },
      hovermode: "closest",
      margin: { t: 30, l: 60, r: showLegend ? 20 : 30, b: 50 },
      showlegend: showLegend,
    };
    if (showLegend) {
      layout.legend = {
        title: { text: "CLUMP ID" },
        x: 1.02,
        y: 1,
        xanchor: "left",
        yanchor: "top",
        bgcolor: "rgba(255,255,255,0.8)",
        bordercolor: "#d1d5db",
        borderwidth: 1,
      };
    }
    return { data: traces, layout };
  }

  function buildGenesScatterSpec() {
    return buildScatterSpec("genes");
  }
  function buildVariantsScatterSpec() {
    return buildScatterSpec("variants");
  }

  /**
   * Per-component histogram card (LogSummary). Returns { data, layout, stats }.
   */
  function buildLogIterHistogramSpec(component, chrView /* 'all' | chromosome */) {
    const logStore = store.datasets.log;
    const values = [];
    if (chrView === "all") {
      Object.keys(logStore.data).forEach((chr) => {
        values.push(...(logStore.data[chr][component] || []));
      });
    } else if (logStore.data[chrView]) {
      values.push(...(logStore.data[chrView][component] || []));
    }
    const positives = values.filter((v) => v > 0);
    const sorted = [...positives].sort((a, b) => a - b);
    const stats =
      sorted.length === 0
        ? null
        : {
            n: sorted.length,
            min: sorted[0],
            max: sorted[sorted.length - 1],
            mean: sorted.reduce((a, b) => a + b, 0) / sorted.length,
            median:
              sorted.length % 2
                ? sorted[Math.floor(sorted.length / 2)]
                : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2,
          };
    const idx =
      Math.abs(
        [...component].reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 0),
      ) % FALCON_PALETTE.length;
    return {
      stats,
      data: [
        {
          x: positives,
          type: "histogram",
          name: component,
          marker: { color: FALCON_PALETTE[idx], line: { color: "white", width: 1 } },
          opacity: 0.8,
        },
      ],
      layout: {
        margin: { t: 10, l: 45, r: 20, b: 40 },
        xaxis: { title: "Time (Seconds)", zeroline: false },
        yaxis: { title: "Count" },
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
        autosize: true,
      },
    };
  }

  /**
   * Per-chromosome total pre-process time bar chart.
   * `chrView` highlights one chromosome in green if not 'all'.
   */
  function buildLogPreprocessBarSpec(chrView /* 'all' | chromosome */) {
    const logStore = store.datasets.log;
    const chrs = Array.from(logStore.chromosomes).sort((a, b) => {
      const na = parseInt(a, 10);
      const nb = parseInt(b, 10);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      return a.localeCompare(b);
    });
    const totals = chrs.map((chr) => {
      const pp = logStore.preProcess[chr] || {};
      return Object.values(pp).reduce((a, b) => a + b, 0);
    });
    const colors = chrs.map((c) =>
      chrView && chrView !== "all" && chrView === c ? "#047857" : "#3b82f6",
    );
    return {
      data: [
        {
          x: chrs.map((c) => `Chr ${c}`),
          y: totals,
          type: "bar",
          marker: { color: colors },
          text: totals.map((t) => `${t.toFixed(2)}s`),
          textposition: "auto",
          hoverinfo: "x+y",
        },
      ],
      layout: {
        margin: { t: 10, l: 45, r: 20, b: 40 },
        xaxis: { title: "Chromosome", type: "category" },
        yaxis: { title: "Time (Seconds)" },
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
        autosize: true,
      },
    };
  }

  /**
   * Pre-process step accumulation summary, mirroring LogSummaryModule.drawPlots
   * (PEGS app.js:2584-2636).
   *
   * For chrView='all': totalTime = parallel-wall-time bottleneck (max chr total),
   * and per-step values = max value across chromosomes (worst-case worker).
   * For a specific chromosome: just the values for that chromosome.
   *
   * Returns { perStep: [{ key, time }], totalTime, parallel: bool }.
   */
  function buildLogPreprocessByStepSpec(chrView /* 'all' | chromosome */, preProcessKeys) {
    const logStore = store.datasets.log;
    const perStep = preProcessKeys.map((k) => ({ key: k, time: 0 }));
    let totalTime = 0;
    const parallel = chrView === "all";

    if (parallel) {
      // Wall-time bottleneck = the slowest single chromosome's total.
      let maxChrTotal = 0;
      Object.keys(logStore.preProcess).forEach((chr) => {
        let chrTotal = 0;
        preProcessKeys.forEach((k) => {
          chrTotal += logStore.preProcess[chr][k] || 0;
        });
        if (chrTotal > maxChrTotal) maxChrTotal = chrTotal;
      });
      totalTime = maxChrTotal;

      // Per-step worst case across workers.
      preProcessKeys.forEach((k, i) => {
        let maxVal = 0;
        Object.keys(logStore.preProcess).forEach((chr) => {
          maxVal = Math.max(maxVal, logStore.preProcess[chr][k] || 0);
        });
        perStep[i].time = maxVal;
      });
    } else if (logStore.preProcess[chrView]) {
      preProcessKeys.forEach((k, i) => {
        const v = logStore.preProcess[chrView][k] || 0;
        perStep[i].time = v;
        totalTime += v;
      });
    }

    return { perStep, totalTime, parallel };
  }

  // -------------------------------------------------------------------
  // Executive Summary plot spec builders.
  // Ported verbatim from PEGS app.js SummaryModule.drawUpsetPlot (1083-1208),
  // drawVennDiagram (1210-1234), drawProbDistributionPlot (1236-1273),
  // drawDistancePlot (1275-1310), drawLeadDistancePlot (1313-1349).
  // Each returns { data, layout } (plus `empty: true` when nothing to draw).
  // -------------------------------------------------------------------
  function buildSummaryUpsetSpec(plotRows) {
    const setNames = ["Top", "Lead", "Novel", "Clinical Trials"];
    const combinations = [];
    for (let i = 1; i < 1 << setNames.length; i++) {
      const sets = [];
      for (let j = 0; j < setNames.length; j++) {
        if ((i >> j) & 1) sets.push(setNames[j]);
      }
      combinations.push({ sets, count: 0 });
    }

    (plotRows || []).forEach((d) => {
      const flags = {
        Top: d.role && d.role.includes("Top"),
        Lead: d.role && d.role.includes("Lead"),
        Novel: d.isNovel === true,
        "Clinical Trials": d.hasClinicalTrials === true,
      };
      const combo = combinations.find((c) =>
        setNames.every((s) => flags[s] === c.sets.includes(s)),
      );
      if (combo) combo.count++;
    });

    const plotData = combinations
      .filter((c) => c.count > 0)
      .sort((a, b) => b.count - a.count);

    if (plotData.length === 0) {
      return {
        data: [],
        layout: {
          margin: { t: 40, l: 100, r: 20, b: 40 },
          plot_bgcolor: "rgba(0,0,0,0)",
          paper_bgcolor: "rgba(0,0,0,0)",
        },
        empty: true,
      };
    }

    const xValues = plotData.map((_, i) => i);
    const barCounts = plotData.map((c) => c.count);

    const traceBar = {
      x: xValues,
      y: barCounts,
      type: "bar",
      name: "Intersection Size",
      marker: { color: "#93c5fd" },
      xaxis: "x",
      yaxis: "y",
      hovertemplate: "%{y}<extra></extra>",
    };

    const matrixTraces = [];
    setNames.forEach((setName, setIdx) => {
      matrixTraces.push({
        x: xValues,
        y: Array(xValues.length).fill(setIdx),
        mode: "markers",
        marker: { color: "#e5e7eb", size: 12 },
        showlegend: false,
        xaxis: "x",
        yaxis: "y2",
        hoverinfo: "none",
      });
    });

    plotData.forEach((combo, xIdx) => {
      const activeIdx = [];
      setNames.forEach((setName, setIdx) => {
        if (combo.sets.includes(setName)) activeIdx.push(setIdx);
      });

      if (activeIdx.length > 1) {
        matrixTraces.push({
          x: [xIdx, xIdx],
          y: [Math.min(...activeIdx), Math.max(...activeIdx)],
          mode: "lines",
          line: { color: "#1f2937", width: 3 },
          showlegend: false,
          xaxis: "x",
          yaxis: "y2",
          hoverinfo: "none",
        });
      }

      matrixTraces.push({
        x: Array(activeIdx.length).fill(xIdx),
        y: activeIdx,
        mode: "markers",
        marker: { color: "#1f2937", size: 14 },
        showlegend: false,
        xaxis: "x",
        yaxis: "y2",
        hoverinfo: "none",
      });
    });

    const layout = {
      grid: { rows: 2, columns: 1, pattern: "independent" },
      margin: { t: 40, l: 100, r: 20, b: 40 },
      showlegend: false,
      xaxis: { visible: false, domain: [0, 1] },
      yaxis: {
        title: "Intersection Size",
        domain: [0.4, 1],
        fixedrange: true,
      },
      yaxis2: {
        title: "Sets",
        domain: [0, 0.35],
        tickvals: [0, 1, 2, 3],
        ticktext: setNames,
        range: [-0.5, 3.5],
        autorange: "reversed",
        fixedrange: true,
      },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
      hovermode: "closest",
    };

    return { data: [traceBar, ...matrixTraces], layout };
  }

  function buildSummaryVennSpec(stats) {
    const s = stats || { topOnly: 0, leadOnly: 0, both: 0 };
    const total = s.topOnly + s.leadOnly + s.both;
    const getPct = (v) => (total > 0 ? `${((v / total) * 100).toFixed(1)}%` : "0%");

    const traces = [
      {
        x: [0, 1],
        y: [0, 1],
        mode: "markers",
        marker: { opacity: 0 },
        hoverinfo: "none",
        showlegend: false,
      },
    ];

    const layout = {
      xaxis: { visible: false, range: [0, 1], fixedrange: true },
      yaxis: { visible: false, range: [0, 1], fixedrange: true },
      margin: { t: 30, l: 10, r: 10, b: 10 },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
      shapes: [
        {
          type: "circle",
          xref: "x",
          yref: "y",
          x0: 0.15,
          y0: 0.1,
          x1: 0.65,
          y1: 0.85,
          fillcolor: "rgba(147, 51, 234, 0.3)",
          line: { color: "#9333ea", width: 2 },
        },
        {
          type: "circle",
          xref: "x",
          yref: "y",
          x0: 0.35,
          y0: 0.1,
          x1: 0.85,
          y1: 0.85,
          fillcolor: "rgba(56, 189, 248, 0.3)",
          line: { color: "#38bdf8", width: 2 },
        },
      ],
      annotations: [
        { x: 0.25, y: 0.95, text: "<b>Top</b>", showarrow: false, font: { size: 16, color: "#7e22ce" } },
        { x: 0.75, y: 0.95, text: "<b>Lead</b>", showarrow: false, font: { size: 16, color: "#38bdf8" } },
        { x: 0.25, y: 0.48, text: `<b>${s.topOnly}</b><br>(${getPct(s.topOnly)})`, showarrow: false, font: { size: 14 } },
        { x: 0.75, y: 0.48, text: `<b>${s.leadOnly}</b><br>(${getPct(s.leadOnly)})`, showarrow: false, font: { size: 14, color: "#38bdf8" } },
        { x: 0.5, y: 0.48, text: `<b>${s.both}</b><br>(${getPct(s.both)})`, showarrow: false, font: { size: 14, color: "#111827" } },
      ],
    };

    return { data: traces, layout, empty: total === 0 };
  }

  function buildSummaryProbDistSpec(rows) {
    const buildTrace = (roleFilter, name, color) => {
      const filtered = (rows || []).filter((d) => d.role === roleFilter);
      if (filtered.length === 0) return null;
      return {
        y: filtered.map((d) => d.rawProb),
        text: filtered.map(
          (d) =>
            `<b>${d.name}</b><br>Role: ${d.role}<br>Clump: ${d.clump}<br>Prob: ${d.prob}<br>Sig: ${d.significance}`,
        ),
        type: "box",
        name,
        marker: { color },
        boxpoints: "all",
        jitter: 0.3,
        pointpos: -1.8,
        hoverinfo: "y+text",
      };
    };

    const traces = [
      buildTrace("🏆 Top", "Top Only", "#9333ea"),
      buildTrace("⭐ Lead", "Lead Only", "#38bdf8"),
      buildTrace("🏆 Top & ⭐ Lead", "Both", "#111827"),
    ].filter((t) => t !== null);

    const layout = {
      margin: { t: 20, l: 40, r: 20, b: 30 },
      yaxis: { title: "Probability", range: [-0.05, 1.05] },
      showlegend: false,
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
    };

    return { data: traces, layout, empty: traces.length === 0 };
  }

  function buildSummaryDistanceSpec(distances) {
    if (!distances || distances.length === 0) {
      return {
        data: [],
        layout: {
          margin: { t: 20, l: 60, r: 20, b: 30 },
          plot_bgcolor: "rgba(0,0,0,0)",
          paper_bgcolor: "rgba(0,0,0,0)",
        },
        empty: true,
      };
    }

    const yVals = distances.map((d) => d.dist);
    const textVals = distances.map(
      (d) =>
        `<b>Variant:</b> ${d.variant}<br><b>Gene:</b> ${d.gene}<br><b>Distance:</b> ${d.dist.toLocaleString()} BP`,
    );

    const traces = [
      {
        y: yVals,
        text: textVals,
        type: "box",
        name: "Nearest Gene",
        marker: { color: "#059669" },
        boxpoints: "all",
        jitter: 0.3,
        pointpos: -1.8,
        hoverinfo: "y+text",
      },
    ];

    const layout = {
      margin: { t: 20, l: 60, r: 20, b: 30 },
      yaxis: { title: "Distance (BP)", autorange: true },
      showlegend: false,
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
    };

    return { data: traces, layout };
  }

  function buildSummaryLeadDistanceSpec(leadDistances) {
    if (!leadDistances || leadDistances.length === 0) {
      return {
        data: [],
        layout: {
          margin: { t: 20, l: 60, r: 20, b: 30 },
          plot_bgcolor: "rgba(0,0,0,0)",
          paper_bgcolor: "rgba(0,0,0,0)",
        },
        empty: true,
      };
    }

    const yVals = leadDistances.map((d) => d.dist);
    const textVals = leadDistances.map(
      (d) =>
        `<b>Chr:</b> ${d.chr}<br><b>Variant 1:</b> ${d.v1}<br><b>Variant 2:</b> ${d.v2}<br><b>Distance:</b> ${d.dist.toLocaleString()} BP`,
    );

    const traces = [
      {
        y: yVals,
        text: textVals,
        type: "box",
        name: "Lead-to-Lead",
        marker: { color: "#eab308" },
        boxpoints: "all",
        jitter: 0.3,
        pointpos: -1.8,
        hoverinfo: "y+text",
      },
    ];

    const layout = {
      margin: { t: 20, l: 60, r: 20, b: 30 },
      yaxis: { title: "Distance (BP)", autorange: true },
      showlegend: false,
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
    };

    return { data: traces, layout };
  }

  return {
    buildGenesScatterSpec,
    buildVariantsScatterSpec,
    buildLogIterHistogramSpec,
    buildLogPreprocessBarSpec,
    buildLogPreprocessByStepSpec,
    buildSummaryUpsetSpec,
    buildSummaryVennSpec,
    buildSummaryProbDistSpec,
    buildSummaryDistanceSpec,
    buildSummaryLeadDistanceSpec,
  };
}
