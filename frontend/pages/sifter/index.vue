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
const recombination = ref([]);
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

watch(guid, () => {
  searchRegion.value = null;
  rows.value = [];
  genes.value = [];
  recombination.value = [];
  refRow.value = null;
  status.value = null;
  error.value = "";
});

async function loadRegion(region, ldRefRow = null) {
  const baseUrl = config.public.bioindexUrl;
  if (!baseUrl) throw new Error("NUXT_PUBLIC_BIOINDEX_URL is not configured");
  const out = await loader.load({
    baseUrl, guid: guid.value, region, ancestry: ancestry.value, refRow: ldRefRow,
  });
  rows.value = out.rows;
  genes.value = out.genes;
  recombination.value = out.recombination;
  refRow.value = ldRefRow || out.refRow;
  status.value = out.status;
}

async function search() {
  error.value = "";
  busy.value = true;
  try {
    const region = await resolver.resolve(regionInput.value, expandBp.value);
    searchRegion.value = region;
    regionZoom.value = 0;
    await loadRegion(region);
  } catch (e) {
    error.value = e.message;
    rows.value = [];
  } finally {
    busy.value = false;
  }
}

async function setLdReference(row) {
  selectedRow.value = null;
  busy.value = true;
  try {
    await loadRegion(searchRegion.value, row);
  } finally {
    busy.value = false;
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
