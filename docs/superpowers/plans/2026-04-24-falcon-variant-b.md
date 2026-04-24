# FALCON Port — Variant B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Variant B ("PrimeVue shell, custom guts") of the FALCON Results Viewer at `/falcon-b`, consuming the shared foundation delivered by `falcon-port-base`.

**Architecture:** A Nuxt page at `pages/falcon-b/index.vue` with a PrimeVue `Tabs` shell (shared with Variant A) — but the tab content keeps the **original dashboard's look** for tables, cards, the chromosome filter, the data inspector panel, and the summary rows. Only the outer chrome (tab strip, active-dataset pill) and the global filter bar use PrimeVue. Dark mode is partial (the PrimeVue chrome works; custom-CSS components stay in a light palette).

**Tech Stack:** Nuxt 3 + Vue 3 + PrimeVue 4.5 (chrome only) + Tailwind + Pinia + Plotly (lazy-loaded).

**Spec:** `docs/superpowers/specs/2026-04-24-falcon-dashboard-port-to-vue3-design.md` (§8 Variant B column).

**Base plan (prerequisite):** `docs/superpowers/plans/2026-04-24-falcon-port-base.md`. All composables, the Pinia store, and utils are in place.

**Source of original markup/CSS:** `/home/dhite/code-repos/broad/PEGS/src/dashboard/index.html` and `.../styles.css`. Tasks below cite exact line ranges the subagent should lift from.

**Deliverable:** `/falcon-b` (behind existing auth) renders the FALCON dashboard. PrimeVue tab strip + active-dataset pill on top; everything inside each tab carries the original aesthetic.

---

## Preamble — ground rules for this plan

1. **Working directory:** `/home/dhite/code-repos/broad/dig-job-server-2/frontend`.
2. **Branch off `falcon-port-base`** (or `main` if base has merged by start time). Parallel to `falcon-variant-a`; the two branches touch disjoint file sets.
3. **Do NOT modify files outside `pages/falcon-b/` and `components/falcon-b/`.** No edits to `stores/`, `composables/`, `utils/`, or any `falcon-a` files.
4. **Commit freely on this feature branch** — user has authorized it. Trailer: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
5. **PrimeVue auto-import is on.** Components like `<Tabs>`, `<Tab>`, `<TabList>`, `<TabPanel>`, `<TabPanels>`, `<Tag>`, `<ToggleButton>`, `<InputNumber>`, `<Button>` are available as-is in templates.
6. **Original CSS strategy:** lift the original's styles into **scoped `<style>` blocks** inside each component (or inside a single `<style>` block per file). Do NOT modify `nuxt.config.ts` or add a global CSS file — per rule 3. Scoped styles keep each component self-contained and match the spec's "components diverge, everything else is shared" principle.
7. **Shared composables available (auto-imported):** `useFalconStore`, `useFalconFilters`, `useFalconPlots`, `useFalconTDP`, `useFalconSummary`, `useClinicalTrials`, `useGeneTraitFetcher`, `usePlotly`. Do not re-implement any of these.
8. **Dark mode is PARTIAL.** The outer chrome (tab strip, pill, global filter) inherits PrimeVue's dark-mode support. Inner components use the original light palette (white cards, gray borders, blue accents) regardless of theme — this is the intentional Variant-B look and the main visual contrast vs. Variant A.

### Standard Plotly mount pattern — use verbatim in every chart-rendering tab

```vue
<script setup>
import { usePlotly } from '~/composables/usePlotly';
const { mount, unmount, getPlotly } = usePlotly();
const plotEl = ref(null);
let current = null;

watchEffect(async () => {
  const spec = buildSpec(); // replace with relevant builder
  if (!plotEl.value) return;
  await mount(plotEl.value, spec);
  current = plotEl.value;
});

onBeforeUnmount(async () => {
  if (current) await unmount(current);
});
</script>
```

### Inspector panel via provide/inject

`pages/falcon-b/index.vue` owns the `<DataInspectorPanel>` instance and provides it:

```js
const inspectorRef = ref(null);
provide('falcon-inspector', inspectorRef);
```

Tabs rendering scatter plots call the panel via:
```js
const inspector = inject('falcon-inspector', null);
inspector?.value?.show(htmlString);
```

---

## File structure

```
pages/falcon-b/
  index.vue                        # host page

components/falcon-b/
  FolderPicker.vue
  GlobalFilterBar.vue              # PrimeVue — identical to Variant A minus Card wrap
  DataInspectorPanel.vue           # original fixed-position panel, custom CSS
  GenomicRegionFilter.vue          # original .chr-btn pills + dual-range <input>
  GenesScatterTab.vue              # Plotly scatter (spec identical to Variant A)
  VariantsScatterTab.vue
  DataTableTab.vue                 # native HTML <table>, custom sort + paginator
  TraitCard.vue                    # original .trait-card CSS
  ExecutiveSummaryTab.vue          # list of original-styled rows
  LogSummaryTab.vue                # plain white cards with inline stats rows
  TDPTab.vue                       # grouped flex toolbar, original CSS
```

Nothing else is created or modified.

---

## Task 1: Create `falcon-variant-b` branch

**Files:** none modified.

- [ ] **Step 1:** From `/home/dhite/code-repos/broad/dig-job-server-2`, verify clean tree on `falcon-port-base` (or `main` if base has merged):
    ```bash
    git status && git log --oneline main..HEAD 2>/dev/null | head -3
    ```

- [ ] **Step 2:** Branch:
    ```bash
    git checkout -b falcon-variant-b
    ```

- [ ] **Step 3:** Verify: `git branch --show-current` → `falcon-variant-b`.

No commit.

