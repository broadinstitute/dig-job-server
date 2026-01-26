<template>
    <div>
        <!-- Show loading skeleton while workflow is running -->
        <div v-if="magmaWorkflowRunning" class="p-4">
            <div class="mb-4 p-4 bg-blue-100 text-blue-700 rounded">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="font-semibold mb-1">
                            MAGMA Analysis Running
                        </h3>
                        <p class="text-sm">
                            The MAGMA workflow is currently processing. Results
                            will be available once complete.
                        </p>
                        <p class="text-sm mt-1">
                            Status: {{ magmaWorkflowStatus }}
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
            <!-- MAGMA Gene Results Section -->
            <div
                class="mb-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
            >
                <div class="flex items-center justify-between mb-4">
                    <h3
                        class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                    >
                        Gene Results
                    </h3>
                    <Tag
                        v-if="magmaTotalRecords > 0"
                        :value="`${magmaTotalRecords} genes`"
                        severity="info"
                    />
                </div>

                <!-- Gene table loading skeleton -->
                <div
                    v-if="magmaLoading && magmaResults.length === 0"
                    class="p-4"
                >
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading MAGMA gene results...</span>
                    </div>
                    <div class="mb-2" v-for="i in 5" :key="i">
                        <Skeleton height="3rem" />
                    </div>
                </div>

                <!-- Gene table -->
                <DataTable
                    v-else-if="magmaResults.length > 0"
                    :first="magmaFirst"
                    :rows="magmaRows"
                    :sortField="magmaSortField"
                    :sortOrder="magmaSortOrder"
                    :value="magmaResults"
                    ref="magmaDt"
                    :lazy="true"
                    :totalRecords="magmaTotalRecords"
                    :loading="magmaLoading"
                    paginator
                    :rows-per-page-options="[10, 20, 50]"
                    @page="onMagmaPage"
                    @sort="onMagmaSort"
                    :filters="magmaFilters"
                    @filter="onMagmaFilter"
                    stripedRows
                    class="p-datatable-sm"
                    filterDisplay="row"
                    :showFilterOperator="false"
                    :showFilterMatchModes="false"
                    :showFilterMenu="false"
                    :showClearButton="false"
                >
                    <Column
                        field="gene"
                        header="Gene"
                        sortable
                        filterMatchMode="equals"
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <AutoComplete
                                v-model="magmaGeneFilterInput"
                                :suggestions="filteredGenes"
                                @complete="searchGenes"
                                placeholder="Search gene"
                                class="p-column-filter w-full"
                                @item-select="onGeneSelect"
                                @clear="onGeneClear"
                                :delay="300"
                                dropdown
                                forceSelection
                            />
                        </template>
                        <template #body="{ data }">
                            <a
                                :href="`https://a2f.hugeamp.org/gene.html?gene=${data.gene}`"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                            >
                                {{ data.gene }}
                            </a>
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
                            <InputNumber
                                v-model="magmaFilters['pValue'].value"
                                placeholder="≤ Value"
                                class="p-column-filter w-full"
                                mode="decimal"
                                :minFractionDigits="3"
                                :maxFractionDigits="9"
                                @keydown.enter="onMagmaFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatPValue(slotProps.data.pValue) }}
                        </template>
                    </Column>

                    <template #empty>
                        <div class="text-center p-4">
                            No MAGMA results found.
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

                <!-- No gene results message -->
                <div
                    v-else-if="!magmaLoading"
                    class="text-center p-4 text-gray-500"
                >
                    No MAGMA gene results available.
                </div>
            </div>

            <!-- MAGMA Pathway Results Section -->
            <div
                class="mt-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
            >
                <div class="flex items-center justify-between mb-4">
                    <h3
                        class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                    >
                        Pathway Results
                    </h3>
                    <Tag
                        v-if="magmaPathwaysTotalRecords > 0"
                        :value="`${magmaPathwaysTotalRecords} pathways`"
                        severity="info"
                    />
                </div>

                <!-- Pathway table loading skeleton -->
                <div
                    v-if="
                        magmaPathwaysLoading &&
                        magmaPathwaysResults.length === 0
                    "
                    class="p-4"
                >
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading MAGMA pathway results...</span>
                    </div>
                    <div class="mb-2" v-for="i in 5" :key="i">
                        <Skeleton height="3rem" />
                    </div>
                </div>

                <!-- Pathway table -->
                <DataTable
                    v-else-if="magmaPathwaysResults.length > 0"
                    :first="magmaPathwaysFirst"
                    :rows="magmaPathwaysRows"
                    :sortField="magmaPathwaysSortField"
                    :sortOrder="magmaPathwaysSortOrder"
                    :value="magmaPathwaysResults"
                    ref="magmaPathwaysDt"
                    :lazy="true"
                    :totalRecords="magmaPathwaysTotalRecords"
                    :loading="magmaPathwaysLoading"
                    paginator
                    :rows-per-page-options="[10, 20, 50]"
                    @page="onMagmaPathwaysPage"
                    @sort="onMagmaPathwaysSort"
                    :filters="magmaPathwaysFilters"
                    @filter="onMagmaPathwaysFilter"
                    stripedRows
                    class="p-datatable-sm"
                    filterDisplay="row"
                    :showFilterOperator="false"
                    :showFilterMatchModes="false"
                    :showFilterMenu="false"
                    :showClearButton="false"
                >
                    <Column
                        field="pathwayName"
                        header="Pathway"
                        sortable
                        filterMatchMode="contains"
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputText
                                v-model="
                                    magmaPathwaysFilters['pathwayName'].value
                                "
                                placeholder="Search pathway"
                                class="p-column-filter w-full"
                                @keydown.enter="onMagmaPathwaysFilter"
                            />
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
                            <InputNumber
                                v-model="magmaPathwaysFilters['pValue'].value"
                                placeholder="≤ Value"
                                class="p-column-filter w-full"
                                mode="decimal"
                                :minFractionDigits="3"
                                :maxFractionDigits="9"
                                @keydown.enter="onMagmaPathwaysFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatPValue(slotProps.data.pValue) }}
                        </template>
                    </Column>
                    <Column field="numGenes" header="# Genes" sortable></Column>
                    <Column field="beta" header="Beta" sortable>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.beta) }}
                        </template>
                    </Column>
                    <Column field="stdErr" header="SE" sortable>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.stdErr) }}
                        </template>
                    </Column>

                    <template #empty>
                        <div class="text-center p-4">
                            No MAGMA pathway results found.
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

                <!-- No pathway results message -->
                <div
                    v-else-if="!magmaPathwaysLoading"
                    class="text-center p-4 text-gray-500"
                >
                    No MAGMA pathway results available.
                </div>
            </div>
        </div>

        <div class="mt-4 flex justify-end">
            <Button
                label="View MAGMA Log"
                icon="pi pi-file-check"
                @click="$router.push(`/log/${jobId}?method=magma`)"
                size="small"
                outlined
            />
        </div>
    </div>
