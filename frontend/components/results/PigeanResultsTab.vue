<template>
    <div>
        <!-- Show loading skeleton while workflow is running -->
        <div v-if="pigeanWorkflowRunning" class="p-4">
            <div class="mb-4 p-4 bg-blue-100 text-blue-700 rounded">
                <div class="flex items-center justify-between">
                    <div>
                        <h3 class="font-semibold mb-1">
                            PIGEAN Analysis Running
                        </h3>
                        <p class="text-sm">
                            The PIGEAN workflow is currently processing. Results
                            will be available once complete.
                        </p>
                        <p class="text-sm mt-1">
                            Status: {{ pigeanWorkflowStatus }}
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
            <!-- Gene Results Section -->
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
                        v-if="pigeanGeneTotalRecords > 0"
                        :value="`${pigeanGeneTotalRecords} genes`"
                        severity="info"
                    />
                </div>

                <!-- Gene Scatter Plot -->
                <div v-if="pigeanGeneDataLoaded" class="mb-6">
                    <PigeanGeneScatterPlot
                        :geneResults="filteredPigeanGeneData"
                        :key="pigeanChartKey"
                    />
                </div>
                <div v-else-if="pigeanGeneLoading" class="mb-6">
                    <h4 class="font-semibold text-lg mb-3">
                        Gene Support Plot
                    </h4>
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading scatter plot data...</span>
                    </div>
                    <Skeleton height="400px" />
                </div>

                <!-- Gene table loading skeleton -->
                <div
                    v-if="pigeanGeneLoading && pigeanGeneAllData.length === 0"
                    class="p-4"
                >
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading PIGEAN gene results...</span>
                    </div>
                    <div class="mb-2" v-for="i in 5" :key="i">
                        <Skeleton height="3rem" />
                    </div>
                </div>

                <!-- Gene table (client-side pagination) -->
                <DataTable
                    v-else
                    :value="filteredPigeanGeneData"
                    dataKey="gene"
                    :first="pigeanGeneFirst"
                    :rows="pigeanGeneRows"
                    :sortField="pigeanGeneSortField"
                    :sortOrder="pigeanGeneSortOrder"
                    :totalRecords="pigeanGeneTotalRecords"
                    paginator
                    :rows-per-page-options="[10, 20, 50]"
                    :filters="pigeanGeneFilters"
                    @page="onPigeanGenePage"
                    @sort="onPigeanGeneSort"
                    :expandedRows="pigeanGeneExpandedRows"
                    @update:expandedRows="onPigeanGeneExpandedRowsChange"
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
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <AutoComplete
                                v-model="pigeanGeneFilterInput"
                                :suggestions="pigeanGeneSuggestions"
                                @complete="onPigeanGeneComplete"
                                @item-select="onPigeanGeneSelect"
                                @clear="onPigeanGeneClear"
                                placeholder="Search gene"
                                class="p-column-filter"
                                fluid
                                showClear
                            />
                        </template>
                        <template #body="{ data }">
                            <a
                                :href="`https://a2f.hugeamp.org/pigean/gene.html?gene=${data.gene}`"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                            >
                                {{ data.gene }}
                            </a>
                        </template>
                    </Column>

                    <Column
                        field="combined"
                        header="Combined Score"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneFilters['combined'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="3"
                                :maxFractionDigits="3"
                                showClear
                                @keydown.enter="onPigeanGeneFilter"
                                @update:modelValue="onPigeanGeneFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.combined || 0) }}
                        </template>
                    </Column>
                    <Column
                        field="huge_score"
                        header="HuGE Score"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneFilters['huge_score'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="3"
                                :maxFractionDigits="3"
                                showClear
                                @keydown.enter="onPigeanGeneFilter"
                                @update:modelValue="onPigeanGeneFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.huge_score || 0) }}
                        </template>
                    </Column>
                    <Column
                        field="log_bf"
                        header="Direct Score"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneFilters['log_bf'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="3"
                                :maxFractionDigits="3"
                                showClear
                                @keydown.enter="onPigeanGeneFilter"
                                @update:modelValue="onPigeanGeneFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.log_bf || 0) }}
                        </template>
                    </Column>
                    <Column
                        field="prior"
                        header="Prior"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneFilters['prior'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="3"
                                :maxFractionDigits="6"
                                showClear
                                @keydown.enter="onPigeanGeneFilter"
                                @update:modelValue="onPigeanGeneFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.prior || 0) }}
                        </template>
                    </Column>
                    <Column
                        field="n"
                        header="# Gene Sets"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneFilters['n'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="0"
                                :maxFractionDigits="0"
                                showClear
                                @keydown.enter="onPigeanGeneFilter"
                                @update:modelValue="onPigeanGeneFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{
                                slotProps.data.n !== null &&
                                slotProps.data.n !== undefined
                                    ? slotProps.data.n.toLocaleString()
                                    : "—"
                            }}
                        </template>
                    </Column>
                    <Column header="Gene Sets">
                        <template #body="{ data }">
                            <span
                                class="inline-flex"
                                v-tooltip.left="
                                    !data?.gene_sets?.length
                                        ? 'No data available'
                                        : null
                                "
                            >
                                <Button
                                    size="small"
                                    outlined
                                    :label="
                                        isPigeanGeneRowExpanded(data)
                                            ? 'Hide'
                                            : 'Show'
                                    "
                                    :disabled="!data?.gene_sets?.length"
                                    @click="togglePigeanGeneRow(data)"
                                />
                            </span>
                        </template>
                    </Column>

                    <template #expansion="slotProps">
                        <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded">
                            <h4 class="font-semibold mb-2">
                                Gene Sets for {{ slotProps.data.gene }}
                            </h4>

                            <DataTable
                                v-if="slotProps.data?.gene_sets?.length"
                                :value="slotProps.data.gene_sets"
                                size="small"
                                class="p-datatable-sm"
                                paginator
                                :rows="5"
                                :rowsPerPageOptions="[5, 10, 20]"
                            >
                                <Column field="gene_set" header="Gene Set">
                                    <template #body="{ data }">
                                        <a
                                            v-if="data?.gene_set"
                                            :href="`https://a2f.hugeamp.org/pigean/geneset.html?geneset=${encodeURIComponent(
                                                data.gene_set,
                                            )}&genesetSize=small&traitGroup=portal`"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                        >
                                            {{ data.gene_set }}
                                        </a>
                                        <span v-else>—</span>
                                    </template>
                                </Column>

                                <Column field="beta" header="Beta (Joint)">
                                    <template #body="row">
                                        {{
                                            typeof row.data.beta === "number"
                                                ? formatNumber(row.data.beta)
                                                : "—"
                                        }}
                                    </template>
                                </Column>
                                <Column
                                    field="beta_uncorrected"
                                    header="Beta (Marginal)"
                                >
                                    <template #body="row">
                                        {{
                                            typeof row.data.beta_uncorrected ===
                                            "number"
                                                ? formatNumber(
                                                      row.data.beta_uncorrected,
                                                  )
                                                : "—"
                                        }}
                                    </template>
                                </Column>
                            </DataTable>

                            <div v-else class="text-sm text-gray-500">
                                No gene-set details available for this gene.
                            </div>
                        </div>
                    </template>

                    <template #empty>
                        <div class="text-center p-4">
                            No PIGEAN gene results found.
                        </div>
                    </template>
                </DataTable>
            </div>

            <!-- Gene Set Results Section -->
            <div
                class="mt-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
            >
                <div class="flex items-center justify-between mb-4">
                    <h3
                        class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                    >
                        Gene Set Results
                    </h3>
                    <Tag
                        v-if="pigeanGeneSetTotalRecords > 0"
                        :value="`${pigeanGeneSetTotalRecords} gene sets`"
                        severity="info"
                    />
                </div>

                <!-- Gene Set Scatter Plot -->
                <div v-if="pigeanGeneSetDataLoaded" class="mb-6">
                    <PigeanGeneSetScatterPlot
                        :geneSetResults="filteredPigeanGeneSetData"
                        :key="pigeanGeneSetChartKey"
                    />
                </div>
                <div v-else-if="pigeanGeneSetLoading" class="mb-6">
                    <h4 class="font-semibold text-lg mb-3">Gene Set Plot</h4>
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading scatter plot data...</span>
                    </div>
                    <Skeleton height="400px" />
                </div>

                <!-- Gene set table loading skeleton -->
                <div
                    v-if="
                        pigeanGeneSetLoading &&
                        pigeanGeneSetAllData.length === 0
                    "
                    class="p-4"
                >
                    <div
                        class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                    >
                        <i class="pi pi-spinner pi-spin text-primary"></i>
                        <span>Loading PIGEAN gene set results...</span>
                    </div>
                    <div class="mb-2" v-for="i in 5" :key="i">
                        <Skeleton height="3rem" />
                    </div>
                </div>

                <!-- Gene set table (client-side pagination) -->
                <DataTable
                    v-else
                    :value="filteredPigeanGeneSetData"
                    dataKey="gene_set"
                    :first="pigeanGeneSetFirst"
                    :rows="pigeanGeneSetRows"
                    :sortField="pigeanGeneSetSortField"
                    :sortOrder="pigeanGeneSetSortOrder"
                    :totalRecords="pigeanGeneSetTotalRecords"
                    paginator
                    :rows-per-page-options="[10, 20, 50]"
                    :filters="pigeanGeneSetFilters"
                    @page="onPigeanGeneSetPage"
                    @sort="onPigeanGeneSetSort"
                    :expandedRows="pigeanGeneSetExpandedRows"
                    @update:expandedRows="onPigeanGeneSetExpandedRowsChange"
                    stripedRows
                    class="p-datatable-sm"
                    filterDisplay="row"
                    :showFilterOperator="false"
                    :showFilterMatchModes="false"
                    :showFilterMenu="false"
                    :showClearButton="false"
                >
                    <Column
                        field="gene_set"
                        header="Gene Set"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <AutoComplete
                                v-model="pigeanGeneSetFilterInput"
                                :suggestions="pigeanGeneSetSuggestions"
                                @complete="onPigeanGeneSetComplete"
                                @item-select="onPigeanGeneSetSelect"
                                @clear="onPigeanGeneSetClear"
                                placeholder="Search gene set"
                                class="p-column-filter"
                                fluid
                                showClear
                            />
                        </template>
                        <template #body="{ data }">
                            <a
                                :href="`https://a2f.hugeamp.org/pigean/geneset.html?geneset=${encodeURIComponent(
                                    data.gene_set || '',
                                )}&genesetSize=small&traitGroup=portal`"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                            >
                                {{ data.gene_set }}
                            </a>
                        </template>
                    </Column>
                    <Column
                        field="beta_uncorrected"
                        header="Beta (Marginal)"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="
                                    pigeanGeneSetFilters['beta_uncorrected']
                                        .value
                                "
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="3"
                                :maxFractionDigits="3"
                                @keydown.enter="onPigeanGeneSetFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{
                                formatNumber(
                                    slotProps.data.beta_uncorrected || 0,
                                )
                            }}
                        </template>
                    </Column>
                    <Column
                        field="beta"
                        header="Beta (Joint)"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneSetFilters['beta'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="3"
                                :maxFractionDigits="3"
                                @keydown.enter="onPigeanGeneSetFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{ formatNumber(slotProps.data.beta || 0) }}
                        </template>
                    </Column>
                    <Column
                        field="n"
                        header="# Genes"
                        sortable
                        :showFilterMenu="false"
                    >
                        <template #filter>
                            <InputNumber
                                v-model="pigeanGeneSetFilters['n'].value"
                                placeholder="≥ Value"
                                class="p-column-filter w-full"
                                :minFractionDigits="0"
                                :maxFractionDigits="0"
                                @keydown.enter="onPigeanGeneSetFilter"
                            />
                        </template>
                        <template #body="slotProps">
                            {{
                                slotProps.data.n !== null &&
                                slotProps.data.n !== undefined
                                    ? slotProps.data.n.toLocaleString()
                                    : "—"
                            }}
                        </template>
                    </Column>
                    <Column header="Genes">
                        <template #body="{ data }">
                            <span
                                class="inline-flex"
                                v-tooltip.left="
                                    !data?.genes?.length
                                        ? 'No data available'
                                        : null
                                "
                            >
                                <Button
                                    size="small"
                                    outlined
                                    :label="
                                        isPigeanGeneSetRowExpanded(
                                            data.gene_set,
                                        )
                                            ? 'Hide'
                                            : 'Show'
                                    "
                                    :disabled="!data?.genes?.length"
                                    @click="togglePigeanGeneSetRow(data)"
                                />
                            </span>
                        </template>
                    </Column>

                    <template #expansion="slotProps">
                        <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded">
                            <h4 class="font-semibold mb-2">
                                Genes in {{ slotProps.data.gene_set }}
                            </h4>
                            <DataTable
                                v-if="slotProps.data?.genes?.length"
                                :value="slotProps.data.genes"
                                size="small"
                                class="p-datatable-sm"
                                paginator
                                :rows="5"
                                :rowsPerPageOptions="[5, 10, 20]"
                            >
                                <Column field="gene" header="Gene">
                                    <template #body="{ data }">
                                        <a
                                            v-if="data?.gene"
                                            :href="`https://a2f.hugeamp.org/pigean/gene.html?gene=${data.gene}`"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                        >
                                            {{ data.gene }}
                                        </a>
                                        <span v-else>—</span>
                                    </template>
                                </Column>
                                <Column
                                    field="combined"
                                    header="Combined Score"
                                >
                                    <template #body="row">
                                        {{
                                            typeof row.data.combined ===
                                            "number"
                                                ? formatNumber(
                                                      row.data.combined,
                                                  )
                                                : "—"
                                        }}
                                    </template>
                                </Column>

                                <Column field="prior" header="Prior">
                                    <template #body="row">
                                        {{
                                            typeof row.data.prior === "number"
                                                ? formatNumber(row.data.prior)
                                                : "—"
                                        }}
                                    </template>
                                </Column>
                                <Column field="log_bf" header="Direct Score">
                                    <template #body="row">
                                        {{
                                            typeof row.data.log_bf === "number"
                                                ? formatNumber(row.data.log_bf)
                                                : "—"
                                        }}
                                    </template>
                                </Column>
                            </DataTable>
                            <div v-else class="text-sm text-gray-500">
                                No gene-level details available for this gene
                                set.
                            </div>
                        </div>
                    </template>

                    <template #empty>
                        <div class="text-center p-4">
                            No PIGEAN gene set results found.
                        </div>
                    </template>
                </DataTable>
            </div>
        </div>

        <div class="mt-4 flex justify-end">
            <Button
                label="View PIGEAN Log"
                icon="pi pi-file-check"
                @click="$router.push(`/log/${jobId}?method=pigean`)"
                size="small"
                outlined
            />
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
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
    pigeanWorkflowRunning: {
        type: Boolean,
        default: false,
    },
    pigeanWorkflowStatus: {
        type: String,
        default: "",
    },
    hasPigeanGeneResults: {
        type: Boolean,
        default: false,
    },
    hasPigeanGeneSetResults: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["refresh", "dataLoaded"]);