---

## Task 2: Page scaffold `pages/falcon-b/index.vue`

**Files:** create `frontend/pages/falcon-b/index.vue`.

Structurally near-identical to Variant A's scaffold (same Tabs/TabList/TabPanels, same URL-sync, same FolderPicker + GlobalFilterBar + DataInspectorPanel mounts). Only the subtitle text differs.

- [ ] **Step 1:** `mkdir -p frontend/pages/falcon-b`.

- [ ] **Step 2:** Write `frontend/pages/falcon-b/index.vue`:

    ```vue
    <template>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-6 space-y-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h1 class="text-2xl font-bold">FALCON Dashboard</h1>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Variant B — PrimeVue shell, custom guts
            </p>
          </div>
          <Tag
            v-if="store.folderName"
            severity="success"
            :value="`Active Dataset: ${store.folderName}`"
          />
        </div>

        <FolderPicker />
        <GlobalFilterBar />

        <p v-if="store.status" class="text-sm text-gray-500">{{ store.status }}</p>

        <Tabs :value="activeTab" @update:value="onTabChange">
          <TabList>
            <Tab value="summary" :disabled="!store.datasets.genes.isLoaded">
              Executive Summary
            </Tab>
            <Tab value="tdp">FALCON Zoom</Tab>
            <Tab value="genes" :disabled="!store.datasets.genes.isLoaded">
              Genes Plot
            </Tab>
            <Tab value="variants" :disabled="!store.datasets.variants.isLoaded">
              Variants Plot
            </Tab>
            <Tab value="table" :disabled="!store.datasets.genes.isLoaded">
              Data Table
            </Tab>
            <Tab value="log" :disabled="!store.datasets.log.isLoaded">
              Execution Time
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel value="summary">
              <ExecutiveSummaryTab v-if="store.datasets.genes.isLoaded" />
              <EmptyTab v-else reason="Load a folder to see the executive summary." />
            </TabPanel>
            <TabPanel value="tdp"><TDPTab /></TabPanel>
            <TabPanel value="genes">
              <GenesScatterTab v-if="store.datasets.genes.isLoaded" />
              <EmptyTab v-else reason="Load a folder containing .wg.genes." />
            </TabPanel>
            <TabPanel value="variants">
              <VariantsScatterTab v-if="store.datasets.variants.isLoaded" />
              <EmptyTab v-else reason="Load a folder containing .wg.variants." />
            </TabPanel>
            <TabPanel value="table">
              <DataTableTab v-if="store.datasets.genes.isLoaded" />
              <EmptyTab v-else reason="Load a folder to browse the raw tables." />
            </TabPanel>
            <TabPanel value="log">
              <LogSummaryTab v-if="store.datasets.log.isLoaded" />
              <EmptyTab v-else reason="Load a folder containing .wg.log." />
            </TabPanel>
          </TabPanels>
        </Tabs>

        <DataInspectorPanel ref="inspectorRef" />
      </div>
    </template>

    <script setup>
    import { h, ref, provide, watch } from 'vue';
    import { useFalconStore } from '~/stores/FalconStore';

    const store = useFalconStore();
    const route = useRoute();
    const router = useRouter();
    const activeTab = ref(route.query.tab || 'summary');
    const inspectorRef = ref(null);
    provide('falcon-inspector', inspectorRef);

    const EmptyTab = (props) =>
      h('p', { class: 'text-sm text-gray-500 dark:text-gray-400 py-6' }, props.reason || 'No data yet.');
    EmptyTab.props = ['reason'];

    function onTabChange(next) {
      if (!next || next === activeTab.value) return;
      activeTab.value = next;
      router.push({ query: { ...route.query, tab: next } });
    }

    watch(() => route.query.tab, (next) => {
      if (next && next !== activeTab.value) activeTab.value = next;
    });
    </script>
    ```

- [ ] **Step 3:** Create `frontend/components/falcon-b/` and stub all nine referenced components to the same pattern as Plan 2 Task 2 Step 4 (bash `for` loop with a `[ComponentName — stub]` placeholder). This lets the page mount cleanly.

- [ ] **Step 4:** Start dev server, visit `/falcon-b`. Expected: chrome renders, tabs disabled until a folder loads, no console errors.

- [ ] **Step 5:** Commit:
    ```
    feat(falcon-b): scaffold /falcon-b page with Tabs shell

    Same Tabs scaffold pattern as Variant A (PrimeVue chrome). Inner
    components stubbed. Subtitle calls out "Variant B — PrimeVue shell,
    custom guts" so reviewers can tell branches apart.
    ```

---

## Task 3: `FolderPicker.vue` + `GlobalFilterBar.vue` + `DataInspectorPanel.vue`

**Files:** modify three stubs.

### 3a — `FolderPicker.vue` (plain, unstyled native input; matches original `index.html:24`)

```vue
<template>
  <div class="flex items-center gap-3">
    <input
      ref="fileInput"
      type="file"
      webkitdirectory
      directory
      class="falcon-b-folder-input"
      @change="onChange"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();
const fileInput = ref(null);

async function onChange(e) {
  await store.loadFolder(e.target.files);
}
</script>

<style scoped>
/* From PEGS styles.css:20-22 — original input appearance */
.falcon-b-folder-input {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  font-size: 0.9em;
}
</style>
```

### 3b — `GlobalFilterBar.vue` (PrimeVue widgets in a flex row — no Card, no Fieldset)

