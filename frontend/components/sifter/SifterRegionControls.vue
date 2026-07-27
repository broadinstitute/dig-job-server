<script setup>
import { REGION_EXPAND_OPTIONS } from "~/utils/sifter/searchUtils";
import { VKS_REGION_ZOOM_MIN, VKS_REGION_ZOOM_MAX } from "~/utils/sifter/regionZoom";

defineProps({
  modelValue: { type: String, default: "" },
  // REGION_EXPAND_OPTIONS' "bounds only" entry has value null, not 0. Defaulting
  // to 0 leaves the Select with nothing selected on load.
  expandBp: { type: Number, default: null },
  regionZoom: { type: Number, default: 0 },
  busy: { type: Boolean, default: false },
});
defineEmits(["update:modelValue", "update:expandBp", "update:regionZoom", "search"]);
</script>

<template>
  <div class="mb-3 flex flex-wrap items-end gap-3">
    <div class="min-w-64 flex-1">
      <label class="mb-1 block text-sm">Region or gene</label>
      <InputText
        :model-value="modelValue"
        placeholder="e.g. 10:114700000-114800000 or TCF7L2"
        class="w-full"
        @update:model-value="$emit('update:modelValue', $event)"
        @keyup.enter="$emit('search')"
      />
    </div>
    <div>
      <label class="mb-1 block text-sm">Region expand</label>
      <Select
        :model-value="expandBp"
        :options="REGION_EXPAND_OPTIONS"
        option-label="label"
        option-value="value"
        @update:model-value="$emit('update:expandBp', $event)"
      />
    </div>
    <div class="min-w-48">
      <label class="mb-1 block text-sm">Region zoom</label>
      <Slider
        :model-value="regionZoom"
        :min="VKS_REGION_ZOOM_MIN"
        :max="VKS_REGION_ZOOM_MAX"
        @update:model-value="$emit('update:regionZoom', $event)"
      />
    </div>
    <Button label="Search" :loading="busy" @click="$emit('search')" />
  </div>
</template>
