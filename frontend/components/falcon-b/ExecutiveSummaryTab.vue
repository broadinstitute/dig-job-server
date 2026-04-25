<template>
  <div>
    <!-- ─── Executive Summary plots (row 1: upset + venn) ─── -->
    <div class="plot-row plot-row--two">
      <div class="plot-card">
        <h4>🧬 Gene Intersection: Top, Lead, and Novel</h4>
        <p class="plot-desc">
          <strong>Top Genes</strong> are highest probability targets.
          <strong>Lead Genes</strong> are physically nearest.
          <strong>Novel Genes</strong> have no previous associations in our catalog.
          <strong>Clinical Trials</strong> indicates genes with known clinical data.
        </p>
        <div class="plot-mount plot-mount--upset">
          <div ref="upsetEl" class="plot-inner" />
          <div v-if="upsetSpec?.empty" class="plot-empty">No intersection data.</div>
        </div>
      </div>

      <div class="plot-card">
        <h4>🔬 Variant Overlap: Top vs. Lead</h4>
        <p class="plot-desc">
          <strong>Top Variants</strong> are the variants with the highest FALCON probability in their clump.
          <strong>Lead Variants</strong> represent the index signal of the clump.
          This diagram shows how often the model's top variant matches the original index signal.
        </p>
        <div class="plot-mount plot-mount--venn">
          <div ref="vennEl" class="plot-inner" />
        </div>
      </div>
    </div>

    <!-- ─── row 2: probability distributions ─── -->
    <div class="plot-row plot-row--two">
      <div class="plot-card">
        <h4>📊 Gene Probability Distribution</h4>
        <p class="plot-desc">
          Distribution of FALCON probabilities across the Top, Lead, and Concordant gene categories.
        </p>
        <div class="plot-mount plot-mount--dist">
          <div ref="probGenesEl" class="plot-inner" />
          <div v-if="probGenesSpec?.empty" class="plot-empty">No gene probability data.</div>
        </div>
      </div>

      <div class="plot-card">
        <h4>📊 Variant Probability Distribution</h4>
        <p class="plot-desc">
          Distribution of FALCON probabilities across the Top, Lead, and Concordant variant categories.
        </p>
        <div class="plot-mount plot-mount--dist">
          <div ref="probVariantsEl" class="plot-inner" />
          <div v-if="probVariantsSpec?.empty" class="plot-empty">No variant probability data.</div>
        </div>
      </div>
    </div>

    <!-- ─── row 3: distance plots ─── -->
    <div class="plot-row plot-row--two">
      <div class="plot-card">
        <h4>📏 Distance to Nearest Gene</h4>
        <p class="plot-desc">
          Physical distance (BP) from the <strong>Index Variant</strong> to its designated <strong>Lead Gene</strong>.
        </p>
        <div class="plot-mount plot-mount--dist">
          <div ref="distEl" class="plot-inner" />
          <div v-if="distSpec?.empty" class="plot-empty">No distance data available.</div>
        </div>
      </div>

      <div class="plot-card">
        <h4>📏 Distance Between Lead Variants</h4>
        <p class="plot-desc">
          Physical distance (BP) between adjacent <strong>Index Variants</strong> across the same chromosome.
        </p>
        <div class="plot-mount plot-mount--dist">
          <div ref="leadDistEl" class="plot-inner" />
          <div v-if="leadDistSpec?.empty" class="plot-empty">
            Not enough adjacent lead variants available to measure distances.
          </div>
        </div>
      </div>
    </div>

    <div class="summary-toolbar">
      <button
        class="summary-btn"
        :class="{ primary: !clinicalTrials.isLoaded, success: clinicalTrials.isLoaded }"
        @click="triggerTrialsUpload"
      >
        {{ clinicalTrials.isLoaded ? '✓ Clinical Trials Loaded' : 'Load Clinical Trials CSV' }}
      </button>
      <button
        class="summary-btn outline"
        :disabled="noveltyLoading"
        @click="toggleNovelty"
      >
        {{
          noveltyLoading
            ? 'Loading novelty…'
            : showNovel
              ? '★ Novelty filter: ON'
              : '☆ Novelty filter: OFF'
        }}
      </button>
      <span v-if="noveltyError" class="novelty-error">
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

    <SummarySection
      title="Top Genes per Clump"
      :rows="summary.genes?.top || []"
      :show-novel-filter="showNovel"
    />
    <SummarySection
      title="Lead Genes per Chromosome"
      :rows="summary.genes?.lead || []"
      :show-novel-filter="showNovel"
    />
    <SummarySection
      title="Top Variants per Clump"
      :rows="summary.variants?.top || []"
      :show-novel-filter="false"
    />
    <SummarySection
      title="Lead Variants per Chromosome"
      :rows="summary.variants?.lead || []"
      :show-novel-filter="false"
    />
  </div>
</template>

<script setup>
import { computed, h, onBeforeUnmount, ref, watch, watchEffect } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconSummary } from '~/composables/useFalconSummary';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { usePlotly } from '~/composables/usePlotly';
import TraitCard from '~/components/falcon-b/TraitCard.vue';

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

watchEffect(() => { mountPlot(upsetEl.value, upsetSpec.value); });
watchEffect(() => { mountPlot(vennEl.value, vennSpec.value); });
watchEffect(() => { mountPlot(probGenesEl.value, probGenesSpec.value); });
watchEffect(() => { mountPlot(probVariantsEl.value, probVariantsSpec.value); });
watchEffect(() => { mountPlot(distEl.value, distSpec.value); });
watchEffect(() => { mountPlot(leadDistEl.value, leadDistSpec.value); });

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

