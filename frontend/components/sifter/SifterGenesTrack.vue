<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import {
  layoutGenesInLanes, renderGenesTrack, computeGenesTrackCanvasHeight,
  computeGeneTrackHitRegions, findGeneHitAtCanvasPoint,
} from "~/utils/sifter/genesTrackRender";
import { normalizePlotMargin, setupPlotCanvas } from "~/utils/sifter/plotShared";

const props = defineProps({
  genes: { type: Array, default: () => [] },
  visibleRegion: { type: Object, required: true },
});
const emit = defineEmits(["select-gene"]);

const canvasEl = ref(null);
const containerEl = ref(null);
const hitRegions = ref([]);
const margin = normalizePlotMargin({ top: 8, right: 20, bottom: 8, left: 56 });
let observer = null;

// xPosByPixel is pixels-per-base-pair, a NUMBER. Upstream uses it as
// `xStart + (gene.start - xMin) * xPosByPixel`; a callback here yields NaN.
const pixelsPerBp = (region, plotWidth) =>
  plotWidth / Math.max(region.end - region.start, 1);

function draw() {
  const canvas = canvasEl.value;
  const container = containerEl.value;
  if (!canvas || !container) return;
  const width = container.clientWidth;
  const region = props.visibleRegion;

  // layoutGenesInLanes returns { layouts, laneCount } — NOT an array.
  const { laneCount } = layoutGenesInLanes(
    props.genes, region.start, region.end, margin.left,
    pixelsPerBp(region, width - margin.left - margin.right),
  );
  const height = computeGenesTrackCanvasHeight(margin, Math.max(laneCount, 1));
  const ctx = setupPlotCanvas(canvas, width, height);
  if (!ctx) return;
  ctx.clearRect(0, 0, width, height);

  // renderGenesTrack takes visibleRegion, not xMin/xMax, and needs canvasHeight.
  renderGenesTrack(ctx, {
    genes: props.genes,
    visibleRegion: region,
    margin,
    canvasWidth: width,
    canvasHeight: height,
  });
  // computeGeneTrackHitRegions takes (genes, visibleRegion, margin, canvasWidth, ctx).
  hitRegions.value = computeGeneTrackHitRegions(props.genes, region, margin, width, ctx);
}

function onClick(event) {
  const canvas = canvasEl.value;
  const rect = canvas.getBoundingClientRect();
  // setupPlotCanvas renders at internal canvas coordinates that are twice the
  // CSS display size (see plotShared.js), but getBoundingClientRect() reports
  // CSS pixels. Scale client offsets into canvas-internal coordinates before
  // hit-testing against hitRegions, which are expressed in those internal
  // coordinates.
  if (rect.width === 0 || rect.height === 0) return;
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const x = (event.clientX - rect.left) * scaleX;
  const y = (event.clientY - rect.top) * scaleY;
  const hit = findGeneHitAtCanvasPoint(hitRegions.value, x, y);
  if (hit) emit("select-gene", hit.gene);
}

onMounted(() => {
  draw();
  observer = new ResizeObserver(draw);
  if (containerEl.value) observer.observe(containerEl.value);
});
onBeforeUnmount(() => observer?.disconnect());
watch(() => [props.genes, props.visibleRegion], draw, { deep: true });
</script>

<template>
  <div ref="containerEl" class="w-full">
    <canvas ref="canvasEl" class="w-full cursor-pointer" @click="onClick" />
  </div>
</template>
