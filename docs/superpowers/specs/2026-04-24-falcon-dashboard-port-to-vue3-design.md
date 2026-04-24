# FALCON Dashboard Port to Vue 3 — Design

**Date:** 2026-04-24
**Status:** Design approved, ready for implementation plan
**Source:** `PEGS/src/dashboard/` (vanilla-JS FALCON Results Viewer, ~3,400 LoC)
**Target:** `dig-job-server-2/frontend/` (Nuxt 3 + Vue 3 + PrimeVue 4.5 + Tailwind + Pinia, `ssr: false`)

## 1. Overview

Port the standalone FALCON Results Viewer — a client-side dashboard that ingests FALCON pipeline output (`.wg.genes`, `.wg.variants`, `.wg.log`, LD matrices, and a clinical-trials CSV) and renders six interactive Plotly views — into the existing `dig-job-server-2` Nuxt frontend, preserving full feature parity.

The port is client-only. The user selects a folder from their machine, the browser parses files in-place, and all analysis happens locally. A data-source seam is left in place so a server-backed mode can slot in later without re-plumbing the UI.

To compare visual treatments on a single deployment, both variants land in `main` at separate routes:

- **Variant B — `/falcon-b`, "PrimeVue shell, custom guts."** Outer chrome uses PrimeVue; charts, data tables, the genomic-region filter, and the data inspector keep their original look.
- **Variant A — `/falcon-a`, "full PrimeVue."** Every surface with a PrimeVue equivalent uses it (DataTable, Slider, SelectButton, Card, etc.); dark-mode works throughout.

Each variant's UI lives under its own directory (`components/falcon-a/` and `components/falcon-b/`); shared composables, stores, and utils are untouched. After comparison on the deployed environment, a third short PR deletes the loser's page and components directory.

## 2. Goals and non-goals

**Goals**

- Full feature parity with the original dashboard (all six tabs, all filters, clinical-trials integration, gene-trait lookup, FALCON Zoom/LD correlation).
- URL-only deployment at `/falcon`, behind the existing auth middleware, with no header link — a soft launch.
- Preserve the algorithms and data-parsing code nearly verbatim by lifting them into composables; the risk of behavior regressions stays low.
- Leave a data-source seam so a future server-backed mode can be added without UI changes.
- Produce two visually distinct branches suitable for side-by-side comparison.

**Non-goals**

- Introducing a test framework. The host app has none; v1 ships with a documented manual test plan.
- Fixing the original's known UX traps (see §11 "Preserved quirks"). Strict parity in v1 keeps behavior comparisons clean.
- A new Python backend endpoint for gene-trait lookup. v1 keeps the original's client-side `api.codetabs.com` proxy; migrating this is a v2 candidate.
- Linking `/falcon` from the app header. v1 is URL-only.
- Server-backed dataset mode — the seam is in place, but `loadFromServer()` is a stub.
- A CSV download button on the data table (an original-parity decision).

## 3. Architecture

A Nuxt page at `pages/falcon/index.vue` lazy-loads Plotly on route entry and renders a `Tabs`/`TabList`/`TabPanels` shell. State lives in a single Pinia store. Logic lives in composables that hold algorithms lifted from the original `app.js`. Rendering lives in per-tab components under `components/falcon/`.

### Directory layout (additions to `frontend/`)

Base plan (`falcon-port-base`, already landed) contributes the scaffold page, the store, and all composables + utils — everything shared between variants:

```
pages/
  falcon/
    index.vue                      # base scaffold — kept as a minimal "health check" page
  falcon-a/
    index.vue                      # Variant A — added by Plan 2
  falcon-b/
    index.vue                      # Variant B — added by Plan 3
components/
  falcon-a/                        # added by Plan 2
    ExecutiveSummaryTab.vue
    GenesScatterTab.vue
    VariantsScatterTab.vue
    DataTableTab.vue
    LogSummaryTab.vue
    TDPTab.vue
    GlobalFilterBar.vue
    FolderPicker.vue
    GenomicRegionFilter.vue
    DataInspectorPanel.vue
    TraitCard.vue
  falcon-b/                        # added by Plan 3 — same component set, Variant B styling
    ... (symmetric with falcon-a/)
stores/
  FalconStore.js                   # base — shared
composables/                       # base — all shared
  useFalconDataSource.js
  useFalconFileLoader.js
  useFalconLogParser.js
  useFalconFilters.js
  useFalconPlots.js
  useFalconTDP.js
  useFalconSummary.js
  useClinicalTrials.js
  useGeneTraitFetcher.js
  usePlotly.js
utils/                             # base — all shared
  falcon/
    colorPalette.js
    config.js
    pako.js
```

