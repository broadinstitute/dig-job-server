# FALCON Port — Base Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the shared foundation (`falcon-port-base` branch) for the FALCON Results Viewer port: Pinia store, composables, page scaffold, and dependencies. Both `falcon-port-b` and `falcon-port-a` will fork from this branch.

**Architecture:** Client-only Nuxt 3 page at `/falcon`. Pinia store owns loaded datasets + global filters + caches. Composables hold parsing, filtering, and chart-spec-building logic (lifted nearly verbatim from `PEGS/src/dashboard/app.js`). Plotly is lazy-loaded only on route entry. No UI components in this plan — tab rendering lives in the two branch plans that follow.

**Tech Stack:** Nuxt 3 + Vue 3 + Pinia (composition API) + PapaParse + pako (already a dep) + plotly.js-dist-min.

**Spec:** `docs/superpowers/specs/2026-04-24-falcon-dashboard-port-to-vue3-design.md`

**Source:** `/home/dhite/code-repos/broad/PEGS/src/dashboard/` (original vanilla-JS dashboard).

**Deliverable of this plan:** Navigate to `/falcon` (logged in), pick a folder, see the store populate (`datasets.genes.isLoaded` / `datasets.variants.isLoaded` / `datasets.log.isLoaded` → `true`). No charts render yet. Subsequent plans add the visible UI.

---

## Preamble — ground rules for this plan

1. **Working directory for all tasks:** `/home/dhite/code-repos/broad/dig-job-server-2/frontend` unless stated otherwise. All `ls`, `npm`, `git` commands run from here.
2. **Reference directory (read-only):** `/home/dhite/code-repos/broad/PEGS/src/dashboard/` — the original. Tasks reference exact line ranges to port.
3. **Test fixtures:** `~/falcon-fixtures/kp5/T2D/` and `~/falcon-fixtures/kp5/TGnonT2D/`. Use these for manual verification steps.
4. **User commit-approval preference — important:** the user's standing preference is to approve commits manually. For every "Commit" step: stage, show `git status` + `git diff --cached`, propose the commit message, **wait for the user's explicit go-ahead before running `git commit`**. Do not skip this gate.
5. **No automated tests.** The host frontend has no test framework. Each task substitutes a manual verification step (load the dev server, inspect devtools, confirm store shape). Introducing a test framework is explicitly out of scope per the spec.
6. **Composable style.** Follow the Vue 3 composition-API / Pinia pattern already used in the host app (see `stores/ResultsStore.js`, `composables/useAxios.js`). Composables are plain functions that return objects of functions and refs; they don't use `defineStore`.
7. **Nuxt auto-imports are on** for `~/composables`, `~/stores`, and PrimeVue components. Don't add manual imports for those.

---

## File structure

Files created by this plan (all paths relative to `frontend/`):

```
package.json                        # modify — add plotly.js-dist-min, papaparse
stores/
  FalconStore.js                    # create — Pinia store
composables/
  useFalconFileLoader.js            # create — .wg.genes / .wg.variants TSV parse
  useFalconLogParser.js             # create — .wg.log regex state machine
  useFalconDataSource.js            # create — loadFromLocalFiles orchestrator
  useFalconFilters.js               # create — strict + region filter predicates
  useFalconPlots.js                 # create — Plotly spec builders (scatter + histogram + bar)
  useFalconTDP.js                   # create — TDP zoom/LD analysis
  useFalconSummary.js               # create — top/lead aggregation + novelty/clinical attach
  useClinicalTrials.js              # create — clinical-trials CSV loader
  useGeneTraitFetcher.js            # create — codetabs proxy + AbortSignal
  usePlotly.js                      # create — dynamic-import wrapper
utils/
  falcon/
    config.js                       # create — port of AppConfig.tabs
    colorPalette.js                 # create — port of ColorManager (pure, state via store.caches)
    pako.js                         # create — gzip helper for LD files
pages/
  falcon/
    index.vue                       # create — minimal scaffold: folder picker + status
```

No files under `components/falcon/` are created by this plan — they belong to Plans 2 and 3.

---

## Task 1: Create `falcon-port-base` branch

**Files:** none modified; branch setup only.

- [ ] **Step 1: Verify clean working tree on main**

Run (from `/home/dhite/code-repos/broad/dig-job-server-2`):
```bash
git status
```
Expected: `On branch main` and `nothing to commit, working tree clean`. If not clean, stop and ask the user how to proceed.

- [ ] **Step 2: Pull latest main**

```bash
git fetch origin && git checkout main && git pull --ff-only
```

- [ ] **Step 3: Create and check out `falcon-port-base`**

```bash
git checkout -b falcon-port-base
```

- [ ] **Step 4: Verify**

```bash
git branch --show-current
```
Expected: `falcon-port-base`

No commit for this task.

---

## Task 2: Install `plotly.js-dist-min` and `papaparse`

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`

- [ ] **Step 1: Confirm neither is already installed**

From `frontend/`:
```bash
grep -E '"plotly\.js|"papaparse"' package.json
```
Expected: no output (both are absent).

- [ ] **Step 2: Install**

```bash
npm install plotly.js-dist-min papaparse
```
(pako is already in `dependencies` — confirm with `grep '"pako"' package.json`.)

- [ ] **Step 3: Verify install**

```bash
grep -E '"plotly\.js|"papaparse"|"pako"' package.json
```
Expected: all three present.

- [ ] **Step 4: Confirm dev server still starts**

```bash
npm run dev
```
Wait for `Local: http://localhost:3000/` (or similar), then Ctrl-C.

- [ ] **Step 5: Commit** (requires user approval per preamble rule 4)

Stage & show:
```bash
git add package.json package-lock.json
git status && git diff --cached --stat
```
Proposed message:
```
chore(falcon): add plotly.js-dist-min and papaparse dependencies

Adds Plotly (lazy-loaded on /falcon route) and PapaParse (TSV parsing
for .wg.genes / .wg.variants and clinical-trials CSV). pako (gzip) is
already a dep.
```
**Wait for user approval, then:**
```bash
git commit -m "<message>"
```

---

## Task 3: Port `AppConfig.tabs` to `utils/falcon/config.js`

**Files:**
- Create: `frontend/utils/falcon/config.js`

Reference: `PEGS/src/dashboard/app.js:26-37` (the `AppConfig` object).

- [ ] **Step 1: Create the file**

```js
// frontend/utils/falcon/config.js
// Port of PEGS/src/dashboard/app.js AppConfig.
// Tab ids map to route query param ?tab=<id>.
// `requires` is the dataset that must be loaded for the tab to enable.

export const FALCON_TABS = [
  { id: 'summary',  label: 'Executive Summary',  requires: 'genes' },
  { id: 'tdp',      label: 'FALCON Zoom',        requires: null    }, // always enabled
  { id: 'genes',    label: 'Genes Plot',         requires: 'genes' },
  { id: 'variants', label: 'Variants Plot',      requires: 'variants' },
  { id: 'table',    label: 'Data Table',         requires: 'genes' }, // switches between genes/variants internally
  { id: 'log',      label: 'Execution Time',     requires: 'log'   },
];

export const FALCON_ROWS_PER_PAGE = 15;

// Strict filter thresholds used internally for "top per clump" calculation.
// User-controlled thresholds live in the store (globalFilter.minProb / minNegP).
export const STRICT_TOP_MIN_PROB = 0.05;
export const STRICT_TOP_MIN_NEGP = 1;
```

- [ ] **Step 2: Verify the file is in place**

