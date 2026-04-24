<template>
  <div>
    <h3 class="tdp-title">FALCON Zoom & LD Correlation</h3>
    <p class="tdp-hint">
      To apply the global filters the plot needs to be reloaded.
    </p>

    <div class="tdp-toolbar">
      <div class="input-group">
        <label>Target Gene</label>
        <input v-model="cfg.gene" type="text" placeholder="e.g., CETP" />
      </div>
      <div class="input-group">
        <label>Boundary (BP)</label>
        <input v-model.number="cfg.boundary" type="number" step="50000" />
      </div>
      <div class="input-group">
        <label>Focus</label>
        <select v-model="cfg.focus">
          <option value="region">Region</option>
          <option value="gene">Gene Only</option>
        </select>
      </div>
      <div class="input-group">
        <label>Plot Type</label>
        <select v-model="cfg.plotType">
          <option value="falcon">FALCON</option>
          <option value="raw">Raw input</option>
          <option value="overlay">Overlay</option>
        </select>
      </div>

      <div class="toolbar-divider" />

      <div class="input-group">
        <label class="ld-label">LD Matrix (.gz or .sorted files)</label>
        <div class="ld-row">
          <button class="ld-btn" @click="triggerLdDialog">
            📁 {{ store.tdp.ldFolderName || 'Load LD Folder' }}
          </button>
          <input
            ref="ldInput"
            type="file"
            webkitdirectory
            directory
            class="hidden"
            @change="onLdChange"
          />
          <span class="divider-v" />
          <label>Min R²</label>
          <input
            v-model.number="cfg.minR2"
            type="number"
            min="0"
            max="1"
            step="0.1"
            class="mini-input"
          />
          <span class="divider-v" />
          <label>Max Stretch</label>
          <input
            v-model.number="cfg.maxStretch"
            type="range"
            min="0.1"
            max="1"
            step="0.05"
            class="stretch-range"
          />
        </div>
      </div>

      <div class="toolbar-spacer" />
      <button
        class="run-btn"
        :disabled="running || !cfg.gene"
        @click="run"
      >
        {{ running ? 'Running…' : 'Run Analysis' }}
      </button>
    </div>

    <div v-if="store.tdp.status" class="tdp-status">
      {{ store.tdp.status }}
    </div>

    <div ref="plotEl" class="tdp-plot" />
  </div>
</template>

<script setup>
import { reactive, ref, onBeforeUnmount } from 'vue';
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

function triggerLdDialog() { ldInput.value?.click(); }
async function onLdChange(e) { await store.loadLdFolder(e.target.files); }

onBeforeUnmount(async () => {
  if (mountedEl) await unmount(mountedEl);
});
</script>

<style scoped>
.tdp-title {
  font-size: 1.25em;
  font-weight: 700;
  color: #111827;
  margin-bottom: 8px;
}
.tdp-hint {
  font-size: 0.85em;
  color: #6b7280;
  margin-bottom: 15px;
}
.tdp-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  background: #f9fafb;
  padding: 15px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  align-items: center;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.input-group > label {
  font-size: 0.8em;
  font-weight: bold;
  color: #4b5563;
}
.input-group input[type='text'],
.input-group input[type='number'],
.input-group select {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
}
.toolbar-divider {
  width: 0;
  border-left: 2px dashed #d1d5db;
  height: 40px;
  margin: 0 5px;
}
.ld-label { color: #2563eb; font-weight: bold; }
.ld-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ld-btn {
  padding: 6px 12px;
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #93c5fd;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}
.ld-btn:hover { background: #dbeafe; }
.divider-v {
  width: 0;
  border-left: 1px solid #d1d5db;
  height: 20px;
}
.mini-input {
  width: 50px;
  padding: 4px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}
.stretch-range { width: 80px; }
.toolbar-spacer { flex: 1; }
.run-btn {
  padding: 10px 20px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}
.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tdp-status {
  margin-bottom: 15px;
  color: #3b82f6;
  font-weight: bold;
}
.tdp-plot {
  width: 100%;
  height: 850px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
}
.hidden { display: none; }
</style>
