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
        :icon="noveltyLoading ? 'pi pi-spin pi-spinner' : noveltyLoaded ? 'pi pi-check' : 'pi pi-download'"
        :label="noveltyLoading ? 'Loading novelty…' : noveltyLoaded ? 'Novelty Loaded' : 'Load Novelty Data'"
        :severity="noveltyLoaded ? 'success' : 'secondary'"
        outlined
        :disabled="noveltyLoading || noveltyLoaded"
        @click="loadNovelty"
      />
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

    <SignalTable
      title="Top Genes per Clump"
      dataset="genes"
      :rows="genesTableRows"
      :show-novelty-cols="true"
    />
    <SignalTable
      title="Top Variants per Clump"
      dataset="variants"
      :rows="variantsTableRows"
      :show-novelty-cols="false"
    />
  </div>
</template>

<script setup>
import { computed, h, onBeforeUnmount, reactive, ref, resolveComponent, watch, watchEffect } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconSummary } from '~/composables/useFalconSummary';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { usePlotly } from '~/composables/usePlotly';

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
const noveltyLoaded = ref(false);
const noveltyLoading = ref(false);
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

// Table row sources — index field required as DataTable dataKey.
const genesTableRows = computed(() =>
  (genesPlotRows.value || []).map((r, i) => ({ ...r, index: i }))
);
const variantsTableRows = computed(() =>
  (variantsPlotRows.value || []).map((r, i) => ({ ...r, index: i }))
);

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

  // Plot-shaped rows — isNovel/traits read from cache if warm.
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