```vue
<template>
  <div
    class="flex flex-wrap items-center gap-4 py-2 px-3 border rounded bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700"
  >
    <ToggleButton
      v-model="store.globalFilter.active"
      on-label="Strict Filter: ON"
      off-label="Strict Filter: OFF"
      on-icon="pi pi-filter"
      off-icon="pi pi-filter-slash"
    />
    <div class="flex items-center gap-2">
      <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Min Prob</label>
      <InputNumber
        v-model="store.globalFilter.minProb"
        :min="0"
        :max="1"
        :step="0.01"
        :min-fraction-digits="2"
        :max-fraction-digits="4"
        show-buttons
        button-layout="horizontal"
        class="w-36"
      />
    </div>
    <div class="flex items-center gap-2">
      <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Min NegP</label>
      <InputNumber
        v-model="store.globalFilter.minNegP"
        :min="0"
        :step="0.5"
        :min-fraction-digits="1"
        :max-fraction-digits="2"
        show-buttons
        button-layout="horizontal"
        class="w-36"
      />
    </div>
  </div>
</template>

<script setup>
import { useFalconStore } from '~/stores/FalconStore';
const store = useFalconStore();
</script>
```

### 3c — `DataInspectorPanel.vue` (fixed-position panel, original CSS from `index.html:214-226`)

```vue
<template>
  <div v-show="visible" class="falcon-inspector">
    <div class="falcon-inspector-header">
      <h4>🔍 Selection Details</h4>
      <button class="falcon-inspector-close" @click="visible = false">&times;</button>
    </div>
    <div class="falcon-inspector-body">
      <div class="falcon-inspector-content" v-html="html" />
      <button class="falcon-inspector-copy" @click="copy">
        📋 {{ copyLabel }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const html = ref('');
const copyLabel = ref('Copy to Clipboard');

function show(rawHtml) {
  html.value = rawHtml || 'No data available for this point.';
  visible.value = true;
}

async function copy() {
  const tmp = document.createElement('div');
  tmp.innerHTML = html.value;
  try {
    await navigator.clipboard.writeText(tmp.innerText);
    copyLabel.value = 'Copied!';
    setTimeout(() => (copyLabel.value = 'Copy to Clipboard'), 1500);
  } catch (err) {
    console.error('clipboard write failed', err);
  }
}

defineExpose({ show });
</script>

<style scoped>
/* From PEGS index.html:214-226 — preserves the floating-panel aesthetic */
.falcon-inspector {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 320px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  z-index: 9999;
  overflow: hidden;
  color: #111827;
}
.falcon-inspector-header {
  padding: 12px 15px;
  background: #f3f4f6;
  border-bottom: 1px solid #d1d5db;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.falcon-inspector-header h4 {
  margin: 0;
  color: #111827;
  font-size: 1em;
}
.falcon-inspector-close {
  background: none;
  border: none;
  font-size: 1.2em;
  color: #6b7280;
  cursor: pointer;
}
.falcon-inspector-body {
  padding: 15px;
}
.falcon-inspector-content {
  font-family: monospace;
  font-size: 0.95em;
  line-height: 1.6;
  color: #374151;
  margin-bottom: 15px;
  user-select: text;
}
.falcon-inspector-copy {
  width: 100%;
  padding: 8px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  color: #374151;
  transition: background 0.2s;
}
.falcon-inspector-copy:hover {
  background: #f3f4f6;
}
</style>
```

- [ ] **Step 1:** Replace the three stubs with the above.
- [ ] **Step 2:** Dev-server check: load `/falcon-b`. Folder picker renders as a plain native chooser. Global filter bar is a flex row of PrimeVue widgets (no Card wrapper). Inspector panel not yet visible (no scatter click yet) — but it's mounted (hidden).
- [ ] **Step 3:** Commit:
    ```
    feat(falcon-b): folder picker, PrimeVue filter bar, original inspector

    - FolderPicker: plain <input webkitdirectory> with original CSS.
    - GlobalFilterBar: PrimeVue widgets in a naked flex row (no Card wrap).
    - DataInspectorPanel: fixed-position panel with the original's exact
      CSS (lifted from PEGS index.html:214-226), kept light-palette
      regardless of theme (per Variant-B "partial dark mode").
    ```

---

## Task 4: `GenomicRegionFilter.vue` — original pills + dual-range slider

**Files:** modify stub.

**Reference CSS:** `PEGS/src/dashboard/styles.css:55-110` (the `.filter-card`, `.chr-btn`, `.range-slider`, `.region-inputs` blocks). **Reference HTML:** `PEGS/src/dashboard/index.html:60-93`.

Implements the original "Genomic Region Filter" card: a row of chromosome pill buttons and a custom dual-range slider (two overlapping `<input type=range>` elements with a CSS-drawn bar between them), plus two number inputs for start/end BP.

The chromosome bounds and the store wiring are identical to Plan 2's Task 4 — the only difference is the rendered appearance.

- [ ] **Step 1:** Lift the bounds-calculation logic and `selectedChr`/`bpRange` state from Plan 2 Task 4 (`components/falcon-a/GenomicRegionFilter.vue` after it's been written, or from spec §7 if Plan 2 hasn't been implemented yet). The `<script setup>` should be identical.

