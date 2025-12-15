<template>
    <div>
        <!-- Show loading skeleton while workflow is running -->
        <div v-if="sldscWorkflowRunning" class="p-4">
            <div class="mb-4 p-4 bg-blue-100 text-blue-700 rounded">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="font-semibold mb-1">
                            SLDSC Analysis Running
                        </h3>
                        <p class="text-sm">
                            The SLDSC workflow is currently processing. Results
                            will be available once complete.
                        </p>
                        <p class="text-sm mt-1">
                            Status: {{ sldscWorkflowStatus }}
                        </p>
                    </div>
                    <Button
                        label="Refresh"
                        @click="$emit('refresh')"
                        class="ml-2"
                        size="small"
                    />
                </div>
            </div>
            <div class="mb-2" v-for="i in 5" :key="i">
                <Skeleton height="3rem" />
            </div>
        </div>

        <div v-else>
            <!-- SLDSC Results Section -->
            <div
                class="mb-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
            >
                <div class="flex items-center justify-between mb-4">
                    <h3
                        class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                    >
                        SLDSC Results
                    </h3>
                    <Tag
                        v-if="sldscTotalRecords > 0"
                        :value="`${sldscTotalRecords} results`"
                        severity="info"
                    />
                </div>

                <!-- Volcano Plot -->
                <div v-if="sldscAllData.length > 0" class="mb-6">
                    <SldscVolcanoPlot
                        :annotationResults="filteredSldscData"
                        :key="'sldsc-plot-' + dataset + '-' + sldscTotalRecords"
                    />
                </div>

                <!-- Loading skeleton -->
                <div
                    v-if="sldscLoading && sldscAllData.length === 0"
                    class="p-4"
                >
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading SLDSC results...</span>
                    </div>
                    <div class="mb-2" v-for="i in 5" :key="i">
                        <Skeleton height="3rem" />
                    </div>
                </div>

                <!-- SLDSC Results Table -->
                <DataTable
                    v-else-if="filteredSldscData.length > 0"
                    :value="paginatedSldscData"
                    dataKey="id"
                    :first="sldscFirst"
                    :rows="sldscRows"
                    :sortField="sldscSortField"
                    :sortOrder="sldscSortOrder"
                    ref="sldscDt"
                    :lazy="true"
                    :totalRecords="sldscTotalRecords"
                    :loading="sldscLoading"
                    paginator
                    :rows-per-page-options="[10, 20, 50]"
                    @update:first="sldscFirst = $event"
                    @update:rows="sldscRows = $event"
                    @page="onSldscPage"
                    @sort="onSldscSort"
                    :filters="filters"
                    @filter="onSldscFilter"
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
                        <template #filter>
                            <Select
                                v-model="filters['annotation'].value"
                                :options="annotationOptions"
                                optionLabel="label"
                                optionValue="value"
                                placeholder="Select annotation"
                                class="p-column-filter w-full"
                                @change="onSldscFilter"
                            />
                        </template>
                        <template #body="{ data }">
                            <div class="flex items-center">
                                <div
                                    :class="'color-dot ' + data.annotation"
                                ></div>
                                <span class="ml-2">{{ data.annotation }}</span>
                            </div>
                        </template>
                    </Column>
                    <Column
                        field="tissue"
                        header="Tissue"
                        sortable
                        filterMatchMode="equals"
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <Select
                                v-model="filters['tissue'].value"
                                :options="tissueOptions"
                                optionLabel="label"
                                optionValue="value"
                                placeholder="Select tissue"
                                class="p-column-filter w-full"
                                @change="onSldscFilter"
                            />
                        </template>
                    </Column>
                    <Column
                        field="biosample"
                        header="Biosample"
                        sortable
                        filterMatchMode="equals"
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <AutoComplete
                                v-model="biosampleFilterInput"
                                :suggestions="filteredBiosamples"
                                @complete="searchBiosamples"
                                placeholder="Search biosample"
                                class="p-column-filter w-full"
                                @item-select="onBiosampleSelect"
                                @clear="onBiosampleClear"
                                :delay="300"
                                dropdown
                                forceSelection
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
                        <template #filter>
                            <div class="flex items-center gap-2">
                                <InputNumber
                                    v-model="filters['enrichment'].value"
                                    placeholder="≥ Value"
                                    class="p-column-filter w-full"
                                    :minFractionDigits="3"
                                    :maxFractionDigits="3"
                                    @keydown.enter="onSldscFilter"
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
                        <template #filter>
                            <div class="flex items-center gap-2">
                                <InputNumber
                                    v-model="filters['pValue'].value"
                                    placeholder="≤ Value"
                                    class="p-column-filter w-full"
                                    mode="decimal"
                                    :minFractionDigits="3"
                                    :maxFractionDigits="3"
                                    @keydown.enter="onSldscFilter"
                                />
                            </div>
                        </template>
                        <template #body="slotProps">
                            {{ formatPValue(slotProps.data.pValue) }}
                        </template>
                    </Column>

                    <template #empty>
                        <div class="text-center p-4">
                            No SLDSC results found.
                        </div>
                    </template>
                    <template #loading>
                        <div class="p-4">
                            <div class="mb-2" v-for="i in 5" :key="i">
                                <Skeleton height="3rem" />
                            </div>
                        </div>
                    </template>
                </DataTable>

                <!-- No results message -->
                <div v-else-if="!sldscLoading" class="text-center p-4">
                    <p class="text-gray-500">
                        No SLDSC results available for this dataset.
                    </p>
                </div>
            </div>
        </div>

        <div class="mt-4 flex justify-end">
            <Button
                label="View SLDSC Log"
                icon="pi pi-file-check"
                @click="$router.push(`/log/${jobId}?method=sldsc`)"
                size="small"
                outlined
            />
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useResultsStore } from "~/stores/ResultsStore.js";
import { storeToRefs } from "pinia";

