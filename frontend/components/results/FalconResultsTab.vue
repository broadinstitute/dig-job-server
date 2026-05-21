<template>
  <div class="space-y-4">
    <p v-if="store.status" class="text-sm text-gray-500">{{ store.status }}</p>

    <GlobalFilterBar v-if="store.datasets.genes.isLoaded || store.datasets.variants.isLoaded" />

    <Tabs :value="subTab" @update:value="onSubTabChange">
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
        <TabPanel value="summary" :lazy="true">
          <ExecutiveSummaryTab v-if="store.datasets.genes.isLoaded" />
          <Empty v-else reason="Loading executive summary..." />
        </TabPanel>
        <TabPanel value="tdp" :lazy="true"><TDPTab /></TabPanel>
        <TabPanel value="genes" :lazy="true">
          <GenesScatterTab v-if="store.datasets.genes.isLoaded" />
          <Empty v-else reason="Loading genes plot..." />
        </TabPanel>
        <TabPanel value="variants" :lazy="true">
          <VariantsScatterTab v-if="store.datasets.variants.isLoaded" />
          <Empty v-else reason="Loading variants plot..." />
        </TabPanel>
        <TabPanel value="table" :lazy="true">
          <DataTableTab v-if="store.datasets.genes.isLoaded" />
          <Empty v-else reason="Loading tables..." />
        </TabPanel>
        <TabPanel value="log" :lazy="true">
          <LogSummaryTab v-if="store.datasets.log.isLoaded" />
          <Empty v-else reason="Loading log..." />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <DataInspectorPanel ref="inspectorRef" />
  </div>
</template>

<script setup>
import { h, ref, provide, watch, onMounted } from "vue";
import { useFalconStore } from "~/stores/FalconStore";

const props = defineProps({ dataset: { type: String, required: true } });

const store = useFalconStore();
const inspectorRef = ref(null);
provide("falcon-inspector", inspectorRef);

const subTab = ref("summary");
function onSubTabChange(next) {
  if (next) subTab.value = next;
}

const Empty = (p) =>
  h("p", { class: "text-sm text-gray-500 dark:text-gray-400 py-6" }, p.reason || "No data yet.");
Empty.props = ["reason"];

onMounted(async () => {
  await store.loadFromDataset(props.dataset);
});

watch(() => props.dataset, async (next, prev) => {
  if (next && next !== prev) await store.loadFromDataset(next);
});
</script>
