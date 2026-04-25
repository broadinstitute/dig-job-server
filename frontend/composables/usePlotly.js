// frontend/composables/usePlotly.js
// Lazy-load Plotly only on /falcon. The import promise is cached so
// subsequent mounts are immediate.

let plotlyPromise = null;
const observers = new WeakMap();

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
