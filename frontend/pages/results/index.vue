<template>
    <div class="results-container">
        <div
            v-if="error"
            class="error-message p-6 bg-red-100 text-red-700 rounded"
        >
            {{ error }}
            <Button label="Retry" @click="loadResults" class="ml-2" />
        </div>

        <div>
            <h2 class="text-2xl font-bold mb-4 text-center">
                Analysis Results for Dataset: {{ dataset }}
            </h2>
        </div>

        <div class="flex justify-between items-center">
            <Button
                label="Back to Datasets"
                icon="pi pi-arrow-left"
                @click="$router.push('/')"
                class="mb-4"
                outlined
                size="small"
            />
            <Button
                icon="pi pi-download"
                label="Download Results"
                @click="openDownloadLink"
                size="small"
            />
        </div>

        <Card>
            <template #content>
                <DataTable
                    :first="first"
                    :rows="rows"
                    :sortField="sortField"
                    :sortOrder="sortOrder"
                    :value="results"
                    ref="dt"
                    :lazy="true"
                    :totalRecords="totalRecords"
                    :loading="loading"
                    paginator
                    :rows-per-page-options="[10, 20, 50]"
                    @page="onPage"
                    @sort="onSort"
                    :filters="filters"
                    @filter="onFilter"
                    stripedRows
                    class="p-datatable-sm"
                    filterDisplay="row"
                    :showFilterOperator="false"
                    :showFilterMatchModes="false"
                    :showFilterMenu="false"
                    :showClearButton="false"
                >
                    <Column
                        field="annotation"
                        header="Annotation"
                        sortable
                        filterMatchMode="equals"
                        :showFilterMenu="false"
                    >
                        <template #filter="{ filterModel }">
                            <Select
                                v-model="filters['annotation'].value"
                                :options="annotationOptions"
                                optionLabel="label"
                                optionValue="value"
                                placeholder="Select annotation"
                                class="p-column-filter w-full"
                                @change="onFilter"
                            />
                        </template>
                        <template #body="{ data }">
                            <Chip
                                :label="data.annotation"
                                :class="'chip_' + data.annotation"
                            />
                        </template>
                    </Column>
                    <Column
                        field="tissue"
                        header="Tissue"
                        sortable
                        filterMatchMode="equals"
                        :showFilterMenu="false"
                    >
                        <template #filter="{ filterModel }">
                            <Select
                                v-model="filters['tissue'].value"
                                :options="tissueOptions"
                                optionLabel="label"
                                optionValue="value"
                                placeholder="Select tissue"
                                class="p-column-filter w-full"
                                @change="onFilter"
                            />
                        </template>
                    </Column>
                    <Column
                        field="biosample"
                        header="Biosample"
                        sortable
                        filterMatchMode="contains"
                        :showFilterMenu="false"
                    >
                        <template #filter="{ filterModel }">
                            <InputText
                                v-model="filters['biosample'].value"
                                type="text"
                                class="p-column-filter"
                                placeholder="Search biosample"
                                @change="onFilter"
                            />
                        </template>
                    </Column>
                    <Column
                        field="enrichment"
                        header="Enrichment"
                        sortable
                        filterMatchMode="gte"
                        :showFilterMenu="false"
                    >
                        <template #filter="{ filterModel }">
                            <div class="flex items-center gap-2">
                                <InputNumber
                                    v-model="filters['enrichment'].value"
                                    placeholder="≥ Value"
                                    class="p-column-filter w-full"
                                    :minFractionDigits="3"
                                    :maxFractionDigits="3"
                                    @keydown.enter="onFilter"
                                />
                            </div>
                        </template>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.enrichment) }}
                        </template>
                    </Column>
                    <Column
                        field="pValue"
                        header="P-Value"
                        sortable
                        filterMatchMode="lte"
                        :showFilterMenu="false"
                    >
                        <template #filter="{ filterModel }">
                            <div class="flex items-center gap-2">
                                <InputNumber
                                    v-model="filters['pValue'].value"
                                    placeholder="≤ Value"
                                    class="p-column-filter w-full"
                                    mode="decimal"
                                    :minFractionDigits="3"
                                    :maxFractionDigits="3"
                                    @keydown.enter="onFilter"
                                />
                            </div>
                        </template>
                        <template #body="slotProps">
                            {{ formatPValue(slotProps.data.pValue) }}
                        </template>
                    </Column>

                    <template #empty>
                        <div class="text-center p-4">No results found.</div>
                    </template>
                    <template #loading>
                        <div class="p-4">
                            <div class="mb-2" v-for="i in 5" :key="i">
                                <Skeleton height="3rem" />
                            </div>
                        </div>
                    </template>
                </DataTable>
            </template>
            <template #footer
                ><small>Total records: {{ totalRecords }}</small></template
            >
        </Card>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { useResultsStore } from "~/stores/ResultsStore.js";
