<script setup>
import { computed } from "vue";
import { visibleColumns } from "~/utils/sifter/associationsTableFormat";
import { decorateAssociationRows } from "~/utils/sifter/decorateRows";

const props = defineProps({ rows: { type: Array, default: () => [] } });

const decorated = computed(() => decorateAssociationRows(props.rows));
const columns = computed(() => visibleColumns(decorated.value));
</script>

<template>
  <DataTable
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
    />
    <template #empty>No variants in this region.</template>
  </DataTable>
</template>
