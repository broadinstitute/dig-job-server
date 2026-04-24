# FALCON Port — Variant A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land Variant A ("full PrimeVue") of the FALCON Results Viewer at `/falcon-a`, consuming the shared foundation delivered by `falcon-port-base`.

**Architecture:** A Nuxt page at `pages/falcon-a/index.vue` with a PrimeVue `Tabs` shell. Every UI surface uses PrimeVue widgets where one exists (`DataTable`, `Slider`, `SelectButton`, `Panel`, `Card`, `Dialog`, `ToggleButton`, `InputNumber`). Charts are Plotly specs produced by the shared composables in `~/composables/useFalconPlots` and mounted via `usePlotly`. Dark mode is expected to work on every surface.

**Tech Stack:** Nuxt 3 + Vue 3 + PrimeVue 4.5 (Aura/Indigo preset) + Tailwind + Pinia + Plotly (lazy-loaded).

**Spec:** `docs/superpowers/specs/2026-04-24-falcon-dashboard-port-to-vue3-design.md`

**Base plan (prerequisite):** `docs/superpowers/plans/2026-04-24-falcon-port-base.md` — the foundation this plan builds on. All composables, the Pinia store, and utils are already in place.

**Deliverable:** `/falcon-a` (behind existing auth) renders the FALCON dashboard with a PrimeVue `Tabs` strip exposing all six tabs (Summary, Zoom, Genes, Variants, Table, Log). A folder picker populates the store; each tab renders live when its required dataset is loaded.

---

## Preamble — ground rules for this plan