// ---------------------------------------------------------------------------
// Inline section component: per-section search + role filter + paginator,
// porting SummaryModule.buildInteractiveTable filtering UX (PEGS app.js:1421+).
// Inline rather than a separate file to keep variant-B's blast radius small.
// Uses native inputs + .page-btn / .search-input styling shared with
// DataTableTab.vue, preserving the original PEGS dashboard aesthetic.
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
    showNovelFilter: { type: Boolean, default: false },
  },
  setup(props) {
    const search = ref('');
    const roleFilter = ref('all');
    const page = ref(1);
    const pageSize = 10;

    // The shape coming out of useFalconSummary doesn't carry an explicit
    // "role" — top rows live in .top, leads in .lead. The same gene can
    // appear in both. Detect "both" by treating isLead as the proxy.
    const filtered = computed(() => {
      const list = props.rows || [];
      const q = search.value.trim().toLowerCase();
      return list.filter((row) => {
        if (roleFilter.value === 'top' && row.isLead) return false;
        if (roleFilter.value === 'lead' && !row.isLead) return false;
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

    watch(
      [search, roleFilter, () => props.rows.length, () => props.showNovelFilter],
      () => {
        if (page.value > totalPages.value) page.value = totalPages.value;
        if (page.value < 1) page.value = 1;
      },
    );

    return () =>
      h('section', { class: 'summary-section' }, [
        h('div', { class: 'section-header' }, [
          h('h3', {}, [
            props.title,
            h(
              'span',
              { class: 'muted' },
              ` (${filtered.value.length} of ${(props.rows || []).length})`,
            ),
          ]),
          h('div', { class: 'section-controls' }, [
            h(
              'select',
              {
                class: 'role-select',
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
              class: 'search-input search-input--small',
              placeholder: 'Search name / clump / chr…',
              value: search.value,
              onInput: (e) => {
                search.value = e.target.value;
                page.value = 1;
              },
            }),
          ]),
        ]),
        pageRows.value.length === 0
          ? h(
              'div',
              { class: 'no-rows' },
              (props.rows || []).length === 0
                ? 'No data loaded.'
                : 'No rows match current filters.',
            )
          : h(
              'div',
              { class: 'section-list' },
              pageRows.value.map((row, i) =>
                h(TraitCard, { row, key: `${row.name || 'r'}-${row.index ?? i}` }),
              ),
            ),
        h('div', { class: 'pagination' }, [
          h(
            'button',
            {
              class: 'page-btn',
              disabled: page.value <= 1,
              onClick: () => (page.value = Math.max(1, page.value - 1)),
            },
            'Prev',
          ),
          h(
            'span',
            { class: 'page-info' },
            `Page ${page.value} of ${totalPages.value}`,
          ),
          h(
            'button',
            {
              class: 'page-btn',
              disabled: page.value >= totalPages.value,
              onClick: () =>
                (page.value = Math.min(totalPages.value, page.value + 1)),
            },
            'Next',
          ),
        ]),
      ]);
  },
};
</script>

<style scoped>
.plot-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}
.plot-row--two > .plot-card {
  flex: 1;
  min-width: 300px;
}
.plot-card {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.plot-card h4 {
  margin-top: 0;
  margin-bottom: 8px;
  padding-bottom: 8px;
  color: #111827;
  font-size: 1.1em;
  border-bottom: 2px solid #e5e7eb;
}
.plot-desc {
  font-size: 0.9em;
  color: #4b5563;
  line-height: 1.5;
  margin-bottom: 10px;
  margin-top: 0;
}
.plot-mount {
  position: relative;
  width: 100%;
}
.plot-mount--upset { height: 350px; }
.plot-mount--venn  { height: 280px; }
.plot-mount--dist  { height: 260px; }
.plot-inner {
  width: 100%;
  height: 100%;
}
.plot-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  font-style: italic;
  pointer-events: none;
  font-size: 0.9em;
  text-align: center;
  padding: 0 10px;
}

.summary-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  align-items: center;
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
.summary-btn.outline:hover:not(:disabled) { background: #f3f4f6; }
.summary-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.novelty-error { color: #dc2626; font-size: 0.85em; font-weight: 600; }

.summary-section {
  margin-bottom: 28px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid #3b82f6;
}
.section-header h3 {
  font-size: 1.05em;
  font-weight: 700;
  color: #111827;
  margin: 0;
}
.section-header .muted {
  color: #9ca3af;
  font-weight: 400;
  font-size: 0.85em;
  margin-left: 6px;
}
.section-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.role-select {
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  font-size: 0.85em;
  min-width: 130px;
}
.search-input {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  width: 250px;
  font-size: 0.9em;
}
.search-input--small { padding: 6px 8px; width: 220px; font-size: 0.85em; }
.section-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.no-rows {
  color: #6b7280;
  font-style: italic;
  padding: 12px 4px;
}
.pagination {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  margin-top: 10px;
}
.page-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  border-radius: 4px;
}
.page-btn:hover:not(:disabled) { background: #f3f4f6; }
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.page-info { color: #6b7280; font-size: 0.85em; }
.hidden { display: none; }
</style>
