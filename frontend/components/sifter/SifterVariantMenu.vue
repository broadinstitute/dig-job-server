<script setup>
import { computed } from "vue";
import variantUtils from "~/utils/sifter/_portal/variantUtils";

const props = defineProps({
  row: { type: Object, default: null },
  visible: { type: Boolean, default: false },
});
defineEmits(["set-ld-reference", "close"]);

// Rows arriving here are decorated (Task 3B), so they already carry a
// "Variant ID" built by upstream's own join rules. Prefer it over recomputing,
// which would duplicate that logic and could silently drift from it.
const variantId = computed(() => {
  const row = props.row;
  if (!row) return "";
  if (row["Variant ID"]) return row["Variant ID"];
  return variantUtils.gaitVariant(
    `${row.chromosome}:${row.position}:${row.reference}:${row.alt}`,
  );
});

// LD enrichment writes `LDS`, not `ldScore`. Reading the wrong name means the
// r-squared row silently never renders.
const ldScore = computed(() => {
  const value = props.row?.LDS;
  return value == null ? null : Number(value);
});
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :header="variantId"
    :style="{ width: '24rem' }"
    @update:visible="$emit('close')"
  >
    <dl v-if="row" class="mb-4 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
      <dt class="font-semibold">P-Value</dt><dd>{{ row.pValue }}</dd>
      <dt class="font-semibold">Beta</dt><dd>{{ row.beta }}</dd>
      <template v-if="ldScore != null">
        <dt class="font-semibold">r²</dt><dd>{{ ldScore.toFixed(3) }}</dd>
      </template>
    </dl>
    <Button label="Set as LD reference" class="w-full" @click="$emit('set-ld-reference', row)" />
  </Dialog>
</template>
