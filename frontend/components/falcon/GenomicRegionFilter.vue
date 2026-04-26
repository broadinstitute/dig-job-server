<template>
  <Card>
    <template #content>
      <Fieldset legend="Genomic Region Filter" :toggleable="true">
        <div class="flex items-center gap-2 mb-3">
          <Button
            v-if="selectedChr !== 'All'"
            icon="pi pi-refresh"
            label="Reset to All Chromosomes"
            severity="danger"
            outlined
            size="small"
            @click="reset"
          />
        </div>

        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
          Select a chromosome:
        </p>
        <SelectButton
          v-model="selectedChr"
          :options="chrOptions"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          class="mb-4 flex-wrap"
        />

        <div v-if="selectedChr !== 'All' && currentBounds" class="space-y-2">
          <p class="text-xs text-gray-500 dark:text-gray-400">
            Select base-pair range:
          </p>
          <Slider
            v-model="bpRange"
            range
            :min="currentBounds.min"
            :max="currentBounds.max"
            :step="bpStep"
            class="mx-2"
            @change="applyRange"
          />
          <div class="flex items-end gap-3">
            <div class="flex flex-col gap-1">
              <label
                class="text-xs font-semibold text-gray-600 dark:text-gray-300"
                >Start BP</label
              >
              <InputNumber
                v-model="bpRange[0]"
                :min="currentBounds.min"
                :max="bpRange[1]"
                :use-grouping="true"
                class="w-40"
                @blur="applyRange"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label
                class="text-xs font-semibold text-gray-600 dark:text-gray-300"
                >End BP</label
              >
              <InputNumber
                v-model="bpRange[1]"
                :min="bpRange[0]"
                :max="currentBounds.max"
                :use-grouping="true"
                class="w-40"
                @blur="applyRange"
              />
            </div>
          </div>
        </div>
      </Fieldset>
    </template>
  </Card>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const props = defineProps({
  dataset: { type: String, default: 'genes' }, // 'genes' | 'variants'
});

const store = useFalconStore();

// Derive per-chromosome bounds from the loaded dataset.
// Genes use START/END (interval); variants use POS (single point).
const chrBounds = computed(() => {
  const bounds = new Map();
  const isVariants = props.dataset === 'variants';
  for (const row of store.datasets[props.dataset].data) {
    const chr = row.CHR ? String(row.CHR).trim() : '';
    if (!chr) continue;
    const b = bounds.get(chr) || { min: Infinity, max: -Infinity };
    if (isVariants) {
      const p = parseFloat(row.POS);
      if (isNaN(p)) continue;
      b.min = Math.min(b.min, p);
      b.max = Math.max(b.max, p);
    } else {
      const s = parseFloat(row.START);
      const e = parseFloat(row.END);
      if (isNaN(s) && isNaN(e)) continue;
      if (!isNaN(s)) b.min = Math.min(b.min, s);
      if (!isNaN(e)) b.max = Math.max(b.max, e);
    }
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

const selectedChr = ref(store.plotFilters[props.dataset].chr || 'All');
const currentBounds = computed(() =>
  selectedChr.value === 'All' ? null : chrBounds.value.get(selectedChr.value),
);

const bpRange = ref([0, 0]);
const bpStep = computed(() => {
  if (!currentBounds.value) return 1;
  const span = currentBounds.value.max - currentBounds.value.min;
  return Math.max(1, Math.round(span / 1000)); // ~1000-step slider resolution
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
  store.plotFilters[props.dataset].chr = chr;
  if (chr === 'All') {
    store.plotFilters[props.dataset].minStart = null;
    store.plotFilters[props.dataset].maxEnd = null;
  }
});

function applyRange() {
  if (!currentBounds.value) return;
  store.plotFilters[props.dataset].minStart = bpRange.value[0];
  store.plotFilters[props.dataset].maxEnd = bpRange.value[1];
}

function reset() {
  selectedChr.value = 'All';
}
</script>
