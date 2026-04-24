<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <Button
        icon="pi pi-database"
        :label="
          clinicalTrials.isLoaded
            ? 'Clinical Trials Loaded'
            : 'Load Clinical Trials CSV'
        "
        :severity="clinicalTrials.isLoaded ? 'success' : 'primary'"
        @click="triggerTrialsUpload"
      />
      <Button
        :icon="showNovel ? 'pi pi-star-fill' : 'pi pi-star'"
        :label="showNovel ? 'Novelty filter: ON' : 'Novelty filter: OFF'"
        severity="secondary"
        outlined
        @click="toggleNovelty"
      />
      <input
        ref="trialsInput"
        type="file"
        accept=".csv"
        class="hidden"
        @change="onTrialsFile"
      />
    </div>

    <section>
      <h3 class="text-lg font-semibold mb-2">Top Genes per Clump</h3>
      <TraitCard
        v-for="row in filteredGenesTop"
        :key="`g-top-${row.index}`"
        :row="row"
      />
    </section>

    <section>
      <h3 class="text-lg font-semibold mb-2">Lead Genes per Chromosome</h3>
      <TraitCard
        v-for="row in filteredGenesLead"
        :key="`g-lead-${row.index}`"
        :row="row"
      />
    </section>

    <section>
      <h3 class="text-lg font-semibold mb-2">Top Variants per Clump</h3>
      <TraitCard
        v-for="row in summary.variants?.top || []"
        :key="`v-top-${row.index}`"
        :row="row"
      />
    </section>

    <section>
      <h3 class="text-lg font-semibold mb-2">Lead Variants per Chromosome</h3>
      <TraitCard
        v-for="row in summary.variants?.lead || []"
        :key="`v-lead-${row.index}`"
        :row="row"
      />
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
    const all = [
      ...summary.value.genes.top,
      ...summary.value.genes.lead,
    ];
    try {
      await attachNoveltyFlags(all, abortCtrl.signal);
    } catch (err) {
      if (err.name !== 'AbortError') console.error(err);
    }
  }
}

const trialsInput = ref(null);
function triggerTrialsUpload() {
  trialsInput.value?.click();
}
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