- [ ] **Step 2:** Replace the template with the original markup, adapting to Vue bindings:

    ```vue
    <template>
      <div class="filter-card">
        <div class="filter-header">
          <h4><span style="font-size: 1.2em">🧬</span> Genomic Region Filter</h4>
          <button
            v-if="selectedChr !== 'All'"
            class="reset-btn"
            @click="reset"
          >
            Reset to All Chromosomes
          </button>
        </div>
        <div class="filter-body">
          <p class="filter-hint">Select a Chromosome:</p>
          <div class="chr-grid">
            <button
              v-for="opt in chrOptions"
              :key="opt.value"
              class="chr-btn"
              :class="{ active: selectedChr === opt.value }"
              @click="selectedChr = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>

          <div
            v-if="selectedChr !== 'All' && currentBounds"
            class="region-selector"
          >
            <p class="filter-hint">Select Base Pair Range:</p>
            <div class="range-slider">
              <div class="slider-track" />
              <div
                class="slider-range"
                :style="{ left: rangePercent(0) + '%', width: rangeWidthPercent() + '%' }"
              />
              <input
                type="range"
                :min="currentBounds.min"
                :max="currentBounds.max"
                :step="bpStep"
                :value="bpRange[0]"
                @input="onLowInput($event)"
              />
              <input
                type="range"
                :min="currentBounds.min"
                :max="currentBounds.max"
                :step="bpStep"
                :value="bpRange[1]"
                @input="onHighInput($event)"
              />
            </div>
            <div class="region-inputs">
              <div class="input-group">
                <label>Start BP</label>
                <input
                  type="number"
                  :min="currentBounds.min"
                  :max="bpRange[1]"
                  :value="bpRange[0]"
                  @blur="bpRange = [Number($event.target.value), bpRange[1]]; applyRange()"
                />
              </div>
              <div class="input-group">
                <label>End BP</label>
                <input
                  type="number"
                  :min="bpRange[0]"
                  :max="currentBounds.max"
                  :value="bpRange[1]"
                  @blur="bpRange = [bpRange[0], Number($event.target.value)]; applyRange()"
                />
              </div>
              <button class="apply-btn" @click="applyRange">Apply Range</button>
            </div>
          </div>
        </div>
      </div>
    </template>
    ```

- [ ] **Step 3:** Add the `onLowInput`, `onHighInput`, `rangePercent`, `rangeWidthPercent` helpers in `<script setup>` (they update `bpRange` while keeping `[0] ≤ [1]`):

    ```js
    function onLowInput(e) {
      const v = Number(e.target.value);
      bpRange.value = [Math.min(v, bpRange.value[1]), bpRange.value[1]];
      applyRange();
    }
    function onHighInput(e) {
      const v = Number(e.target.value);
      bpRange.value = [bpRange.value[0], Math.max(v, bpRange.value[0])];
      applyRange();
    }
    function rangePercent(idx) {
      if (!currentBounds.value) return 0;
      const { min, max } = currentBounds.value;
      return ((bpRange.value[idx] - min) / (max - min)) * 100;
    }
    function rangeWidthPercent() {
      return rangePercent(1) - rangePercent(0);
    }
    ```

- [ ] **Step 4:** Add scoped styles lifted from `PEGS/src/dashboard/styles.css:55-110`:

    ```vue
    <style scoped>
    .filter-card {
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      margin-bottom: 20px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      overflow: hidden;
    }
    .filter-header {
      padding: 12px 20px;
      background: #f9fafb;
      border-bottom: 1px solid #d1d5db;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .filter-header h4 {
      margin: 0;
      color: #111827;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .filter-body {
      padding: 20px;
      transition: all 0.3s ease;
    }
    .filter-hint {
      margin: 0 0 10px 0;
      font-size: 0.9em;
      color: #4b5563;
    }
    .reset-btn {
      padding: 4px 10px;
      font-size: 0.8em;
      background: #fee2e2;
      color: #b91c1c;
      border: 1px solid #f87171;
      border-radius: 4px;
      cursor: pointer;
      transition: 0.2s;
    }
    .reset-btn:hover {
      background: #fecaca;
    }
    .chr-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    .chr-btn {
      padding: 6px 12px;
      border: 1px solid #d1d5db;
      background: white;
      border-radius: 20px;
      cursor: pointer;
      font-weight: 500;
      color: #4b5563;
      transition: all 0.2s ease;
    }
    .chr-btn:hover {
      border-color: #3b82f6;
      color: #3b82f6;
    }
    .chr-btn.active {
      background: #3b82f6;
      color: white;
      border-color: #3b82f6;
      box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
    }
    .region-selector {
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px dashed #d1d5db;
      animation: fadeInDown 0.4s ease forwards;
    }
    @keyframes fadeInDown {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .range-slider {
      position: relative;
      width: 100%;
      height: 40px;
    }
    .slider-track {
      position: absolute;
      width: 100%;
      height: 6px;
      background: #e5e7eb;
      border-radius: 3px;
      top: 50%;
      transform: translateY(-50%);
      z-index: 1;
    }
    .slider-range {
      position: absolute;
      height: 6px;
      background: #3b82f6;
      border-radius: 3px;
      top: 50%;
      transform: translateY(-50%);
      z-index: 2;
    }
    .range-slider input[type='range'] {
      position: absolute;
      width: 100%;
      height: 100%;
      top: 0;
      -webkit-appearance: none;
      background: transparent;
      pointer-events: none;
      z-index: 3;
      margin: 0;
    }
    .range-slider input[type='range']::-webkit-slider-thumb {
      pointer-events: auto;
      -webkit-appearance: none;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: white;
      border: 2px solid #3b82f6;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
      cursor: grab;
    }
    .range-slider input[type='range']::-webkit-slider-thumb:active {
      cursor: grabbing;
      background: #3b82f6;
    }
    .region-inputs {
      display: flex;
      gap: 15px;
      align-items: flex-end;
      margin-top: 15px;
    }
    .input-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
    }
    .input-group label {
      font-size: 0.8em;
      font-weight: bold;
      color: #4b5563;
    }
    .input-group input {
      padding: 8px;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      font-family: monospace;
    }
    .apply-btn {
      padding: 8px 14px;
      background: #3b82f6;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      height: fit-content;
    }
    .apply-btn:hover {
      background: #2563eb;
    }
    </style>
    ```