### Data flow

```
FolderPicker ──▶ FalconStore.loadFolder(files)
                   │
                   ├── useFalconDataSource.loadFromLocalFiles(files)
                   │     ├── useFalconFileLoader.parseGenesFile → datasets.genes
                   │     ├── useFalconFileLoader.parseVariantsFile → datasets.variants
                   │     └── useFalconLogParser.parseLog → datasets.log
                   │
                   └── resetCaches()   # clumpColor, traitLookup, ldBinCache

[ Tab components ]
  │
  ├── read store (datasets, filters, caches)
  ├── call useFalconFilters.filterDataset(name) for display
  ├── call useFalconPlots.build*Spec() for Plotly {data, layout}
  ├── call usePlotly().mount(el, spec)
  └── wire plotly_click → DataInspectorPanel.showData(html)
```

## 4. Branching strategy

```
main
 └── falcon-port-base              # shared foundation (stores/, composables/, utils/, scaffold)
 └── falcon-variant-a              # forks from main after base merges; adds /falcon-a
 └── falcon-variant-b              # forks from main after base merges; adds /falcon-b
 └── falcon-cleanup                # forks from main after eval; deletes the loser
```

**Workflow:**
1. `falcon-port-base` → PR → merge to `main`. Contributes the shared foundation.
2. `falcon-variant-a` and `falcon-variant-b` fork from `main` in parallel. Each adds its own page + components dir. Neither touches the other's files, so the two PRs never conflict.
3. Both variant PRs merge to `main`. Deploy. Compare live at `/falcon-a` vs `/falcon-b`.
4. Pick the winner. `falcon-cleanup` deletes the loser's page and components directory, possibly renames the winner to `/falcon` (consolidating) or leaves it at `/falcon-<winner>` if a nicer URL can wait. PR, merge, done.

No long-lived feature branches, no merge waiting on product decisions, and the deployed env always carries whatever's been merged.

## 5. Pinia store shape

```js
export const useFalconStore = defineStore('falcon', () => {
  const datasets = reactive({
    genes:    { data: [], columns: [], isLoaded: false },
    variants: { data: [], columns: [], isLoaded: false },
    log:      { data: {}, preProcess: {}, chromosomes: new Set(),
                totalTime: '', isLoaded: false },
  });

  const folderName = ref('');
  const status     = ref('');

  const globalFilter = reactive({
    active: true, minProb: 0.1, minNegP: 8,
  });

  const tableStates = reactive({
    genes:    { searchQuery: '', sortCol: null, sortAsc: true, currentPage: 1 },
    variants: { searchQuery: '', sortCol: null, sortAsc: true, currentPage: 1 },
  });

  const plotFilters = reactive({
    genes:    { chr: null, bpMin: null, bpMax: null },
    variants: { chr: null, bpMin: null, bpMax: null },
  });

  const clinicalTrials = reactive({ isLoaded: false, byGene: {} });

  const tdp = reactive({
    ldFiles: [], ldFolderName: '',
    lastAnalysis: null, status: '',
  });

  const caches = reactive({
    clumpColor:  new Map(),   // clumpId → hex
    traitLookup: {},          // gene   → trait rows
    ldBinCache:  new Map(),   // bp-bin → parsed LD rows
  });

  function resetCaches() { /* clears all three */ }
  async function loadFolder(files) { /* resetCaches, then delegate */ }
  async function loadClinicalTrialsCsv(file) { /* ... */ }
  async function loadLdFolder(files) { /* ... */ }

  return { datasets, folderName, status, globalFilter, tableStates,
           plotFilters, clinicalTrials, tdp, caches,
           resetCaches, loadFolder, loadClinicalTrialsCsv, loadLdFolder };
});
```

