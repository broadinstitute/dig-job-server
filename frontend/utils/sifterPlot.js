// Pure Plotly {data, layout} builder for the sifter region plot. No DOM.
// Consumers mount via usePlotly(). Mirrors the -log10(P) scattergl approach in
// composables/useFalconPlots.js.

export function buildAssociationsScatter(records, { region } = {}) {
  const x = [];
  const y = [];
  const text = [];
  for (const r of records) {
    const p = Number(r.pValue);
    if (!(p > 0)) continue;
    x.push(Number(r.position));
    y.push(-Math.log10(p));
    const beta = r.beta != null ? `<br>β=${r.beta}` : "";
    text.push(`${r.chromosome}:${r.position} ${r.reference}/${r.alt}<br>p=${p.toExponential(2)}${beta}`);
  }
  const data = [
    {
      type: "scattergl",
      mode: "markers",
      x,
      y,
      text,
      hoverinfo: "text",
      marker: { size: 6, color: "#4f46e5" },
    },
  ];
  const layout = {
    title: region ? `Associations — ${region}` : "Associations",
    xaxis: { title: "Position" },
    yaxis: { title: "-log10(P)" },
    hovermode: "closest",
    margin: { t: 40, r: 20, b: 50, l: 60 },
  };
  return { data, layout };
}