- [ ] **Step 5:** Commit:
    ```
    feat(falcon-b): genomic region filter with original pill-button aesthetic

    Lifts the .chr-btn grid, dual-range <input type=range> slider, and
    fadeInDown animation from PEGS styles.css:55-110 into a scoped
    style block. Chromosome bounds + BP range state mirror the Variant-A
    implementation; only the DOM and CSS differ.
    ```

---

## Task 5: `GenesScatterTab.vue` + `VariantsScatterTab.vue`

**Files:** modify both stubs.

**IDENTICAL to Variant A Task 5** — the Plotly specs come from the same shared composable (`useFalconPlots`), and the click-to-inspector pattern is the same. The only thing that differs is the `<GenomicRegionFilter>` inside `GenesScatterTab.vue` uses Variant B's styled component. Since Variant-B's filter is drop-in at the same path, the template looks the same. So:

- [ ] **Step 1:** Use exactly the Variant-A Task 5 component code (see `plans/2026-04-24-falcon-variant-a.md` §Task 5) but save the files at `components/falcon-b/GenesScatterTab.vue` and `.../VariantsScatterTab.vue`. The imports from `~/composables/*` are shared; the only component import in-template is `GenomicRegionFilter` — that's auto-resolved via Nuxt's component auto-discovery to the `falcon-b` sibling since both files live under `components/falcon-b/`.

    Note: if Nuxt's component auto-discovery is ambiguous (e.g., picks `components/falcon-a/GenomicRegionFilter.vue` instead), switch to an explicit import:
    ```js
    import GenomicRegionFilter from '~/components/falcon-b/GenomicRegionFilter.vue';
    ```
    Same for `DataInspectorPanel` if needed — though that's injected via `provide`/`inject` so auto-import doesn't matter.

- [ ] **Step 2:** Dev check: load T2D, click "Genes Plot" — scatter renders; chromosome filter pills appear with the original aesthetic. Click a point → inspector panel appears bottom-right with the original fixed-position styling.

- [ ] **Step 3:** Commit:
    ```
    feat(falcon-b): genes and variants scatter tabs

    Identical chart logic to Variant A (same useFalconPlots composable,
    same plotly_click → inspector wiring). The visual divergence from
    Variant A lives in the components they host — the Variant-B
    GenomicRegionFilter and DataInspectorPanel.
    ```

---

## Task 6: `DataTableTab.vue` — native HTML table with custom sort + paginator

**Files:** modify stub.

**Reference HTML:** `PEGS/src/dashboard/index.html:103-119`. **Reference CSS:** `PEGS/src/dashboard/styles.css:40-50`.

Drops the PrimeVue `DataTable`. Uses a plain `<table>` with sticky `<thead>`, click-to-sort headers, a visible "Page N of M" label, and Prev/Next buttons. Same filter + sort semantics as Variant A, different markup.

```vue
<template>
  <div>
    <div class="toolbar">
      <div class="inner-switch">
        <button
          v-for="opt in datasetOptions"
          :key="opt.value"
          :class="{ active: currentDataset === opt.value }"
          @click="currentDataset = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
      <input
        v-model="state.searchQuery"
        type="text"
        placeholder="Search entire table..."
        class="search-input"
      />
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col"
              @click="handleSort(col)"
            >
              {{ col }}
              <span v-if="state.sortCol === col" class="sort-arrow">
                {{ state.sortAsc ? '▲' : '▼' }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in pageRows" :key="i">
            <td v-for="col in columns" :key="col">{{ row[col] }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button
        class="page-btn"
        :disabled="state.currentPage <= 1"
        @click="state.currentPage--"
      >
        Previous
      </button>
      <span>Page {{ state.currentPage }} of {{ totalPages }}</span>
      <button
        class="page-btn"
        :disabled="state.currentPage >= totalPages"
        @click="state.currentPage++"
      >
        Next
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { FALCON_ROWS_PER_PAGE } from '~/utils/falcon/config';

const store = useFalconStore();
const rowsPerPage = FALCON_ROWS_PER_PAGE;

const datasetOptions = [
  { value: 'genes', label: 'Genes' },
  { value: 'variants', label: 'Variants' },
];
const currentDataset = ref('genes');
const state = computed(() => store.tableStates[currentDataset.value]);
const columns = computed(() => store.datasets[currentDataset.value].columns);

const filteredAndSorted = computed(() => {
  const raw = store.datasets[currentDataset.value].data;
  const q = state.value.searchQuery?.toLowerCase();
  let rows = raw;
  if (q) {
    rows = rows.filter((r) =>
      columns.value.some((c) => String(r[c] ?? '').toLowerCase().includes(q)),
    );
  }
  const { sortCol, sortAsc } = state.value;
  if (sortCol) {
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol], bv = b[sortCol];
      const an = parseFloat(av), bn = parseFloat(bv);
      const num = !isNaN(an) && !isNaN(bn);
      const cmp = num ? an - bn : String(av ?? '').localeCompare(String(bv ?? ''));
      return sortAsc ? cmp : -cmp;
    });
  }
  return rows;
});

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredAndSorted.value.length / rowsPerPage)),
);

const pageRows = computed(() => {
  const start = (state.value.currentPage - 1) * rowsPerPage;
  return filteredAndSorted.value.slice(start, start + rowsPerPage);
});

function handleSort(col) {
  if (state.value.sortCol === col) {
    state.value.sortAsc = !state.value.sortAsc;
  } else {
    state.value.sortCol = col;
    state.value.sortAsc = true;
  }
  state.value.currentPage = 1;
}

watch([currentDataset, () => state.value.searchQuery], () => {
  state.value.currentPage = 1;
});
</script>

<style scoped>
/* Adapted from PEGS styles.css:40-50 */
.toolbar {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 15px;
}
.inner-switch {
  display: flex;
  gap: 4px;
}
.inner-switch button {
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  border-radius: 4px;
  font-weight: 500;
  color: #4b5563;
  transition: 0.2s;
}
.inner-switch button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}
.search-input {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  width: 250px;
  font-size: 0.9em;
}
.table-wrapper {
  overflow: auto;
  max-height: 60vh;
  border: 1px solid #d1d5db;
  margin-bottom: 15px;
  background: white;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
  font-size: 0.9em;
}
th {
  background-color: #f3f4f6;
  cursor: pointer;
  position: sticky;
  top: 0;
  z-index: 10;
}
th:hover {
  background-color: #e5e7eb;
}
.sort-arrow {
  margin-left: 4px;
  color: #3b82f6;
}
.pagination {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}
.page-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  border-radius: 4px;
}
.page-btn:hover:not(:disabled) {
  background: #f3f4f6;
}
.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
```

