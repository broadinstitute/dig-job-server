<template>
  <div class="filter-card">
    <div class="filter-header">
      <h4><span style="font-size: 1.2em">🧬</span> Genomic Region Filter</h4>
      <button
        v-if="selectedChr !== 'All'"
        class="reset-btn"
        @click="reset"
      >
        Reset to All Chromosomes
      </button>
    </div>
    <div class="filter-body">
      <p class="filter-hint">Select a Chromosome:</p>
      <div class="chr-grid">
        <button
          v-for="opt in chrOptions"
          :key="opt.value"
          class="chr-btn"
          :class="{ active: selectedChr === opt.value }"
          @click="selectedChr = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>

      <div
        v-if="selectedChr !== 'All' && currentBounds"
        class="region-selector"
      >
        <p class="filter-hint">Select Base Pair Range:</p>
        <div class="range-slider">
          <div class="slider-track" />
          <div
            class="slider-range"
            :style="{
              left: rangePercent(0) + '%',
              width: rangeWidthPercent() + '%',
            }"
          />
          <input
            type="range"
            :min="currentBounds.min"
            :max="currentBounds.max"
            :step="bpStep"
            :value="bpRange[0]"
            @input="onLowInput($event)"
          />
          <input
            type="range"
            :min="currentBounds.min"
            :max="currentBounds.max"
            :step="bpStep"
            :value="bpRange[1]"
            @input="onHighInput($event)"
          />
        </div>
        <div class="region-inputs">
          <div class="input-group">
            <label>Start BP</label>
            <input
              type="number"
              :min="currentBounds.min"
              :max="bpRange[1]"
              :value="bpRange[0]"
              @blur="onStartBlur"
            />
          </div>
          <div class="input-group">
            <label>End BP</label>
            <input
              type="number"
              :min="bpRange[0]"
              :max="currentBounds.max"
              :value="bpRange[1]"
              @blur="onEndBlur"
            />
          </div>
          <button class="apply-btn" @click="applyRange">Apply Range</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();

const chrBounds = computed(() => {
  const bounds = new Map();
  for (const row of store.datasets.genes.data) {
    const chr = row.CHR ? String(row.CHR).trim() : '';
    if (!chr) continue;
    const s = parseFloat(row.START);
    const e = parseFloat(row.END);
    if (isNaN(s) && isNaN(e)) continue;
    const b = bounds.get(chr) || { min: Infinity, max: -Infinity };
    if (!isNaN(s)) b.min = Math.min(b.min, s);
    if (!isNaN(e)) b.max = Math.max(b.max, e);
    bounds.set(chr, b);
  }
  return bounds;
});

const chrOptions = computed(() => {
  const chrs = Array.from(chrBounds.value.keys()).sort((a, b) => {
    const na = parseInt(a, 10);
    const nb = parseInt(b, 10);
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    return a.localeCompare(b);
  });
  return [
    { value: 'All', label: 'All' },
    ...chrs.map((c) => ({ value: c, label: c })),
  ];
});

const selectedChr = ref(store.plotFilters.genes.chr || 'All');
const currentBounds = computed(() =>
  selectedChr.value === 'All' ? null : chrBounds.value.get(selectedChr.value),
);

const bpRange = ref([0, 0]);
const bpStep = computed(() => {
  if (!currentBounds.value) return 1;
  const span = currentBounds.value.max - currentBounds.value.min;
  return Math.max(1, Math.round(span / 1000));
});

watch(
  currentBounds,
  (b) => {
    if (!b) return;
    bpRange.value = [b.min, b.max];
    applyRange();
  },
  { immediate: true },
);

watch(selectedChr, (chr) => {
  store.plotFilters.genes.chr = chr;
  if (chr === 'All') {
    store.plotFilters.genes.minStart = null;
    store.plotFilters.genes.maxEnd = null;
  }
});

function onLowInput(e) {
  const v = Number(e.target.value);
  bpRange.value = [Math.min(v, bpRange.value[1]), bpRange.value[1]];
  applyRange();
}
function onHighInput(e) {
  const v = Number(e.target.value);
  bpRange.value = [bpRange.value[0], Math.max(v, bpRange.value[0])];
  applyRange();
}
function onStartBlur(e) {
  bpRange.value = [Number(e.target.value), bpRange.value[1]];
  applyRange();
}
function onEndBlur(e) {
  bpRange.value = [bpRange.value[0], Number(e.target.value)];
  applyRange();
}
function rangePercent(idx) {
  if (!currentBounds.value) return 0;
  const { min, max } = currentBounds.value;
  return ((bpRange.value[idx] - min) / (max - min)) * 100;
}
function rangeWidthPercent() {
  return rangePercent(1) - rangePercent(0);
}
function applyRange() {
  if (!currentBounds.value) return;
  store.plotFilters.genes.minStart = bpRange.value[0];
  store.plotFilters.genes.maxEnd = bpRange.value[1];
}
function reset() {
  selectedChr.value = 'All';
}
</script>

<style scoped>
/* Lifted from PEGS styles.css:55-110 */
.filter-card {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}
.filter-header {
  padding: 12px 20px;
  background: #f9fafb;
  border-bottom: 1px solid #d1d5db;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-header h4 {
  margin: 0;
  color: #111827;
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-body {
  padding: 20px;
  transition: all 0.3s ease;
}
.filter-hint {
  margin: 0 0 10px 0;
  font-size: 0.9em;
  color: #4b5563;
}
.reset-btn {
  padding: 4px 10px;
  font-size: 0.8em;
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #f87171;
  border-radius: 4px;
  cursor: pointer;
  transition: 0.2s;
}
.reset-btn:hover {
  background: #fecaca;
}
.chr-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.chr-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  color: #4b5563;
  transition: all 0.2s ease;
}
.chr-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}
.chr-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}
.region-selector {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed #d1d5db;
  animation: fadeInDown 0.4s ease forwards;
}
@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.range-slider {
  position: relative;
  width: 100%;
  height: 40px;
}
.slider-track {
  position: absolute;
  width: 100%;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
}
.slider-range {
  position: absolute;
  height: 6px;
  background: #3b82f6;
  border-radius: 3px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
}
.range-slider input[type='range'] {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  -webkit-appearance: none;
  background: transparent;
  pointer-events: none;
  z-index: 3;
  margin: 0;
}
.range-slider input[type='range']::-webkit-slider-thumb {
  pointer-events: auto;
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  border: 2px solid #3b82f6;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  cursor: grab;
}
.range-slider input[type='range']::-webkit-slider-thumb:active {
  cursor: grabbing;
  background: #3b82f6;
}
.region-inputs {
  display: flex;
  gap: 15px;
  align-items: flex-end;
  margin-top: 15px;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.input-group label {
  font-size: 0.8em;
  font-weight: bold;
  color: #4b5563;
}
.input-group input {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-family: monospace;
}
.apply-btn {
  padding: 8px 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  height: fit-content;
}
.apply-btn:hover {
  background: #2563eb;
}
</style>