1. **Working directory:** `/home/dhite/code-repos/broad/dig-job-server-2/frontend` unless stated otherwise.
2. **Branch off `falcon-port-base`.** Base hasn't merged to main yet at the time this plan starts. After base merges, `falcon-variant-a` can be rebased onto main if you want, but isn't required — the only important thing is that both branches share the same foundation commits.
3. **Do NOT modify files outside `pages/falcon-a/` and `components/falcon-a/`.** The whole point of the route-per-variant model is isolation. No edits to `stores/`, `composables/`, `utils/`, or any other page/component directory. If something in those looks wrong, stop and escalate.
4. **Commit freely on this feature branch** — user has authorized branch-level commits without per-commit approval. Use the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
5. **No automated tests.** Manual verification per task via Playwright MCP (or browser) — the end-of-plan smoke test exercises everything.
6. **PrimeVue auto-import is on** (see `nuxt.config.ts` — `primevue: { autoImport: true }`). Do NOT add explicit PrimeVue imports in `<script setup>`; just use the tags/components directly.
7. **Dark mode.** Every component written here must look correct under both light and dark. The pattern is Tailwind `dark:` classes + letting PrimeVue's Aura theme do the rest. The app wraps `<html>` with `.dark` when dark mode is active (see `layouts/default.vue` + `composables/useTheme.js`).
8. **Shared composables available (auto-imported under `~/composables/*`):** `useFalconStore` (Pinia), `useFalconDataSource`, `useFalconFilters`, `useFalconPlots`, `useFalconTDP`, `useFalconSummary`, `useClinicalTrials`, `useGeneTraitFetcher`, `usePlotly`.
9. **Test fixtures:** `~/falcon-fixtures/kp5/T2D/` and `~/falcon-fixtures/kp5/TGnonT2D/`. During smoke test, the helper `frontend/public/kp5` symlink (added as a git-local exclude during base smoke-testing) lets the dev server serve them for in-browser load via `fetch('/kp5/T2D/pegs1.wg.genes')`. If the symlink has been removed, re-create per the base plan's smoke-test section.
10. **Default-login env is already set up** in `frontend/.env` (also gitignored; don't re-commit).
11. **Plotly mount pattern — use this verbatim across all tabs rendering charts:**

    ```vue
    <script setup>
    import { usePlotly } from '~/composables/usePlotly';
    const { mount, unmount } = usePlotly();
    const plotEl = ref(null);

    // Rebuild and remount whenever spec or filters change.
    let current = null;
    watchEffect(async () => {
        const spec = buildSpec();  // replaces with the relevant builder
        if (!plotEl.value) return;
        await mount(plotEl.value, spec);
        current = plotEl.value;
    });

    onBeforeUnmount(async () => {
        if (current) await unmount(current);
    });
    </script>
    ```

    This makes every tab's chart reactive to `store.globalFilter` and `store.plotFilters` without manual re-render wiring.

---

## File structure

All files created live under exactly two directories:

```
pages/falcon-a/
  index.vue                        # host page: Tabs shell, URL-synced active tab,
                                   # mounts GlobalFilterBar + FolderPicker + DataInspectorPanel

components/falcon-a/
  FolderPicker.vue                 # PrimeVue Button → hidden <input webkitdirectory>
  GlobalFilterBar.vue              # ToggleButton + InputNumber × 2 in a Card
  DataInspectorPanel.vue           # Dialog (OverlayPanel-style, bottom-right)
  GenomicRegionFilter.vue          # SelectButton chromosome grid + Slider :range
  GenesScatterTab.vue              # Plotly scatter (uses GenomicRegionFilter)
  VariantsScatterTab.vue           # Plotly scatter (no region filter)
  DataTableTab.vue                 # PrimeVue DataTable with lazy paginator
  TraitCard.vue                    # PrimeVue Panel (collapsible) per expanded summary row
  ExecutiveSummaryTab.vue          # DataView of signals + TraitCards + summary charts
  LogSummaryTab.vue                # Per-component Card grid with Plotly histograms
  TDPTab.vue                       # Controls row + separate LD folder picker + zoom Plotly
```

Nothing else is created or modified in this plan.

---

## Task 1: Create `falcon-variant-a` branch

**Files:** none modified.

- [ ] **Step 1:** From `/home/dhite/code-repos/broad/dig-job-server-2`, verify current state:
    ```bash
    git status && git log --oneline main..HEAD | head -3
    ```
    Expected: clean tree; HEAD is on `falcon-port-base` with the base-plan commits.

- [ ] **Step 2:** Branch from the current tip of `falcon-port-base`:
    ```bash
    git checkout -b falcon-variant-a
    ```

- [ ] **Step 3:** Verify:
    ```bash
    git branch --show-current
    ```
    Expected: `falcon-variant-a`.

No commit for this task.

---

## Task 2: Page scaffold `pages/falcon-a/index.vue`

**Files:**
- Create: `frontend/pages/falcon-a/index.vue`

Delivers a rendered `/falcon-a` page with a PrimeVue `Tabs` shell, URL-synced active tab, mounts for `FolderPicker` + `GlobalFilterBar` + `DataInspectorPanel` (inline placeholder comments — wired in Task 3), and a "Coming soon" panel in each tab. After this task, visiting `/falcon-a` logged in shows the chrome and no console errors.

- [ ] **Step 1:** Create the directory:
    ```bash
    mkdir -p /home/dhite/code-repos/broad/dig-job-server-2/frontend/pages/falcon-a
    ```

- [ ] **Step 2:** Write `frontend/pages/falcon-a/index.vue`:

    ```vue
    <template>
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-6 space-y-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h1 class="text-2xl font-bold">FALCON Dashboard</h1>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Variant A — full PrimeVue
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

            <TabPanel value="tdp">
              <TDPTab />
            </TabPanel>

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

        <DataInspectorPanel />
      </div>
    </template>

    <script setup>
    import { useFalconStore } from '~/stores/FalconStore';

    const store = useFalconStore();
    const route = useRoute();
    const router = useRouter();
    const activeTab = ref(route.query.tab || 'summary');

    function onTabChange(next) {
      if (!next || next === activeTab.value) return;
      activeTab.value = next;
      router.push({ query: { ...route.query, tab: next } });
    }

    watch(
      () => route.query.tab,
      (next) => {
        if (next && next !== activeTab.value) activeTab.value = next;
      },
    );
    </script>
    ```

    This references several components that don't exist yet. Add an inline `EmptyTab` helper to avoid "unknown component" warnings:

- [ ] **Step 3:** At the top of the `<script setup>` block, after the `store` line, add a small local component for the empty-tab placeholder:

    ```vue
    <script setup>
    import { useFalconStore } from '~/stores/FalconStore';
    import { h } from 'vue';

    const store = useFalconStore();
    // ... rest as above ...

    // Local helper — renders a muted message inside empty tab panels until
    // a dataset is loaded. Avoids pulling in an extra .vue file for one line.
    const EmptyTab = (props) =>
      h(
        'p',
        { class: 'text-sm text-gray-500 dark:text-gray-400 py-6' },
        props.reason || 'No data yet.',
      );
    EmptyTab.props = ['reason'];
    </script>
    ```

    Adjust the full `<script setup>` so the merged block reads cleanly (imports first, then reactive state, then helper component, then functions, then watcher). Keep everything in one `<script setup>` block.

- [ ] **Step 4:** Write stubs for the other referenced components so the page mounts cleanly:

    ```bash
    mkdir -p /home/dhite/code-repos/broad/dig-job-server-2/frontend/components/falcon-a
    cd /home/dhite/code-repos/broad/dig-job-server-2/frontend/components/falcon-a
    for n in FolderPicker GlobalFilterBar DataInspectorPanel ExecutiveSummaryTab TDPTab GenesScatterTab VariantsScatterTab DataTableTab LogSummaryTab; do
      cat > ${n}.vue <<EOF
    <template>
      <div class="text-xs text-gray-400 dark:text-gray-600 py-2">
        [${n} — stub; implemented in a later task]
      </div>
    </template>
    EOF
    done
    ls -la
    ```

    Expected: nine stub .vue files created.

- [ ] **Step 5:** Start the dev server and visit `/falcon-a`:
    ```bash
    cd /home/dhite/code-repos/broad/dig-job-server-2/frontend && npm run dev
    ```
    Open `http://localhost:3000/falcon-a` (default-user auto-login active). Expected:
    - Title "FALCON Dashboard" + subtitle "Variant A — full PrimeVue"
    - Empty "Active Dataset" pill (not rendered)
    - Folder picker stub visible
    - Global filter bar stub visible
    - Tabs strip with all six tabs; tabs needing genes/variants/log are disabled
    - "FALCON Zoom" tab selectable (no dataset gate per spec)
    - No console errors
    - Ctrl-C the dev server.

- [ ] **Step 6:** Commit:
    ```bash
    cd /home/dhite/code-repos/broad/dig-job-server-2
    git add frontend/pages/falcon-a/ frontend/components/falcon-a/
    git commit -m "$(cat <<'EOF'
    feat(falcon-a): scaffold /falcon-a page with PrimeVue Tabs shell

    Host page renders the FALCON Dashboard chrome — title, active-dataset
    pill, folder picker mount, global filter mount, six-tab Tabs strip
    with per-tab disable based on dataset presence, URL-synced active
    tab via ?tab=. Inner components are stubbed for now; each is fleshed
    out in subsequent tasks.

    Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
    EOF
    )"
    ```

---

## Task 3: Small shared components — FolderPicker + GlobalFilterBar + DataInspectorPanel

**Files:** modify (replace stubs) `frontend/components/falcon-a/{FolderPicker,GlobalFilterBar,DataInspectorPanel}.vue`.

### 3a — `FolderPicker.vue`

```vue
<template>
  <div class="flex items-center gap-3">
    <Button
      icon="pi pi-folder-open"
      label="Choose Folder"
      severity="secondary"
      outlined
      @click="triggerFileDialog"
    />
    <span
      v-if="selectedFileCount > 0"
      class="text-xs text-gray-500 dark:text-gray-400"
    >
      {{ selectedFileCount }} file(s) selected
    </span>
    <input
      ref="fileInput"
      type="file"
      webkitdirectory
      directory
      class="hidden"
      @change="onChange"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();
const fileInput = ref(null);
const selectedFileCount = ref(0);

function triggerFileDialog() {
  fileInput.value?.click();
}

async function onChange(e) {
  selectedFileCount.value = e.target.files?.length || 0;
  await store.loadFolder(e.target.files);
}
</script>
```

### 3b — `GlobalFilterBar.vue`

```vue
<template>
  <Card>
    <template #content>
      <Fieldset legend="Global Filters" :toggleable="false" class="!p-0">
        <div class="flex flex-wrap items-center gap-4 py-1">
          <ToggleButton
            v-model="store.globalFilter.active"
            on-label="Strict Filter: ON"
            off-label="Strict Filter: OFF"
            on-icon="pi pi-filter"
            off-icon="pi pi-filter-slash"
          />
          <div class="flex items-center gap-2">
            <label
              for="gf-min-prob"
              class="text-xs font-semibold text-gray-600 dark:text-gray-300"
              >Min Prob</label
            >
            <InputNumber
              id="gf-min-prob"
              v-model="store.globalFilter.minProb"
              :min="0"
              :max="1"
              :step="0.01"
              :min-fraction-digits="2"
              :max-fraction-digits="4"
              show-buttons
              button-layout="horizontal"
              class="w-40"
            />
          </div>
          <div class="flex items-center gap-2">
            <label
              for="gf-min-negp"
              class="text-xs font-semibold text-gray-600 dark:text-gray-300"
              >Min NegP</label
            >
            <InputNumber
              id="gf-min-negp"
              v-model="store.globalFilter.minNegP"
              :min="0"
              :step="0.5"
              :min-fraction-digits="1"
              :max-fraction-digits="2"
              show-buttons
              button-layout="horizontal"
              class="w-40"
            />
          </div>
        </div>
      </Fieldset>
    </template>
  </Card>
</template>

<script setup>
import { useFalconStore } from '~/stores/FalconStore';
const store = useFalconStore();
</script>
```

### 3c — `DataInspectorPanel.vue`

```vue
<template>
  <Dialog
    v-model:visible="visible"
    header="Selection Details"
    :modal="false"
    :dismissable-mask="true"
    :style="{ width: '380px' }"
    position="bottomright"
    class="!z-50"
  >
    <div
      class="font-mono text-sm leading-6 text-gray-800 dark:text-gray-200 mb-3 select-text"
      v-html="html"
    />
    <Button
      icon="pi pi-copy"
      :label="copyLabel"
      severity="secondary"
      outlined
      size="small"
      class="w-full"
      @click="copy"
    />
  </Dialog>
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
  // Read the rendered plain text, not the HTML markup
  const plain = (() => {
    const tmp = document.createElement('div');
    tmp.innerHTML = html.value;
    return tmp.innerText;
  })();
  try {
    await navigator.clipboard.writeText(plain);
    copyLabel.value = 'Copied!';
    setTimeout(() => (copyLabel.value = 'Copy to Clipboard'), 1500);
  } catch (err) {
    console.error('clipboard write failed', err);
  }
}

defineExpose({ show });
</script>
```

- [ ] **Step 1:** Replace stubs with the three component files above.

- [ ] **Step 2:** Expose a global way for any tab to show the inspector. Add an `inject`/`provide` pair — in `pages/falcon-a/index.vue`, inside `<script setup>` after creating refs, provide a ref to the DataInspectorPanel:

    ```vue
    const inspectorRef = ref(null);
    provide('falcon-inspector', inspectorRef);
    ```

    And update the template so `<DataInspectorPanel>` has a ref:

    ```vue
    <DataInspectorPanel ref="inspectorRef" />
    ```

    Tab components that need the inspector will call `inject('falcon-inspector').value?.show(html)`.

- [ ] **Step 3:** Dev-server smoke test: load `/falcon-a`, click "Choose Folder" → native directory picker opens. Click somewhere else to dismiss. Change "Strict Filter" toggle → `store.globalFilter.active` flips (verify via devtools `window.__falcon?.globalFilter` if the store is pinned, otherwise via Vue Devtools).

- [ ] **Step 4:** Commit:

    ```
    feat(falcon-a): folder picker, global filter bar, data inspector

    Three small shared components for Variant A:
    - FolderPicker: PrimeVue Button triggers a hidden <input webkitdirectory>;
      uses store.loadFolder() from the shared data-source seam.
    - GlobalFilterBar: ToggleButton + InputNumber × 2 in a Card/Fieldset;
      bound directly to store.globalFilter.
    - DataInspectorPanel: PrimeVue Dialog anchored bottom-right, with a
      show(html) method exposed via provide/inject so any tab can pop up
      point details after a Plotly click.
    ```

---

## Task 4: `GenomicRegionFilter.vue`

**Files:** modify `frontend/components/falcon-a/GenomicRegionFilter.vue` (currently a stub).

Binds to `store.plotFilters.genes` (only genes has a region filter in this port). Offers a chromosome `SelectButton` pill grid and a two-handle `Slider :range` for BP range.

```vue
<template>
  <Card>
    <template #content>
      <Fieldset legend="Genomic Region Filter" :toggleable="true">
        <div class="flex items-center gap-2 mb-3">
          <Button
            v-if="selectedChr !== 'All'"
            icon="pi pi-refresh"
            label="Reset to All Chromosomes"
            severity="danger"
            outlined
            size="small"
            @click="reset"
          />
        </div>

        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
          Select a chromosome:
        </p>
        <SelectButton
          v-model="selectedChr"
          :options="chrOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          class="mb-4 flex-wrap"
        />

        <div v-if="selectedChr !== 'All' && currentBounds" class="space-y-2">
          <p class="text-xs text-gray-500 dark:text-gray-400">
            Select base-pair range:
          </p>
          <Slider
            v-model="bpRange"
            range
            :min="currentBounds.min"
            :max="currentBounds.max"
            :step="bpStep"
            class="mx-2"
            @change="applyRange"
          />
          <div class="flex items-end gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-xs font-semibold text-gray-600 dark:text-gray-300"
                >Start BP</label
              >
              <InputNumber
                v-model="bpRange[0]"
                :min="currentBounds.min"
                :max="bpRange[1]"
                :use-grouping="true"
                class="w-40"
                @blur="applyRange"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-xs font-semibold text-gray-600 dark:text-gray-300"
                >End BP</label
              >
              <InputNumber
                v-model="bpRange[1]"
                :min="bpRange[0]"
                :max="currentBounds.max"
                :use-grouping="true"
                class="w-40"
                @blur="applyRange"
              />
            </div>
          </div>
        </div>
      </Fieldset>
    </template>
  </Card>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();

// Derive per-chromosome bounds from the loaded genes dataset.
const chrBounds = computed(() => {
  const bounds = new Map();
  for (const row of store.datasets.genes.data) {
    const chr = row.CHR ? String(row.CHR).trim() : '';
    if (!chr) continue;
    const s = parseFloat(row.START);
    const e = parseFloat(row.END);
    if (isNaN(s) && isNaN(e)) continue;
    const b = bounds.get(chr) || { min: Infinity, max: -Infinity };
    if (!isNaN(s)) b.min = Math.min(b.min, s);
    if (!isNaN(e)) b.max = Math.max(b.max, e);
    bounds.set(chr, b);
  }
  return bounds;
});

const chrOptions = computed(() => {
  const chrs = Array.from(chrBounds.value.keys()).sort((a, b) => {
    const na = parseInt(a, 10);
    const nb = parseInt(b, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  return [{ value: 'All', label: 'All' }, ...chrs.map((c) => ({ value: c, label: c }))];
});

const selectedChr = ref(store.plotFilters.genes.chr || 'All');
const currentBounds = computed(() =>
  selectedChr.value === 'All' ? null : chrBounds.value.get(selectedChr.value),
);

const bpRange = ref([0, 0]);
const bpStep = computed(() => {
  if (!currentBounds.value) return 1;
  const span = currentBounds.value.max - currentBounds.value.min;
  return Math.max(1, Math.round(span / 1000)); // ~1000-step slider resolution
});

watch(currentBounds, (b) => {
  if (!b) return;
  bpRange.value = [b.min, b.max];
  applyRange();
}, { immediate: true });

watch(selectedChr, (chr) => {
  store.plotFilters.genes.chr = chr;
  if (chr === 'All') {
    store.plotFilters.genes.minStart = null;
    store.plotFilters.genes.maxEnd = null;
  }
});

function applyRange() {
  if (!currentBounds.value) return;
  store.plotFilters.genes.minStart = bpRange.value[0];
  store.plotFilters.genes.maxEnd = bpRange.value[1];
}

function reset() {
  selectedChr.value = 'All';
}
</script>
```

- [ ] **Step 1:** Replace the stub.
- [ ] **Step 2:** Dev-server check: load T2D fixture; navigate to Genes tab (not yet implemented — or import GenomicRegionFilter temporarily into index.vue for a quick visual check). The "Genomic Region Filter" fieldset should show 22 chromosome pills. For now there's no Genes tab to host it, so skip direct validation here — it'll be exercised in Task 5.
- [ ] **Step 3:** Commit:

    ```
    feat(falcon-a): genomic region filter (chromosome pills + BP slider)

    SelectButton multi-state for chromosome choice; Slider :range + twin
    InputNumbers for BP bounds. Derives per-chromosome bounds from
    store.datasets.genes on the fly. Writes back to store.plotFilters.genes,
    which the scatter spec builders already read.
    ```

---

## Task 5: `GenesScatterTab.vue` + `VariantsScatterTab.vue`

**Files:** modify both (stubs).

### 5a — `GenesScatterTab.vue`

```vue
<template>
  <div class="space-y-4">
    <GenomicRegionFilter />
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded p-2">
      <div ref="plotEl" class="w-full" style="height: 600px" />
    </div>
  </div>
</template>

<script setup>
import { ref, watchEffect, onBeforeUnmount, inject } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { usePlotly } from '~/composables/usePlotly';

const store = useFalconStore();
const { buildGenesScatterSpec } = useFalconPlots(store);
const { mount, unmount, getPlotly } = usePlotly();
const inspector = inject('falcon-inspector', null);
const plotEl = ref(null);

let current = null;
let clickHandler = null;

watchEffect(async () => {
  // React to globalFilter, plotFilters.genes, and dataset changes.
  const spec = buildGenesScatterSpec();
  if (!plotEl.value) return;
  await mount(plotEl.value, spec);
  current = plotEl.value;

  // Wire plotly_click → inspector after newPlot. Bind once per (re)mount.
  const Plotly = await getPlotly();
  if (clickHandler) current.removeAllListeners?.('plotly_click');
  clickHandler = (ev) => {
    if (!ev?.points?.length || !inspector?.value) return;
    const p = ev.points[0];
    const txt = p.text || p.hovertext || 'No data available.';
    inspector.value.show(txt);
  };
  current.on('plotly_click', clickHandler);
});

onBeforeUnmount(async () => {
  if (current) await unmount(current);
});
</script>
```

### 5b — `VariantsScatterTab.vue`

Same structure minus the `GenomicRegionFilter` and using `buildVariantsScatterSpec`:

```vue
<template>
  <div class="space-y-4">
    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded p-2">
      <div ref="plotEl" class="w-full" style="height: 600px" />
    </div>
  </div>
</template>

<script setup>
import { ref, watchEffect, onBeforeUnmount, inject } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { useFalconPlots } from '~/composables/useFalconPlots';
import { usePlotly } from '~/composables/usePlotly';

const store = useFalconStore();
const { buildVariantsScatterSpec } = useFalconPlots(store);
const { mount, unmount, getPlotly } = usePlotly();
const inspector = inject('falcon-inspector', null);
const plotEl = ref(null);

let current = null;
let clickHandler = null;

watchEffect(async () => {
  const spec = buildVariantsScatterSpec();
  if (!plotEl.value) return;
  await mount(plotEl.value, spec);
  current = plotEl.value;

  const Plotly = await getPlotly();
  if (clickHandler) current.removeAllListeners?.('plotly_click');
  clickHandler = (ev) => {
    if (!ev?.points?.length || !inspector?.value) return;
    const p = ev.points[0];
    const txt = p.text || p.hovertext || 'No data available.';
    inspector.value.show(txt);
  };
  current.on('plotly_click', clickHandler);
});

onBeforeUnmount(async () => {
  if (current) await unmount(current);
});
</script>
```

- [ ] **Step 1:** Replace both stubs.
- [ ] **Step 2:** Dev-server check: load T2D fixture; click "Genes Plot" tab → scatter renders with CLUMP-colored points; region filter works; clicking a point opens the inspector. Click "Variants Plot" → similar, no region filter. No console errors.
- [ ] **Step 3:** Commit:

    ```
    feat(falcon-a): genes and variants scatter tabs

    Reactive Plotly scatter via useFalconPlots.buildGenesScatterSpec and
    buildVariantsScatterSpec. watchEffect rebuilds on globalFilter /
    plotFilters changes. plotly_click → DataInspectorPanel via provide/
    inject. Genes tab includes the GenomicRegionFilter; variants does not
    (matches original).
    ```

---

## Task 6: `DataTableTab.vue`

**Files:** modify stub.

Shows genes OR variants in a PrimeVue `DataTable` with lazy loading, client-side sort, client-side global search, pagination. Inner `SelectButton` switches between the two datasets. Preserves the original "strict parity" behavior — no download button.

```vue
<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <SelectButton
        v-model="currentDataset"
        :options="datasetOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
      />
      <InputText
        v-model="state.searchQuery"
        placeholder="Search entire table..."
        class="w-64"
      />
    </div>

    <DataTable
      :value="pageRows"
      :lazy="true"
      :paginator="true"
      :rows="rowsPerPage"
      :total-records="filteredCount"
      :first="(state.currentPage - 1) * rowsPerPage"
      @page="onPage"
      @sort="onSort"
      :sort-field="state.sortCol"
      :sort-order="state.sortAsc ? 1 : -1"
      striped-rows
      scrollable
      scroll-height="60vh"
      class="p-datatable-sm"
    >
      <Column
        v-for="col in columns"
        :key="col"
        :field="col"
        :header="col"
        sortable
      />
    </DataTable>
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

const filteredCount = computed(() => filteredAndSorted.value.length);

const pageRows = computed(() => {
  const start = (state.value.currentPage - 1) * rowsPerPage;
  return filteredAndSorted.value.slice(start, start + rowsPerPage);
});

function onPage(evt) {
  state.value.currentPage = (evt.first / rowsPerPage) + 1;
}

function onSort(evt) {
  state.value.sortCol = evt.sortField;
  state.value.sortAsc = evt.sortOrder === 1;
}

// Reset page when dataset or query changes
watch([currentDataset, () => state.value.searchQuery], () => {
  state.value.currentPage = 1;
});
</script>
```

- [ ] **Step 1:** Replace the stub.
- [ ] **Step 2:** Dev-server check: load T2D; click "Data Table" tab → table shows genes (18K rows). Paginate, sort columns (numeric vs string sort should both work), search for a known gene (e.g. `CETP`). Switch to variants via SelectButton → table reloads. No console errors.
- [ ] **Step 3:** Commit:

    ```
    feat(falcon-a): data table tab with PrimeVue DataTable

    Lazy-mode DataTable driven by store.tableStates. Inner SelectButton
    switches genes/variants. Global-search input filters across all
    columns; Column headers sort numerically when possible, string
    otherwise. 15 rows/page per original AppConfig.rowsPerPage.
    ```

---

## Task 7: `TraitCard.vue` + `ExecutiveSummaryTab.vue`

**Files:** modify both stubs.

### 7a — `TraitCard.vue`

Expandable summary row. Used by `ExecutiveSummaryTab` to render a gene- or variant-signal row with collapsible trait citations + clinical trial matches.

```vue
<template>
  <Panel :toggleable="true" :collapsed="collapsed" class="mb-2">
    <template #header>
      <div class="flex items-center gap-3 w-full">
        <span class="font-semibold text-gray-900 dark:text-gray-100">{{ row.name }}</span>
        <Tag :value="`Clump ${row.clumpId}`" severity="info" />
        <Tag v-if="row.isLead" value="⭐ Lead" severity="warning" />
        <Tag v-if="row.isNovel === false" value="Known" severity="secondary" />
        <Tag v-if="row.isNovel === true" value="Novel" severity="success" />
        <span class="text-xs text-gray-500 dark:text-gray-400 ml-auto">
          Chr {{ row.chr }} · Prob {{ row.prob.toFixed(3) }} · NegP
          {{ row.negP.toFixed(2) }}
        </span>
      </div>
    </template>

    <div v-if="row.traits?.length" class="mb-3">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
        Associated traits
      </h4>
      <ul class="text-xs space-y-1 list-disc list-inside">
        <li v-for="(t, i) in row.traits" :key="i">
          <span class="font-mono">{{ t.Trait || t.trait || '—' }}</span>
          <span v-if="t.Citation || t.citation" class="text-gray-500">
            ({{ t.Citation || t.citation }})
          </span>
        </li>
      </ul>
    </div>

    <div v-if="row.clinicalTrials?.length">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
        Clinical trials
      </h4>
      <ul class="text-xs space-y-1">
        <li v-for="(t, i) in row.clinicalTrials" :key="i">
          <span class="font-mono">{{ t.drugId }}</span>
          · {{ t.indication }} ·
          <Tag :value="`Phase ${t.phase}`" severity="info" class="ml-1" />
        </li>
      </ul>
    </div>

    <div
      v-if="!row.traits?.length && !row.clinicalTrials?.length"
      class="text-xs text-gray-500 dark:text-gray-400"
    >
      No trait or trial data.
    </div>
  </Panel>
</template>

<script setup>
defineProps({
  row: { type: Object, required: true },
  collapsed: { type: Boolean, default: true },
});
</script>
```

### 7b — `ExecutiveSummaryTab.vue`

```vue
<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <Button
        icon="pi pi-database"
        :label="clinicalTrials.isLoaded ? 'Clinical Trials Loaded' : 'Load Clinical Trials CSV'"
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
      <TraitCard v-for="row in filteredGenesTop" :key="`g-top-${row.index}`" :row="row" />
    </section>

    <section>
      <h3 class="text-lg font-semibold mb-2">Lead Genes per Chromosome</h3>
      <TraitCard v-for="row in filteredGenesLead" :key="`g-lead-${row.index}`" :row="row" />
    </section>

    <section>
      <h3 class="text-lg font-semibold mb-2">Top Variants per Clump</h3>
      <TraitCard v-for="row in summary.variants?.top || []" :key="`v-top-${row.index}`" :row="row" />
    </section>

    <section>
      <h3 class="text-lg font-semibold mb-2">Lead Variants per Chromosome</h3>
      <TraitCard v-for="row in summary.variants?.lead || []" :key="`v-lead-${row.index}`" :row="row" />
    </section>
  </div>
</template>

<script setup>
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
  // Side-effect: attach clinical trials if loaded (mutates rows)
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
    // Hydrate novelty flags (async codetabs fetch)
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
```

- [ ] **Step 1:** Replace the two stubs.
- [ ] **Step 2:** Dev-server check: load T2D; click "Executive Summary" tab → four sections render with TraitCards. Expand a few cards. Click "Load Clinical Trials CSV" → native chooser; use `/home/dhite/code-repos/broad/PEGS/src/dashboard/data/clinical_trials.csv` → clinical trials appear in relevant cards. Click "Novelty filter: OFF" → async fetch kicks off; when done, only cards marked Novel remain.
- [ ] **Step 3:** Commit:

    ```
    feat(falcon-a): executive summary + trait cards

    ExecutiveSummaryTab mounts four DataView-style sections of TraitCards
    (top/lead × genes/variants). Clinical-trials CSV can be loaded from a
    separate button. Novelty filter toggles async fetch via
    useFalconSummary.attachNoveltyFlags with an AbortController so mid-
    fetch toggles don't leak requests.
    ```

---

## Task 8: `LogSummaryTab.vue`

**Files:** modify stub.

Renders a total-time pill, an explainer card (the "Parallel Wall Time" note verbatim from the original), a per-chromosome selector, a per-chromosome pre-process bar chart, and a grid of histogram cards — one per Gibbs component (`ITER_COMPONENTS` from the shared composable).

```vue
<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <h3 class="text-xl font-semibold">FALCON Execution Time Summary</h3>
      <Tag severity="success" :value="`Total Execution Time: ${totalTime}`" class="text-base" />
    </div>

    <Card>
      <template #title>About this summary</template>
      <template #content>
        <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
          This section visualizes the execution time for various components of the
          FALCON algorithm per iteration. If a component was skipped during an
          iteration for optimization (e.g., "Lazy link activated"), the sample is
          ignored on the analysis, and <b>n</b> on the top of each plot shows the
          number of times the step was actually performed.
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
          waits for the last chromosome to finish preparing before beginning the
          synchronized Gibbs sampling.
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

    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));">
      <Card v-for="comp in components" :key="comp">
        <template #title>{{ comp }}</template>
        <template #content>
          <div class="flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2 pb-2 border-b border-dashed border-gray-200 dark:border-gray-700">
            <template v-if="compStats[comp]">
              <Tag severity="secondary" :value="`Min: ${compStats[comp].min.toFixed(2)}s`" />
              <Tag severity="secondary" :value="`Med: ${compStats[comp].median.toFixed(2)}s`" />
              <Tag severity="secondary" :value="`Mean: ${compStats[comp].mean.toFixed(2)}s`" />
              <Tag severity="secondary" :value="`Max: ${compStats[comp].max.toFixed(2)}s`" />
              <span class="text-gray-400">n={{ compStats[comp].n }}</span>
            </template>
            <span v-else class="text-red-500 font-semibold">
              No data recorded (component entirely skipped).
            </span>
          </div>
          <div :ref="(el) => (histRefs[comp] = el)" class="w-full" style="height: 240px" />
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
  return [{ value: 'all', label: 'Whole Genome (Aggregate)' }, ...chrs.map((c) => ({ value: c, label: `Chromosome ${c}` }))];
});

const totalTime = computed(() => store.datasets.log.totalTime);

const preprocessEl = ref(null);
const histRefs = ref({});
const mounted = new Set();

// Build per-component stats/spec (keyed on chrView).
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
  // Pre-process bar — always whole-genome (doesn't depend on chrView).
  if (preprocessEl.value) {
    await mount(preprocessEl.value, buildLogPreprocessBarSpec());
    mounted.add(preprocessEl.value);
  }

  // Per-component histograms — rebuild on chrView change.
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
```

- [ ] **Step 1:** Replace the stub.
- [ ] **Step 2:** Dev-server check: load T2D; click "Execution Time" tab → total-time pill shows `6149.27 seconds`; explainer card renders; chromosome selector shows 22 entries + Whole Genome; pre-process bar chart renders with 22 bars; histogram grid shows all 8 components, each with stats + histogram. Switch to "Chromosome 1" → histograms re-render with per-chr data. No console errors.
- [ ] **Step 3:** Commit:

    ```
    feat(falcon-a): log execution time summary

    Total-time pill + explainer Card (parallel wall-time note verbatim)
    + chromosome selector + pre-process bar + grid of per-component
    histogram Cards each with Tag-based stats. Uses
    useFalconPlots.buildLogPreprocessBarSpec / buildLogIterHistogramSpec
    and ITER_COMPONENTS from the shared log parser.
    ```

---

## Task 9: `TDPTab.vue`

**Files:** modify stub.

The heaviest tab. Controls row (target gene, boundary, focus, plot type, LD folder picker, min R², max stretch slider, Run Analysis button), a status line, and a single tall Plotly container for the returned zoom-plot spec.

```vue
<template>
  <div class="space-y-4">
    <Card>
      <template #title>FALCON Zoom & LD Correlation</template>
      <template #content>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Global filters apply at the moment you click Run Analysis — reload
          the plot after changing them.
        </p>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold">Target Gene</label>
            <InputText v-model="cfg.gene" placeholder="e.g., CETP" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold">Boundary (BP)</label>
            <InputNumber v-model="cfg.boundary" :min="1000" :step="50000" :use-grouping="true" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold">Focus</label>
            <Select
              v-model="cfg.focus"
              :options="focusOptions"
              option-label="label"
              option-value="value"
            />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold">Plot Type</label>
            <Select
              v-model="cfg.plotType"
              :options="plotTypeOptions"
              option-label="label"
              option-value="value"
            />
          </div>
        </div>

        <Card class="mt-4 !bg-blue-50 dark:!bg-blue-950/40">
          <template #title>LD Matrix</template>
          <template #content>
            <div class="flex flex-wrap items-end gap-3">
              <div class="flex flex-col gap-1">
                <label class="text-xs font-semibold">LD Folder (.gz / .sorted)</label>
                <div class="flex items-center gap-2">
                  <Button
                    icon="pi pi-folder-open"
                    :label="store.tdp.ldFolderName || 'Load LD Folder'"
                    severity="secondary"
                    outlined
                    @click="triggerLdDialog"
                  />
                  <input
                    ref="ldInput"
                    type="file"
                    webkitdirectory
                    directory
                    class="hidden"
                    @change="onLdChange"
                  />
                </div>
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-xs font-semibold">Min R²</label>
                <InputNumber
                  v-model="cfg.minR2"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  :min-fraction-digits="1"
                  :max-fraction-digits="2"
                  class="w-28"
                />
              </div>
              <div class="flex flex-col gap-1 min-w-[160px]">
                <label class="text-xs font-semibold">Max Stretch: {{ cfg.maxStretch.toFixed(2) }}</label>
                <Slider v-model="cfg.maxStretch" :min="0.1" :max="1" :step="0.05" />
              </div>
            </div>
          </template>
        </Card>

        <div class="flex items-center justify-between mt-4">
          <p v-if="store.tdp.status" class="text-sm text-primary-600 dark:text-primary-400 font-semibold">
            {{ store.tdp.status }}
          </p>
          <span v-else></span>
          <Button
            icon="pi pi-play"
            label="Run Analysis"
            severity="primary"
            :loading="running"
            :disabled="running || !cfg.gene"
            @click="run"
          />
        </div>
      </template>
    </Card>

    <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded p-2">
      <div ref="plotEl" class="w-full" style="height: 850px" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onBeforeUnmount } from 'vue';
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

const focusOptions = [
  { value: 'region', label: 'Region' },
  { value: 'gene', label: 'Gene Only' },
];
const plotTypeOptions = [
  { value: 'falcon', label: 'FALCON' },
  { value: 'raw', label: 'Raw input' },
  { value: 'overlay', label: 'Overlay' },
];

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

function triggerLdDialog() {
  ldInput.value?.click();
}
async function onLdChange(e) {
  await store.loadLdFolder(e.target.files);
}

onBeforeUnmount(async () => {
  if (mountedEl) await unmount(mountedEl);
});
</script>
```

- [ ] **Step 1:** Replace the stub.
- [ ] **Step 2:** Dev-server check: load T2D; click "FALCON Zoom" tab; controls render; click "Run Analysis" with default `CETP`/500000/region/falcon (no LD folder) → status messages appear in `store.tdp.status`, then the scatter plot renders showing trait traces + gene/clump shapes (no LD heatmap since no LD folder). No console errors beyond expected "no LD files" info messages.
- [ ] **Step 3:** Commit:

    ```
    feat(falcon-a): FALCON Zoom & LD Correlation tab

    Controls Card with target gene / boundary / focus / plot-type / LD
    folder picker / min R² / max stretch slider. Run Analysis calls
    useFalconTDP.runAnalysis and mounts the returned {data, layout} spec
    via usePlotly. Partial-LD (no LD folder) falls back to trait-only
    rendering, matching the original's behavior.
    ```

---

## Task 10: End-to-end smoke test

**Files:** none.

Goal: walk through every tab of `/falcon-a` with real data and confirm no broken behaviors. Run in a browser (or via Playwright MCP following the base-plan pattern). Uses the `frontend/public/kp5` symlink set up during the base-plan smoke test — if it's been removed, re-create per the base plan.

- [ ] **Step 1:** Start the dev server:
    ```bash
    cd /home/dhite/code-repos/broad/dig-job-server-2/frontend && npm run dev
    ```

- [ ] **Step 2:** Visit `http://localhost:3000/falcon-a` (auto-login via default user).

- [ ] **Step 3:** Confirm chrome renders: title "FALCON Dashboard", subtitle "Variant A — full PrimeVue", folder picker, global filter bar, Tabs strip with six entries (all but "FALCON Zoom" disabled).

- [ ] **Step 4:** Click "Choose Folder"; in a browser, select `~/falcon-fixtures/kp5/T2D/`. In Playwright, use the in-browser `DataTransfer` technique from the base plan (fetch `/kp5/T2D/*.wg.*`, shove into input, dispatch change).

- [ ] **Step 5:** Verify "Active Dataset: T2D" pill appears; tabs unlock.

- [ ] **Step 6:** Visit each tab in order and verify:
    - **Executive Summary** — four TraitCard sections render. Expand a card. Click "Load Clinical Trials CSV" → pick `/home/dhite/code-repos/broad/PEGS/src/dashboard/data/clinical_trials.csv` → clinical trial Tags appear where genes match.
    - **FALCON Zoom** — controls render; click "Run Analysis" with defaults → plot renders.
    - **Genes Plot** — Plotly scatter renders with CLUMP-colored points. Change min prob in GlobalFilterBar → scatter refreshes (watchEffect). Click a point → DataInspectorPanel Dialog opens bottom-right with details. Click the chromosome pill "1" in GenomicRegionFilter → scatter rescopes. Reset.
    - **Variants Plot** — scatter renders; no GenomicRegionFilter shown.
    - **Data Table** — 18,575 genes paginated. Sort by PROBABILITY descending → top rows are highest. Search "CETP" → filters rows. Switch SelectButton to "Variants" → 134,585 rows.
    - **Execution Time** — total-time pill `6149.27 seconds`; 22 chromosomes in selector; pre-process bar chart renders; 8 histogram Cards with stats. Switch to "Chromosome 1" → histograms re-render.

- [ ] **Step 7:** Toggle dark mode via the footer's moon icon. Every tab must remain readable. (Branch A's full-PrimeVue promise.)

- [ ] **Step 8:** Reload a different fixture (TGnonT2D) via the folder picker → cache-reset and dataset-swap both work; all tabs reflect the new data.

- [ ] **Step 9:** Ctrl-C the dev server.

No commit for this task.

---

## Done when

- All 10 tasks complete.
- Branch health:
    ```bash
    cd /home/dhite/code-repos/broad/dig-job-server-2 && git status && git log --oneline main..HEAD
    ```
    Expected: clean tree; ~8–9 commits on `falcon-variant-a` ahead of `main` (or `falcon-port-base`, depending on whether base has merged).
- Smoke test (Task 10) passes, including dark mode.
- Zero edits to shared files under `stores/`, `composables/`, `utils/`.

**Next:** open a PR for `falcon-variant-a` → `main` (after base has merged). Then run Plan 3 for `falcon-variant-b`. Once both variant PRs land, compare `/falcon-a` vs `/falcon-b` on the deployed env and run the cleanup PR per spec §13.
