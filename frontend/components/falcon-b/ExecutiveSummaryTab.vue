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
import { computed, h, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconSummary } from '~/composables/useFalconSummary';
import TraitCard from '~/components/falcon-b/TraitCard.vue';

const store = useFalconStore();
const { computeTopAndLeadSignals, attachClinicalTrials, attachNoveltyFlags } =
  useFalconSummary(store);

const clinicalTrials = store.clinicalTrials;
const summary = ref({
  genes: { top: [], lead: [] },
  variants: { top: [], lead: [] },
});
const showNovel = ref(false);
const noveltyLoading = ref(false);
const noveltyError = ref(false);
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