const props = defineProps({
    dataset: {
        type: String,
        required: true,
    },
    jobId: {
        type: String,
        default: null,
    },
    sldscWorkflowRunning: {
        type: Boolean,
        default: false,
    },
    sldscWorkflowStatus: {
        type: String,
        default: "",
    },
    hasSldscResults: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["refresh", "dataLoaded"]);

const resultsStore = useResultsStore();
const {
    tissues: apiTissues,
    biosamples: apiBiosamples,
    annotations: apiAnnotations,
} = storeToRefs(resultsStore);

// Local state
const sldscAllData = ref([]);
const sldscLoading = ref(false);
const sldscFirst = ref(0);
const sldscRows = ref(10);
const sldscSortField = ref("pValue");
const sldscSortOrder = ref(1);
const sldscDt = ref();
const sldscDataLoaded = ref(false);

const filteredBiosamples = ref([]);
const biosampleFilterInput = ref(null);

// Filters
const filters = ref({
    annotation: { value: null, matchMode: "equals" },
    tissue: { value: null, matchMode: "equals" },
    biosample: { value: null, matchMode: "equals" },
    enrichment: { value: null, matchMode: "gte" },
    pValue: { value: null, matchMode: "lte" },
});

// Computed: filtered data with client-side filtering
// NOTE: Do NOT sort here - DataTable handles sorting when lazy="false"
const filteredSldscData = computed(() => {
    let data = [...sldscAllData.value];

    const filterObj = filters.value;

    if (filterObj.annotation?.value) {
        const searchTerm = filterObj.annotation.value.toLowerCase();
        data = data.filter((item) =>
            item.annotation?.toLowerCase().includes(searchTerm),
        );
    }

    if (filterObj.tissue?.value) {
        data = data.filter((item) => item.tissue === filterObj.tissue.value);
    }

    if (filterObj.biosample?.value) {
        data = data.filter(
            (item) => item.biosample === filterObj.biosample.value,
        );
    }

    if (filterObj.enrichment?.value != null) {
        data = data.filter(
            (item) => item.enrichment >= filterObj.enrichment.value,
        );
    }

    if (filterObj.pValue?.value != null) {
        data = data.filter((item) => item.pValue <= filterObj.pValue.value);
    }

    // Apply sorting
    if (sldscSortField.value) {
        const field = sldscSortField.value;
        const order = sldscSortOrder.value || 1;
        data.sort((a, b) => {
            const aVal = a[field] ?? 0;
            const bVal = b[field] ?? 0;
            if (aVal < bVal) return -1 * order;
            if (aVal > bVal) return 1 * order;
            return 0;
        });
    }

    return data;
});

const sldscTotalRecords = computed(() => {
    return filteredSldscData.value.length;
});

const paginatedSldscData = computed(() => {
    const data = filteredSldscData.value;
    if (!data.length) return [];

    const start = Math.min(sldscFirst.value, data.length - 1);
    const end = start + sldscRows.value;
    return data.slice(start, end);
});

// Dropdown options
const annotationOptions = computed(() => {
    if (!apiAnnotations.value || apiAnnotations.value.length === 0) {
        return [
            { label: "All Annotations", value: null },
            { label: "Binding Sites", value: "binding_sites" },
            { label: "Accessible Chromatin", value: "accessible_chromatin" },
            { label: "Enhancer", value: "enhancer" },
            { label: "Promoter", value: "promoter" },
        ];
    }

    return [
        { label: "All Annotations", value: null },
        ...apiAnnotations.value.map((annotation) => ({
            label: annotation,
            value: annotation,
        })),
    ];
});

const tissueOptions = computed(() => {
    if (!apiTissues.value || apiTissues.value.length === 0) {
        if (!sldscAllData.value?.length)
            return [{ label: "All Tissues", value: null }];

        const uniqueTissues = [
            ...new Set(sldscAllData.value.map((item) => item.tissue)),
        ];
        return [
            { label: "All Tissues", value: null },
            ...uniqueTissues.map((tissue) => ({
                label: tissue,
                value: tissue,
            })),
        ];
    }

    return [
        { label: "All Tissues", value: null },
        ...apiTissues.value.map((tissue) => ({
            label: tissue,
            value: tissue,
        })),
    ];
});

// Biosample autocomplete
const searchBiosamples = (event) => {
    const query = event.query.toLowerCase();

    if (query === "") {
        if (apiBiosamples.value && apiBiosamples.value.length > 0) {
            filteredBiosamples.value = apiBiosamples.value;
        } else if (sldscAllData.value?.length) {
            filteredBiosamples.value = [
                ...new Set(sldscAllData.value.map((item) => item.biosample)),
            ];
        } else {
            filteredBiosamples.value = [];
        }
        return;
    }

    if (apiBiosamples.value && apiBiosamples.value.length > 0) {
        filteredBiosamples.value = apiBiosamples.value.filter((biosample) =>
            biosample.toLowerCase().includes(query),
        );
    } else if (sldscAllData.value?.length) {
        const uniqueBiosamples = [
            ...new Set(sldscAllData.value.map((item) => item.biosample)),
        ];
        filteredBiosamples.value = uniqueBiosamples.filter((biosample) =>
            biosample.toLowerCase().includes(query),
        );
    } else {
        filteredBiosamples.value = [];
    }
};

const onBiosampleSelect = (event) => {
    biosampleFilterInput.value = event.value;
    filters.value.biosample.value = event.value;
    onSldscFilter();
};

const onBiosampleClear = () => {
    biosampleFilterInput.value = null;
    filters.value.biosample.value = null;
    onSldscFilter();
};

// Formatting helpers
const formatNumber = (value) => {
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
    }).format(value);
};