</template>

<script setup>
import { useResultsStore } from "~/stores/ResultsStore.js";

const props = defineProps({
    dataset: {
        type: String,
        required: true,
    },
    jobId: {
        type: String,
        default: null,
    },
    magmaWorkflowRunning: {
        type: Boolean,
        default: false,
    },
    magmaWorkflowStatus: {
        type: String,
        default: "",
    },
    hasMagmaResults: {
        type: Boolean,
        default: false,
    },
    hasMagmaPathwaysResults: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["refresh", "dataLoaded"]);

const resultsStore = useResultsStore();
const { genes: apiGenes } = storeToRefs(resultsStore);

// MAGMA Gene Results state
const magmaResults = ref([]);
const magmaTotalRecords = ref(0);
const magmaLoading = ref(false);
const magmaFirst = ref(0);
const magmaRows = ref(10);
const magmaSortField = ref("pValue");
const magmaSortOrder = ref(1);
const magmaDt = ref();

// MAGMA Pathways state
const magmaPathwaysResults = ref([]);
const magmaPathwaysTotalRecords = ref(0);
const magmaPathwaysLoading = ref(false);
const magmaPathwaysFirst = ref(0);
const magmaPathwaysRows = ref(10);
const magmaPathwaysSortField = ref("pValue");
const magmaPathwaysSortOrder = ref(1);
const magmaPathwaysDt = ref();

// Gene autocomplete
const filteredGenes = ref([]);
const magmaGeneFilterInput = ref(null);

// Filters
const magmaFilters = ref({
    gene: { value: null, matchMode: "equals" },
    pValue: { value: null, matchMode: "lte" },
});

const magmaPathwaysFilters = ref({
    pathwayName: { value: null, matchMode: "contains" },
    pValue: { value: null, matchMode: "lte" },
});

// Transform filters to API format
const transformFilters = (filters) => {
    const transformedFilters = {};
    Object.entries(filters).forEach(([key, filter]) => {
        if (
            !filter ||
            filter.value === null ||
            filter.value === "" ||
            typeof filter.value === "undefined"
        ) {
            return;
        }

        const filterName = filter.paramKey || key;
        const filterKey = `filter_${filterName}`;
        const matchMode = filter.matchMode || "equals";
        const value = filter.value;

        switch (matchMode) {
            case "lte":
                transformedFilters[filterKey] = `<=${value}`;
                break;
            case "gte":
                transformedFilters[filterKey] = `>=${value}`;
                break;
            case "equals":
                transformedFilters[filterKey] = `eq:${value}`;
                break;
            case "contains":
                transformedFilters[filterKey] = `contains:${value}`;
                break;
            default:
                transformedFilters[filterKey] = value;
        }
    });
    return transformedFilters;
};

// Gene autocomplete
const searchGenes = (event) => {
    const query = event.query.toLowerCase();

    if (query === "") {
        if (apiGenes.value && apiGenes.value.length > 0) {
            filteredGenes.value = apiGenes.value;
        } else if (magmaResults.value?.length) {
            filteredGenes.value = [
                ...new Set(magmaResults.value.map((item) => item.gene)),
            ];
        } else {
            filteredGenes.value = [];
        }
        return;
    }

    if (apiGenes.value && apiGenes.value.length > 0) {
        filteredGenes.value = apiGenes.value.filter((gene) =>
            gene.toLowerCase().includes(query),
        );
    } else if (magmaResults.value?.length) {
        const uniqueGenes = [
            ...new Set(magmaResults.value.map((item) => item.gene)),
        ];
        filteredGenes.value = uniqueGenes.filter((gene) =>
            gene.toLowerCase().includes(query),
        );
    } else {
        filteredGenes.value = [];
    }
};

const onGeneSelect = (event) => {
    magmaGeneFilterInput.value = event.value;
    magmaFilters.value.gene.value = event.value;
    onMagmaFilter();
};

const onGeneClear = () => {
    magmaGeneFilterInput.value = null;
    magmaFilters.value.gene.value = null;
    onMagmaFilter();
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

// MAGMA Gene Results loading (server-side pagination)
const loadMagmaResults = async () => {
    try {
        magmaLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: magmaFirst.value,
            rows: magmaRows.value,
            sort_field: magmaSortField.value,
            sort_order: magmaSortOrder.value,
        });

        const transformedFilters = transformFilters(magmaFilters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/magma-results/${props.dataset}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            magmaResults.value = data.items;
        }
        if (data.totalRecords) magmaTotalRecords.value = data.totalRecords;
        if (data.genes) apiGenes.value = data.genes;

        emit("dataLoaded", {
            type: "gene",
            hasResults: magmaResults.value.length > 0,
            totalRecords: magmaTotalRecords.value,
        });
    } catch (err) {
        console.error("Failed to load MAGMA results:", err);
    } finally {
        magmaLoading.value = false;
    }
};