const route = useRoute();
import { storeToRefs } from "pinia";

const resultsStore = useResultsStore();
const {
    items: results,
    totalRecords,
    annotations,
    tissues,
    biosamples,
    loading,
    error,
} = storeToRefs(resultsStore);

const first = ref(0);
const rows = ref(10);
const sortField = ref("pValue");
const sortOrder = ref(-1);
const dataset = ref(route.query.dataset);
const dt = ref();

const formatNumber = (value) => {
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
    }).format(value);
};

const config = useRuntimeConfig();
const downloadUrl = computed(
    () => `${config.public.apiBaseUrl}/api/download/${dataset.value}`,
);

function openDownloadLink() {
    window.open(
        downloadUrl.value + `?token=${localStorage.getItem("authToken")}`,
        "_blank",
    );
}

const formatPValue = (value) => {
    if (value < 0.001) {
        return value.toExponential(2);
    }
    return value.toFixed(3);
};

// Define options for dropdowns
const annotationOptions = ref([
    { label: "All Annotations", value: null },
    { label: "Binding Sites", value: "binding_sites" },
    { label: "Accessible Chromatin", value: "accessible_chromatin" },
    { label: "Enhancer", value: "enhancer" },
    { label: "Promoter", value: "promoter" },
]);

// Get unique tissues from results
const tissueOptions = computed(() => {
    if (!results.value?.length) return [{ label: "All Tissues", value: null }];

    const uniqueTissues = [
        ...new Set(results.value.map((item) => item.tissue)),
    ];
    return [
        { label: "All Tissues", value: null },
        ...uniqueTissues.map((tissue) => ({ label: tissue, value: tissue })),
    ];
});

const filters = ref({
    annotation: { value: null, matchMode: "equals" },
    tissue: { value: null, matchMode: "equals" },
    biosample: { value: null, matchMode: "contains" },
    enrichment: { value: null, matchMode: "gte" },
    pValue: { value: null, matchMode: "lte" },
});

const onFilter = (event) => {
    first.value = 0;
    loadResults();
};

const transformFilters = (filters) => {
    const transformedFilters = {};
    Object.entries(filters).forEach(([key, filter]) => {
        if (filter.value !== null && filter.value !== "") {
            if (key === "pValue") {
                transformedFilters[`filter_${key}`] = `<=${filter.value}`;
            } else if (key === "enrichment") {
                transformedFilters[`filter_${key}`] = `>=${filter.value}`;
            } else if (key === "biosample") {
                transformedFilters[`filter_${key}`] =
                    `contains:${filter.value}`;
            } else {
                transformedFilters[`filter_${key}`] = filter.value;
            }
        }
    });
    return transformedFilters;
};

const loadResults = async () => {
    try {
        await resultsStore.getResults(dataset.value, {
            first: first.value,
            rows: rows.value,
            sort_field: sortField.value,
            sort_order: sortOrder.value,
            ...transformFilters(filters.value),
        });
    } catch (err) {
        console.error("Failed to load results:", err);
    }
};

const onPage = (event) => {
    first.value = event.first;
    rows.value = event.rows;
    loadResults();
};

const onSort = (event) => {
    sortField.value = event.sortField;
    sortOrder.value = event.sortOrder;
    loadResults();
};

onMounted(() => {
    loadResults();
});
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

/* :deep(.p-datatable) {
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
    border-radius: 4px;
} */

:deep(.p-column-header-content) {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Annotation chip colors */
:deep(.chip_binding_sites) {
    border: 2px solid #2196f3;
    color: #2196f3;
    background-color: transparent;
    padding-block: 0.1rem;
}

:deep(.chip_accessible_chromatin) {
    border: 2px solid #4caf50;
    color: #4caf50;
    background-color: transparent;
    padding-block: 0.1rem;
}

:deep(.chip_enhancer) {
    border: 2px solid #ff9800;
    color: #ff9800;
    background-color: transparent;
    padding-block: 0.1rem;
}

:deep(.chip_promoter) {
    border: 2px solid #e91e63;
    color: #e91e63;
    background-color: transparent;
    padding-block: 0.1rem;
}

:deep(.p-column-filter) {
    width: 100%;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
}

:deep(.p-select-label) {
    text-overflow: ellipsis;
    font-size: 0.875rem;
}

:deep(.p-select-panel .p-select-items) {
    font-size: 0.875rem;
}

:deep(.p-column-header-content) {
    flex-direction: column;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
    padding: 0.5rem;
}

:deep(.p-datatable .p-datatable-thead > tr > th) {
    padding-bottom: 0.5rem;
}

:deep(.p-inputtext, .p-inputnumber) {
    font-size: 0.875rem;
}

:deep(.p-datatable-filter-row) {
    background-color: #f8f9fa;
}
</style>
