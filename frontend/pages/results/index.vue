<template>
  <div class="results-container">
    <div v-if="error" class="error-message p-4 bg-red-100 text-red-700 rounded">
      {{ error }}
      <Button label="Retry" @click="loadResults" class="ml-2" />
    </div>

    <DataTable
        v-model:first="first"
        v-model:rows="rows"
        v-model:sortField="sortField"
        v-model:sortOrder="sortOrder"
        :value="results"
        ref="dt"
        :lazy="true"
        :totalRecords="totalRecords"
        :loading="loading"
        paginator
        :rows-per-page-options="[10, 20, 50]"
        @page="onPage"
        @sort="onSort"
        stripedRows
        class="p-datatable-sm"
    >
      <template #header>
        <div class="text-end pb-4">
          <Button icon="pi pi-external-link" label="Export" @click="openDownloadLink" />
        </div>
      </template>
      <Column
          field="annotation"
          header="Annotation"
          sortable
      />
      <Column
          field="tissue"
          header="Tissue"
          sortable
      />
      <Column
          field="biosample"
          header="Biosample"
          sortable
      />
      <Column
          field="enrichment"
          header="Enrichment"
          sortable
      >
        <template #body="slotProps">
          {{ formatNumber(slotProps.data.enrichment) }}
        </template>
      </Column>
      <Column
          field="pValue"
          header="P-Value"
          sortable
      >
        <template #body="slotProps">
          {{ formatPValue(slotProps.data.pValue) }}
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useResultsStore } from '~/stores/ResultsStore.js'
const route = useRoute();
import { storeToRefs } from 'pinia'
import Column from 'primevue/column'
import Button from 'primevue/button'

const resultsStore = useResultsStore()
const { items: results, totalRecords, loading, error } = storeToRefs(resultsStore)

const first = ref(0)
const rows = ref(50)
const sortField = ref("pValue")
const sortOrder = ref(-1)
const dataset = ref(route.query.dataset)
const dt = ref();

const formatNumber = (value) => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value)
}

const config = useRuntimeConfig();
const downloadUrl = computed(() => `${config.public.apiBaseUrl}/api/download/${dataset.value}`);

function openDownloadLink() {
  window.open(downloadUrl.value + `?token=${localStorage.getItem('authToken')}`, '_blank');
}

const formatPValue = (value) => {
  if (value < 0.001) {
    return value.toExponential(2)
  }
  return value.toFixed(3)
}

const loadResults = async () => {
  try {
    await resultsStore.getResults(dataset.value, {
      first: first.value,
      rows: rows.value,
      sort_field: sortField.value,
      sort_order: sortOrder.value
    })
  } catch (err) {
    console.error('Failed to load results:', err)
  }
}

const onPage = (event) => {
  first.value = event.first
  rows.value = event.rows
  loadResults()
}

const onSort = (event) => {
  sortField.value = event.sortField
  sortOrder.value = event.sortOrder
  loadResults()
}

onMounted(() => {
  loadResults()
})
</script>

<style scoped>
.results-container {
  padding: 1rem;
}

.error-message {
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

:deep(.p-datatable) {
  box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
  border-radius: 4px;
}

:deep(.p-column-header-content) {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
