<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import {
  buildPlotPoints,
  LD_LEGEND_ENTRIES,
  LD_REFERENCE_COLOR,
} from "~/utils/sifter/associationsPlotData";
import {
  renderPlotDot, setupPlotCanvas, normalizePlotMargin, VKS_PLOT_DISPLAY_HEIGHT,
  renderRecombinationLine, renderPlotAxis, canvasPointerPosition,
} from "~/utils/sifter/plotShared";
import { renderStar } from "~/utils/sifter/_portal/plotUtils";
import { computeRegionPlotWidth } from "~/utils/sifter/genesTrackRender";

const props = defineProps({
  rows: { type: Array, default: () => [] },
  visibleRegion: { type: Object, required: true },
  refRow: { type: Object, default: null },
  recombination: { type: Object, default: null },
});
const emit = defineEmits(["select-variant"]);

const canvasEl = ref(null);
const containerEl = ref(null);
const points = ref([]);
// Margin is sized for renderPlotAxis's fixed 24px (2x-resolution) tick font —
// see plotShared.js's renderPlotAxis doc comment. left/right are wider than a
// bare scatter would need because type: "asso" (below) always draws a second,
// right-hand recombination-rate axis + rotated label, matching upstream's
// VariantSifterAssociationRegionPlot.vue call — there is no "asso" variant
// without it. Don't shrink these to reclaim plot width; it clips tick labels
// instead (see associationsPlotData.js buildPlotPoints' yMin/yMax comment for
// why the axis and the dots must never disagree on scale, which is the whole
// reason this axis exists).
const margin = normalizePlotMargin({ top: 10, right: 110, bottom: 60, left: 130 });
let observer = null;

function draw() {
  const canvas = canvasEl.value;
  const container = containerEl.value;
  if (!canvas || !container) return;
  // setupPlotCanvas expects a 2x-internal-pixel canvas.width (retina sizing,
  // matching internalHeight which is already VKS_PLOT_DISPLAY_HEIGHT * 2) —
  // see setupPlotCanvas doc comment in plotShared.js.
  const width = container.clientWidth * 2;
  const height = VKS_PLOT_DISPLAY_HEIGHT * 2;
  // setupPlotCanvas sizes the canvas, resets the transform and clears it.
  const ctx = setupPlotCanvas(canvas, width, height);
  if (!ctx) return;

  // Same x-scale formula buildPlotPoints uses internally (computeRegionPlotWidth,
  // asymmetric by upstream design) — matching it here means the axis's
  // position ticks land under the same x pixels the dots are drawn at.
  const plotWidth = computeRegionPlotWidth(width, margin);
  const plotHeight = height - margin.top - margin.bottom;

  const built = buildPlotPoints(props.rows, props.visibleRegion, { width, height, margin });
  points.value = built.points;

  // Drawn before the recomb line/dots, mirroring upstream's render order.
  // yMin/yMax come straight from buildPlotPoints so the axis and the dots
  // always agree on the y scale.
  renderPlotAxis(ctx, {
    margin,
    plotWidth,
    plotHeight,
    yMin: built.yMin,
    yMax: built.yMax,
    xMin: props.visibleRegion.start,
    xMax: props.visibleRegion.end,
    type: "asso",
    yAxisLabel: "-log10(p-value)",
    xAxisLabel: "",
  });

  renderRecombinationLine(ctx, margin, plotWidth, plotHeight, props.visibleRegion, props.recombination);

  for (const p of points.value) renderPlotDot(ctx, p.x, p.y, p.color);

  const refVariantId = props.refRow?.["Variant ID"];
  if (refVariantId != null) {
    // enrichAssociationRowsWithLdScoresForRef returns NEW row objects
    // (rows.map(row => ({...row, LDS}))), so refRow is never identical
    // (===) to any row in points.value once LD enrichment has run. Match
    // on the decorated "Variant ID" field instead of object identity.
    const refPoint = points.value.find((p) => p.row?.["Variant ID"] === refVariantId);
    if (refPoint) {
      renderStar(ctx, refPoint.x, refPoint.y, 5, 10, 6,
                 LD_REFERENCE_COLOR, LD_REFERENCE_COLOR);
    }
  }
}

function onClick(event) {
  const canvas = canvasEl.value;
  const rect = canvas.getBoundingClientRect();
  // Guard against a zero-sized rect (before layout settles, or while hidden):
  // canvasPointerPosition divides by rect.width/height and would return
  // Infinity/NaN in that case.
  if (rect.width === 0 || rect.height === 0) return;
  const { x, y } = canvasPointerPosition(event, canvas);
  let best = null;
  let bestDist = Infinity;
  for (const p of points.value) {
    const d = (p.x - x) ** 2 + (p.y - y) ** 2;
    if (d < bestDist) { bestDist = d; best = p; }
  }
  if (best && bestDist <= 20 ** 2) emit("select-variant", best.row);
}

onMounted(() => {
  draw();
  observer = new ResizeObserver(draw);
  if (containerEl.value) observer.observe(containerEl.value);
});
onBeforeUnmount(() => observer?.disconnect());
watch(() => [props.rows, props.visibleRegion, props.refRow, props.recombination], draw, { deep: true });
</script>

<template>
  <div ref="containerEl" class="w-full">
    <div class="mb-1 flex flex-wrap items-center gap-3 text-xs">
      <span class="flex items-center gap-1 font-semibold">
        <span
          class="inline-block h-3 w-3 rotate-45"
          :style="{ backgroundColor: LD_REFERENCE_COLOR }"
        />
        Reference variant
      </span>
      <span v-for="entry in LD_LEGEND_ENTRIES" :key="entry.label" class="flex items-center gap-1">
        <span class="inline-block h-3 w-3 rounded" :style="{ backgroundColor: entry.color }" />
        {{ entry.label }}
      </span>
    </div>
    <canvas ref="canvasEl" class="w-full cursor-pointer" @click="onClick" />
  </div>
</template>