// MAGMA Pathways loading (server-side pagination)
const loadMagmaPathwaysResults = async () => {
    try {
        magmaPathwaysLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: magmaPathwaysFirst.value,
            rows: magmaPathwaysRows.value,
            sort_field: magmaPathwaysSortField.value,
            sort_order: magmaPathwaysSortOrder.value,
        });

        const transformedFilters = transformFilters(magmaPathwaysFilters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/magma-pathways-results/${props.dataset}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            magmaPathwaysResults.value = data.items;
        }
        if (data.totalRecords)
            magmaPathwaysTotalRecords.value = data.totalRecords;

        emit("dataLoaded", {
            type: "pathway",
            hasResults: magmaPathwaysResults.value.length > 0,
            totalRecords: magmaPathwaysTotalRecords.value,
        });
    } catch (err) {
        console.error("Failed to load MAGMA pathways results:", err);
    } finally {
        magmaPathwaysLoading.value = false;
    }
};

// Event handlers
const onMagmaPage = (event) => {
    magmaFirst.value = event.first;
    magmaRows.value = event.rows;
    loadMagmaResults();
};

const onMagmaSort = (event) => {
    magmaSortField.value = event.sortField;
    magmaSortOrder.value = event.sortOrder;
    loadMagmaResults();
};

const onMagmaFilter = () => {
    magmaFirst.value = 0;
    loadMagmaResults();
};