const resultsStore = useResultsStore();

// Gene Results state
const pigeanGeneAllData = ref([]);
const pigeanGeneLoading = ref(false);
const pigeanGeneFirst = ref(0);
const pigeanGeneRows = ref(10);
const pigeanGeneSortField = ref("combined");
const pigeanGeneSortOrder = ref(-1);
const pigeanGeneExpandedRows = ref({});
const pigeanGeneDataLoaded = ref(false);

// Gene Set Results state
const pigeanGeneSetAllData = ref([]);
const pigeanGeneSetLoading = ref(false);
const pigeanGeneSetFirst = ref(0);
const pigeanGeneSetRows = ref(10);
const pigeanGeneSetSortField = ref("beta");
const pigeanGeneSetSortOrder = ref(-1);
const pigeanGeneSetExpandedRows = ref({});
const pigeanGeneSetDataLoaded = ref(false);

// Autocomplete state
const pigeanGeneFilterInput = ref(null);
const pigeanGeneSuggestions = ref([]);
const pigeanGeneSetFilterInput = ref(null);
const pigeanGeneSetSuggestions = ref([]);

// Filters
const pigeanGeneFilters = ref({
    gene: { value: null, matchMode: "contains" },
    prior: { value: null, matchMode: "gte" },
    combined: { value: null, matchMode: "gte" },
    huge_score: { value: null, matchMode: "gte" },
    log_bf: { value: null, matchMode: "gte" },
    n: { value: null, matchMode: "gte" },
});

