// Single source of truth for the FALCON viewer. See
// docs/superpowers/specs/2026-04-24-falcon-dashboard-port-to-vue3-design.md §5.
//
// State is partitioned so that loading a new folder resets only the data and
// caches — user-controlled filter settings persist across reloads.
import { defineStore } from "pinia";
import { reactive, ref } from "vue";

export const useFalconStore = defineStore("falcon", () => {
  // ─── loaded datasets ───
  const datasets = reactive({
    genes: { data: [], columns: [], isLoaded: false },
    variants: { data: [], columns: [], isLoaded: false },
    // cS2G variant→gene evidence (per-chromosome `<base>.<chr>.v2g`), loaded
    // from S3 alongside genes/variants and consumed by the TDP zoom.
    v2g: { data: [], columns: [], isLoaded: false },
    log: {
      data: {}, // Record<chr, Record<component, number[]>>
      preProcess: {}, // Record<chr, Record<step, number>>
      chromosomes: new Set(),
      totalTime: "Not Found / Incomplete Run",
      isLoaded: false,
    },
  });

  const folderName = ref("");
  const status = ref("");

  // ─── global filters ───
  const globalFilter = reactive({
    active: true,
    minProb: 0.1,
    minNegP: 8,
  });

  // ─── per-dataset table state ───
  const tableStates = reactive({
    genes: { searchQuery: "", sortCol: null, sortAsc: true, currentPage: 1 },
    variants: { searchQuery: "", sortCol: null, sortAsc: true, currentPage: 1 },
  });

  // ─── per-plot genomic region filter ───
  const plotFilters = reactive({
    genes: { chr: "All", minStart: null, maxEnd: null },
    variants: { chr: "All", minStart: null, maxEnd: null },
  });

  const clinicalTrials = reactive({ isLoaded: false, byGene: {} });

  const tdp = reactive({
    ldFiles: [],
    ldFolderName: "",
    lastAnalysis: null,
    status: "",
  });

  // ─── caches that reset on every new folder load ───
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
    datasets.v2g.data = [];
    datasets.v2g.columns = [];
    datasets.v2g.isLoaded = false;
    datasets.log.data = {};
    datasets.log.preProcess = {};
    datasets.log.chromosomes = new Set();
    datasets.log.totalTime = "Not Found / Incomplete Run";
    datasets.log.isLoaded = false;
  }

  async function loadFromDataset(dataset) {
    const { useFalconDataSource } = await import("~/composables/useFalconDataSource");
    const source = useFalconDataSource(useFalconStore());
    await source.loadFromServer(dataset);
  }

  async function loadLdFolder(files) {
    const arr = Array.from(files);
    tdp.ldFiles = arr;
    tdp.ldFolderName = arr[0]?.webkitRelativePath?.split("/")[0] || "(ld folder)";
  }

  // Lazily fetch the (large) v2g dataset the first time the TDP zoom needs it.
  // No-op once loaded, or when no dataset has been loaded from S3.
  async function ensureV2gLoaded() {
    if (datasets.v2g.isLoaded || !folderName.value) return;
    const { useFalconDataSource } = await import("~/composables/useFalconDataSource");
    const source = useFalconDataSource(useFalconStore());
    await source.loadV2g(folderName.value);
  }

  return {
    datasets,
    folderName,
    status,
    globalFilter,
    tableStates,
    plotFilters,
    clinicalTrials,
    tdp,
    caches,
    resetCaches,
    resetDatasets,
    loadFromDataset,
    loadLdFolder,
    ensureV2gLoaded,
  };
});