<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h3 class="text-xl font-semibold">FALCON Execution Time Summary</h3>
      <Tag
        severity="success"
        :value="`Total Execution Time: ${totalTime}`"
        class="text-base"
      />
    </div>

    <Card>
      <template #title>About this summary</template>
      <template #content>
        <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
          This section visualizes the execution time for various components of
          the FALCON algorithm per iteration. If a component was skipped during
          an iteration for optimization (e.g., "Lazy link activated"), the
          sample is ignored on the analysis, and <b>n</b> on the top of each
          plot shows the number of times the step was actually performed.
        </p>
        <p
          class="text-sm text-gray-600 dark:text-gray-300 border-l-4 border-primary-500 pl-3 py-2 bg-gray-50 dark:bg-gray-800"
        >
          <b>⏱️ Parallel Wall Time Calculation:</b> Because FALCON processes
          chromosomes concurrently and does not synchronize until
          <em>each chromosome finishes all of its pre-process steps</em>, the
          Whole Genome pre-process time is not the sum of individual step
          maximums. Instead, it is calculated as the maximum total pre-process
          time across all chromosomes (i.e., the slowest overall chromosome).
          This accurately reflects the real-world elapsed time, as the pipeline
          waits for the last chromosome to finish preparing before beginning
          the synchronized Gibbs sampling.
        </p>
      </template>
    </Card>

    <div class="flex items-center gap-3">
      <label class="text-sm font-semibold text-gray-700 dark:text-gray-200"
        >Chromosome view:</label
      >
      <Select
        v-model="chrView"
        :options="chrOptions"
        option-label="label"
        option-value="value"
        class="w-64"
      />
    </div>

    <div ref="preprocessEl" class="w-full" style="height: 320px" />

    <div
      class="grid gap-4"
      style="grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));"
    >
      <Card v-for="comp in components" :key="comp">
        <template #title>{{ comp }}</template>
        <template #content>
          <div
            class="flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2 pb-2 border-b border-dashed border-gray-200 dark:border-gray-700"
          >
            <template v-if="compStats[comp]">
              <Tag
                severity="secondary"
                :value="`Min: ${compStats[comp].min.toFixed(2)}s`"
              />
              <Tag
                severity="secondary"
                :value="`Med: ${compStats[comp].median.toFixed(2)}s`"
              />
              <Tag
                severity="secondary"
                :value="`Mean: ${compStats[comp].mean.toFixed(2)}s`"
              />
              <Tag
                severity="secondary"
                :value="`Max: ${compStats[comp].max.toFixed(2)}s`"
              />
              <span class="text-gray-400">n={{ compStats[comp].n }}</span>
            </template>
            <span v-else class="text-red-500 font-semibold">
              No data recorded (component entirely skipped).
            </span>
          </div>
          <div
            :ref="(el) => (histRefs[comp] = el)"
            class="w-full"
            style="height: 240px"
          />
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watchEffect, onBeforeUnmount } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { useFalconLogParser } from '~/composables/useFalconLogParser';
import { usePlotly } from '~/composables/usePlotly';

const store = useFalconStore();
const { buildLogIterHistogramSpec, buildLogPreprocessBarSpec } =
  useFalconPlots(store);
const { ITER_COMPONENTS: components } = useFalconLogParser();
const { mount, unmount } = usePlotly();

const chrView = ref('all');
const chrOptions = computed(() => {
  const chrs = Array.from(store.datasets.log.chromosomes).sort((a, b) => {
    const na = parseInt(a, 10),
      nb = parseInt(b, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  return [
    { value: 'all', label: 'Whole Genome (Aggregate)' },
    ...chrs.map((c) => ({ value: c, label: `Chromosome ${c}` })),
  ];
});

const totalTime = computed(() => store.datasets.log.totalTime);

const preprocessEl = ref(null);
const histRefs = ref({});
const mounted = new Set();

const specs = computed(() => {
  const out = {};
  for (const c of components)
    out[c] = buildLogIterHistogramSpec(c, chrView.value);
  return out;
});

const compStats = computed(() => {
  const out = {};
  for (const c of components) out[c] = specs.value[c].stats;
  return out;
});

watchEffect(async () => {
  if (preprocessEl.value) {
    await mount(preprocessEl.value, buildLogPreprocessBarSpec());
    mounted.add(preprocessEl.value);
  }
  for (const comp of components) {
    const el = histRefs.value[comp];
    if (!el) continue;
    const s = specs.value[comp];
    if (!s.stats) {
      el.innerHTML = '';
      continue;
    }
    await mount(el, { data: s.data, layout: s.layout });
    mounted.add(el);
  }
});

onBeforeUnmount(async () => {
  for (const el of mounted) await unmount(el);
});
</script>