- [ ] **Step 1:** Replace stub.
- [ ] **Step 2:** Dev check: load T2D, click Data Table → native table renders with 15 rows. Click a header → sort arrow shows and rows re-sort. Search narrows results. Switch to Variants via inner-switch button. Prev/Next work.
- [ ] **Step 3:** Commit:
    ```
    feat(falcon-b): data table with native HTML <table> + custom paginator

    Drops PrimeVue DataTable; uses sticky-header <table> with click-sort
    columns, Prev/Next paginator, and a custom inner-switch button group
    for genes/variants. Preserves the original table aesthetic (styles
    lifted from PEGS styles.css:40-50).
    ```

---

## Task 7: `TraitCard.vue` + `ExecutiveSummaryTab.vue`

**Files:** modify both stubs.

**Reference CSS:** `PEGS/src/dashboard/styles.css:113-129` (`.trait-card`).

### 7a — `TraitCard.vue` — original card appearance

```vue
<template>
  <div class="trait-card">
    <div class="trait-card-header" @click="expanded = !expanded">
      <span class="trait-name">{{ row.name }}</span>
      <span class="trait-chip clump">Clump {{ row.clumpId }}</span>
      <span v-if="row.isLead" class="trait-chip lead">⭐ Lead</span>
      <span v-if="row.isNovel === false" class="trait-chip known">Known</span>
      <span v-if="row.isNovel === true" class="trait-chip novel">Novel</span>
      <span class="trait-meta">
        Chr {{ row.chr }} · Prob {{ row.prob.toFixed(3) }} · NegP {{ row.negP.toFixed(2) }}
      </span>
      <span class="trait-toggle">{{ expanded ? '−' : '+' }}</span>
    </div>

    <div v-if="expanded" class="trait-card-body">
      <div v-if="row.traits?.length" class="trait-section">
        <h4>Associated traits</h4>
        <ul>
          <li v-for="(t, i) in row.traits" :key="i" class="trait-citation">
            <span class="mono">{{ t.Trait || t.trait || '—' }}</span>
            <span v-if="t.Citation || t.citation" class="muted">
              ({{ t.Citation || t.citation }})
            </span>
          </li>
        </ul>
      </div>
      <div v-if="row.clinicalTrials?.length" class="trait-section">
        <h4>Clinical trials</h4>
        <ul>
          <li v-for="(t, i) in row.clinicalTrials" :key="i" class="trial-row">
            <span class="mono">{{ t.drugId }}</span>
            · {{ t.indication }}
            <span class="trait-chip phase">Phase {{ t.phase }}</span>
          </li>
        </ul>
      </div>
      <div
        v-if="!row.traits?.length && !row.clinicalTrials?.length"
        class="muted"
      >
        No trait or trial data.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
defineProps({ row: { type: Object, required: true } });
const expanded = ref(false);
</script>

<style scoped>
/* Lifted + extended from PEGS styles.css:113-129 */
.trait-card {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 10px 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  overflow-wrap: break-word;
  word-break: break-word;
  margin-bottom: 8px;
  color: #111827;
}
.trait-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex-wrap: wrap;
}
.trait-name {
  font-weight: 600;
  color: #111827;
}
.trait-chip {
  font-size: 0.75em;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  background: #f3f4f6;
  color: #374151;
}
.trait-chip.lead { background: #fef3c7; border-color: #fbbf24; color: #92400e; }
.trait-chip.known { background: #e5e7eb; border-color: #9ca3af; color: #4b5563; }
.trait-chip.novel { background: #d1fae5; border-color: #10b981; color: #047857; }
.trait-chip.clump { background: #dbeafe; border-color: #60a5fa; color: #1e40af; }
.trait-chip.phase { background: #ede9fe; border-color: #a78bfa; color: #5b21b6; }
.trait-meta {
  margin-left: auto;
  font-size: 0.8em;
  color: #6b7280;
}
.trait-toggle {
  width: 18px;
  text-align: center;
  color: #6b7280;
  font-weight: bold;
}
.trait-card-body {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}
.trait-section {
  margin-bottom: 10px;
}
.trait-section h4 {
  margin: 0 0 4px 0;
  font-size: 0.85em;
  font-weight: 600;
  color: #374151;
}
.trait-section ul {
  list-style: disc inside;
  font-size: 0.85em;
  margin: 0;
  padding: 0;
}
.trait-citation {
  margin-bottom: 4px;
  line-height: 1.4;
}
.mono { font-family: monospace; }
.muted { color: #6b7280; font-size: 0.85em; }
</style>
```