const onMagmaPathwaysPage = (event) => {
    magmaPathwaysFirst.value = event.first;
    magmaPathwaysRows.value = event.rows;
    loadMagmaPathwaysResults();
};

const onMagmaPathwaysSort = (event) => {
    magmaPathwaysSortField.value = event.sortField;
    magmaPathwaysSortOrder.value = event.sortOrder;
    loadMagmaPathwaysResults();
};

const onMagmaPathwaysFilter = () => {
    magmaPathwaysFirst.value = 0;
    loadMagmaPathwaysResults();
};

// Load data on mount
onMounted(async () => {
    if (props.hasMagmaResults && magmaResults.value.length === 0) {
        await loadMagmaResults();
    }
    if (
        props.hasMagmaPathwaysResults &&
        magmaPathwaysResults.value.length === 0
    ) {
        await loadMagmaPathwaysResults();
    }
});

// Watch for hasMagmaResults changes
watch(
    () => props.hasMagmaResults,
    async (newVal) => {
        if (newVal && magmaResults.value.length === 0) {
            await loadMagmaResults();
        }
    },
);

// Watch for hasMagmaPathwaysResults changes
watch(
    () => props.hasMagmaPathwaysResults,
    async (newVal) => {
        if (newVal && magmaPathwaysResults.value.length === 0) {
            await loadMagmaPathwaysResults();
        }
    },
);

// Watch for dataset changes
watch(
    () => props.dataset,
    async () => {
        // Reset state
        magmaResults.value = [];
        magmaTotalRecords.value = 0;
        magmaFirst.value = 0;
        magmaFilters.value = {
            gene: { value: null, matchMode: "equals" },
            pValue: { value: null, matchMode: "lte" },
        };
        magmaGeneFilterInput.value = null;

        magmaPathwaysResults.value = [];
        magmaPathwaysTotalRecords.value = 0;
        magmaPathwaysFirst.value = 0;
        magmaPathwaysFilters.value = {
            pathwayName: { value: null, matchMode: "contains" },
            pValue: { value: null, matchMode: "lte" },
        };

        if (props.hasMagmaResults) {
            await loadMagmaResults();
        }
        if (props.hasMagmaPathwaysResults) {
            await loadMagmaPathwaysResults();
        }
    },
);

// Expose methods to parent
defineExpose({
    loadMagmaResults,
    loadMagmaPathwaysResults,
});
</script>
