<template>
  <div class="space-y-4">
    <div class="flex items-center gap-4 text-xs text-gray-700 dark:text-gray-300">
      <span class="inline-flex items-center gap-1">
        <span class="inline-block w-3 h-3 rounded-full" style="background: #6b7280" /> Other
      </span>
      <span class="inline-flex items-center gap-1">
        <span
          class="inline-block w-3 h-3"
          style="background: #fbbf24; clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);"
        /> Lead (★)
      </span>
      <span class="inline-flex items-center gap-1">
        <span
          class="inline-block w-3 h-3 rounded-full border-2"
          style="border-color: #9333ea"
        /> Top (per clump)
      </span>
    </div>
    <div class="plot-wrapper">
      <div ref="plotEl" class="w-full" style="height: 600px" />
    </div>
  </div>
</template>

<script setup>
import { ref, watchEffect, onBeforeUnmount, onActivated, onMounted, inject, nextTick } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { usePlotly } from '~/composables/usePlotly';

const store = useFalconStore();
const { buildVariantsScatterSpec } = useFalconPlots(store);
const { mount, unmount, getPlotly } = usePlotly();
const inspector = inject('falcon-inspector', null);
const plotEl = ref(null);

let current = null;
let clickHandler = null;

watchEffect(async () => {
  const spec = buildVariantsScatterSpec();
  if (!plotEl.value) return;
  await mount(plotEl.value, spec);
  current = plotEl.value;

  await getPlotly();
  if (clickHandler) current.removeAllListeners?.('plotly_click');
  clickHandler = (ev) => {
    if (!ev?.points?.length || !inspector?.value) return;
    const p = ev.points[0];
    const txt = p.text || p.hovertext || 'No data available.';
    inspector.value.show(txt);
  };
  current.on('plotly_click', clickHandler);
});

async function nudgeResize() {
  if (!current) return;
  const Plotly = await getPlotly();
  await nextTick();
  try {
    if (current.offsetParent !== null) Plotly.Plots.resize(current);
  } catch {
    // ignore
  }
}
onMounted(nudgeResize);
onActivated(nudgeResize);

onBeforeUnmount(async () => {
  if (current) await unmount(current);
});
</script>

<style scoped>
.plot-wrapper {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 8px;
}
</style>
