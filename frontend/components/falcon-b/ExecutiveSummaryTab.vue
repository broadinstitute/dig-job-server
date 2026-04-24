<template>
  <div>
    <div class="summary-toolbar">
      <button
        class="summary-btn"
        :class="{ primary: !clinicalTrials.isLoaded, success: clinicalTrials.isLoaded }"
        @click="triggerTrialsUpload"
      >
        {{ clinicalTrials.isLoaded ? '✓ Clinical Trials Loaded' : 'Load Clinical Trials CSV' }}
      </button>
      <button class="summary-btn outline" @click="toggleNovelty">
        {{ showNovel ? 'Novelty filter: ON' : 'Novelty filter: OFF' }}
      </button>
      <input
        ref="trialsInput"
        type="file"
        accept=".csv"
        class="hidden"
        @change="onTrialsFile"
      />
    </div>

    <section class="summary-section">
      <h3>Top Genes per Clump</h3>
      <TraitCard v-for="row in filteredGenesTop" :key="`g-top-${row.index}`" :row="row" />
    </section>
    <section class="summary-section">
      <h3>Lead Genes per Chromosome</h3>
      <TraitCard v-for="row in filteredGenesLead" :key="`g-lead-${row.index}`" :row="row" />
    </section>
    <section class="summary-section">
      <h3>Top Variants per Clump</h3>
      <TraitCard v-for="row in summary.variants?.top || []" :key="`v-top-${row.index}`" :row="row" />
    </section>
    <section class="summary-section">
      <h3>Lead Variants per Chromosome</h3>
      <TraitCard v-for="row in summary.variants?.lead || []" :key="`v-lead-${row.index}`" :row="row" />
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconSummary } from '~/composables/useFalconSummary';

const store = useFalconStore();
const { computeTopAndLeadSignals, attachClinicalTrials, attachNoveltyFlags } =
  useFalconSummary(store);

const clinicalTrials = store.clinicalTrials;
const summary = ref({
  genes: { top: [], lead: [] },
  variants: { top: [], lead: [] },
});
const showNovel = ref(false);
let abortCtrl = null;

watch(
  () => [
    store.datasets.genes.isLoaded,
    store.datasets.variants.isLoaded,
    clinicalTrials.isLoaded,
  ],
  recompute,
  { immediate: true },
);

function recompute() {
  const s = computeTopAndLeadSignals();
  ['top', 'lead'].forEach((k) => {
    attachClinicalTrials(s.genes[k]);
    attachClinicalTrials(s.variants[k]);
  });
  summary.value = s;
}

const filteredGenesTop = computed(() =>
  showNovel.value
    ? (summary.value.genes?.top || []).filter((r) => r.isNovel === true)
    : summary.value.genes?.top || [],
);
const filteredGenesLead = computed(() =>
  showNovel.value
    ? (summary.value.genes?.lead || []).filter((r) => r.isNovel === true)
    : summary.value.genes?.lead || [],
);

async function toggleNovelty() {
  showNovel.value = !showNovel.value;
  if (showNovel.value) {
    if (abortCtrl) abortCtrl.abort();
    abortCtrl = new AbortController();
    const all = [...summary.value.genes.top, ...summary.value.genes.lead];
    try {
      await attachNoveltyFlags(all, abortCtrl.signal);
    } catch (err) {
      if (err.name !== 'AbortError') console.error(err);
    }
  }
}

const trialsInput = ref(null);
function triggerTrialsUpload() { trialsInput.value?.click(); }
async function onTrialsFile(e) {
  const f = e.target.files?.[0];
  if (!f) return;
  try {
    await store.loadClinicalTrialsCsv(f);
    recompute();
  } catch (err) {
    console.error('clinical trials load failed', err);
  }
}
</script>

<style scoped>
.summary-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.summary-btn {
  padding: 8px 14px;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #d1d5db;
  background: white;
  color: #374151;
  transition: 0.2s;
}
.summary-btn.primary { background: #3b82f6; color: white; border-color: #3b82f6; }
.summary-btn.primary:hover { background: #2563eb; }
.summary-btn.success { background: #d1fae5; color: #047857; border-color: #10b981; }
.summary-btn.outline { background: white; }
.summary-btn.outline:hover { background: #f3f4f6; }
.summary-section {
  margin-bottom: 28px;
}
.summary-section h3 {
  font-size: 1.05em;
  font-weight: 700;
  color: #111827;
  margin: 0 0 10px 0;
  padding-bottom: 6px;
  border-bottom: 2px solid #3b82f6;
}
.hidden { display: none; }
</style>