**Addresses audit findings:**
- LD state lives in `tdp`, not in a shared `FileLoader` — no cross-module reach-ins.
- `resetCaches()` runs at the top of every `loadFolder()` — fixes stale-color/stale-LD bugs.
- `clumpColor` is a store-scoped Map — eliminates the race condition on concurrent chart renders.

## 6. Composable contracts

```
useFalconDataSource(store)
  loadFromLocalFiles(files: File[]): Promise<void>
  loadFromServer(datasetId: string): Promise<void>    // v2 stub

useFalconFileLoader()
  parseGenesFile(file: File):    Promise<Row[]>
  parseVariantsFile(file: File): Promise<Row[]>

useFalconLogParser()
  parseLog(file: File): Promise<{
    data: Record<chr, Record<component, number[]>>,
    preProcess: Record<chr, Record<step, number>>,
    chromosomes: Set<string>,
    totalTime: string,
  }>

useFalconFilters(store)
  filterDataset(name: 'genes' | 'variants'): Row[]
  strictPredicate(row): boolean

useFalconPlots(store)
  buildGenesScatterSpec():        { data, layout }
  buildVariantsScatterSpec():     { data, layout }
  buildLogPreprocessBarSpec(chr): { data, layout }
  buildLogIterHistogramSpec(component, chr): { data, layout }

useFalconSummary(store)
  computeTopAndLeadSignals():     { genes: Summary[], variants: Summary[] }
  attachClinicalTrials(rows):     void
  attachNoveltyFlags(rows, signal: AbortSignal): Promise<void>

useFalconTDP(store)
  runAnalysis(cfg: { gene, boundary, focus, plotType, minR2, maxStretch }):
    Promise<{ data, layout }>

useClinicalTrials(store)
  loadCsv(file: File): Promise<void>

useGeneTraitFetcher(store)
  fetchCatalog(signal: AbortSignal): Promise<void>
  fetchTraits(geneNames: string[], signal: AbortSignal): Promise<void>

usePlotly()
  getPlotly():            Promise<Plotly>     // dynamic import, one-shot
  mount(el, spec):        Promise<void>
  unmount(el):            void
```

Chart-spec builders are pure: they read the store and return `{data, layout}` objects. They never touch the DOM. Components own mount/unmount.

## 7. Per-tab components

All tabs: no props, read from `useFalconStore()`, mount charts via `usePlotly()` + local `ref`, `unmount` in `onBeforeUnmount`, re-render on `globalFilter` change via `watchEffect`.

- **`ExecutiveSummaryTab.vue`** — ports `SummaryModule`. Two signal tables (genes + variants) with top-scoring-per-CLUMP and lead-per-CHR sections. Per-row expansion (`TraitCard`) shows trait citations + clinical-trial matches. Search, role filter, novelty toggle (triggers cancelable `fetchTraits`). Three embedded Plotly charts: probability box-plots, lead-to-lead distance distribution, clinical-trial phase bar.

- **`GenesScatterTab.vue`** — ports `PlotModule.renderScatterPlot('genes', …)`. Mounts `GenomicRegionFilter` above a `scattergl` plot (PROBABILITY vs −log10 p, colored by CLUMP). Wires `plotly_click` → `DataInspectorPanel`.

- **`VariantsScatterTab.vue`** — identical structure, reads `datasets.variants`, no genomic-region filter (matches original).

- **`DataTableTab.vue`** — ports `TableModule`. Inner genes/variants switch, search, sortable columns, pagination.
  - Variant B: native `<table>` with sticky headers and custom sort/paginator (verbatim port).
  - Variant A: `<DataTable :lazy>` with `<Column v-for>`, `@sort`, `@page`, `filterDisplay="row"`.

- **`LogSummaryTab.vue`** — ports `LogSummaryModule`. Total-time pill, explainer card (the "Parallel Wall Time Calculation" note, verbatim), per-chromosome dropdown, pre-process bar chart, grid of per-component histograms with min/med/mean/max stats.

