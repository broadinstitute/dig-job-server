<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import {
  layoutGenesInLanes, renderGenesTrack, computeGenesTrackCanvasHeight,
  computeGeneTrackHitRegions, findGeneHitAtCanvasPoint, computeRegionPlotWidth,
} from "~/utils/sifter/genesTrackRender";
import { normalizePlotMargin, setupPlotCanvas, canvasPointerPosition } from "~/utils/sifter/plotShared";

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

  // renderGenesTrack/computeGeneTrackHitRegions derive plot width from
  // computeRegionPlotWidth (canvasWidth - margin.left * 2, asymmetric by
  // upstream design). Share that formula here so the lane layout used to
  // size the canvas agrees with what actually gets drawn and hit-tested.
  const plotWidth = computeRegionPlotWidth(width, margin);

  // layoutGenesInLanes returns { layouts, laneCount } — NOT an array.
  const { laneCount } = layoutGenesInLanes(
    props.genes, region.start, region.end, margin.left,
    pixelsPerBp(region, plotWidth),
  );
  const height = computeGenesTrackCanvasHeight(margin, Math.max(laneCount, 1));
  const ctx = setupPlotCanvas(canvas, width, height);
  if (!ctx) return;

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
  // Guard against a zero-sized rect (before layout settles, or while hidden):
  // canvasPointerPosition divides by rect.width/height and would return
  // Infinity/NaN in that case.
  if (rect.width === 0 || rect.height === 0) return;
  const { x, y } = canvasPointerPosition(event, canvas);
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