```bash
test -f frontend/utils/falcon/config.js && echo OK
```

- [ ] **Step 3: No commit yet** (accumulate with next task)

---

## Task 4: Port `ColorManager` to `utils/falcon/colorPalette.js` (pure)

**Files:**
- Create: `frontend/utils/falcon/colorPalette.js`

Reference: `PEGS/src/dashboard/app.js:42-59`. The original carries its own `clumpColorMap` as module state, which causes a race condition when multiple plots render concurrently (flagged in audit). The port moves the Map into `store.caches.clumpColor`; these helpers are pure.

- [ ] **Step 1: Create the file**

```js
// frontend/utils/falcon/colorPalette.js
// Port of PEGS/src/dashboard/app.js ColorManager. Color-for-clump assignment
// is pure here — the caller passes in the Map (owned by FalconStore.caches.clumpColor)
// so dataset reloads reset cleanly via store.resetCaches().

export const FALCON_PALETTE = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
];

export const UNASSIGNED_CLUMP_COLOR = '#d1d5db';
export const UNASSIGNED_CLUMP_ID = 'Unassigned (No Clump)';

/**
 * Look up (and assign if missing) a color for a clump.
 * @param {Map<string, string>} clumpColorMap  store.caches.clumpColor
 * @param {string} clumpId
 * @returns {string} hex color
 */
export function getColorForClump(clumpColorMap, clumpId) {
  if (clumpId === UNASSIGNED_CLUMP_ID) return UNASSIGNED_CLUMP_COLOR;
  if (!clumpColorMap.has(clumpId)) {
    const idx = clumpColorMap.size % FALCON_PALETTE.length;
    clumpColorMap.set(clumpId, FALCON_PALETTE[idx]);
  }
  return clumpColorMap.get(clumpId);
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/utils/falcon/colorPalette.js && echo OK
```

- [ ] **Step 3: Commit** (requires user approval)

Stage & show:
```bash
git add frontend/utils/falcon/
git status && git diff --cached
```
Proposed message:
```
feat(falcon): add tab config and color palette utils

Ports AppConfig.tabs and ColorManager from the original dashboard into
pure utils. ColorManager state now lives in the Pinia store so it can be
reset per dataset.
```
**Wait for approval, then commit.**

---

## Task 5: Create `stores/FalconStore.js`

**Files:**
- Create: `frontend/stores/FalconStore.js`

Per spec §5 store shape. Actions are initially stubs — they're wired up in Task 8 (`loadFolder`), Task 12 (`loadClinicalTrialsCsv`), and Task 15 (`loadLdFolder`).

- [ ] **Step 1: Create the file**

```js
// frontend/stores/FalconStore.js
// Single source of truth for the FALCON viewer. See spec §5.
import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';

export const useFalconStore = defineStore('falcon', () => {
  // ─── loaded datasets ───
  const datasets = reactive({
    genes:    { data: [], columns: [], isLoaded: false },
    variants: { data: [], columns: [], isLoaded: false },
    log:      {
      data: {},            // Record<chr, Record<component, number[]>>
      preProcess: {},      // Record<chr, Record<step, number>>
      chromosomes: new Set(),
      totalTime: 'Not Found / Incomplete Run',
      isLoaded: false,
    },
  });

  const folderName = ref('');
  const status     = ref('');

  // ─── global filters (affect plots; Summary table preserves original behavior) ───
  const globalFilter = reactive({
    active: true,
    minProb: 0.1,
    minNegP: 8,
  });

  // ─── per-dataset table state ───
  const tableStates = reactive({
    genes:    { searchQuery: '', sortCol: null, sortAsc: true, currentPage: 1 },
    variants: { searchQuery: '', sortCol: null, sortAsc: true, currentPage: 1 },
  });

  // ─── per-plot genomic region filter (original only wires this for genes) ───
  const plotFilters = reactive({
    genes:    { chr: 'All', minStart: null, maxEnd: null },
    variants: { chr: 'All', minStart: null, maxEnd: null },
  });

  // ─── clinical trials (loaded via separate picker) ───
  const clinicalTrials = reactive({ isLoaded: false, byGene: {} });

  // ─── TDP (FALCON Zoom) state ───
  const tdp = reactive({
    ldFiles: [],
    ldFolderName: '',
    lastAnalysis: null,
    status: '',
  });

  // ─── caches reset on every new folder load ───
  const caches = reactive({
    clumpColor: new Map(),
    traitLookup: {},
    ldBinCache: new Map(),
  });

  function resetCaches() {
    caches.clumpColor.clear();
    caches.traitLookup = {};
    caches.ldBinCache.clear();
  }

  function resetDatasets() {
    datasets.genes.data = [];
    datasets.genes.columns = [];
    datasets.genes.isLoaded = false;
    datasets.variants.data = [];
    datasets.variants.columns = [];
    datasets.variants.isLoaded = false;
    datasets.log.data = {};
    datasets.log.preProcess = {};
    datasets.log.chromosomes = new Set();
    datasets.log.totalTime = 'Not Found / Incomplete Run';
    datasets.log.isLoaded = false;
  }

  // ─── actions (stubs — wired in later tasks) ───
  async function loadFolder(/* files */) {
    throw new Error('loadFolder not wired yet (see Task 8)');
  }
  async function loadClinicalTrialsCsv(/* file */) {
    throw new Error('loadClinicalTrialsCsv not wired yet (see Task 12)');
  }
  async function loadLdFolder(/* files */) {
    throw new Error('loadLdFolder not wired yet (see Task 15)');
  }

  return {
    datasets, folderName, status,
    globalFilter, tableStates, plotFilters,
    clinicalTrials, tdp, caches,
    resetCaches, resetDatasets,
    loadFolder, loadClinicalTrialsCsv, loadLdFolder,
  };
});
```

- [ ] **Step 2: Verify the store imports cleanly**