### 7b — `ExecutiveSummaryTab.vue`

Same `<script setup>` as Variant A's Task 7 (lifts `useFalconSummary`, computes `summary`, toggles novelty). Only the template wraps TraitCards in "section headers + simple div" rather than using PrimeVue DataView:

```vue
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
// Script setup identical to Variant A Task 7b; copy exactly.
// (Reproduced inline in full to match "no placeholders" plan rule.)
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconSummary } from '~/composables/useFalconSummary';

const store = useFalconStore();
const { computeTopAndLeadSignals, attachClinicalTrials, attachNoveltyFlags } = useFalconSummary(store);

const clinicalTrials = store.clinicalTrials;
const summary = ref({ genes: { top: [], lead: [] }, variants: { top: [], lead: [] } });
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
  showNovel.value ? (summary.value.genes?.top || []).filter((r) => r.isNovel === true) : (summary.value.genes?.top || []),
);
const filteredGenesLead = computed(() =>
  showNovel.value ? (summary.value.genes?.lead || []).filter((r) => r.isNovel === true) : (summary.value.genes?.lead || []),
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
```

- [ ] **Step 1:** Replace both stubs.
- [ ] **Step 2:** Dev check: load T2D, click "Executive Summary" → four sections of styled TraitCards. Click a header → expands. Load `PEGS/src/dashboard/data/clinical_trials.csv` → chips appear on matched cards. Toggle novelty → async fetch, filter narrows.
- [ ] **Step 3:** Commit:
    ```
    feat(falcon-b): executive summary with original trait-card aesthetic

    TraitCard uses the .trait-card CSS from PEGS styles.css:113-129, extended
    with color-coded chips for lead/known/novel/phase. ExecutiveSummaryTab
    drops the PrimeVue DataView and Panel in favor of plain sections with
    underlined headings. Same async novelty-fetch (AbortController) as
    Variant A — the store behavior is shared.
    ```

---

## Task 8: `LogSummaryTab.vue` — plain white cards

**Files:** modify stub.

Same logic as Variant A (same composable calls, same `chrView` state, same per-component histogram + pre-process bar). Only the markup and CSS change — plain white cards with inline stats rows instead of PrimeVue `Card` + `Tag`.

```vue
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
const { buildLogIterHistogramSpec, buildLogPreprocessBarSpec } = useFalconPlots(store);
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
  for (const c of components) out[c] = buildLogIterHistogramSpec(c, chrView.value);
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
    if (!s.stats) { el.innerHTML = ''; continue; }
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
```

- [ ] **Step 1:** Replace stub.
- [ ] **Step 2:** Dev check: load T2D, click "Execution Time" → total-time pill, explainer card, chromosome select, bar chart, 8 histogram cards with the original aesthetic.
- [ ] **Step 3:** Commit:
    ```
    feat(falcon-b): log summary with original plain-white-card aesthetic

    Same Plotly specs (shared useFalconPlots), same chr-view state; plain
    HTML cards with inline <span> stats rows replace PrimeVue Card/Tag.
    Explainer card preserves the verbatim "Parallel Wall Time" note from
    the original.
    ```

---

## Task 9: `TDPTab.vue` — grouped flex toolbar

**Files:** modify stub.

Same `cfg` state and same `runAnalysis` call as Variant A. The toolbar is a flex row with native-styled inputs (not PrimeVue `Card`/`InputText`/`Slider`), lifted approximately from `PEGS/src/dashboard/index.html:157-207`.

