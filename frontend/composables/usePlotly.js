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
    return el;
  }

  async function unmount(el) {
    if (!el) return;
    const Plotly = await loadPlotly();
    Plotly.purge(el);
  }

  return { getPlotly: loadPlotly, mount, unmount };
}
