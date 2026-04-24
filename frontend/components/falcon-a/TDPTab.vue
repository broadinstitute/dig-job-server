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
            <InputNumber
              v-model="cfg.boundary"
              :min="1000"
              :step="50000"
              :use-grouping="true"
            />
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
                <label class="text-xs font-semibold"
                  >LD Folder (.gz / .sorted)</label
                >
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
                <label class="text-xs font-semibold"
                  >Max Stretch: {{ cfg.maxStretch.toFixed(2) }}</label
                >
                <Slider
                  v-model="cfg.maxStretch"
                  :min="0.1"
                  :max="1"
                  :step="0.05"
                />
              </div>
            </div>
          </template>
        </Card>

        <div class="flex items-center justify-between mt-4">
          <p
            v-if="store.tdp.status"
            class="text-sm text-primary-600 dark:text-primary-400 font-semibold"
          >
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

    <div
      class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded p-2"
    >
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
