<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h3 class="text-xl font-semibold">FALCON Execution Time Summary</h3>
      <Tag
        severity="success"
        :value="`Total Execution Time: ${formattedTotalTime}`"
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

    <Card>
      <template #title>
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <span>Pre-process Steps Accumulation Time</span>
          <Tag
            severity="success"
            :value="`${preProcess.parallel ? 'Total Pre-process (Parallel Wall Time)' : 'Total Pre-process'}: ${formatTime(preProcess.totalTime)}`"
          />
        </div>
      </template>
      <template #content>
        <div
          class="grid gap-2"
          style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));"
        >
          <div
            v-for="step in preProcess.perStep"
            :key="step.key"
            class="flex justify-between items-center px-3 py-2 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm"
          >
            <span class="text-gray-500 dark:text-gray-400">{{ step.key }}</span>
            <strong
              :class="
                step.time === 0
                  ? 'text-red-500 font-normal'
                  : 'text-emerald-700 dark:text-emerald-400'
              "
            >
              {{ step.time === 0 ? 'Skipped / 0.00s' : `${step.time.toFixed(2)}s` }}
            </strong>
          </div>
        </div>
      </template>
    </Card>

    <Card>
      <template #title>Total Pre-process Time by Chromosome</template>
      <template #content>
        <div ref="preprocessEl" class="w-full" style="height: 320px" />
      </template>
    </Card>

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
const {
  buildLogIterHistogramSpec,
  buildLogPreprocessBarSpec,
  buildLogPreprocessByStepSpec,
} = useFalconPlots(store);
const { ITER_COMPONENTS: components, PRE_PROCESS_KEYS } = useFalconLogParser();
const { mount, unmount } = usePlotly();

function formatTime(seconds) {
  if (!isFinite(seconds) || seconds <= 0) return '0.00s';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = (seconds % 60).toFixed(2);
  const parts = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0 || h > 0) parts.push(`${m}m`);
  parts.push(`${s}s`);
  return `${parts.join(' ')} (${seconds.toFixed(2)}s)`;
}

const chrView = ref('all');

const preProcess = computed(() =>
  buildLogPreprocessByStepSpec(chrView.value, PRE_PROCESS_KEYS),
);

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

// Reformat the parsed totalTime ("6149.27 seconds") into h/m/s + raw,
// matching LogSummaryModule.render (PEGS app.js:2531-2548). When the parser
// found no total (string "Not Found / Incomplete Run"), pass it through.
const formattedTotalTime = computed(() => {
  const raw = parseFloat(totalTime.value);
  if (isNaN(raw)) return totalTime.value || 'No log file detected.';
  return formatTime(raw);
});

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
    await mount(preprocessEl.value, buildLogPreprocessBarSpec(chrView.value));
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
