<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3 flex-wrap">
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
        :label="
          noveltyLoading
            ? 'Loading novelty…'
            : showNovel
              ? 'Novelty filter: ON'
              : 'Novelty filter: OFF'
        "
        severity="secondary"
        outlined
        :loading="noveltyLoading"
        @click="toggleNovelty"
      />
      <span
        v-if="noveltyError"
        class="text-xs text-red-600 dark:text-red-400 ml-2"
      >
        Novelty fetch failed — see console.
      </span>
      <input
        ref="trialsInput"
        type="file"
        accept=".csv"
        class="hidden"
        @change="onTrialsFile"
      />
    </div>

    <!-- ─── Executive Summary Plots (row 1: upset + venn) ─── -->
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));">
      <Card>
        <template #title>🧬 Gene Intersection: Top, Lead, and Novel</template>
        <template #content>
          <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
            <strong>Top Genes</strong> are highest probability targets.
            <strong>Lead Genes</strong> are physically nearest.
            <strong>Novel Genes</strong> have no previous associations in our catalog.
            <strong>Clinical Trials</strong> indicates genes with known clinical data.
          </p>
          <div class="relative" style="height: 350px">
            <div ref="upsetEl" class="w-full h-full" />
            <div
              v-if="upsetSpec?.empty"
              class="absolute inset-0 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 pointer-events-none"
            >
              No intersection data.
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>🔬 Variant Overlap: Top vs. Lead</template>
        <template #content>
          <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
            <strong>Top Variants</strong> are the variants with the highest FALCON probability in their clump.
            <strong>Lead Variants</strong> represent the index signal of the clump.
            This diagram shows how often the model's top variant matches the original index signal.
          </p>
          <div class="relative" style="height: 280px">
            <div ref="vennEl" class="w-full h-full" />
          </div>
        </template>
      </Card>
    </div>

    <!-- ─── row 2: probability distributions ─── -->
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
      <Card>
        <template #title>📊 Gene Probability Distribution</template>
        <template #content>
          <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
            Distribution of FALCON probabilities across the Top, Lead, and Concordant gene categories.
          </p>
          <div class="relative" style="height: 260px">
            <div ref="probGenesEl" class="w-full h-full" />
            <div
              v-if="probGenesSpec?.empty"
              class="absolute inset-0 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 pointer-events-none"
            >
              No gene probability data.
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>📊 Variant Probability Distribution</template>
        <template #content>
          <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
            Distribution of FALCON probabilities across the Top, Lead, and Concordant variant categories.
          </p>
          <div class="relative" style="height: 260px">
            <div ref="probVariantsEl" class="w-full h-full" />
            <div
              v-if="probVariantsSpec?.empty"
              class="absolute inset-0 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 pointer-events-none"
            >
              No variant probability data.
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- ─── row 3: distance plots ─── -->
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
      <Card>
        <template #title>📏 Distance to Nearest Gene</template>
        <template #content>
          <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
            Physical distance (BP) from the <strong>Index Variant</strong> to its designated <strong>Lead Gene</strong>.
          </p>
          <div class="relative" style="height: 260px">
            <div ref="distEl" class="w-full h-full" />
            <div
              v-if="distSpec?.empty"
              class="absolute inset-0 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 pointer-events-none"
            >
              No distance data available.
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>📏 Distance Between Lead Variants</template>
        <template #content>
          <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
            Physical distance (BP) between adjacent <strong>Index Variants</strong> across the same chromosome.
          </p>
          <div class="relative" style="height: 260px">
            <div ref="leadDistEl" class="w-full h-full" />
            <div
              v-if="leadDistSpec?.empty"
              class="absolute inset-0 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400 pointer-events-none"
            >
              Not enough adjacent lead variants available to measure distances.
            </div>
          </div>
        </template>
      </Card>
    </div>

    <SummarySection
      title="Top Genes per Clump"
      :rows="summary.genes?.top || []"
      :show-novelty="true"
      :show-novel-filter="showNovel"
    />

    <SummarySection
      title="Lead Genes per Chromosome"
      :rows="summary.genes?.lead || []"
      :show-novelty="true"
      :show-novel-filter="showNovel"
    />

    <SummarySection
      title="Top Variants per Clump"
      :rows="summary.variants?.top || []"
      :show-novelty="false"
    />

    <SummarySection
      title="Lead Variants per Chromosome"
      :rows="summary.variants?.lead || []"
      :show-novelty="false"
    />
  </div>
</template>

