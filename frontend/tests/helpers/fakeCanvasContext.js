// Recording 2D context stand-in. The sifter's renderers take a ctx and issue
// drawing calls, so asserting the call sequence gives real coverage of plot
// geometry without pixel diffing.
const METHODS = [
  "beginPath", "closePath", "moveTo", "lineTo", "arc", "rect", "fill",
  "stroke", "fillRect", "clearRect", "fillText", "strokeText", "save",
  "restore", "translate", "scale", "setLineDash", "measureText", "clip",
  "quadraticCurveTo", "bezierCurveTo",
];

export function createFakeCtx() {
  const ctx = {
    calls: [],
    fillStyle: null,
    strokeStyle: null,
    lineWidth: null,
    font: null,
    textAlign: null,
    canvas: { width: 1000, height: 300 },
  };
  for (const fn of METHODS) {
    ctx[fn] = (...args) => {
      ctx.calls.push({ fn, args });
      if (fn === "measureText") return { width: String(args[0] ?? "").length * 6 };
      return undefined;
    };
  }
  return ctx;
}
