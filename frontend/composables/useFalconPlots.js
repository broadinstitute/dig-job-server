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

    const layout = {
      xaxis: { title: "PROBABILITY" },
      yaxis: { title: "Negative Log10(P-Value)" },
      hovermode: "closest",
      margin: { t: 30, l: 60, r: 20, b: 50 },
      showlegend: true,
      legend: {
        title: { text: "CLUMP ID" },
        x: 1.02,
        y: 1,
        xanchor: "left",
        yanchor: "top",
        bgcolor: "rgba(255,255,255,0.8)",
        bordercolor: "#d1d5db",
        borderwidth: 1,
      },
    };
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
   */
  function buildLogPreprocessBarSpec() {
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
    const colors = chrs.map((_, i) => FALCON_PALETTE[i % FALCON_PALETTE.length]);
    return {
      data: [
        {
          x: chrs,
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

  return {
    buildGenesScatterSpec,
    buildVariantsScatterSpec,
    buildLogIterHistogramSpec,
    buildLogPreprocessBarSpec,
  };
}
