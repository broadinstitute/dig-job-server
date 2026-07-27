<script setup>
import { computed, ref, watch } from "vue";
import {
  visibleColumns,
  buildFilterModel,
  NUMERIC_FILTER_FIELDS,
} from "~/utils/sifter/associationsTableFormat";
import { decorateAssociationRows } from "~/utils/sifter/decorateRows";

const props = defineProps({ rows: { type: Array, default: () => [] } });

const decorated = computed(() => decorateAssociationRows(props.rows));
const columns = computed(() => visibleColumns(decorated.value));

// Filters model, kept in lockstep with `columns` (spec §5.1: both are driven
// by field presence in the data). Rebuilt whenever the visible field set
// changes, but merged onto the existing model rather than replaced outright
// so an in-progress filter isn't wiped out by an unrelated data refresh.
// (populated by the immediate watcher below, not here, so buildFilterModel
// isn't run twice on mount)
const filters = ref({});
watch(
  decorated,
  (rows) => {
    const fresh = buildFilterModel(rows);
    const next = {};
    for (const field of Object.keys(fresh)) {
      next[field] = filters.value[field] ?? fresh[field];
    }
    filters.value = next;
  },
  { immediate: true },
);
</script>

<template>
  <DataTable
    v-model:filters="filters"
    :value="decorated"
    :rows="10"
    paginator
    sort-mode="multiple"
    filter-display="menu"
    striped-rows
    size="small"
  >
    <Column
      v-for="col in columns"
      :key="col.field"
      :field="col.field"
      :header="col.header"
      sortable
      :show-filter-match-modes="false"
    >
      <template #filter="{ filterModel, filterCallback }">
        <InputNumber
          v-if="NUMERIC_FILTER_FIELDS.has(col.field)"
          v-model="filterModel.value"
          class="p-column-filter w-full"
          mode="decimal"
          :min-fraction-digits="0"
          :max-fraction-digits="10"
          placeholder="Filter value"
          @input="filterCallback()"
          @keydown.enter="filterCallback()"
        />
        <InputText
          v-else
          v-model="filterModel.value"
          class="p-column-filter w-full"
          placeholder="Filter"
          @input="filterCallback()"
          @keydown.enter="filterCallback()"
        />
      </template>
    </Column>
    <template #empty>No variants in this region.</template>
  </DataTable>
</template>
