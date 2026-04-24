<template>
  <div
    class="flex flex-wrap items-center gap-4 py-2 px-3 border rounded bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700"
  >
    <ToggleButton
      v-model="store.globalFilter.active"
      on-label="Strict Filter: ON"
      off-label="Strict Filter: OFF"
      on-icon="pi pi-filter"
      off-icon="pi pi-filter-slash"
    />
    <div class="flex items-center gap-2">
      <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Min Prob</label>
      <InputNumber
        v-model="store.globalFilter.minProb"
        :min="0"
        :max="1"
        :step="0.01"
        :min-fraction-digits="2"
        :max-fraction-digits="4"
        show-buttons
        button-layout="horizontal"
        class="w-36"
      />
    </div>
    <div class="flex items-center gap-2">
      <label class="text-xs font-semibold text-gray-600 dark:text-gray-300">Min NegP</label>
      <InputNumber
        v-model="store.globalFilter.minNegP"
        :min="0"
        :step="0.5"
        :min-fraction-digits="1"
        :max-fraction-digits="2"
        show-buttons
        button-layout="horizontal"
        class="w-36"
      />
    </div>
  </div>
</template>

<script setup>
import { useFalconStore } from '~/stores/FalconStore';
const store = useFalconStore();
</script>
