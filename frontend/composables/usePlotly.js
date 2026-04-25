// frontend/composables/usePlotly.js
// Lazy-load Plotly only on /falcon. The import promise is cached so
// subsequent mounts are immediate.

import { watch } from "vue";
import { useTheme } from "~/composables/useTheme";

let plotlyPromise = null;
const observers = new WeakMap();
const mounted = new Set();
let themeWatchAttached = false;

function loadPlotly() {
  if (!plotlyPromise) {
    plotlyPromise = import("plotly.js-dist-min").then((m) => m.default || m);
  }
  return plotlyPromise;
}

function themeLayout(isDark) {
  const fg = isDark ? "#e5e7eb" : "#374151";
  const grid = isDark ? "#374151" : "#e5e7eb";
  const line = isDark ? "#6b7280" : "#9ca3af";
  return {
    font: { color: fg },
    xaxis: { color: fg, gridcolor: grid, linecolor: line, zerolinecolor: grid },
    yaxis: { color: fg, gridcolor: grid, linecolor: line, zerolinecolor: grid },
    yaxis2: { color: fg, gridcolor: grid, linecolor: line, zerolinecolor: grid },
    modebar: {
      orientation: "v",
      bgcolor: isDark ? "rgba(17,24,39,0.6)" : "rgba(255,255,255,0.6)",
      color: fg,
      activecolor: isDark ? "#60a5fa" : "#2563eb",
    },
  };
}

// Deep-merge `src` into `dst` non-destructively (returns new object).
function deepMerge(dst, src) {
  if (!src) return dst;
  if (!dst) return src;
  const out = { ...dst };
  Object.keys(src).forEach((k) => {
    const sv = src[k];
    const dv = dst[k];
    if (sv && typeof sv === "object" && !Array.isArray(sv) &&
        dv && typeof dv === "object" && !Array.isArray(dv)) {
      out[k] = deepMerge(dv, sv);
    } else {
      out[k] = sv;
    }
  });
  return out;
}

export function usePlotly() {
  const { isDarkMode } = useTheme();

  // Attach the global theme watch the first time usePlotly() is called from
  // a component setup (Nuxt context required for useTheme/useState).
  if (!themeWatchAttached) {
    themeWatchAttached = true;
    watch(isDarkMode, async (dark) => {
      const Plotly = await loadPlotly();
      const overrides = themeLayout(dark);
      mounted.forEach((el) => {
        if (!el.isConnected) return;
        try {
          Plotly.relayout(el, overrides);
        } catch {
          // Plotly may have purged this element between frames.
        }
      });
    });
  }

  async function mount(el, spec /* { data, layout, config? } */) {
    const Plotly = await loadPlotly();
    const config = { responsive: true, displaylogo: false, ...(spec.config || {}) };
    const themedLayout = deepMerge(spec.layout || {}, themeLayout(isDarkMode.value));
    await Plotly.newPlot(el, spec.data, themedLayout, config);
    mounted.add(el);

    // PrimeVue Tabs lazy-mounts panels: when our plot first paints inside
    // an inactive tab, the host has zero dimensions and Plotly latches its
    // default 700x450 canvas. `responsive: true` only listens for window
    // resizes, not container size changes. Observe the host so any 0 → real
    // transition (tab activation, sibling reflow) triggers a resize.
    if (observers.has(el)) observers.get(el).disconnect();
    const ro = new ResizeObserver(() => {
      if (!el.isConnected) return;
      try {
        Plotly.Plots.resize(el);
      } catch {
        // Safe to swallow — Plotly may have been purged between frames.
      }
    });
    ro.observe(el);
    observers.set(el, ro);

    return el;
  }

  async function unmount(el) {
    if (!el) return;
    mounted.delete(el);
    const ro = observers.get(el);
    if (ro) {
      ro.disconnect();
      observers.delete(el);
    }
    const Plotly = await loadPlotly();
    Plotly.purge(el);
  }

  return { getPlotly: loadPlotly, mount, unmount };
}