const pigeanGeneSetFilters = ref({
    gene_set: { value: null, matchMode: "contains" },
    beta_uncorrected: { value: null, matchMode: "gte" },
    beta: { value: null, matchMode: "gte" },
    n: { value: null, matchMode: "gte" },
});

// Computed: filtered gene data with client-side filtering
const filteredPigeanGeneData = computed(() => {
    let data = [...pigeanGeneAllData.value];

    const filters = pigeanGeneFilters.value;

    // Gene name filter (case-insensitive contains)
    if (filters.gene?.value) {
        const searchTerm = filters.gene.value.toLowerCase();
        data = data.filter((item) =>
            item.gene?.toLowerCase().includes(searchTerm),
        );
    }
    if (filters.combined?.value != null) {
        data = data.filter((item) => item.combined >= filters.combined.value);
    }
    if (filters.huge_score?.value != null) {
        data = data.filter(
            (item) => item.huge_score >= filters.huge_score.value,
        );
    }
    if (filters.log_bf?.value != null) {
        data = data.filter((item) => item.log_bf >= filters.log_bf.value);
    }
    if (filters.prior?.value != null) {
        data = data.filter((item) => item.prior >= filters.prior.value);
    }
    if (filters.n?.value != null) {
        data = data.filter((item) => item.n >= filters.n.value);
    }

    // Apply sorting
    if (pigeanGeneSortField.value) {
        const field = pigeanGeneSortField.value;
        const order = pigeanGeneSortOrder.value || 1;
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

const pigeanGeneTotalRecords = computed(() => {
    return filteredPigeanGeneData.value.length;
});

const pigeanChartKey = computed(() => {
    return `pigean-chart-${props.dataset}-${pigeanGeneTotalRecords.value}`;
});

// Computed: filtered gene set data with client-side filtering
const filteredPigeanGeneSetData = computed(() => {
    let data = [...pigeanGeneSetAllData.value];

    const filters = pigeanGeneSetFilters.value;

    if (filters.gene_set?.value) {
        const searchTerm = filters.gene_set.value.toLowerCase();
        data = data.filter((item) =>
            item.gene_set?.toLowerCase().includes(searchTerm),
        );
    }
    if (filters.beta_uncorrected?.value != null) {
        data = data.filter(
            (item) => item.beta_uncorrected >= filters.beta_uncorrected.value,
        );
    }
    if (filters.beta?.value != null) {
        data = data.filter((item) => item.beta >= filters.beta.value);
    }
    if (filters.n?.value != null) {
        data = data.filter((item) => item.n >= filters.n.value);
    }

    // Apply sorting
    if (pigeanGeneSetSortField.value) {
        const field = pigeanGeneSetSortField.value;
        const order = pigeanGeneSetSortOrder.value || 1;
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

const pigeanGeneSetTotalRecords = computed(() => {
    return filteredPigeanGeneSetData.value.length;
});

const pigeanGeneSetChartKey = computed(() => {
    return `pigean-geneset-chart-${props.dataset}-${pigeanGeneSetTotalRecords.value}`;
});

// Formatting helper
const formatNumber = (value) => {
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
    }).format(value);
};

// Gene autocomplete
const onPigeanGeneComplete = (event) => {
    const query = event.query.toLowerCase();
    const allGenes = pigeanGeneAllData.value
        .map((item) => item.gene)
        .filter((gene) => gene?.toLowerCase().includes(query));
    pigeanGeneSuggestions.value = [...new Set(allGenes)].slice(0, 20);
};

const onPigeanGeneSelect = (event) => {
    pigeanGeneFilters.value.gene.value = event.value;
    pigeanGeneFilterInput.value = event.value;
    onPigeanGeneFilter();
};

const onPigeanGeneClear = () => {
    pigeanGeneFilterInput.value = null;
    pigeanGeneFilters.value.gene.value = null;
    onPigeanGeneFilter();
};

// Gene set autocomplete
const onPigeanGeneSetComplete = (event) => {
    const query = event.query.toLowerCase();
    const allGeneSets = pigeanGeneSetAllData.value
        .map((item) => item.gene_set)
        .filter((geneSet) => geneSet?.toLowerCase().includes(query));
    pigeanGeneSetSuggestions.value = [...new Set(allGeneSets)].slice(0, 20);
};

const onPigeanGeneSetSelect = (event) => {
    pigeanGeneSetFilters.value.gene_set.value = event.value;
    pigeanGeneSetFilterInput.value = event.value;
    onPigeanGeneSetFilter();
};

const onPigeanGeneSetClear = () => {
    pigeanGeneSetFilterInput.value = null;
    pigeanGeneSetFilters.value.gene_set.value = null;
    onPigeanGeneSetFilter();
};

// Data loading
const loadPigeanGeneData = async () => {
    if (pigeanGeneDataLoaded.value || pigeanGeneLoading.value) return;

    try {
        pigeanGeneLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: 0,
            rows: 1000,
            sort_field: "combined",
            sort_order: -1,
        });

        const endpoint = `/api/pigean-gene-results/${props.dataset}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        pigeanGeneAllData.value = data.items || [];
        pigeanGeneDataLoaded.value = true;

        emit("dataLoaded", {
            type: "gene",
            hasResults: pigeanGeneAllData.value.length > 0,
            totalRecords: pigeanGeneAllData.value.length,
        });
    } catch (err) {
        console.error("Failed to load PIGEAN gene results:", err);
        pigeanGeneDataLoaded.value = false;
    } finally {
        pigeanGeneLoading.value = false;
    }
};

const loadPigeanGeneSetResults = async () => {
    if (pigeanGeneSetDataLoaded.value || pigeanGeneSetLoading.value) return;

    try {
        pigeanGeneSetLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: 0,
            rows: 1000,
            sort_field: "beta",
            sort_order: -1,
        });

        const endpoint = `/api/pigean-gene-set-results/${props.dataset}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        pigeanGeneSetAllData.value = data.items || [];
        pigeanGeneSetDataLoaded.value = true;

        emit("dataLoaded", {
            type: "geneSet",
            hasResults: pigeanGeneSetAllData.value.length > 0,
            totalRecords: pigeanGeneSetAllData.value.length,
        });
    } catch (err) {
        console.error("Failed to load PIGEAN gene set results:", err);
        pigeanGeneSetDataLoaded.value = false;
    } finally {
        pigeanGeneSetLoading.value = false;
    }
};

// Event handlers
const onPigeanGenePage = (event) => {
    pigeanGeneFirst.value = event.first;
    pigeanGeneRows.value = event.rows;
};

const onPigeanGeneSort = (event) => {
    pigeanGeneSortField.value = event.sortField;
    pigeanGeneSortOrder.value = event.sortOrder;
    pigeanGeneFirst.value = 0;
};

const onPigeanGeneFilter = () => {
    pigeanGeneFirst.value = 0;
};

const onPigeanGeneSetPage = (event) => {
    pigeanGeneSetFirst.value = event.first;
    pigeanGeneSetRows.value = event.rows;
};

const onPigeanGeneSetSort = (event) => {
    pigeanGeneSetSortField.value = event.sortField;
    pigeanGeneSetSortOrder.value = event.sortOrder;
    pigeanGeneSetFirst.value = 0;
};

const onPigeanGeneSetFilter = () => {
    pigeanGeneSetFirst.value = 0;
};

// Expanded rows handlers
const onPigeanGeneExpandedRowsChange = (value) => {
    pigeanGeneExpandedRows.value = value;
};

const togglePigeanGeneRow = (rowData) => {
    const current = { ...pigeanGeneExpandedRows.value };
    const key = rowData?.gene;
    if (!key) return;

    if (current[key]) {
        delete current[key];
    } else {
        current[key] = rowData;
    }

    pigeanGeneExpandedRows.value = current;
};

const isPigeanGeneRowExpanded = (rowData) => {
    const key = rowData?.gene;
    if (!key) return false;
    return Boolean(pigeanGeneExpandedRows.value?.[key]);
};

const onPigeanGeneSetExpandedRowsChange = (value) => {
    pigeanGeneSetExpandedRows.value = value;
};

const togglePigeanGeneSetRow = (rowData) => {
    const current = { ...pigeanGeneSetExpandedRows.value };
    const key = rowData?.gene_set;
    if (!key) return;

    if (current[key]) {
        delete current[key];
    } else {
        current[key] = rowData;
    }

    pigeanGeneSetExpandedRows.value = current;
};

const isPigeanGeneSetRowExpanded = (geneSet) => {
    if (!geneSet) return false;
    return Boolean(pigeanGeneSetExpandedRows.value?.[geneSet]);
};

// Load data on mount
onMounted(async () => {
    if (props.hasPigeanGeneResults && !pigeanGeneDataLoaded.value) {
        await loadPigeanGeneData();
    }
    if (props.hasPigeanGeneSetResults && !pigeanGeneSetDataLoaded.value) {
        await loadPigeanGeneSetResults();
    }
});

// Watch for hasPigeanGeneResults changes
watch(
    () => props.hasPigeanGeneResults,
    async (newVal) => {
        if (newVal && !pigeanGeneDataLoaded.value) {
            await loadPigeanGeneData();
        }
    },
);

// Watch for hasPigeanGeneSetResults changes
watch(
    () => props.hasPigeanGeneSetResults,
    async (newVal) => {
        if (newVal && !pigeanGeneSetDataLoaded.value) {
            await loadPigeanGeneSetResults();
        }
    },
);

// Watch for dataset changes
watch(
    () => props.dataset,
    async () => {
        // Reset all state
        pigeanGeneAllData.value = [];
        pigeanGeneDataLoaded.value = false;
        pigeanGeneFirst.value = 0;
        pigeanGeneExpandedRows.value = {};
        pigeanGeneFilters.value = {
            gene: { value: null, matchMode: "contains" },
            prior: { value: null, matchMode: "gte" },
            combined: { value: null, matchMode: "gte" },
            huge_score: { value: null, matchMode: "gte" },
            log_bf: { value: null, matchMode: "gte" },
            n: { value: null, matchMode: "gte" },
        };
        pigeanGeneFilterInput.value = null;

        pigeanGeneSetAllData.value = [];
        pigeanGeneSetDataLoaded.value = false;
        pigeanGeneSetFirst.value = 0;
        pigeanGeneSetExpandedRows.value = {};
        pigeanGeneSetFilters.value = {
            gene_set: { value: null, matchMode: "contains" },
            beta_uncorrected: { value: null, matchMode: "gte" },
            beta: { value: null, matchMode: "gte" },
            n: { value: null, matchMode: "gte" },
        };
        pigeanGeneSetFilterInput.value = null;

        if (props.hasPigeanGeneResults) {
            await loadPigeanGeneData();
        }
        if (props.hasPigeanGeneSetResults) {
            await loadPigeanGeneSetResults();
        }
    },
);

// Expose methods to parent
defineExpose({
    loadPigeanGeneData,
    loadPigeanGeneSetResults,
    pigeanGeneDataLoaded,
    pigeanGeneSetDataLoaded,
});
</script>
