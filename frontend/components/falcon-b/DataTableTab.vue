<template>
  <div>
    <div class="toolbar">
      <div class="inner-switch">
        <button
          v-for="opt in datasetOptions"
          :key="opt.value"
          :class="{ active: currentDataset === opt.value }"
          @click="currentDataset = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>
      <input
        v-model="state.searchQuery"
        type="text"
        placeholder="Search entire table..."
        class="search-input"
      />
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col"
              @click="handleSort(col)"
            >
              {{ col }}
              <span v-if="state.sortCol === col" class="sort-arrow">
                {{ state.sortAsc ? '▲' : '▼' }}
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in pageRows" :key="i">
            <td v-for="col in columns" :key="col">{{ row[col] }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button
        class="page-btn"
        :disabled="state.currentPage <= 1"
        @click="state.currentPage--"
      >
        Previous
      </button>
      <span>Page {{ state.currentPage }} of {{ totalPages }}</span>
      <button
        class="page-btn"
        :disabled="state.currentPage >= totalPages"
        @click="state.currentPage++"
      >
        Next
      </button>
    </div>
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
        String(r[c] ?? '').toLowerCase().includes(q),
      ),
    );
  }
  const { sortCol, sortAsc } = state.value;
  if (sortCol) {
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol], bv = b[sortCol];
      const an = parseFloat(av), bn = parseFloat(bv);
      const num = !isNaN(an) && !isNaN(bn);
      const cmp = num
        ? an - bn
        : String(av ?? '').localeCompare(String(bv ?? ''));
      return sortAsc ? cmp : -cmp;
    });
  }
  return rows;
});

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredAndSorted.value.length / rowsPerPage)),
);

const pageRows = computed(() => {
  const start = (state.value.currentPage - 1) * rowsPerPage;
  return filteredAndSorted.value.slice(start, start + rowsPerPage);
});

function handleSort(col) {
  if (state.value.sortCol === col) {
    state.value.sortAsc = !state.value.sortAsc;
  } else {
    state.value.sortCol = col;
    state.value.sortAsc = true;
  }
  state.value.currentPage = 1;
}

watch([currentDataset, () => state.value.searchQuery], () => {
  state.value.currentPage = 1;
});
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 15px;
}
.inner-switch {
  display: flex;
  gap: 4px;
}
.inner-switch button {
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  border-radius: 4px;
  font-weight: 500;
  color: #4b5563;
  transition: 0.2s;
}
.inner-switch button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}
.search-input {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  width: 250px;
  font-size: 0.9em;
}
.table-wrapper {
  overflow: auto;
  max-height: 60vh;
  border: 1px solid #d1d5db;
  margin-bottom: 15px;
  background: white;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
  font-size: 0.9em;
}
th {
  background-color: #f3f4f6;
  cursor: pointer;
  position: sticky;
  top: 0;
  z-index: 10;
}
th:hover {
  background-color: #e5e7eb;
}
.sort-arrow {
  margin-left: 4px;
  color: #3b82f6;
}
.pagination {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}
.page-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  background: white;
  cursor: pointer;
  border-radius: 4px;
}
.page-btn:hover:not(:disabled) {
  background: #f3f4f6;
}
.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
