<template>
  <div>
    <div class="log-header">
      <h3>FALCON Execution Time Summary</h3>
      <span class="total-time-pill">Total Execution Time: {{ totalTime }}</span>
    </div>

    <div class="explain-card">
      <h4>About this summary</h4>
      <p>
        This section visualizes the execution time for various components of
        the FALCON algorithm per iteration. If a component was skipped during
        an iteration for optimization (e.g., "Lazy link activated"), the
        sample is ignored on the analysis, and <b>n</b> on the top of the
        plot shows the number of times the step was actually performed.
      </p>
      <p class="explain-callout">
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
    </div>

    <div class="chr-select-row">
      <label for="chr-view">Select Chromosome View:</label>
      <select id="chr-view" v-model="chrView">
        <option
          v-for="opt in chrOptions"
          :key="opt.value"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>
    </div>

    <div ref="preprocessEl" class="preprocess-bar" />

    <div class="hist-grid">
      <div v-for="comp in components" :key="comp" class="hist-card">
        <h4>{{ comp }}</h4>
        <div v-if="compStats[comp]" class="stats-row">
          <span><b>Min:</b> {{ compStats[comp].min.toFixed(2) }}s</span>
          <span><b>Med:</b> {{ compStats[comp].median.toFixed(2) }}s</span>
          <span><b>Mean:</b> {{ compStats[comp].mean.toFixed(2) }}s</span>
          <span><b>Max:</b> {{ compStats[comp].max.toFixed(2) }}s</span>
          <span class="muted">(n={{ compStats[comp].n }})</span>
        </div>
        <span v-else class="no-data">No data recorded (component skipped).</span>
        <div :ref="(el) => (histRefs[comp] = el)" class="hist-plot" />
      </div>
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
    const na = parseInt(a, 10), nb = parseInt(b, 10);
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

<style scoped>
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 15px;
}
.log-header h3 { margin: 0; color: #111827; }
.total-time-pill {
  font-size: 1.1em;
  font-weight: bold;
  color: #047857;
  background: #d1fae5;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #10b981;
}
.explain-card {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.explain-card h4 { margin-top: 0; color: #111827; }
.explain-card p {
  font-size: 0.9em;
  color: #4b5563;
  line-height: 1.5;
  margin-bottom: 10px;
}
.explain-callout {
  padding: 10px;
  border-left: 3px solid #3b82f6;
  background: #f9fafb;
  margin: 0;
}
.chr-select-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.chr-select-row label {
  font-weight: bold;
  color: #4b5563;
}
.chr-select-row select {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  min-width: 220px;
}
.preprocess-bar {
  width: 100%;
  height: 320px;
  margin-bottom: 20px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
}
.hist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
}
.hist-card {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.hist-card h4 { margin: 0 0 8px 0; color: #111827; }
.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 0.85em;
  color: #4b5563;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px dashed #e5e7eb;
}
.stats-row .muted { color: #9ca3af; font-size: 0.9em; }
.no-data {
  color: #ef4444;
  font-weight: bold;
  display: block;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px dashed #e5e7eb;
}
.hist-plot {
  width: 100%;
  height: 240px;
}
</style>