const formatPValue = (value) => {
    if (value < 0.001) {
        return value.toExponential(2);
    }
    return value.toFixed(3);
};

// Data loading
const loadSldscAllData = async () => {
    if (sldscDataLoaded.value || sldscLoading.value) return;

    try {
        sldscLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: 0,
            rows: 10000,
        });

        const endpoint = `/api/results/${props.dataset}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            // Add unique ID for dataKey to ensure proper reactivity
            sldscAllData.value = data.items.map((item, index) => ({
                ...item,
                id: index,
            }));
            sldscDataLoaded.value = true;
            emit("dataLoaded", {
                hasResults: data.items.length > 0,
                totalRecords: data.items.length,
            });
        }
        if (data.tissues) apiTissues.value = data.tissues;
        if (data.biosamples) apiBiosamples.value = data.biosamples;
        if (data.annotations) apiAnnotations.value = data.annotations;
    } catch (err) {
        console.error("Failed to load SLDSC results:", err);
        sldscDataLoaded.value = false;
    } finally {
        sldscLoading.value = false;
    }
};

// Event handlers
const onSldscPage = (event) => {
    sldscFirst.value = event.first;
    sldscRows.value = event.rows;
};

const onSldscSort = (event) => {
    sldscSortField.value = event.sortField;
    sldscSortOrder.value = event.sortOrder;
    sldscFirst.value = 0;
};

const onSldscFilter = () => {
    sldscFirst.value = 0;
};

watch(filteredSldscData, (newVal) => {
    if (sldscFirst.value >= newVal.length) {
        sldscFirst.value = 0;
    }
});

watch(sldscRows, () => {
    if (sldscFirst.value >= filteredSldscData.value.length) {
        sldscFirst.value = 0;
    }
});

// Load data on mount if results are available
onMounted(async () => {
    if (props.hasSldscResults && !sldscDataLoaded.value) {
        await loadSldscAllData();
    }
});

// Watch for changes in hasSldscResults prop
watch(
    () => props.hasSldscResults,
    async (newVal) => {
        if (newVal && !sldscDataLoaded.value) {
            await loadSldscAllData();
        }
    },
);

// Watch for dataset changes
watch(
    () => props.dataset,
    async () => {
        // Reset state
        sldscAllData.value = [];
        sldscDataLoaded.value = false;
        sldscFirst.value = 0;
        filters.value = {
            annotation: { value: null, matchMode: "equals" },
            tissue: { value: null, matchMode: "equals" },
            biosample: { value: null, matchMode: "equals" },
            enrichment: { value: null, matchMode: "gte" },
            pValue: { value: null, matchMode: "lte" },
        };
        biosampleFilterInput.value = null;

        if (props.hasSldscResults) {
            await loadSldscAllData();
        }
    },
);

// Expose method to parent for manual refresh
defineExpose({
    loadSldscAllData,
    sldscDataLoaded,
});
</script>

<style scoped>
/* Annotation dot colors */
.color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.color-dot.binding_sites {
    background-color: #2196f3;
}

.color-dot.accessible_chromatin {
    background-color: #4caf50;
}

.color-dot.enhancer {
    background-color: #ff9800;
}

.color-dot.promoter {
    background-color: #e91e63;
}
</style>
