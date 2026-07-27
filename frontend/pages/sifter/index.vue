<script setup>
import { ref, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { createSifterRegionResolver } from "~/composables/useSifterRegion";
import { createSifterLoader } from "~/composables/useSifterData";
import { computeVisibleRegion } from "~/utils/sifter/regionZoom";
import { formatRegion } from "~/utils/sifter/searchUtils";

const route = useRoute();
const config = useRuntimeConfig();

const dataset = computed(() => route.query.dataset || "");
const guid = computed(() => route.query.guid || "");
const ancestry = computed(() => route.query.ancestry || null);

const regionInput = ref("");
const expandBp = ref(null); // matches REGION_EXPAND_OPTIONS' "bounds only" value
const regionZoom = ref(0);
const searchRegion = ref(null);
const rows = ref([]);
const genes = ref([]);
const recombination = ref(null);
const refRow = ref(null);
const status = ref(null);
const busy = ref(false);
const error = ref("");
const selectedRow = ref(null);

const resolver = createSifterRegionResolver();
const loader = createSifterLoader();

const visibleRegion = computed(() =>
  searchRegion.value ? computeVisibleRegion(searchRegion.value, regionZoom.value, 0) : null,
);

// UX heuristic only — NOT a hard limit. The LD service itself caps at 100,000
// variants; this is just the point past which the browser visibly struggles,
// so we warn (without throttling, truncating, or blocking rendering).
const LARGE_REGION_ROW_WARNING = 5000;
const largeRegionWarning = computed(() => rows.value.length > LARGE_REGION_ROW_WARNING);

// Request-sequence token: guards against overlapping searches/LD-reference
// changes resolving out of order. Every call that mutates view state via
// loadRegion() captures the counter's value *before* its own async work
// starts; if the counter has moved on by the time that work resolves, a
// newer call has already started (or finished) and this result is stale, so
// it's discarded instead of overwriting the newer state.
let requestSeq = 0;

watch(guid, () => {
  requestSeq++; // invalidate any in-flight load from the previous dataset
  searchRegion.value = null;
  rows.value = [];
  genes.value = [];
  recombination.value = null;
  refRow.value = null;
  status.value = null;
  error.value = "";
});

async function loadRegion(region, ldRefRow, seq) {
  const baseUrl = config.public.bioindexUrl;
  if (!baseUrl) throw new Error("NUXT_PUBLIC_BIOINDEX_URL is not configured");
  const out = await loader.load({
    baseUrl, guid: guid.value, region, ancestry: ancestry.value, refRow: ldRefRow,
  });
  if (seq !== requestSeq) return; // superseded by a newer load; discard stale result
  rows.value = out.rows;
  genes.value = out.genes;
  recombination.value = out.recombination;
  // The loader already resolves explicitRef || pickLeadVariantRow internally,
  // so out.refRow already reflects ldRefRow when one was passed.
  refRow.value = out.refRow;
  status.value = out.status;
}

async function search() {
  const seq = ++requestSeq;
  error.value = "";
  busy.value = true;
  try {
    const region = await resolver.resolve(regionInput.value, expandBp.value);
    if (seq !== requestSeq) return; // superseded while resolving the region
    searchRegion.value = region;
    regionZoom.value = 0;
    await loadRegion(region, null, seq);
  } catch (e) {
    if (seq !== requestSeq) return; // superseded; don't clobber a newer search's state
    error.value = e.message;
    // Clear all view state, not just rows — otherwise the header/plot/table
    // context left over from a previous successful search (searchRegion,
    // genes, recombination, refRow, status) keeps describing the OLD region
    // while the error banner describes the NEW, failed one.
    searchRegion.value = null;
    rows.value = [];
    genes.value = [];
    recombination.value = null;
    refRow.value = null;
    status.value = null;
  } finally {
    if (seq === requestSeq) busy.value = false;
  }
}

async function setLdReference(row) {
  selectedRow.value = null;
  const seq = ++requestSeq;
  busy.value = true;
  try {
    await loadRegion(searchRegion.value, row, seq);
  } finally {
    if (seq === requestSeq) busy.value = false;
  }
}
</script>

<template>
  <div class="p-4">
    <div class="mb-3 flex flex-wrap items-baseline gap-3">
      <h1 class="text-xl font-semibold">{{ dataset || "Variant Sifter" }}</h1>
      <span v-if="searchRegion" class="text-sm text-surface-500">
        {{ formatRegion(visibleRegion) }}
      </span>
    </div>

    <SifterRegionControls
      v-model="regionInput"
      v-model:expand-bp="expandBp"
      v-model:region-zoom="regionZoom"
      :busy="busy"
      @search="search"
    />

    <Message v-if="error" severity="error" class="mb-3">{{ error }}</Message>

    <Message v-if="status && status.ld === 'failed'" severity="warn" class="mb-3">
      LD scores unavailable — variants are shown without LD colouring.
    </Message>
    <Message v-if="largeRegionWarning" severity="warn" class="mb-3">
      This region returned a very large number of variants ({{ rows.length }}). Narrowing the region
      will be faster.
    </Message>
    <!--
      Deliberately NO "gene track unavailable" banner. fetchGenesTrackData
      swallows its own errors and returns [], and a region legitimately having no
      genes is indistinguishable from a failed fetch at this layer — so such a
      banner could never fire reliably and would be dead, misleading code.
      An empty gene track is self-evident on screen.
    -->

    <template v-if="visibleRegion && rows.length">
      <h2 class="mb-1 text-lg font-semibold">Associations</h2>
      <SifterAssociationsPlot
        :rows="rows"
        :visible-region="visibleRegion"
        :ref-row="refRow"
        :recombination="recombination"
        class="mb-2"
        @select-variant="selectedRow = $event"
      />
      <SifterGenesTrack :genes="genes" :visible-region="visibleRegion" class="mb-4" />
      <SifterAssociationsTable :rows="rows" />
    </template>

    <div v-else-if="!busy && !error" class="text-surface-500">
      Enter a region or gene to view associations.
    </div>

    <SifterVariantMenu
      :row="selectedRow"
      :visible="!!selectedRow"
      @set-ld-reference="setLdReference"
      @close="selectedRow = null"
    />
  </div>
</template>
