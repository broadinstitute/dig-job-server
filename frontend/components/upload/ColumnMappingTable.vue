<script setup>
// The "column from data -> canonical field" table shared by the GWAS upload
// wizard and the credible-set form. Required-field chips are NOT here: each
// host renders its own (the wizard's are composite, e.g. `beta | oddsRatio`).
import { isOptionDisabled, resetMapping, withField } from "~/utils/upload/columnMapping";

const props = defineProps({
    columns: { type: Array, default: () => [] },
    options: { type: Array, required: true }, // [{ name, value }]
    modelValue: { type: Object, required: true }, // { column: field | null }
});
const emit = defineEmits(["update:modelValue"]);

const rows = computed(() => props.columns.map((column) => ({ column })));

function setField(column, value) {
    emit("update:modelValue", withField(props.modelValue, column, value));
}
function reset() {
    emit("update:modelValue", resetMapping(props.columns));
}
</script>

<template>
    <div v-if="columns.length" class="flex">
        <Button
            type="button"
            label="Reset Mapping"
            icon="pi pi-refresh"
            @click="reset"
            severity="help"
            variant="outlined"
            size="small"
        />
    </div>
    <DataTable v-if="columns.length" :value="rows" rowHover class="w-full" responsiveLayout="scroll">
        <Column field="column" header="Column from data" style="width: 35%" />
        <Column header=">>" style="width: 5%" />
        <Column header="Required field" style="width: 60%">
            <template #body="{ data }">
                <Select
                    data-cy="column-dropdown"
                    class="w-full"
                    :options="options"
                    option-label="name"
                    option-value="value"
                    :option-disabled="(option) => isOptionDisabled(modelValue, option.value, data.column)"
                    :model-value="modelValue[data.column] ?? null"
                    @update:model-value="setField(data.column, $event)"
                    showClear
                    placeholder="select field"
                />
            </template>
        </Column>
    </DataTable>
    <div v-else class="p-4 text-center text-gray-500">
        <i class="pi pi-file text-3xl mb-2"></i>
        <p>Upload a file to map columns</p>
    </div>
</template>
