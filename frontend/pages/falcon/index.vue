<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-6 space-y-4">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold">FALCON Dashboard</h1>
      </div>
      <Tag
        v-if="store.folderName"
        severity="success"
        :value="`Active Dataset: ${store.folderName}`"
      />
    </div>

    <Message
      v-if="!store.folderName"
      severity="info"
      :closable="false"
      class="!my-0"
    >
      <div class="space-y-1">
        <p class="font-semibold">Getting started</p>
        <ol class="list-decimal list-inside text-sm space-y-1">
          <li>
            Run FALCON locally to produce your results — see the
            <!-- TODO: replace sagehen03 with the team namespace when set up -->
            <a
              href="https://hub.docker.com/r/sagehen03/falcon"
              target="_blank"
              rel="noopener noreferrer"
              class="underline font-medium"
            >FALCON image on Docker Hub</a>
            for setup and a worked example.
          </li>
          <li>
            When the run finishes, click <b>Choose Folder</b> below and select
            your <code>results/</code> directory.
          </li>
        </ol>
      </div>
    </Message>

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
        <TabPanel value="summary" :lazy="true">
          <ExecutiveSummaryTab v-if="store.datasets.genes.isLoaded" />
          <EmptyTab v-else reason="Load a folder to see the executive summary." />
        </TabPanel>

        <TabPanel value="tdp" :lazy="true">
          <TDPTab />
        </TabPanel>

        <TabPanel value="genes" :lazy="true">
          <GenesScatterTab v-if="store.datasets.genes.isLoaded" />
          <EmptyTab v-else reason="Load a folder containing .wg.genes." />
        </TabPanel>

        <TabPanel value="variants" :lazy="true">
          <VariantsScatterTab v-if="store.datasets.variants.isLoaded" />
          <EmptyTab v-else reason="Load a folder containing .wg.variants." />
        </TabPanel>

        <TabPanel value="table" :lazy="true">
          <DataTableTab v-if="store.datasets.genes.isLoaded" />
          <EmptyTab v-else reason="Load a folder to browse the raw tables." />
        </TabPanel>

        <TabPanel value="log" :lazy="true">
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

// Local helper — muted empty-state message for tabs until their dataset loads.
const EmptyTab = (props) =>
  h(
    'p',
    { class: 'text-sm text-gray-500 dark:text-gray-400 py-6' },
    props.reason || 'No data yet.',
  );
EmptyTab.props = ['reason'];

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
