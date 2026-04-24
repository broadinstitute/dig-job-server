<template>
  <div class="space-y-4">
    <div
      class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded p-2"
    >
      <div ref="plotEl" class="w-full" style="height: 600px" />
    </div>
  </div>
</template>

<script setup>
import { ref, watchEffect, onBeforeUnmount, inject } from 'vue';
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

onBeforeUnmount(async () => {
  if (current) await unmount(current);
});
</script>
