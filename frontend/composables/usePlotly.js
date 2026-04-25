// frontend/composables/usePlotly.js
// Lazy-load Plotly only on /falcon. The import promise is cached so
// subsequent mounts are immediate.

let plotlyPromise = null;

function loadPlotly() {
  if (!plotlyPromise) {
    plotlyPromise = import("plotly.js-dist-min").then((m) => m.default || m);
  }
  return plotlyPromise;
}

export function usePlotly() {
  async function mount(el, spec /* { data, layout, config? } */) {
    const Plotly = await loadPlotly();
    const config = { responsive: true, displaylogo: false, ...(spec.config || {}) };
    await Plotly.newPlot(el, spec.data, spec.layout, config);
    // PrimeVue Tabs lazy-mounts panels: when our plot first paints, the
    // host is display:none, so Plotly latches a 0-width canvas. After the
    // next animation frame the panel has its real dimensions; nudge Plotly
    // to recompute. Fixes "Genes Plot / Variants Plot squished to the left".
    requestAnimationFrame(() => {
      try {
        if (el && el.offsetParent !== null) Plotly.Plots.resize(el);
      } catch {
        // best-effort resize; safe to swallow if Plotly disposed the element.
      }
    });
    return el;
  }

  async function unmount(el) {
    if (!el) return;
    const Plotly = await loadPlotly();
    Plotly.purge(el);
  }

  return { getPlotly: loadPlotly, mount, unmount };
}