<script setup>
import { computed, h, onBeforeUnmount, ref, watch, watchEffect } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconSummary } from '~/composables/useFalconSummary';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { usePlotly } from '~/composables/usePlotly';
import TraitCard from '~/components/falcon/TraitCard.vue';

const store = useFalconStore();
const {
  computeTopAndLeadSignals,
  attachClinicalTrials,
  attachNoveltyFlags,
  computeSummaryRowsForPlots,
  computeDistances,
} = useFalconSummary(store);
const {
  buildSummaryUpsetSpec,
  buildSummaryVennSpec,
  buildSummaryProbDistSpec,
  buildSummaryDistanceSpec,
  buildSummaryLeadDistanceSpec,
} = useFalconPlots(store);
const { mount, unmount } = usePlotly();

const clinicalTrials = store.clinicalTrials;
const summary = ref({
  genes: { top: [], lead: [] },
  variants: { top: [], lead: [] },
});
const showNovel = ref(false);
const noveltyLoading = ref(false);
const noveltyError = ref(false);
let abortCtrl = null;

// Plot-shaped summary data and refs.
const genesPlotRows = ref([]);
const variantsPlotRows = ref([]);
const variantsStats = ref({ topOnly: 0, leadOnly: 0, both: 0 });
const distances = ref([]);
const leadDistances = ref([]);

const upsetEl = ref(null);
const vennEl = ref(null);
const probGenesEl = ref(null);
const probVariantsEl = ref(null);
const distEl = ref(null);
const leadDistEl = ref(null);

const upsetSpec = computed(() => buildSummaryUpsetSpec(genesPlotRows.value));
const vennSpec = computed(() => buildSummaryVennSpec(variantsStats.value));
const probGenesSpec = computed(() => buildSummaryProbDistSpec(genesPlotRows.value));
const probVariantsSpec = computed(() => buildSummaryProbDistSpec(variantsPlotRows.value));
const distSpec = computed(() => buildSummaryDistanceSpec(distances.value));
const leadDistSpec = computed(() => buildSummaryLeadDistanceSpec(leadDistances.value));