```vue
<template>
  <div>
    <h3 class="tdp-title">FALCON Zoom & LD Correlation</h3>
    <p class="tdp-hint">
      To apply the global filters the plot needs to be reloaded.
    </p>

    <div class="tdp-toolbar">
      <div class="input-group">
        <label>Target Gene</label>
        <input v-model="cfg.gene" type="text" placeholder="e.g., CETP" />
      </div>
      <div class="input-group">
        <label>Boundary (BP)</label>
        <input v-model.number="cfg.boundary" type="number" step="50000" />
      </div>
      <div class="input-group">
        <label>Focus</label>
        <select v-model="cfg.focus">
          <option value="region">Region</option>
          <option value="gene">Gene Only</option>
        </select>
      </div>
      <div class="input-group">
        <label>Plot Type</label>
        <select v-model="cfg.plotType">
          <option value="falcon">FALCON</option>
          <option value="raw">Raw input</option>
          <option value="overlay">Overlay</option>
        </select>
      </div>

      <div class="toolbar-divider" />

      <div class="input-group">
        <label class="ld-label">LD Matrix (.gz or .sorted files)</label>
        <div class="ld-row">
          <button class="ld-btn" @click="triggerLdDialog">
            📁 {{ store.tdp.ldFolderName || 'Load LD Folder' }}
          </button>
          <input
            ref="ldInput"
            type="file"
            webkitdirectory
            directory
            class="hidden"
            @change="onLdChange"
          />
          <span class="divider-v" />
          <label>Min R²</label>
          <input
            v-model.number="cfg.minR2"
            type="number"
            min="0"
            max="1"
            step="0.1"
            class="mini-input"
          />
          <span class="divider-v" />
          <label>Max Stretch</label>
          <input
            v-model.number="cfg.maxStretch"
            type="range"
            min="0.1"
            max="1"
            step="0.05"
            class="stretch-range"
          />
        </div>
      </div>

      <div class="toolbar-spacer" />
      <button
        class="run-btn"
        :disabled="running || !cfg.gene"
        @click="run"
      >
        {{ running ? 'Running…' : 'Run Analysis' }}
      </button>
    </div>

    <div v-if="store.tdp.status" class="tdp-status">
      {{ store.tdp.status }}
    </div>

    <div ref="plotEl" class="tdp-plot" />
  </div>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconTDP } from '~/composables/useFalconTDP';
import { usePlotly } from '~/composables/usePlotly';

const store = useFalconStore();
const { runAnalysis } = useFalconTDP(store);
const { mount, unmount } = usePlotly();

const cfg = reactive({
  gene: 'CETP',
  boundary: 500000,
  focus: 'region',
  plotType: 'falcon',
  minR2: 0.0,
  maxStretch: 1.0,
});

const plotEl = ref(null);
const ldInput = ref(null);
const running = ref(false);
let mountedEl = null;

async function run() {
  running.value = true;
  try {
    const spec = await runAnalysis({ ...cfg });
    if (!spec || !plotEl.value) return;
    await mount(plotEl.value, spec);
    mountedEl = plotEl.value;
  } catch (err) {
    console.error('TDP runAnalysis failed:', err);
    store.tdp.status = `Error: ${err.message || String(err)}`;
  } finally {
    running.value = false;
  }
}

function triggerLdDialog() { ldInput.value?.click(); }
async function onLdChange(e) { await store.loadLdFolder(e.target.files); }

onBeforeUnmount(async () => {
  if (mountedEl) await unmount(mountedEl);
});
</script>

<style scoped>
.tdp-title {
  font-size: 1.25em;
  font-weight: 700;
  color: #111827;
  margin-bottom: 8px;
}
.tdp-hint {
  font-size: 0.85em;
  color: #6b7280;
  margin-bottom: 15px;
}
.tdp-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  background: #f9fafb;
  padding: 15px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  align-items: center;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.input-group > label {
  font-size: 0.8em;
  font-weight: bold;
  color: #4b5563;
}
.input-group input[type='text'],
.input-group input[type='number'],
.input-group select {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
}
.toolbar-divider {
  width: 0;
  border-left: 2px dashed #d1d5db;
  height: 40px;
  margin: 0 5px;
}
.ld-label { color: #2563eb; font-weight: bold; }
.ld-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ld-btn {
  padding: 6px 12px;
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #93c5fd;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}
.ld-btn:hover {
  background: #dbeafe;
}
.divider-v {
  width: 0;
  border-left: 1px solid #d1d5db;
  height: 20px;
}
.mini-input {
  width: 50px;
  padding: 4px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}
.stretch-range {
  width: 80px;
}
.toolbar-spacer {
  flex: 1;
}
.run-btn {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}
.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tdp-status {
  margin-bottom: 15px;
  color: #3b82f6;
  font-weight: bold;
}
.tdp-plot {
  width: 100%;
  height: 850px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
}
.hidden { display: none; }
</style>
```

- [ ] **Step 1:** Replace stub.
- [ ] **Step 2:** Dev check: load T2D, click "FALCON Zoom", change target gene to something in the T2D dataset, click "Run Analysis" → status shows, plot renders below. No LD folder → trait-only rendering, same behavior as Variant A.
- [ ] **Step 3:** Commit:
    ```
    feat(falcon-b): FALCON Zoom tab with grouped flex toolbar

    Same runAnalysis flow and lastAnalysis caching as Variant A; the
    visual divergence is the toolbar — native <input>/<select> inside
    a gray-background flex row, as in PEGS index.html:157-207. LD
    controls are styled with the original blue-accent treatment.
    ```

---

## Task 10: End-to-end smoke test

**Files:** none.

- [ ] **Step 1:** Start dev: `npm run dev` from `frontend/`.
- [ ] **Step 2:** Visit `http://localhost:3000/falcon-b`.
- [ ] **Step 3:** Confirm chrome: title, subtitle "Variant B — PrimeVue shell, custom guts", folder picker (plain), global filter bar (PrimeVue flex row), Tabs strip.
- [ ] **Step 4:** Load `~/falcon-fixtures/kp5/T2D/` (via Playwright's in-browser DataTransfer technique from the base-plan smoke test, or native picker in a real browser). Active dataset pill appears.
- [ ] **Step 5:** Visit each tab:
    - **Executive Summary** — four sections of styled TraitCards; expand cards; load clinical trials.
    - **FALCON Zoom** — controls toolbar renders; Run Analysis works.
    - **Genes Plot** — Plotly scatter renders; original-style chromosome pill grid; click a point → Inspector panel (floating, original CSS) shows.
    - **Variants Plot** — scatter renders, no chromosome filter.
    - **Data Table** — native table with sticky header; sort/search/paginate/switch dataset work.
    - **Execution Time** — total-time green pill, 8 plain white histogram cards.
- [ ] **Step 6:** Toggle dark mode via footer. Chrome (tabs, pill, global filter) adapts to dark. Inner components stay in the light palette — THIS IS EXPECTED per the "partial dark mode" spec choice for Variant B. No broken visibility.
- [ ] **Step 7:** Reload with TGnonT2D — cache resets, data repopulates.
- [ ] **Step 8:** Ctrl-C the dev server.

No commit.

---

## Done when

- All 10 tasks complete.
- `git log --oneline main..HEAD` on `falcon-variant-b` shows ~8–9 commits.
- Smoke test passes — outer chrome responds to dark mode, inner content stays in the light palette, all six tabs function.
- Zero edits to shared files under `stores/`, `composables/`, `utils/`, and no edits to `pages/falcon-a/` or `components/falcon-a/`.

**Next:** open a PR `falcon-variant-b` → `main` (after base has merged). Once both variant PRs land, compare `/falcon-a` vs `/falcon-b` on the deployed env and run the cleanup PR per spec §13.
