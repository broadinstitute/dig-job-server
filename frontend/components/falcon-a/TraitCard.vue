<template>
  <Panel :toggleable="true" :collapsed="collapsed" class="mb-2">
    <template #header>
      <div class="flex items-center gap-3 w-full">
        <span class="font-semibold text-gray-900 dark:text-gray-100">{{
          row.name
        }}</span>
        <Tag :value="`Clump ${row.clumpId}`" severity="info" />
        <Tag v-if="row.isLead" value="⭐ Lead" severity="warning" />
        <Tag v-if="row.isNovel === false" value="Known" severity="secondary" />
        <Tag v-if="row.isNovel === true" value="Novel" severity="success" />
        <span class="text-xs text-gray-500 dark:text-gray-400 ml-auto">
          Chr {{ row.chr }} · Prob {{ row.prob.toFixed(3) }} · NegP
          {{ row.negP.toFixed(2) }}
        </span>
      </div>
    </template>

    <div v-if="row.traits?.length" class="mb-3">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
        Associated traits
      </h4>
      <ul class="text-xs space-y-1 list-disc list-inside">
        <li v-for="(t, i) in row.traits" :key="i">
          <span class="font-mono">{{ t.Trait || t.trait || '—' }}</span>
          <span v-if="t.Citation || t.citation" class="text-gray-500">
            ({{ t.Citation || t.citation }})
          </span>
        </li>
      </ul>
    </div>

    <div v-if="row.clinicalTrials?.length">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
        Clinical trials
      </h4>
      <ul class="text-xs space-y-1">
        <li v-for="(t, i) in row.clinicalTrials" :key="i">
          <span class="font-mono">{{ t.drugId }}</span>
          · {{ t.indication }} ·
          <Tag :value="`Phase ${t.phase}`" severity="info" class="ml-1" />
        </li>
      </ul>
    </div>

    <div
      v-if="!row.traits?.length && !row.clinicalTrials?.length"
      class="text-xs text-gray-500 dark:text-gray-400"
    >
      No trait or trial data.
    </div>
  </Panel>
</template>

<script setup>
defineProps({
  row: { type: Object, required: true },
  collapsed: { type: Boolean, default: true },
});
</script>
