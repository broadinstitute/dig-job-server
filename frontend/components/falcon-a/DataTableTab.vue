<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <SelectButton
        v-model="currentDataset"
        :options="datasetOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
      />
      <InputText
        v-model="state.searchQuery"
        placeholder="Search entire table..."
        class="w-64"
      />
    </div>

    <DataTable
      :value="pageRows"
      :lazy="true"
      :paginator="true"
      :rows="rowsPerPage"
      :total-records="filteredCount"
      :first="(state.currentPage - 1) * rowsPerPage"
      @page="onPage"
      @sort="onSort"
      :sort-field="state.sortCol"
      :sort-order="state.sortAsc ? 1 : -1"
      striped-rows
      scrollable
      scroll-height="60vh"
      class="p-datatable-sm"
    >
      <Column
        v-for="col in columns"
        :key="col"
        :field="col"
        :header="col"
        sortable
      />
    </DataTable>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';
import { FALCON_ROWS_PER_PAGE } from '~/utils/falcon/config';

const store = useFalconStore();
const rowsPerPage = FALCON_ROWS_PER_PAGE;

const datasetOptions = [
  { value: 'genes', label: 'Genes' },
  { value: 'variants', label: 'Variants' },
];
const currentDataset = ref('genes');
const state = computed(() => store.tableStates[currentDataset.value]);

const columns = computed(() => store.datasets[currentDataset.value].columns);

const filteredAndSorted = computed(() => {
  const raw = store.datasets[currentDataset.value].data;
  const q = state.value.searchQuery?.toLowerCase();
  let rows = raw;
  if (q) {
    rows = rows.filter((r) =>
      columns.value.some((c) =>
        String(r[c] ?? '')
          .toLowerCase()
          .includes(q),
      ),
    );
  }
  const { sortCol, sortAsc } = state.value;
  if (sortCol) {
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol],
        bv = b[sortCol];
      const an = parseFloat(av),
        bn = parseFloat(bv);
      const num = !isNaN(an) && !isNaN(bn);
      const cmp = num
        ? an - bn
        : String(av ?? '').localeCompare(String(bv ?? ''));
      return sortAsc ? cmp : -cmp;
    });
  }
  return rows;
});

const filteredCount = computed(() => filteredAndSorted.value.length);

const pageRows = computed(() => {
  const start = (state.value.currentPage - 1) * rowsPerPage;
  return filteredAndSorted.value.slice(start, start + rowsPerPage);
});

function onPage(evt) {
  state.value.currentPage = evt.first / rowsPerPage + 1;
}

function onSort(evt) {
  state.value.sortCol = evt.sortField;
  state.value.sortAsc = evt.sortOrder === 1;
}

// Reset page when dataset or query changes
watch([currentDataset, () => state.value.searchQuery], () => {
  state.value.currentPage = 1;
});
</script>
