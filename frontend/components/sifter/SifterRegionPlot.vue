<template>
  <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded p-2">
    <div ref="plotEl" class="w-full" style="height: 480px" />
  </div>
</template>

<script setup>
import { ref, watchEffect, onBeforeUnmount } from "vue";
import { usePlotly } from "~/composables/usePlotly";
import { buildAssociationsScatter } from "~/utils/sifterPlot";

const props = defineProps({
  records: { type: Array, default: () => [] },
  region: { type: String, default: "" },
});

const { mount, unmount } = usePlotly();
const plotEl = ref(null);
let current = null;

watchEffect(async () => {
  const spec = buildAssociationsScatter(props.records, { region: props.region });
  if (!plotEl.value) return;
  await mount(plotEl.value, spec);
  current = plotEl.value;
});

onBeforeUnmount(async () => {
  if (current) await unmount(current);
});
</script>