- **`TDPTab.vue`** — ports `TDPModule`. Controls row (target gene, boundary, focus, plot type, LD folder picker, min R², max stretch, Run Analysis). Single 850px Plotly container with trait scatter traces, LD heatmap, gene rectangles + clump span lines as `layout.shapes`, gene name annotations.

- **`GlobalFilterBar.vue`** — rendered by `pages/falcon/index.vue` above the tab strip. Three controls bound to `store.globalFilter`.

- **`DataInspectorPanel.vue`** — floating bottom-right panel. Owns open/closed state. `showData(html)` called after a `plotly_click`. Copy-to-clipboard button.

- **`FolderPicker.vue`** — custom `<input type=file webkitdirectory>` on both branches (PrimeVue `FileUpload` doesn't support directory selection).

- **`GenomicRegionFilter.vue`** — chromosome pill grid + BP range slider; Variant B uses original CSS, Variant A uses PrimeVue `SelectButton` + `Slider :range` inside a `Card`.

Active tab synced to `?tab=summary|genes|variants|table|log|tdp` via `router.push({ query: { ...route.query, tab } })`, mirroring `pages/results/index.vue`.

## 8. Variant A vs Variant B divergence

Both variants implement the full tab set (§7) under `components/falcon-a/` and `components/falcon-b/` respectively, and each gets its own page at `pages/falcon-a/index.vue` and `pages/falcon-b/index.vue`. The divergence below applies per-component:

| Concern | Variant B | Variant A |
|---|---|---|
| Folder picker | Custom `<input webkitdirectory>` | Custom `<input>` styled with PrimeVue `Button` trigger |
| Outer chrome | PrimeVue `Tabs` + `Tag` for active-dataset pill | Same |
| Global filter bar | PrimeVue `ToggleButton` + `InputNumber` × 2, flex row | Wrapped in `Card` with `Fieldset legend="Global Filters"` |
| Data table | Native HTML `<table>`, custom sort + paginator | PrimeVue `DataTable` with `@sort`/`@page` |
| Chromosome filter | Original `.chr-btn` pills + dual-range `<input>` | `SelectButton` + `Slider :range` in a `Card` |
| Summary cards | Original card + expandable-row CSS | `Panel` collapsible + `DataView` |
| TDP controls | Grouped flex toolbar, original CSS | `InputText`/`InputNumber`/`Select`, nested `Card`, `Slider` |
| Log summary cards | Plain white cards + inline stats row | `Card` with `<template #title>` + `Tag` per metric |
| Inspector panel | Fixed-position panel, original CSS | `Dialog` or `OverlayPanel` |
| Plotly specs | Identical | Identical (Variant A optionally swaps paper/font colors on dark mode) |
| Dark mode | Partial (PrimeVue chrome works; custom CSS is light-only) | Full |
| Copy-to-translate ratio | ~60% copy, ~40% Vue wrapping | ~25% copy, ~75% rewrite |

Feature parity is identical on both branches. The divergence is purely presentational.

## 9. Key design decisions

1. **Approach 3 (idiomatic skeleton, lifted algorithms).** Algorithms from the original lift nearly verbatim into composables; components are fresh. Lowest regression risk with a clean Vue shape.
2. **Plotly stays.** `plotly.js-dist-min` (full bundle) is added as a dep and lazy-loaded only on `/falcon` via dynamic `import()`. Chart.js is not used here; Plotly and Chart.js coexist. Bundle cost is absorbed only on this route.
3. **Data-source seam.** `useFalconDataSource` exposes both `loadFromLocalFiles` (v1) and a stub `loadFromServer` (v2). Swapping modes in v2 touches one file, not any component.
4. **Folder picker stays custom.** PrimeVue `FileUpload` lacks `webkitdirectory`. On both branches, `FolderPicker.vue` wraps a native `<input>`.
5. **LD state moves into the store.** Original `FileLoader.ldFiles` was globally mutable; here `tdp.ldFiles` is Pinia-owned.
6. **Cache reset on folder change.** `loadFolder()` calls `resetCaches()` at entry — clears clump colors, trait lookups, LD bin cache. Fixes the "load a second dataset, get stale data" bug the audit flagged.
7. **Gene-trait fetch becomes cancelable.** `fetchTraits` takes an `AbortSignal`; toggling novelty mid-fetch doesn't leak duplicate fetches.
8. **Codetabs proxy preserved for v1.** Since `dig-job-server-2` has no Node server (Nuxt is `ssr: false`, backend is Python), client-side calls to `api.codetabs.com → hugeampkpncms.org` stay as in the original. A new Python endpoint is v2.
9. **Auth stays on.** `/falcon` lives behind the existing `auth.global.js` middleware. No changes to `publicRoutes`.
10. **Strict parity over UX fixes.** Known original quirks (strict filter doesn't affect Summary table; log `totalTime` can NaN under an unparsed suffix) are preserved and flagged for v2.

## 10. Error handling

| Failure | Handling |
|---|---|
| Missing `.wg` files | Status line: "Notice: Missing standard .wg files. FALCON Zoom will still work if trait files exist." |
| Papa.parse error | Console log, dataset stays `isLoaded: false`, status line shows error |
| Log regex misses | Partial parse; log marked loaded anyway (matches original) |
| Clinical trials CSV malformed | `alert("Failed to load clinical trials data.")` |
| Gene-trait fetch fails | Per-gene silent fallback: `isNovel: null`, empty traits |
| LD `.gz` decompression fails | Skip bin, console warn, continue |
| `webkitdirectory` unsupported (Safari) | Feature-detect at `FolderPicker` mount, show "Folder selection requires Chrome/Edge/Firefox" |
| Plotly dynamic import fails | Tab shows "Charts unavailable — reload to retry." |
| Folder change mid-fetch | `AbortSignal` fires on new `loadFolder()`, in-flight fetches drop |

No Sentry/telemetry, no global error boundary, no user-facing retry UI.

## 11. Preserved quirks (v1 parity, v2 fix candidates)

- **Strict filter affects plots but not the Executive Summary table.** A known UX trap in the original.
- **Log total-time NaN.** `parseFloat("1234.56 seconds")` yields `NaN`; masked by a fallback showing the raw string.
- **Gene-trait cache is unbounded, never invalidated.** Reload the page to reset.
- **Novelty fetch has no cancellation in original.** We add an `AbortSignal` — v1 improvement that's invisible to the user.

## 12. Testing

No test framework; documented manual test plan, executed per branch:

1. Upload a FALCON output folder → tabs enable, active-folder pill shows.
2. All six tabs render without console errors.
3. Global filter toggle: plots update; Summary table does not (preserved).
4. Genomic region filter: chromosome pill + BP range rescopes genes scatter.
5. Inspector: click scatter point → panel opens, copy button works.
6. Clinical trials: load `PEGS/src/dashboard/data/clinical_trials.csv` → Summary updates.
7. TDP end-to-end: type `CETP`, load LD folder, Run Analysis → zoom plot renders.
8. Log summary: switch chromosome → histograms rebuild.
9. Data table: sort, search, paginate.
10. Reload with a different dataset → caches reset (new clump colors; no LD leak).
11. Dark mode: toggle from footer — Variant A must pass fully; Variant B partial OK.
12. Auth: logged-out visit to `/falcon` → redirected to `/login`.
13. Sample data: `PEGS/src/dashboard/data/clinical_trials.csv` for test 6; bring your own FALCON folder otherwise.

Both branches must pass tests 1–10 and 12–13 identically. Test 11 is the intentional divergence point.

### 12a. Test fixtures

Fixtures live outside both repos at `~/falcon-fixtures/kp5/`, synced from `s3://falcon-web-data/kp5/`. Never commit this directory.

**Contents (two FALCON output datasets):**

```
~/falcon-fixtures/kp5/
├── T2D/                           # ~195 MiB, 71 files
│   ├── pegs1.wg.genes             # core — Genes tab, Summary, Data Table
│   ├── pegs1.wg.variants          # core — Variants tab, Summary, Data Table
│   ├── pegs1.wg.log               # core — Log Summary tab
│   ├── pegs1.{1..22}.genes        # per-chromosome trait files for TDP tab
│   ├── pegs1.{1..22}.variants     # per-chromosome trait files for TDP tab
│   └── pegs1.{1..22}.v2g          # variant-to-gene map for TDP tab
└── TGnonT2D/                      # ~147 MiB, 70 files
    └── (same structure as T2D)
```

**Which test uses which fixture:**

| Test | Fixture | Notes |
|---|---|---|
| 1, 2, 9 (upload, render all tabs, table ops) | Either `T2D/` or `TGnonT2D/` | Select the whole folder via `FolderPicker` |
| 3 (global filter) | Either | Genes scatter should reveal low-prob points when toggled off |
| 4 (genomic region filter) | Either | 22 chromosomes available |
| 5 (inspector panel) | Either | Click any scatter point |
| 6 (clinical trials) | `PEGS/src/dashboard/data/clinical_trials.csv` | Already in the source repo |
| 7 (TDP zoom) | Either, **plus an LD folder** — see caveat below | Target genes differ by dataset |
| 8 (log summary) | Either `.wg.log` | Multi-chromosome; exercises both the all-chr aggregate and per-chr views |
| 10 (cache reset) | Load `T2D/`, then load `TGnonT2D/` | Verify clump colors reassign, novelty cache clears |

**Caveat — LD files not in this bucket.** `s3://falcon-web-data/kp5/` contains `.wg.genes`, `.wg.variants`, `.wg.log`, and per-chromosome `.genes`/`.variants`/`.v2g` trait files, but **no `.gz` or `.sorted` LD matrices**. Test 7 (TDP end-to-end) requires a separately-supplied LD folder. Until one is provided, validate TDP partially: the Zoom plot can render with trait-only data (plot type `raw` or `overlay`) — only the LD heatmap overlay needs the separate folder.

## 13. Rollout

1. Merge `falcon-port-base` to `main` via PR. `/falcon` (scaffold) reachable behind auth but not useful yet.
2. Merge `falcon-variant-a` and `falcon-variant-b` to `main` (in either order; PRs are independent). Deployed env now has three FALCON routes: `/falcon` (scaffold), `/falcon-a`, `/falcon-b`.
3. Soft-launch: share both variant URLs with pilot reviewers for comparison. No header link to either.
4. Pick a winner based on pilot feedback.
5. Merge `falcon-cleanup` — deletes the loser's `pages/falcon-<loser>/` + `components/falcon-<loser>/`. Optionally renames winner's path to `/falcon` (consolidating), replacing the old scaffold page.
6. (Optional v2 follow-up) add a header nav link once the winner has been used in the wild for a bit.

## 14. Future work (v2 candidates)

- Migrate `useGeneTraitFetcher` to a new Python backend endpoint; remove the codetabs dependency.
- Fix strict-filter / Summary-table inconsistency.
- Server-backed dataset mode via `useFalconDataSource.loadFromServer(datasetId)`.
- Header link and `publicRoutes` adjustment after pilot validation.
- Introduce a frontend test framework (Vitest) and at least smoke tests for the viewer.
- CSV download button on the data table.
- Cache eviction / explicit "clear" button for LD and trait caches.

## 15. Risks

- **Plotly bundle size.** `plotly.js-dist-min` is ~3.6 MB. Mitigated by route-only lazy import. Verify network tab on `/falcon` first-load during testing.
- **`webkitdirectory` browser variance.** Safari has historically been inconsistent; the feature-detect fallback at `FolderPicker` mount surfaces this cleanly rather than silently breaking.
- **Codetabs proxy reliability.** Third-party proxy outages will silently fail novelty lookups. Accepted for v1; tracked in Future Work.
- **Branch drift.** Base changes merged late will need re-basing into both branches. Mitigation: keep base small and stable; don't add features to base after fork.
- **Parity audit on branches.** Both branches must stay aligned on behavior tests (1–10, 12–13). Easy to miss a behavior regression when rewriting a component. Mitigation: side-by-side manual walk-through before picking a winner.