async function loadNovelty() {
  if (noveltyLoaded.value || noveltyLoading.value) return;
  if (abortCtrl) abortCtrl.abort();
  abortCtrl = new AbortController();
  noveltyLoading.value = true;
  const all = [
    ...(summary.value.genes.top || []),
    ...(summary.value.genes.lead || []),
  ];
  try {
    await attachNoveltyFlags(all, abortCtrl.signal);
    noveltyLoaded.value = true;
    recompute(); // re-derive rows now that the cache is warm
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('[ExecutiveSummaryTab] novelty fetch failed', err);
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
// Filter constants (module scope within script setup).
// ---------------------------------------------------------------------------
const ROLE_OPTIONS = [
  { value: 'all', label: 'All Roles' },
  { value: 'top', label: '🏆 Top Only' },
  { value: 'lead', label: '⭐ Lead Only' },
  { value: 'both', label: '🏆 Top & ⭐ Lead' },
];
const NOVEL_OPTIONS = [
  { value: 'all', label: 'All Novel Status' },
  { value: 'true', label: 'Novel: True' },
  { value: 'false', label: 'Novel: False' },
];
const TRIALS_OPTIONS = [
  { value: 'all', label: 'All Trials Status' },
  { value: 'yes', label: 'Has Trials' },
  { value: 'no', label: 'No Trials' },
];

// ---------------------------------------------------------------------------
// filterRows — port of app.js:1459-1479.
// ---------------------------------------------------------------------------
function filterRows(rows, filters, showNoveltyCols) {
  const q = (filters.search || '').trim().toLowerCase();
  return rows.filter((row) => {
    // Role filter
    if (filters.role === 'top' && row.role !== '🏆 Top') return false;
    if (filters.role === 'lead' && row.role !== '⭐ Lead') return false;
    if (filters.role === 'both' && row.role !== '🏆 Top & ⭐ Lead') return false;

    // Novelty + trials filters only when columns are shown
    if (showNoveltyCols) {
      if (filters.novel === 'true' && row.isNovel !== true) return false;
      if (filters.novel === 'false' && row.isNovel !== false) return false;
      if (filters.trials === 'yes' && row.hasClinicalTrials !== true) return false;
      if (filters.trials === 'no' && row.hasClinicalTrials !== false) return false;
    }

    // Text search
    if (q) {
      const hay = `${row.name || ''} ${row.clump || ''} ${row.role || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

// ---------------------------------------------------------------------------
// SignalTable — inline h()-based component (runtime compiler is OFF).
// ---------------------------------------------------------------------------
const SignalTable = {
  name: 'SignalTable',
  props: {
    title: { type: String, required: true },
    dataset: { type: String, required: true },
    rows: { type: Array, required: true },
    showNoveltyCols: { type: Boolean, default: false },
  },
  setup(props) {
    const filters = reactive({ role: 'all', novel: 'all', trials: 'all', search: '' });
    const expandedRows = ref({});

    const filteredRows = computed(() => filterRows(props.rows, filters, props.showNoveltyCols));

    return () => {
      const Card = resolveComponent('Card');
      const DataTable = resolveComponent('DataTable');
      const Column = resolveComponent('Column');
      const Select = resolveComponent('Select');
      const InputText = resolveComponent('InputText');
      const Tag = resolveComponent('Tag');

      const total = props.rows.length;
      const filtered = filteredRows.value;

      // ── toolbar dropdowns ──────────────────────────────────────────────
      const toolbarChildren = [
        h(Select, {
          modelValue: filters.role,
          options: ROLE_OPTIONS,
          optionLabel: 'label',
          optionValue: 'value',
          placeholder: 'All Roles',
          class: 'w-44',
          'onUpdate:modelValue': (v) => { filters.role = v; },
        }),
      ];

      if (props.showNoveltyCols) {
        toolbarChildren.push(
          h(Select, {
            modelValue: filters.novel,
            options: NOVEL_OPTIONS,
            optionLabel: 'label',
            optionValue: 'value',
            placeholder: 'All Novel Status',
            class: 'w-48',
            'onUpdate:modelValue': (v) => { filters.novel = v; },
          }),
          h(Select, {
            modelValue: filters.trials,
            options: TRIALS_OPTIONS,
            optionLabel: 'label',
            optionValue: 'value',
            placeholder: 'All Trials Status',
            class: 'w-48',
            'onUpdate:modelValue': (v) => { filters.trials = v; },
          }),
        );
      }

      toolbarChildren.push(
        h(InputText, {
          modelValue: filters.search,
          placeholder: 'Search…',
          class: 'w-48',
          'onUpdate:modelValue': (v) => { filters.search = v; },
        }),
        h('span', { class: 'text-sm text-gray-600 dark:text-gray-400 ml-2 whitespace-nowrap' },
          `${filtered.length} / ${total}`),
      );

      const toolbar = h('div', { class: 'flex flex-wrap items-center gap-2 mb-3' }, toolbarChildren);

      // ── columns ────────────────────────────────────────────────────────

      // Clump column: colored dot + clump id
      const clumpCol = h(Column, {
        field: 'clump',
        header: 'Clump',
        sortable: true,
      }, {
        body: ({ data }) => h('span', { class: 'flex items-center gap-1' }, [
          h('span', {
            style: `display:inline-block;width:10px;height:10px;border-radius:50%;background:${data.color || '#888'};flex-shrink:0`,
          }),
          h('span', {}, data.clump),
        ]),
      });

      // Probability column
      const probCol = h(Column, {
        field: 'rawProb',
        header: 'Probability',
        sortable: true,
      }, {
        body: ({ data }) => h('span', {}, data.prob),
      });

      // Significance column
      const sigHeader = props.dataset === 'genes' ? '−log₁₀(P)' : 'P-value';
      const sigCol = h(Column, {
        field: 'rawSig',
        header: sigHeader,
        sortable: true,
      }, {
        body: ({ data }) => h('span', {}, data.significance),
      });

      const columns = [
        h(Column, { expander: true, headerStyle: 'width: 3rem' }),
        h(Column, { field: 'name', header: props.dataset === 'genes' ? 'Gene' : 'Variant', sortable: true }),
        clumpCol,
        h(Column, { field: 'role', header: 'Role', sortable: true }),
        probCol,
        sigCol,
      ];

      if (props.showNoveltyCols) {
        // Trials column
        columns.push(h(Column, {
          field: 'hasClinicalTrials',
          header: 'Trials',
          sortable: true,
        }, {
          body: ({ data }) => {
            if (data.hasClinicalTrials === true) {
              return h(Tag, { value: 'Yes', severity: 'success' });
            }
            if (data.hasClinicalTrials === false) {
              return h('span', { class: 'text-gray-400' }, '—');
            }
            return h('span', { class: 'text-gray-400' }, '—');
          },
        }));

        // Novel column
        columns.push(h(Column, {
          field: 'isNovel',
          header: 'Novel',
          sortable: true,
        }, {
          body: ({ data }) => {
            if (data.isNovel === null || data.isNovel === undefined) {
              return h('span', { title: 'Not yet loaded' }, '⏳');
            }
            if (data.isNovel === true) {
              return h(Tag, { value: 'Novel', severity: 'success' });
            }
            return h(Tag, { value: 'Known', severity: 'secondary' });
          },
        }));
      }

      // ── expansion slot ─────────────────────────────────────────────────
      const expansionSlot = {
        expansion: ({ data }) => {
          const children = [];

          // Trials sub-table
          if (data.hasClinicalTrials && data.clinicalTrials?.length) {
            children.push(
              h('div', { class: 'mb-3' }, [
                h('h4', { class: 'text-sm font-semibold mb-1' }, 'Clinical Trials'),
                h('table', { class: 'text-xs w-full border-collapse' }, [
                  h('thead', {}, [
                    h('tr', {}, [
                      h('th', { class: 'border border-gray-200 dark:border-gray-700 px-2 py-1 text-left bg-gray-50 dark:bg-gray-800' }, 'Drug ID'),
                      h('th', { class: 'border border-gray-200 dark:border-gray-700 px-2 py-1 text-left bg-gray-50 dark:bg-gray-800' }, 'Indication'),
                      h('th', { class: 'border border-gray-200 dark:border-gray-700 px-2 py-1 text-left bg-gray-50 dark:bg-gray-800' }, 'Phase'),
                    ]),
                  ]),
                  h('tbody', {},
                    data.clinicalTrials.map((t, ti) =>
                      h('tr', { key: ti }, [
                        h('td', { class: 'border border-gray-200 dark:border-gray-700 px-2 py-1 font-mono' }, t.drugId),
                        h('td', { class: 'border border-gray-200 dark:border-gray-700 px-2 py-1' }, t.indication),
                        h('td', { class: 'border border-gray-200 dark:border-gray-700 px-2 py-1' }, t.phase),
                      ])
                    )
                  ),
                ]),
              ])
            );
          }

          // Trait cards (when known — isNovel === false and traits available)
          if (data.isNovel === false && data.traits?.length) {
            children.push(
              h('div', {}, [
                h('h4', { class: 'text-sm font-semibold mb-1' }, 'Associated Traits'),
                h('div', { class: 'space-y-1' },
                  data.traits.map((t, ti) =>
                    h('div', {
                      key: ti,
                      class: 'border rounded p-2 text-xs dark:border-gray-700',
                    }, [
                      h('div', {}, [h('strong', {}, 'Trait: '), t.trait || '—']),
                      h('div', {}, [h('strong', {}, 'Authors: '), t.authors || '—']),
                      h('div', {}, [h('strong', {}, 'Citation: '), t.citation || '—']),
                      h('div', {}, [
                        h('strong', {}, 'PMID: '),
                        t.pmid && t.pmid !== 'N/A'
                          ? h('a', {
                              href: `https://pubmed.ncbi.nlm.nih.gov/${t.pmid}`,
                              target: '_blank',
                              rel: 'noopener noreferrer',
                              class: 'text-blue-600 dark:text-blue-400 underline',
                            }, t.pmid)
                          : h('span', {}, t.pmid || '—'),
                      ]),
                    ])
                  )
                ),
              ])
            );
          }

          if (children.length === 0) {
            children.push(h('span', { class: 'text-xs text-gray-500 dark:text-gray-400' }, 'No expansion data.'));
          }

          return h('div', { class: 'p-3' }, children);
        },
      };

      // ── DataTable ──────────────────────────────────────────────────────
      const table = h(DataTable, {
        value: filtered,
        dataKey: 'index',
        paginator: true,
        rows: 10,
        sortMode: 'single',
        removableSort: true,
        stripedRows: true,
        expandedRows: expandedRows.value,
        'onUpdate:expandedRows': (v) => { expandedRows.value = v; },
        rowsPerPageOptions: [10, 25, 50],
        class: 'p-datatable-sm',
      }, {
        default: () => columns,
        ...expansionSlot,
      });

      return h(Card, {}, {
        title: () => props.title,
        content: () => h('div', {}, [toolbar, table]),
      });
    };
  },
};
</script>
