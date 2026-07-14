<template>
  <div class="p-6 space-y-4">
    <Card>
      <template #title>Variant Sifter{{ dataset ? ` — ${dataset}` : "" }}</template>
      <template #content>
        <div v-if="!guid" class="text-red-600">
          Missing dataset id. Open this view from the datasets table.
        </div>
        <div v-else>
          <div class="flex items-end gap-2 mb-4">
            <div class="flex-1">
              <label class="block text-sm mb-1">Region or gene</label>
              <InputText
                v-model="regionInput"
                placeholder="e.g. 10:100000-200000 or TCF7L2"
                class="w-full"
                @keydown.enter="runQuery"
              />
            </div>
            <Button label="Search" icon="pi pi-search" :loading="loading" @click="runQuery" />
          </div>

          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <div v-else-if="loading" class="p-4"><Skeleton height="20rem" /></div>
          <div v-else-if="queried">
            <SifterRegionPlot :records="records" :region="region" class="mb-4" />
            <SifterAssociationsTable :records="records" />
          </div>
          <div v-else class="text-gray-500 p-4">
            Enter a region or gene to view associations.
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useBioindex } from "~/composables/useBioindex";

const route = useRoute();
const dataset = route.query.dataset || "";
const guid = route.query.guid || "";
const { queryAssociations } = useBioindex();

const regionInput = ref("");
const region = ref("");
const records = ref([]);
const loading = ref(false);
const error = ref("");
const queried = ref(false);

async function runQuery() {
  const r = regionInput.value.trim();
  if (!r) {
    error.value = "Enter a region (e.g. 10:100000-200000) or a gene name.";
    return;
  }
  error.value = "";
  loading.value = true;
  try {
    const raw = await queryAssociations({ guid, region: r });
    records.value = raw.map((rec, i) => ({ ...rec, id: i }));
    region.value = r;
    queried.value = true;
  } catch (e) {
    error.value = e.message || "Query failed.";
  } finally {
    loading.value = false;
  }
}
</script>