watch(
  () => [
    store.datasets.genes.isLoaded,
    store.datasets.variants.isLoaded,
    clinicalTrials.isLoaded,
    store.globalFilter.active,
    store.globalFilter.minProb,
    store.globalFilter.minNegP,
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

  // Plot-shaped rows. `isNovel` starts null per original behaviour.
  const genes = computeSummaryRowsForPlots('genes');
  const variants = computeSummaryRowsForPlots('variants');
  genesPlotRows.value = genes.results;
  variantsPlotRows.value = variants.results;
  variantsStats.value = variants.stats;

  const d = computeDistances();
  distances.value = d.distances;
  leadDistances.value = d.leadDistances;
}

function mountPlot(el, spec) {
  if (!el || !spec) return;
  if (spec.empty) {
    // Still mount so Plotly can draw an empty axis frame; the overlay in
    // the template shows the placeholder text.
    mount(el, spec);
    return;
  }
  mount(el, spec);
}

watchEffect(() => {
  mountPlot(upsetEl.value, upsetSpec.value);
});
watchEffect(() => {
  mountPlot(vennEl.value, vennSpec.value);
});
watchEffect(() => {
  mountPlot(probGenesEl.value, probGenesSpec.value);
});
watchEffect(() => {
  mountPlot(probVariantsEl.value, probVariantsSpec.value);
});
watchEffect(() => {
  mountPlot(distEl.value, distSpec.value);
});
watchEffect(() => {
  mountPlot(leadDistEl.value, leadDistSpec.value);
});

onBeforeUnmount(async () => {
  for (const el of [upsetEl, vennEl, probGenesEl, probVariantsEl, distEl, leadDistEl]) {
    if (el.value) await unmount(el.value);
  }
});

async function toggleNovelty() {
  // If we are turning OFF, just flip the flag — don't touch cached traits.
  if (showNovel.value) {
    showNovel.value = false;
    return;
  }

  // Turn ON: fetch novelty for every gene row in either gene section.
  if (abortCtrl) abortCtrl.abort();
  abortCtrl = new AbortController();
  noveltyLoading.value = true;
  noveltyError.value = false;
  const all = [
    ...(summary.value.genes.top || []),
    ...(summary.value.genes.lead || []),
  ];
  try {
    await attachNoveltyFlags(all, abortCtrl.signal);
    showNovel.value = true;
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('[ExecutiveSummaryTab] novelty fetch failed', err);
      noveltyError.value = true;
    }
  } finally {
    noveltyLoading.value = false;
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

// ---------------------------------------------------------------------------
// Inline section component: per-section search + role filter + paginator,
// porting SummaryModule.buildInteractiveTable filtering UX (PEGS app.js:1350+).
// Inline rather than a separate file to keep the variant-A blast radius small.
// ---------------------------------------------------------------------------
const ROLE_OPTIONS = [
  { value: 'all', label: 'All Roles' },
  { value: 'top', label: 'Top Only' },
  { value: 'lead', label: 'Lead Only' },
  { value: 'both', label: 'Top & Lead' },
];

const SummarySection = {
  props: {
    title: { type: String, required: true },
    rows: { type: Array, required: true },
    showNovelty: { type: Boolean, default: false },
    showNovelFilter: { type: Boolean, default: false },
  },
  setup(props) {
    const search = ref('');
    const roleFilter = ref('all');
    const page = ref(1);
    const pageSize = 10;

    // The shape coming out of useFalconSummary doesn't carry an explicit
    // "role" — top rows live in .top, leads in .lead. The same gene can
    // appear in both. Detect "both" by intersecting names within this list.
    const filtered = computed(() => {
      const list = props.rows || [];
      const q = search.value.trim().toLowerCase();
      return list.filter((row) => {
        if (roleFilter.value === 'top' && row.isLead) return false;
        if (roleFilter.value === 'lead' && !row.isLead) return false;
        // "both" is approximate without cross-list info — treat as "isLead".
        if (roleFilter.value === 'both' && !row.isLead) return false;

        if (props.showNovelFilter) {
          if (row.isNovel === null || row.isNovel === undefined) return false;
          if (row.isNovel !== true) return false;
        }

        if (q) {
          const hay =
            `${row.name || ''} ${row.clumpId || ''} ${row.chr || ''}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
    });

    const totalPages = computed(() =>
      Math.max(1, Math.ceil(filtered.value.length / pageSize)),
    );
    const pageRows = computed(() => {
      const start = (page.value - 1) * pageSize;
      return filtered.value.slice(start, start + pageSize);
    });

    // Reset to page 1 if filters narrow the list past current page.
    watch([search, roleFilter, () => props.rows.length, () => props.showNovelFilter], () => {
      if (page.value > totalPages.value) page.value = totalPages.value;
      if (page.value < 1) page.value = 1;
    });

    return () =>
      h('section', {}, [
        h(
          'div',
          { class: 'flex items-end gap-3 flex-wrap mb-2' },
          [
            h(
              'h3',
              { class: 'text-lg font-semibold mr-auto' },
              `${props.title} (${filtered.value.length})`,
            ),
            h(
              'select',
              {
                class:
                  'border rounded px-2 py-1 text-sm bg-white dark:bg-gray-900 dark:border-gray-700',
                value: roleFilter.value,
                onChange: (e) => {
                  roleFilter.value = e.target.value;
                  page.value = 1;
                },
              },
              ROLE_OPTIONS.map((o) =>
                h('option', { value: o.value, key: o.value }, o.label),
              ),
            ),
            h('input', {
              type: 'text',
              placeholder: 'Search…',
              class:
                'border rounded px-2 py-1 text-sm w-48 bg-white dark:bg-gray-900 dark:border-gray-700',
              value: search.value,
              onInput: (e) => {
                search.value = e.target.value;
                page.value = 1;
              },
            }),
          ],
        ),
        ...pageRows.value.map((row) =>
          h(TraitCard, {
            key: `${props.title}-${row.index}`,
            row,
          }),
        ),
        filtered.value.length === 0
          ? h(
              'p',
              { class: 'text-sm text-gray-500 dark:text-gray-400 py-2' },
              'No matching rows.',
            )
          : null,
        h(
          'div',
          { class: 'flex items-center gap-2 mt-2 text-sm' },
          [
            h(
              'button',
              {
                class:
                  'px-2 py-1 border rounded disabled:opacity-50 dark:border-gray-700',
                disabled: page.value <= 1,
                onClick: () => (page.value = Math.max(1, page.value - 1)),
              },
              'Previous',
            ),
            h('span', {}, `Page ${page.value} of ${totalPages.value}`),
            h(
              'button',
              {
                class:
                  'px-2 py-1 border rounded disabled:opacity-50 dark:border-gray-700',
                disabled: page.value >= totalPages.value,
                onClick: () =>
                  (page.value = Math.min(totalPages.value, page.value + 1)),
              },
              'Next',
            ),
          ],
        ),
      ]);
  },
};
</script>
