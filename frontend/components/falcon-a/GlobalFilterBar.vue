<template>
  <Card>
    <template #content>
      <Fieldset legend="Global Filters" :toggleable="false" class="!p-0">
        <div class="flex flex-wrap items-center gap-4 py-1">
          <ToggleButton
            v-model="store.globalFilter.active"
            on-label="Strict Filter: ON"
            off-label="Strict Filter: OFF"
            on-icon="pi pi-filter"
            off-icon="pi pi-filter-slash"
          />
          <div class="flex items-center gap-2">
            <label
              for="gf-min-prob"
              class="text-xs font-semibold text-gray-600 dark:text-gray-300"
              >Min Prob</label
            >
            <InputNumber
              id="gf-min-prob"
              v-model="store.globalFilter.minProb"
              :min="0"
              :max="1"
              :step="0.01"
              :min-fraction-digits="2"
              :max-fraction-digits="4"
              show-buttons
              button-layout="horizontal"
              class="w-40"
            />
          </div>
          <div class="flex items-center gap-2">
            <label
              for="gf-min-negp"
              class="text-xs font-semibold text-gray-600 dark:text-gray-300"
              >Min NegP</label
            >
            <InputNumber
              id="gf-min-negp"
              v-model="store.globalFilter.minNegP"
              :min="0"
              :step="0.5"
              :min-fraction-digits="1"
              :max-fraction-digits="2"
              show-buttons
              button-layout="horizontal"
              class="w-40"
            />
          </div>
        </div>
      </Fieldset>
    </template>
  </Card>
</template>

<script setup>
import { useFalconStore } from '~/stores/FalconStore';
const store = useFalconStore();
</script>
