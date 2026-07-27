<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import {
  buildPlotPoints,
  LD_LEGEND_ENTRIES,
  LD_REFERENCE_COLOR,
} from "~/utils/sifter/associationsPlotData";
import {
  renderPlotDot, setupPlotCanvas, normalizePlotMargin, VKS_PLOT_DISPLAY_HEIGHT,
  renderRecombinationLine,
} from "~/utils/sifter/plotShared";
import { renderStar } from "~/utils/sifter/_portal/plotUtils";

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
const margin = normalizePlotMargin({ top: 10, right: 20, bottom: 28, left: 56 });
let observer = null;

function draw() {
  const canvas = canvasEl.value;
  const container = containerEl.value;
  if (!canvas || !container) return;
  const width = container.clientWidth;
  const height = VKS_PLOT_DISPLAY_HEIGHT * 2;
  // setupPlotCanvas sizes the canvas, resets the transform and clears it.
  const ctx = setupPlotCanvas(canvas, width, height);
  if (!ctx) return;

  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  renderRecombinationLine(ctx, margin, plotWidth, plotHeight, props.visibleRegion, props.recombination);

  points.value = buildPlotPoints(props.rows, props.visibleRegion, { width, height, margin });
  for (const p of points.value) renderPlotDot(ctx, p.x, p.y, p.color);

  if (props.refRow) {
    const refPoint = points.value.find((p) => p.row === props.refRow);
    if (refPoint) {
      renderStar(ctx, refPoint.x, refPoint.y, 5, 10, 6,
                 LD_REFERENCE_COLOR, LD_REFERENCE_COLOR);
    }
  }
}

function onClick(event) {
  const rect = canvasEl.value.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
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