```bash
npm run dev
```
Navigate to any existing page (e.g., `http://localhost:3000/datasets`). Open browser devtools → Vue Devtools → Pinia; confirm `falcon` store is listed (it's only registered when something imports it, so skip if not visible). Ctrl-C.

- [ ] **Step 3: Commit** (requires user approval)

```
feat(falcon): scaffold FalconStore (Pinia) with state + cache reset

Ports DataStore from the original dashboard. Action methods are stubs;
they're wired in subsequent tasks. resetCaches() guarantees fresh
clump colors, trait lookups, and LD bins on every folder load.
```

---

## Task 6: Create `composables/useFalconFileLoader.js`

**Files:**
- Create: `frontend/composables/useFalconFileLoader.js`

Reference: `PEGS/src/dashboard/app.js:231-251` (`FileLoader.parseFile` — PapaParse TSV loader).

- [ ] **Step 1: Create the file**

```js
// frontend/composables/useFalconFileLoader.js
// Port of FileLoader.parseFile from PEGS/src/dashboard/app.js:231-251.
// Parses .wg.genes / .wg.variants as tab-delimited files.
import Papa from 'papaparse';

/**
 * Parse a FALCON .wg.* TSV file in chunks.
 * @param {File} file
 * @returns {Promise<{ data: Array<Record<string, any>>, columns: string[] }>}
 */
function parseTsv(file) {
  return new Promise((resolve, reject) => {
    const rows = [];
    let columns = [];
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      delimiter: '\t',
      chunk: (results) => {
        rows.push(...results.data);
        if (columns.length === 0 && results.meta.fields) {
          columns = results.meta.fields;
        }
      },
      complete: () => resolve({ data: rows, columns }),
      error:    (err) => reject(err),
    });
  });
}

export function useFalconFileLoader() {
  return {
    parseGenesFile:    (file) => parseTsv(file),
    parseVariantsFile: (file) => parseTsv(file),
  };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/useFalconFileLoader.js && echo OK
```

No commit yet — grouped with the next composable tasks.

---

## Task 7: Create `composables/useFalconLogParser.js`

**Files:**
- Create: `frontend/composables/useFalconLogParser.js`

Reference: `PEGS/src/dashboard/app.js:114-229` (`FileLoader.parseLogFile`). Keep the regex patterns and the state-machine shape verbatim.

- [ ] **Step 1: Create the file**

```js
// frontend/composables/useFalconLogParser.js
// Port of FileLoader.parseLogFile from PEGS/src/dashboard/app.js:114-229.
// Parses a .wg.log with per-chromosome pre-process + Gibbs-iteration timing.

const ITER_COMPONENTS = [
  'Annotation update', 'Batched SNP update', 'Link Update',
  'Window update', 'Gene status update', 'Gene effect', 'Stats update', 'Iter Time',
];

const PRE_PROCESS_KEYS = [
  'Reading sumstats', 'Dentist', 'Reading S2G', 'Reading LD', 'RVM',
  'Reading annotations', 'Vectorization of region data',
  'Calculating infinitesimal betas', 'Stabilization of sparse matrix',
  'Computing SNPs batches', 'Computing snp to link variables', 'Computing Genes batches',
];

const TIME_RE = /([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s+seconds/i;
const CHR_RE  = /\[Chr\s+([\w]+)\]:/i;

function extractTime(line) {
  const m = line.match(TIME_RE);
  return m ? parseFloat(m[1]) : 0;
}

/**
 * @param {File} file
 * @returns {Promise<{
 *   data: Record<string, Record<string, number[]>>,
 *   preProcess: Record<string, Record<string, number>>,
 *   chromosomes: Set<string>,
 *   totalTime: string
 * }>}
 */
function parseLogFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const out = {
          data: {},
          preProcess: {},
          chromosomes: new Set(),
          totalTime: 'Not Found / Incomplete Run',
        };
        const lines = e.target.result.split('\n');
        let lastChr = null;
        const activePreByChr = {};
        const gibbsStarted = {};

        lines.forEach((line) => {
          const lower = line.toLowerCase();

          if (lower.includes('total time:')) {
            const m = lower.match(/total time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*seconds/i);
            if (m) out.totalTime = parseFloat(m[1]).toFixed(2) + ' seconds';
          }

          const chrMatch = line.match(CHR_RE);
          let chr = lastChr;
          if (chrMatch) {
            chr = chrMatch[1];
            lastChr = chr;
            out.chromosomes.add(chr);
            if (!out.data[chr]) {
              out.data[chr] = {};
              ITER_COMPONENTS.forEach((c) => { out.data[chr][c] = []; });
            }
            if (!out.preProcess[chr]) {
              out.preProcess[chr] = {};
              PRE_PROCESS_KEYS.forEach((k) => { out.preProcess[chr][k] = 0; });
            }
          }
          if (!chr || !out.data[chr]) return;

          if (lower.includes('running gibbs')) {
            gibbsStarted[chr] = true;
            activePreByChr[chr] = null;
          }

          if (!gibbsStarted[chr]) {
            // PHASE 1: Pre-processing
            if      (lower.includes('reading sumstats from'))             activePreByChr[chr] = 'Reading sumstats';
            else if (lower.includes('dentist'))                            activePreByChr[chr] = 'Dentist';
            else if (lower.includes('reading s2g'))                        activePreByChr[chr] = 'Reading S2G';
            else if (lower.includes('reading ld') && lower.includes('sparse matrix')) activePreByChr[chr] = 'Reading LD';
            else if (lower.includes('rvm'))                                activePreByChr[chr] = 'RVM';
            else if (lower.includes('reading annotations'))                activePreByChr[chr] = 'Reading annotations';
            else if (lower.includes('vectorization of region data'))       activePreByChr[chr] = 'Vectorization of region data';
            else if (lower.includes('calculating infinitesimal betas'))    activePreByChr[chr] = 'Calculating infinitesimal betas';
            else if (lower.includes('stabilization of sparse matrix'))     activePreByChr[chr] = 'Stabilization of sparse matrix';
            else if (lower.includes('computing snps batches'))             activePreByChr[chr] = 'Computing SNPs batches';
            else if (lower.includes('computing snp to link variables'))    activePreByChr[chr] = 'Computing snp to link variables';
            else if (lower.includes('computing genes batches'))            activePreByChr[chr] = 'Computing Genes batches';

            const t = extractTime(lower);
            if (t > 0 && activePreByChr[chr]) {
              out.preProcess[chr][activePreByChr[chr]] = Math.max(
                out.preProcess[chr][activePreByChr[chr]], t
              );
            }
          } else {
            // PHASE 2: Gibbs iteration timings
            const t = extractTime(lower);
            if (t > 0) {
              if      (lower.includes('annotation update'))  out.data[chr]['Annotation update'].push(t);
              else if (lower.includes('batched snp update')) out.data[chr]['Batched SNP update'].push(t);
              else if (lower.includes('link update'))        out.data[chr]['Link Update'].push(t);
              else if (lower.includes('window update'))      out.data[chr]['Window update'].push(t);
              else if (lower.includes('gene status update')) out.data[chr]['Gene status update'].push(t);
              else if (lower.includes('gene effect'))        out.data[chr]['Gene effect'].push(t);
              else if (lower.includes('stats update'))       out.data[chr]['Stats update'].push(t);
              else if (lower.includes('iter time'))          out.data[chr]['Iter Time'].push(t);
            }
          }
        });

        resolve(out);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

export function useFalconLogParser() {
  return { parseLog: parseLogFile, ITER_COMPONENTS, PRE_PROCESS_KEYS };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/useFalconLogParser.js && echo OK
```

No commit yet — grouped with the next task.

---

## Task 8: Create `composables/useFalconDataSource.js` and wire `store.loadFolder`

**Files:**
- Create: `frontend/composables/useFalconDataSource.js`
- Modify: `frontend/stores/FalconStore.js` (replace `loadFolder` stub)

Reference: `PEGS/src/dashboard/app.js:72-112` (`FileLoader.handleFolderSelect`). This is the data-source seam — the exported API has both `loadFromLocalFiles` (v1) and `loadFromServer` (v2 stub).

- [ ] **Step 1: Create the composable**

```js
// frontend/composables/useFalconDataSource.js
// Seam between "where data comes from" and the store.
// v1: loadFromLocalFiles (user's browser folder). v2: loadFromServer (stub).
import { useFalconFileLoader } from '~/composables/useFalconFileLoader';
import { useFalconLogParser }  from '~/composables/useFalconLogParser';

export function useFalconDataSource(store) {
  const { parseGenesFile, parseVariantsFile } = useFalconFileLoader();
  const { parseLog }                           = useFalconLogParser();

  /**
   * Accept a FileList (from <input webkitdirectory>) and populate the store.
   * Always resets caches and datasets first; handles partial datasets.
   */
  async function loadFromLocalFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;

    store.resetCaches();
    store.resetDatasets();

    const first = files[0];
    if (first && first.webkitRelativePath) {
      store.folderName = first.webkitRelativePath.split('/')[0];
    } else {
      store.folderName = '(unknown folder)';
    }

    const geneFile    = files.find((f) => f.name.endsWith('.wg.genes'));
    const variantFile = files.find((f) => f.name.endsWith('.wg.variants'));
    const logFile     = files.find((f) => f.name.endsWith('.wg.log'));

    if (!geneFile && !variantFile) {
      store.status = 'Notice: Missing standard .wg files. FALCON Zoom will still work if trait files exist.';
    } else {
      store.status = 'Loading datasets...';
    }

    const jobs = [];

    if (geneFile) {
      jobs.push(parseGenesFile(geneFile).then(({ data, columns }) => {
        store.datasets.genes.data = data;
        store.datasets.genes.columns = columns;
        store.datasets.genes.isLoaded = true;
      }).catch((err) => {
        console.error('genes parse error:', err);
        store.status = 'Error parsing .wg.genes';
      }));
    }
    if (variantFile) {
      jobs.push(parseVariantsFile(variantFile).then(({ data, columns }) => {
        store.datasets.variants.data = data;
        store.datasets.variants.columns = columns;
        store.datasets.variants.isLoaded = true;
      }).catch((err) => {
        console.error('variants parse error:', err);
        store.status = 'Error parsing .wg.variants';
      }));
    }
    if (logFile) {
      jobs.push(parseLog(logFile).then((logData) => {
        store.datasets.log.data         = logData.data;
        store.datasets.log.preProcess   = logData.preProcess;
        store.datasets.log.chromosomes  = logData.chromosomes;
        store.datasets.log.totalTime    = logData.totalTime;
        store.datasets.log.isLoaded     = true;
      }).catch((err) => {
        console.error('log parse error:', err);
      }));
    }

    await Promise.all(jobs);
    if (!store.status.startsWith('Error')) store.status = '';
  }

  async function loadFromServer(/* datasetId */) {
    // v2 — implement when the backend endpoint exists.
    throw new Error('loadFromServer is not implemented in v1');
  }

  return { loadFromLocalFiles, loadFromServer };
}
```

- [ ] **Step 2: Wire `store.loadFolder` to the data source**

Open `frontend/stores/FalconStore.js`. Replace the `loadFolder` stub with the block below. The `await import(...)` avoids the module-load cycle that would result from importing the composable at the top of the store file. `useFalconStore()` called from within an action returns the same store instance — idiomatic Pinia — and Pinia unwraps refs on property access, so the composable's `store.folderName = x` / `store.status = x` writes work without `.value`.

```js
  async function loadFolder(files) {
    const { useFalconDataSource } = await import('~/composables/useFalconDataSource');
    const source = useFalconDataSource(useFalconStore());
    await source.loadFromLocalFiles(files);
  }
```

- [ ] **Step 3: Verify no circular-import errors**

```bash
npm run dev
```
Load `/datasets` (any existing page). Confirm no console errors. Ctrl-C.

- [ ] **Step 4: Commit** (requires user approval)

Stage `frontend/composables/useFalconFileLoader.js`, `frontend/composables/useFalconLogParser.js`, `frontend/composables/useFalconDataSource.js`, `frontend/stores/FalconStore.js`.

Proposed message:
```
feat(falcon): add file loader, log parser, and data-source seam

Ports FileLoader.parseFile + parseLogFile from the original dashboard
into Vue 3 composables. useFalconDataSource is the seam — v1 uses
loadFromLocalFiles; loadFromServer is a v2 stub. Wires store.loadFolder
through the seam.
```

---

## Task 9: Create `composables/useFalconFilters.js`

**Files:**
- Create: `frontend/composables/useFalconFilters.js`

Reference: `PEGS/src/dashboard/app.js:558-619` (the two loops in `PlotModule.renderScatterPlot`). Extract the strict + region predicate into a pure composable so both plots and summary can reuse it.

- [ ] **Step 1: Create the file**

```js
// frontend/composables/useFalconFilters.js
// Port of the per-row filter logic from PlotModule.renderScatterPlot
// (PEGS/src/dashboard/app.js:558-619).

const UNASSIGNED = 'Unassigned (No Clump)';

function getNegP(row, isVariants) {
  if (!isVariants) return parseFloat(row['NEG_LOG_P']);
  let p = parseFloat(row['P_VALUE']);
  if (isNaN(p)) return NaN;
  if (p === 0) p = Number.MIN_VALUE;
  return -Math.log10(p);
}

function normalizedClumpId(row) {
  const raw = row['CLUMP'] ? row['CLUMP'].toString().trim() : '';
  return raw === '' ? UNASSIGNED : raw;
}

function passesGlobalFilter(row, isVariants, globalFilter) {
  if (!globalFilter.active) return true;
  const prob = parseFloat(row['PROBABILITY']);
  const negP = getNegP(row, isVariants);
  if (isNaN(prob) || prob < globalFilter.minProb) return false;
  if (isNaN(negP) || negP < globalFilter.minNegP) return false;
  return true;
}

function passesRegionFilter(row, regionFilter /* { chr, minStart, maxEnd } */) {
  if (!regionFilter || regionFilter.chr === 'All' || regionFilter.chr == null) return true;
  const rowChr = row['CHR'] ? row['CHR'].toString().trim() : '';
  if (rowChr !== regionFilter.chr) return false;
  const rowStart = parseFloat(row['START']);
  const rowEnd   = parseFloat(row['END']);
  if (regionFilter.maxEnd   != null && !isNaN(rowStart) && rowStart > regionFilter.maxEnd)   return false;
  if (regionFilter.minStart != null && !isNaN(rowEnd)   && rowEnd   < regionFilter.minStart) return false;
  return true;
}

export function useFalconFilters(store) {
  /**
   * Return rows passing globalFilter + (genes only) region filter.
   * @param {'genes' | 'variants'} name
   * @returns {Array<Record<string, any>>}
   */
  function filterDataset(name) {
    const rows = store.datasets[name].data;
    const isVariants = name === 'variants';
    const region = name === 'genes' ? store.plotFilters.genes : null;
    return rows.filter(
      (r) => passesGlobalFilter(r, isVariants, store.globalFilter)
          && passesRegionFilter(r, region),
    );
  }

  return { filterDataset, getNegP, normalizedClumpId };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/useFalconFilters.js && echo OK
```

No commit — grouped with the next few composable tasks.

---

## Task 10: Create `composables/usePlotly.js`

**Files:**
- Create: `frontend/composables/usePlotly.js`

- [ ] **Step 1: Create the file**

```js
// frontend/composables/usePlotly.js
// Lazy-load Plotly only on /falcon. The import promise is cached so
// subsequent mounts are immediate.

let plotlyPromise = null;

function loadPlotly() {
  if (!plotlyPromise) {
    plotlyPromise = import('plotly.js-dist-min').then((m) => m.default || m);
  }
  return plotlyPromise;
}

export function usePlotly() {
  /**
   * Mount a spec on a container element. Calls Plotly.newPlot.
   */
  async function mount(el, spec /* { data, layout, config? } */) {
    const Plotly = await loadPlotly();
    const config = { responsive: true, displaylogo: false, ...(spec.config || {}) };
    await Plotly.newPlot(el, spec.data, spec.layout, config);
    return el;
  }

  /**
   * Purge Plotly from a container (call in onBeforeUnmount).
   */
  async function unmount(el) {
    if (!el) return;
    const Plotly = await loadPlotly();
    Plotly.purge(el);
  }

  return { getPlotly: loadPlotly, mount, unmount };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/usePlotly.js && echo OK
```

No commit — grouped with the next task.

---

## Task 11: Create `composables/useFalconPlots.js`

**Files:**
- Create: `frontend/composables/useFalconPlots.js`

This ports `PlotModule.renderScatterPlot` and the relevant histogram/bar builders from `LogSummaryModule`. Keep chart specs pure — no DOM touched here.

- [ ] **Step 1: Create the file**

```js
// frontend/composables/useFalconPlots.js
// Pure {data, layout} builders for Plotly. No DOM. Consumers mount via usePlotly().
//
// Scatter: port of PEGS/src/dashboard/app.js:536-729 (PlotModule.renderScatterPlot).
// Histogram + bar: port of LogSummaryModule pieces (PEGS app.js:2511-2826).
import { getColorForClump, UNASSIGNED_CLUMP_ID, FALCON_PALETTE } from '~/utils/falcon/colorPalette';
import { STRICT_TOP_MIN_PROB, STRICT_TOP_MIN_NEGP } from '~/utils/falcon/config';
import { useFalconFilters } from '~/composables/useFalconFilters';

export function useFalconPlots(store) {
  const { getNegP, normalizedClumpId } = useFalconFilters(store);

  function buildScatterSpec(name /* 'genes' | 'variants' */) {
    const data = store.datasets[name].data;
    const isVariants = name === 'variants';
    const keyName = isVariants ? 'VARIANT' : 'GENE';
    const keyLead = isVariants ? 'LEAD_SNP' : 'NEAREST_TO_LEAD';
    const region  = name === 'genes' ? store.plotFilters.genes : { chr: 'All' };

    // Pass 1: compute top-per-clump under STRICT criteria (not user's globalFilter).
    const topPerClump = new Map();
    data.forEach((row, idx) => {
      const prob = parseFloat(row['PROBABILITY']);
      const negP = getNegP(row, isVariants);
      if (isNaN(prob) || prob < STRICT_TOP_MIN_PROB) return;
      if (isNaN(negP) || negP < STRICT_TOP_MIN_NEGP) return;
      if (!isVariants && region.chr !== 'All') {
        const rChr = row['CHR'] ? row['CHR'].toString().trim() : '';
        if (rChr !== region.chr) return;
        const rS = parseFloat(row['START']), rE = parseFloat(row['END']);
        if (!isNaN(rS) && rS > region.maxEnd)   return;
        if (!isNaN(rE) && rE < region.minStart) return;
      }
      const clumpId = normalizedClumpId(row);
      if (!topPerClump.has(clumpId) || prob > topPerClump.get(clumpId).prob) {
        topPerClump.set(clumpId, { index: idx, prob });
      }
    });

    // Pass 2: build per-clump traces, applying the user's globalFilter for display.
    const groups  = new Map();
    const topData = { x: [], y: [], text: [] };

    data.forEach((row, idx) => {
      const prob = parseFloat(row['PROBABILITY']);
      const negP = getNegP(row, isVariants);

      if (store.globalFilter.active) {
        if (isNaN(prob) || prob < store.globalFilter.minProb) return;
        if (isNaN(negP) || negP < store.globalFilter.minNegP) return;
      }
      if (!isVariants && region.chr !== 'All') {
        const rChr = row['CHR'] ? row['CHR'].toString().trim() : '';
        if (rChr !== region.chr) return;
        const rS = parseFloat(row['START']), rE = parseFloat(row['END']);
        if (!isNaN(rS) && rS > region.maxEnd)   return;
        if (!isNaN(rE) && rE < region.minStart) return;
      }
      if (isNaN(prob) || isNaN(negP)) return;

      const clumpId = normalizedClumpId(row);
      if (!groups.has(clumpId)) {
        groups.set(clumpId, { x: [], y: [], text: [], symbols: [], sizes: [] });
      }
      const g = groups.get(clumpId);
      g.x.push(prob);
      g.y.push(negP);

      const leadRaw = String(row[keyLead] || '').toLowerCase().trim();
      const isLead  = leadRaw === 'true' || leadRaw === '1' || leadRaw === 'yes';
      g.symbols.push(isLead ? 'star' : 'circle');
      g.sizes.push(isLead ? 14 : 8);

      const isTop     = topPerClump.get(clumpId)?.index === idx;
      const typeLabel = isVariants ? 'Variant' : 'Gene';
      const itemName  = row[keyName] || row['RSID'] || row['SNP'] || 'Unknown';

      let badges = '';
      if (isLead) badges += `<br><b>⭐ Lead ${isVariants ? 'SNP' : 'Gene'}</b>`;
      if (isTop)  badges += `<br><b style="color:#9333ea;">🏆 Top ${typeLabel}</b>`;

      const text =
        `${typeLabel}: ${itemName}${badges}<br>Clump: ${clumpId}<br>Prob: ${prob}<br>NegP: ${negP.toFixed(4)}`;
      g.text.push(text);

      if (isTop && clumpId !== UNASSIGNED_CLUMP_ID) {
        topData.x.push(prob); topData.y.push(negP); topData.text.push(text);
      }
    });

    const traces = [];
    Array.from(groups.keys()).sort().forEach((clumpId) => {
      const g = groups.get(clumpId);
      traces.push({
        x: g.x, y: g.y, text: g.text, name: clumpId,
        mode: 'markers', type: 'scattergl', hoverinfo: 'text',
        marker: {
          symbol: g.symbols, size: g.sizes, opacity: 0.8,
          color: getColorForClump(store.caches.clumpColor, clumpId),
        },
      });
    });
    if (topData.x.length > 0) {
      traces.push({
        x: topData.x, y: topData.y, text: topData.text,
        name: isVariants ? 'Top Variants' : 'Top Genes',
        mode: 'markers', type: 'scattergl', hoverinfo: 'text',
        marker: { symbol: 'circle-open', size: 22, color: '#9333ea', line: { width: 3 } },
      });
    }

    const layout = {
      xaxis: { title: 'PROBABILITY' },
      yaxis: { title: 'Negative Log10(P-Value)' },
      hovermode: 'closest',
      margin: { t: 30, l: 60, r: 20, b: 50 },
      showlegend: true,
      legend: {
        title: { text: 'CLUMP ID' },
        x: 1.02, y: 1, xanchor: 'left', yanchor: 'top',
        bgcolor: 'rgba(255,255,255,0.8)', bordercolor: '#d1d5db', borderwidth: 1,
      },
    };
    return { data: traces, layout };
  }

  function buildGenesScatterSpec()    { return buildScatterSpec('genes'); }
  function buildVariantsScatterSpec() { return buildScatterSpec('variants'); }

  /**
   * Per-component histogram card (LogSummary). Returns { data, layout, stats }.
   * Stats lets the consumer render min/med/mean/max above the plot.
   */
  function buildLogIterHistogramSpec(component, chrView /* 'all' | chromosome */) {
    const logStore = store.datasets.log;
    const values = [];
    if (chrView === 'all') {
      Object.keys(logStore.data).forEach((chr) => {
        values.push(...(logStore.data[chr][component] || []));
      });
    } else if (logStore.data[chrView]) {
      values.push(...(logStore.data[chrView][component] || []));
    }
    const positives = values.filter((v) => v > 0);
    const sorted = [...positives].sort((a, b) => a - b);
    const stats = sorted.length === 0
      ? null
      : {
          n:      sorted.length,
          min:    sorted[0],
          max:    sorted[sorted.length - 1],
          mean:   sorted.reduce((a, b) => a + b, 0) / sorted.length,
          median: sorted.length % 2
            ? sorted[Math.floor(sorted.length / 2)]
            : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2,
        };
    const idx = /* stable color per component name */
      Math.abs([...component].reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, 0)) % FALCON_PALETTE.length;
    return {
      stats,
      data: [{
        x: positives, type: 'histogram', name: component,
        marker: { color: FALCON_PALETTE[idx], line: { color: 'white', width: 1 } },
        opacity: 0.8,
      }],
      layout: {
        margin: { t: 10, l: 45, r: 20, b: 40 },
        xaxis: { title: 'Time (Seconds)', zeroline: false },
        yaxis: { title: 'Count' },
        plot_bgcolor: 'rgba(0,0,0,0)', paper_bgcolor: 'rgba(0,0,0,0)',
        autosize: true,
      },
    };
  }

  /**
   * Per-chromosome total pre-process time bar chart.
   * Returns {data, layout}.
   */
  function buildLogPreprocessBarSpec() {
    const logStore = store.datasets.log;
    const chrs = Array.from(logStore.chromosomes).sort((a, b) => {
      const na = parseInt(a, 10), nb = parseInt(b, 10);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      return a.localeCompare(b);
    });
    const totals = chrs.map((chr) => {
      const pp = logStore.preProcess[chr] || {};
      return Object.values(pp).reduce((a, b) => a + b, 0);
    });
    const colors = chrs.map((_, i) => FALCON_PALETTE[i % FALCON_PALETTE.length]);
    return {
      data: [{
        x: chrs, y: totals, type: 'bar', marker: { color: colors },
        text: totals.map((t) => `${t.toFixed(2)}s`), textposition: 'auto', hoverinfo: 'x+y',
      }],
      layout: {
        margin: { t: 10, l: 45, r: 20, b: 40 },
        xaxis: { title: 'Chromosome', type: 'category' },
        yaxis: { title: 'Time (Seconds)' },
        plot_bgcolor: 'rgba(0,0,0,0)', paper_bgcolor: 'rgba(0,0,0,0)',
        autosize: true,
      },
    };
  }

  return {
    buildGenesScatterSpec, buildVariantsScatterSpec,
    buildLogIterHistogramSpec, buildLogPreprocessBarSpec,
  };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/useFalconPlots.js && echo OK
```

- [ ] **Step 3: Commit** (requires user approval)

Stage the three composables from tasks 9–11.

```
feat(falcon): filters, Plotly loader, and chart-spec builders

- useFalconFilters: strict + region predicates extracted from PlotModule
- usePlotly: one-shot dynamic import + mount/unmount
- useFalconPlots: pure {data, layout} builders for scatter, histogram,
  pre-process bar. No DOM.
```

---

## Task 12: Create `composables/useClinicalTrials.js` and wire `store.loadClinicalTrialsCsv`

**Files:**
- Create: `frontend/composables/useClinicalTrials.js`
- Modify: `frontend/stores/FalconStore.js` (replace `loadClinicalTrialsCsv` stub)

Reference: `PEGS/src/dashboard/app.js:1696-1754` (`ClinicalTrialsManager`).

- [ ] **Step 1: Create the composable**

```js
// frontend/composables/useClinicalTrials.js
// Port of ClinicalTrialsManager (PEGS/src/dashboard/app.js:1696-1754).
// CSV columns expected: Gene_Name, Drug_ID, Indication_Name, Phase.
import Papa from 'papaparse';

export function useClinicalTrials(store) {
  /**
   * @param {File} file
   * @returns {Promise<void>}
   */
  function loadCsv(file) {
    return new Promise((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          try {
            const byGene = {};
            results.data.forEach((row) => {
              const raw = row.Gene_Name;
              if (!raw) return;
              const key = raw.toUpperCase().trim();
              if (!byGene[key]) byGene[key] = [];
              byGene[key].push({
                drugId:     row.Drug_ID,
                indication: row.Indication_Name,
                phase:      row.Phase,
              });
            });
            store.clinicalTrials.byGene   = byGene;
            store.clinicalTrials.isLoaded = true;
            resolve();
          } catch (err) { reject(err); }
        },
        error: (err) => reject(err),
      });
    });
  }

  return { loadCsv };
}
```

- [ ] **Step 2: Wire `store.loadClinicalTrialsCsv`**

In `frontend/stores/FalconStore.js`, replace the `loadClinicalTrialsCsv` stub:

```js
  async function loadClinicalTrialsCsv(file) {
    const { useClinicalTrials } = await import('~/composables/useClinicalTrials');
    const { loadCsv } = useClinicalTrials(useFalconStore());
    await loadCsv(file);
  }
```

- [ ] **Step 3: Verify**

```bash
test -f frontend/composables/useClinicalTrials.js && echo OK
```

- [ ] **Step 4: No commit yet** — group with next task.

---

## Task 13: Create `composables/useGeneTraitFetcher.js`

**Files:**
- Create: `frontend/composables/useGeneTraitFetcher.js`

Reference: `PEGS/src/dashboard/app.js:1759-1839` (`GeneTraitFetcher`). **Change from original:** accept an `AbortSignal` per v1 improvement noted in spec §11. URLs preserved exactly.

- [ ] **Step 1: Create the file**

```js
// frontend/composables/useGeneTraitFetcher.js
// Port of GeneTraitFetcher (PEGS/src/dashboard/app.js:1759-1839) with cancellation.
// v1: preserves original's client-side codetabs proxy (spec §9 decision 8).
import Papa from 'papaparse';

const CATALOG_URL =
  'https://api.codetabs.com/v1/proxy?quest=' +
  encodeURIComponent('https://hugeampkpncms.org/rest/data?pageid=Gene_page_PEGLs_475');

const TRAIT_URL_BASE =
  'https://api.codetabs.com/v1/proxy?quest=' +
  encodeURIComponent('https://hugeampkpncms.org/rest/egls?gene=');

export function useGeneTraitFetcher(store) {
  /**
   * Fetch the gene-page catalog (used to mark novelty).
   * Populates store.caches.traitLookup with catalog entries.
   */
  async function fetchCatalog(signal) {
    const res = await fetch(CATALOG_URL, { signal });
    if (!res.ok) throw new Error(`catalog fetch: HTTP ${res.status}`);
    const json = await res.json();
    const csvText = json.field_data_points;
    if (typeof csvText !== 'string') throw new Error('catalog: unexpected shape');
    return new Promise((resolve, reject) => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        complete: (r) => {
          r.data.forEach((row) => {
            const g = (row.Gene || '').toUpperCase().trim();
            if (!g) return;
            if (!store.caches.traitLookup[g]) store.caches.traitLookup[g] = [];
            store.caches.traitLookup[g].push(row);
          });
          resolve();
        },
        error: (err) => reject(err),
      });
    });
  }

  /**
   * Fetch per-gene trait data for the given genes (uncached ones only).
   * Safe to call repeatedly — results are cached in store.caches.traitLookup.
   */
  async function fetchTraits(geneNames, signal) {
    const unique = Array.from(new Set(geneNames.map((g) => g.toUpperCase().trim())));
    const todo   = unique.filter((g) => !store.caches.traitLookup[g]);
    await Promise.all(todo.map(async (g) => {
      try {
        const res = await fetch(TRAIT_URL_BASE + encodeURIComponent(g), { signal });
        if (!res.ok) { store.caches.traitLookup[g] = []; return; }
        const json = await res.json();
        store.caches.traitLookup[g] = Array.isArray(json) ? json : (json?.data || []);
      } catch (err) {
        if (err.name === 'AbortError') throw err;
        store.caches.traitLookup[g] = [];
      }
    }));
  }

  return { fetchCatalog, fetchTraits };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/useGeneTraitFetcher.js && echo OK
```

- [ ] **Step 3: Commit** (requires user approval)

Stage both composables from tasks 12–13.
```
feat(falcon): clinical-trials CSV loader + cancelable gene-trait fetcher

- useClinicalTrials.loadCsv populates clinicalTrials.byGene
- useGeneTraitFetcher takes an AbortSignal (v1 improvement; the original
  had no cancellation). URLs preserved exactly — v2 will migrate behind
  a Python endpoint.
```

---

## Task 14: Create `composables/useFalconSummary.js`

**Files:**
- Create: `frontend/composables/useFalconSummary.js`

Reference: `PEGS/src/dashboard/app.js:734-1089` (`SummaryModule.processDataset` + `processAll`). This is the largest composable. Extract the aggregation shape; keep behavior identical — including the preserved quirk that Summary table is not re-filtered on global filter toggle (spec §11).

- [ ] **Step 1: Create the file**

```js
// frontend/composables/useFalconSummary.js
// Port of SummaryModule aggregation (PEGS/src/dashboard/app.js:734-1089).
// Produces top-per-clump and lead-per-chromosome signals for genes and variants.
// Preserves original quirk: strict filter does NOT affect this output (§11).
import { useFalconFilters } from '~/composables/useFalconFilters';

export function useFalconSummary(store) {
  const { getNegP, normalizedClumpId } = useFalconFilters(store);

  /**
   * Process one dataset into { topPerClump, leadPerChr } arrays.
   */
  function processDataset(name /* 'genes' | 'variants' */) {
    const isVariants = name === 'variants';
    const data = store.datasets[name].data;
    const keyName = isVariants ? 'VARIANT' : 'GENE';
    const keyLead = isVariants ? 'LEAD_SNP' : 'NEAREST_TO_LEAD';

    const topPerClump = new Map(); // clumpId -> best row summary
    const leadsByChr  = {};        // chr -> Array<row summary>

    data.forEach((row, idx) => {
      const prob = parseFloat(row['PROBABILITY']);
      const negP = getNegP(row, isVariants);
      if (isNaN(prob) || isNaN(negP)) return;

      const chr     = row['CHR'] ? row['CHR'].toString().trim() : '';
      const clumpId = normalizedClumpId(row);
      const itemName = row[keyName] || row['RSID'] || row['SNP'] || 'Unknown';
      const leadRaw = String(row[keyLead] || '').toLowerCase().trim();
      const isLead  = leadRaw === 'true' || leadRaw === '1' || leadRaw === 'yes';

      const summary = {
        index: idx, name: itemName, chr, clumpId, prob, negP, isLead,
        start: parseFloat(row['START']), end: parseFloat(row['END']),
        raw: row,
        traits: null,        // filled by attachNoveltyFlags
        isNovel: null,
        clinicalTrials: [],  // filled by attachClinicalTrials
      };

      // top per clump (strict criteria — prob >= 0.05 && negP >= 1 already in spec §11;
      // but the original Summary uses a looser "any row passes" and ranks by prob)
      if (clumpId !== 'Unassigned (No Clump)') {
        if (!topPerClump.has(clumpId) || prob > topPerClump.get(clumpId).prob) {
          topPerClump.set(clumpId, summary);
        }
      }

      // lead per chromosome
      if (isLead && chr) {
        if (!leadsByChr[chr]) leadsByChr[chr] = [];
        leadsByChr[chr].push(summary);
      }
    });

    const top  = Array.from(topPerClump.values()).sort((a, b) => b.prob - a.prob);
    const lead = [];
    Object.keys(leadsByChr).forEach((chr) => {
      leadsByChr[chr].sort((a, b) => b.prob - a.prob);
      lead.push(...leadsByChr[chr]);
    });

    return { top, lead };
  }

  /** Both datasets in one call. */
  function computeTopAndLeadSignals() {
    return {
      genes:    store.datasets.genes.isLoaded    ? processDataset('genes')    : { top: [], lead: [] },
      variants: store.datasets.variants.isLoaded ? processDataset('variants') : { top: [], lead: [] },
    };
  }

  /** Mutate rows in place with clinical-trial matches. */
  function attachClinicalTrials(rows) {
    if (!store.clinicalTrials.isLoaded) return;
    rows.forEach((row) => {
      const hits = store.clinicalTrials.byGene[row.name?.toUpperCase?.()] || [];
      row.clinicalTrials = hits;
    });
  }

  /** Fetch novelty for rows whose `isNovel` is null; mutate in place. */
  async function attachNoveltyFlags(rows, signal) {
    const { useGeneTraitFetcher } = await import('~/composables/useGeneTraitFetcher');
    const fetcher = useGeneTraitFetcher(store);
    const targets = rows.filter((r) => r.isNovel == null).map((r) => r.name);
    if (targets.length === 0) return;
    await fetcher.fetchTraits(targets, signal);
    rows.forEach((row) => {
      const traits = store.caches.traitLookup[row.name?.toUpperCase?.() || ''] || [];
      row.traits  = traits;
      row.isNovel = traits.length === 0;
    });
  }

  return { computeTopAndLeadSignals, attachClinicalTrials, attachNoveltyFlags };
}
```

- [ ] **Step 2: Verify**

```bash
test -f frontend/composables/useFalconSummary.js && echo OK
```

- [ ] **Step 3: No commit yet** — group with next task.

---

## Task 15: Create `composables/useFalconTDP.js`, `utils/falcon/pako.js`, and wire `store.loadLdFolder`

**Files:**
- Create: `frontend/composables/useFalconTDP.js`
- Create: `frontend/utils/falcon/pako.js`
- Modify: `frontend/stores/FalconStore.js` (replace `loadLdFolder` stub)

Reference: `PEGS/src/dashboard/app.js:1842-2507` (`TDPModule`). This is a large port. The plan creates the composable with a `runAnalysis(cfg)` entry point that encapsulates the multi-phase process: pick chromosome → filter trait files → load LD bins → build scatter + heatmap spec.

Because this is ~670 lines of original logic and the port is a straight lift, the step here documents where to source from rather than inlining all the code. The subagent executing this task **must read `PEGS/src/dashboard/app.js:1842-2507` end-to-end** before translating.

- [ ] **Step 1: Create the pako helper**

```js
// frontend/utils/falcon/pako.js
// Helper for .gz LD files. pako is already a dep.
import pako from 'pako';

export async function readGzippedText(file) {
  const buf = await file.arrayBuffer();
  const bytes = new Uint8Array(buf);
  return pako.ungzip(bytes, { to: 'string' });
}
```

- [ ] **Step 2: Create the TDP composable**

```js
// frontend/composables/useFalconTDP.js
// Port of TDPModule (PEGS/src/dashboard/app.js:1842-2507).
// Entry point: runAnalysis(cfg) returns a Plotly {data, layout} spec.
//
// TRANSLATION NOTES for the implementer:
// - Replace DataStore.datasets.* reads with store.datasets.*
// - Replace FileLoader.ldFiles reads with store.tdp.ldFiles
// - Replace ColorManager.getColor / ColorManager.palette with
//   getColorForClump(store.caches.clumpColor, id) and FALCON_PALETTE
// - Cache LD bin parses in store.caches.ldBinCache (key = bp-bin number)
// - Do NOT touch the DOM; return the spec
// - Respect store.globalFilter for trait-row filtering (the original only
//   applies the global filter at run-analysis time, not on re-render —
//   preserve that; see spec §11)
// - The original uses Papa.parse for LD files; keep that
// - Gzipped LD files: use readGzippedText() from utils/falcon/pako.js
import Papa from 'papaparse';
import { readGzippedText } from '~/utils/falcon/pako';
import { getColorForClump, FALCON_PALETTE } from '~/utils/falcon/colorPalette';

export function useFalconTDP(store) {
  /**
   * @param {{
   *   gene: string,
   *   boundary: number,
   *   focus: 'region' | 'gene',
   *   plotType: 'falcon' | 'raw' | 'overlay',
   *   minR2: number,
   *   maxStretch: number,
   * }} cfg
   * @returns {Promise<{ data: any[], layout: any }>}
   */
  async function runAnalysis(cfg) {
    // IMPLEMENTATION: lift logic from PEGS/src/dashboard/app.js:1842-2507.
    // Return { data, layout } to be passed to Plotly.newPlot.
    // When done, also set store.tdp.lastAnalysis = { data, layout, cfg }.
    throw new Error('TDP runAnalysis: port from PEGS/src/dashboard/app.js:1842-2507');
  }

  return { runAnalysis };
}
```

**The `throw` is intentional.** The subagent executing Task 15 fills in the body by translating the original. Do not ship Task 15 with the throw in place.

- [ ] **Step 3: Wire `store.loadLdFolder`**

In `frontend/stores/FalconStore.js`, replace the `loadLdFolder` stub:

```js
  async function loadLdFolder(files) {
    const arr = Array.from(files);
    tdp.ldFiles = arr;
    tdp.ldFolderName = arr[0]?.webkitRelativePath?.split('/')[0] || '(ld folder)';
  }
```

- [ ] **Step 4: Verify the composable loads (dev server)**

```bash
npm run dev
```
Navigate to `http://localhost:3000/datasets` just to ensure no import errors surface in the console. Ctrl-C.

- [ ] **Step 5: Commit** (requires user approval)

Stage `frontend/composables/useFalconSummary.js`, `frontend/composables/useFalconTDP.js`, `frontend/utils/falcon/pako.js`, and the store edits.

```
feat(falcon): summary aggregation and TDP zoom analysis

- useFalconSummary.computeTopAndLeadSignals ports SummaryModule aggregation
- useFalconSummary.attachClinicalTrials / attachNoveltyFlags hydrate rows
- useFalconTDP.runAnalysis ports TDPModule (zoom + LD heatmap)
- utils/falcon/pako.js: gzip decompression helper
- Wires store.loadLdFolder
```

---

## Task 16: Create `pages/falcon/index.vue` scaffold

**Files:**
- Create: `frontend/pages/falcon/index.vue`

Minimum viable page: title, folder picker (inline `<input webkitdirectory>` — no `components/falcon/FolderPicker.vue` in base), active-folder pill, status line, and a "loaded datasets" indicator for manual verification. No tabs, no charts.

- [ ] **Step 1: Create the file**

```vue
<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-6">
    <h1 class="text-2xl font-bold mb-4">FALCON Dashboard</h1>
    <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
      Base scaffold — tab UI arrives in the branch-specific builds.
    </p>

    <div class="flex items-center gap-3 mb-4">
      <input
        ref="folderInput"
        type="file"
        webkitdirectory
        directory
        class="block"
        @change="onFolderSelect"
      />
      <Tag
        v-if="store.folderName"
        severity="success"
        :value="`Active Dataset: ${store.folderName}`"
      />
    </div>

    <p v-if="store.status" class="text-sm text-gray-500 mb-4">{{ store.status }}</p>

    <ul class="text-sm space-y-1">
      <li>genes:    <b>{{ store.datasets.genes.isLoaded    ? 'loaded' : '—' }}</b></li>
      <li>variants: <b>{{ store.datasets.variants.isLoaded ? 'loaded' : '—' }}</b></li>
      <li>log:      <b>{{ store.datasets.log.isLoaded      ? 'loaded' : '—' }}</b></li>
    </ul>
  </div>
</template>

<script setup>
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();

async function onFolderSelect(e) {
  await store.loadFolder(e.target.files);
}
</script>
```

- [ ] **Step 2: Commit** (requires user approval)

```
feat(falcon): scaffold /falcon page with folder upload

Lands the base page. Folder select populates the store. No tabs,
no charts — those are added in the branch builds.
```

---

## Task 17: End-to-end smoke test

**Files:** none.

- [ ] **Step 1: Start the dev server**

From `frontend/`:
```bash
npm run dev
```

- [ ] **Step 2: Auth check**

In a **private browser window** (so you're logged out), visit `http://localhost:3000/falcon`. **Expected:** redirect to `/login`.

- [ ] **Step 3: Log in and visit `/falcon`**

Log in with your dev credentials. Navigate to `http://localhost:3000/falcon`. Expected: page renders with folder input and all three datasets showing `—`.

- [ ] **Step 4: Load fixture**

Click the folder input. Select `~/falcon-fixtures/kp5/T2D/`. Expected within a few seconds:
- Active dataset pill shows "T2D"
- genes: **loaded**
- variants: **loaded**
- log: **loaded**
- Status line clears

- [ ] **Step 5: Verify store shape in devtools**

Open browser devtools → Console:
```js
// Pinia reactive access — works in composition stores on Nuxt
const s = window.$pinia?._s?.get('falcon') ?? (await import('~/stores/FalconStore')).useFalconStore();
console.log({
  folder:    s.folderName,
  geneCount: s.datasets.genes.data.length,
  varCount:  s.datasets.variants.data.length,
  chromos:   Array.from(s.datasets.log.chromosomes),
  totalTime: s.datasets.log.totalTime,
  globalFilter: { ...s.globalFilter },
});
```
Expected:
- `geneCount` and `varCount` both > 0 (thousands for T2D).
- `chromos` array contains chromosome numbers (e.g., `["1","2",...,"22"]`).
- `totalTime` looks like `"NNNN.NN seconds"` (or the fallback string if not parsed).
- `globalFilter` matches the defaults.

- [ ] **Step 6: Cache-reset check**

Select `~/falcon-fixtures/kp5/TGnonT2D/` (the other dataset) with the same picker. Expected:
- Active pill changes to "TGnonT2D"
- All three dataset flags are `loaded` again
- Re-run the devtools snippet — `s.caches.clumpColor.size` should have reset before re-populating.

Quick check:
```js
console.log('clump colors cached:', s.caches.clumpColor.size);
```
The number can be non-zero after data is loaded (if anything touched the cache) or zero (if nothing did yet — base doesn't render scatters). Either is fine; the important thing is that `TGnonT2D` load calls `resetCaches()` (verify in the network/console that no warnings fire about stale state).

- [ ] **Step 7: Stop the dev server**

Ctrl-C in the terminal.

- [ ] **Step 8: Final branch-health check**

```bash
git status && git log --oneline main..HEAD
```
Expected: clean tree, ~7 commits on `falcon-port-base` ahead of `main`.

No commit for this task (testing only).

---

## Done when

- All 17 tasks complete.
- `git status` clean on `falcon-port-base`.
- Smoke test (Task 17) passes.
- The spec's v1 base-branch deliverable is met: `/falcon` loads behind auth, the folder picker populates the Pinia store, and the composable surface is ready for Branch A and Branch B to consume.

**Next step after this plan:** open a PR from `falcon-port-base` → `main`. Once merged, fork `falcon-port-a` and `falcon-port-b` from `main` and run Plans 2 and 3.
