<template>
    <div class="results-container">
        <div
            v-if="error"
            class="error-message p-6 bg-red-100 text-red-700 rounded"
        >
            <InputNumber
                v-model="filters['pValue'].value"
                placeholder="≤ Value"
                class="p-column-filter w-full"
                :minFractionDigits="10"
                :maxFractionDigits="10"
                @keydown.enter="onSldscFilter"
            />
            {{ error }}
            <Button
                label="Retry"
                @click="checkResultsAvailability"
                class="ml-2"
            />
        </div>

        <div
            v-if="
                !hasSldscResults &&
                !hasMagmaResults &&
                !sldscLoading &&
                !magmaLoading &&
                !error
            "
            class="error-message p-6 bg-yellow-100 text-yellow-700 rounded"
        >
            <div v-if="hasWorkflowData">
                <h3 class="font-semibold mb-2">
                    Workflow Status for Dataset: {{ dataset }}
                </h3>
                <div
                    v-for="(methods, workflow) in workflowStatus"
                    :key="workflow"
                    class="mb-2"
                >
                    <div
                        v-for="(details, method) in methods"
                        :key="method"
                        class="flex justify-between items-center"
                    >
                        <span class="capitalize"
                            >{{ workflow }}/{{ method }}:</span
                        >
                        <span
                            :class="getStatusClass(details.status)"
                            class="px-2 py-1 rounded text-sm"
                        >
                            {{ details.status }}
                        </span>
                    </div>
                </div>
                <p class="mt-3 text-sm">
                    Results will be available once workflows complete
                    successfully.
                    <Button
                        label="Refresh"
                        @click="checkResultsAvailability"
                        class="ml-2"
                        size="small"
                    />
                </p>
            </div>
            <div v-else>
                <p>
                    No results or workflow information available for this
                    dataset.
                </p>
                <Button
                    label="Refresh"
                    @click="checkResultsAvailability"
                    class="ml-2"
                    size="small"
                />
            </div>
        </div>

        <div>
            <h2 class="text-2xl font-bold mb-4 text-center">
                Results for Dataset: {{ dataset }}
            </h2>
        </div>

        <div class="flex justify-between items-center">
            <Button
                label="Back to Datasets"
                icon="pi pi-arrow-left"
                @click="$router.push('/datasets')"
                class="mb-4"
                outlined
                size="small"
            />
            <Button
                icon="pi pi-download"
                :label="downloadButtonLabel"
                @click="openDownloadLink"
                :disabled="!canDownloadCurrentTab"
                size="small"
            />
        </div>

        <Card>
            <template #content>
                <Tabs
                    :value="activeTab"
                    @tab-change="onTabChange"
                    @update:value="onTabChange"
                    @change="onTabChange"
                    @tab-click="onTabChange"
                >
                    <TabList>
                        <Tab
                            v-if="shouldShowSldscTab"
                            value="sldsc"
                            :disabled="!hasSldscResults"
                            @click="() => onTabChange({ value: 'sldsc' })"
                            >{{ sldscTabHeader }}</Tab
                        >
                        <Tab
                            v-if="shouldShowMagmaTab"
                            value="magma"
                            :disabled="!hasMagmaResults"
                            @click="() => onTabChange({ value: 'magma' })"
                            >{{ magmaTabHeader }}</Tab
                        >
                    </TabList>
                    <TabPanels>
                        <TabPanel v-if="shouldShowSldscTab" value="sldsc">
                            <!-- Show loading skeleton while workflow is running -->
                            <div v-if="sldscWorkflowRunning" class="p-4">
                                <div
                                    class="mb-4 p-4 bg-blue-100 text-blue-700 rounded"
                                >
                                    <div
                                        class="flex items-center justify-between"
                                    >
                                        <div>
                                            <h3 class="font-semibold mb-1">
                                                SLDSC Analysis Running
                                            </h3>
                                            <p class="text-sm">
                                                The SLDSC workflow is currently
                                                processing. Results will be
                                                available once complete.
                                            </p>
                                            <p class="text-sm mt-1">
                                                Status:
                                                {{ sldscWorkflowStatus }}
                                            </p>
                                        </div>
                                        <Button
                                            label="Refresh"
                                            @click="checkResultsAvailability"
                                            class="ml-2"
                                            size="small"
                                        />
                                    </div>
                                </div>
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>

                            <!-- Show loading skeleton while data is loading -->
                            <div v-else-if="sldscLoading" class="p-4">
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>
                            <!-- SLDSC Results Table -->
                            <DataTable
                                v-else-if="sldscResults.length > 0"
                                :first="sldscFirst"
                                :rows="sldscRows"
                                :sortField="sldscSortField"
                                :sortOrder="sldscSortOrder"
                                :value="sldscResults"
                                ref="sldscDt"
                                :lazy="true"
                                :totalRecords="sldscTotalRecords"
                                :loading="sldscLoading"
                                paginator
                                :rows-per-page-options="[10, 20, 50]"
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
                                            v-model="
                                                filters['annotation'].value
                                            "
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
                                                :class="
                                                    'color-dot ' +
                                                    data.annotation
                                                "
                                            ></div>
                                            <span class="ml-2">{{
                                                data.annotation
                                            }}</span>
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
                                            v-model="filters['biosample'].value"
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
                                                v-model="
                                                    filters['enrichment'].value
                                                "
                                                placeholder="≥ Value"
                                                class="p-column-filter w-full"
                                                :minFractionDigits="3"
                                                :maxFractionDigits="3"
                                                @keydown.enter="onSldscFilter"
                                            />
                                        </div>
                                    </template>
                                    <template #body="slotProps">
                                        {{
                                            formatNumber(
                                                slotProps.data.enrichment,
                                            )
                                        }}
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
                                                v-model="
                                                    filters['pValue'].value
                                                "
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
                                        {{
                                            formatPValue(slotProps.data.pValue)
                                        }}
                                    </template>
                                </Column>

                                <template #empty>
                                    <div class="text-center p-4">
                                        No SLDSC results found.
                                    </div>
                                </template>
                                <template #loading>
                                    <div class="p-4">
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>
                                </template>
                                <template #footer>
                                    <div
                                        class="flex justify-between items-center"
                                    >
                                        <small
                                            >Total records:
                                            {{ sldscTotalRecords }}</small
                                        >
                                        <Button
                                            label="View SLDSC Log"
                                            icon="pi pi-file-check"
                                            @click="
                                                $router.push(`/log/${jobId}`)
                                            "
                                            size="small"
                                            outlined
                                        />
                                    </div>
                                </template>
                                >
                            </DataTable>
                            <div
                                v-else-if="
                                    !sldscLoading && sldscResults.length === 0
                                "
                                class="text-center p-4"
                            >
                                <p class="text-gray-500">
                                    No SLDSC results available for this dataset.
                                </p>
                            </div>
                        </TabPanel>

                        <TabPanel v-if="shouldShowMagmaTab" value="magma">
                            <!-- Show loading skeleton while workflow is running -->
                            <div v-if="magmaWorkflowRunning" class="p-4">
                                <div
                                    class="mb-4 p-4 bg-blue-100 text-blue-700 rounded"
                                >
                                    <div
                                        class="flex items-center justify-between"
                                    >
                                        <div>
                                            <h3 class="font-semibold mb-1">
                                                MAGMA Analysis Running
                                            </h3>
                                            <p class="text-sm">
                                                The MAGMA workflow is currently
                                                processing. Results will be
                                                available once complete.
                                            </p>
                                            <p class="text-sm mt-1">
                                                Status:
                                                {{ magmaWorkflowStatus }}
                                            </p>
                                        </div>
                                        <Button
                                            label="Refresh"
                                            @click="checkResultsAvailability"
                                            class="ml-2"
                                            size="small"
                                        />
                                    </div>
                                </div>
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>

                            <!-- Show loading skeleton while data is loading -->
                            <div v-else-if="magmaLoading" class="p-4">
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>
                            <!-- MAGMA Results Table -->
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
                                            v-model="magmaFilters['gene'].value"
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
                                            v-model="
                                                magmaFilters['pValue'].value
                                            "
                                            placeholder="≤ Value"
                                            class="p-column-filter w-full"
                                            mode="decimal"
                                            :minFractionDigits="3"
                                            :maxFractionDigits="3"
                                            @keydown.enter="onMagmaFilter"
                                        />
                                    </template>
                                    <template #body="slotProps">
                                        {{
                                            formatPValue(slotProps.data.pValue)
                                        }}
                                    </template>
                                </Column>

                                <template #empty>
                                    <div class="text-center p-4">
                                        No MAGMA results found.
                                    </div>
                                </template>
                                <template #loading>
                                    <div class="p-4">
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>
                                </template>
                                <template #footer>
                                    <div
                                        class="flex justify-between items-center"
                                    >
                                        <small
                                            >Total records:
                                            {{ magmaTotalRecords }}</small
                                        >
                                        <Button
                                            label="View MAGMA Log"
                                            icon="pi pi-file-check"
                                            @click="
                                                $router.push(`/log/${jobId}`)
                                            "
                                            size="small"
                                            outlined
                                        />
                                    </div>
                                </template>
                                >
                            </DataTable>
                            <div
                                v-else-if="
                                    !magmaLoading && magmaResults.length === 0
                                "
                                class="text-center p-4"
                            >
                                <p class="text-gray-500">
                                    No MAGMA results available for this dataset.
                                </p>
                            </div>
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from "vue";
import { useResultsStore } from "~/stores/ResultsStore.js";
const route = useRoute();
const router = useRouter();
import { storeToRefs } from "pinia";

const resultsStore = useResultsStore();

const dataset = ref(route.query.dataset);
const tab = ref(route.query.tab || "sldsc"); // 'sldsc' or 'magma'
const filteredBiosamples = ref([]);
const filteredGenes = ref([]);

// Tab management
const activeTab = ref(route.query.tab || "sldsc");

// Workflow status tracking
const workflowStatus = ref({});
const hasWorkflowData = ref(false);

// SLDSC specific data
const sldscResults = ref([]);
const sldscTotalRecords = ref(0);
const sldscLoading = ref(false);
const sldscFirst = ref(0);
const sldscRows = ref(10);
const sldscSortField = ref("pValue");
const sldscSortOrder = ref(1);
const sldscDt = ref();
const hasSldscResults = ref(false);

// MAGMA specific data
const magmaResults = ref([]);
const magmaTotalRecords = ref(0);
const magmaLoading = ref(false);
const magmaFirst = ref(0);
const magmaRows = ref(10);
const magmaSortField = ref("pValue");
const magmaSortOrder = ref(1);
const magmaDt = ref();
const hasMagmaResults = ref(false);

// Job IDs for linking to logs
const sldscJobId = ref(null);
const magmaJobId = ref(null);

// Shared data from store
const {
    error,
    tissues: apiTissues,
    biosamples: apiBiosamples,
    annotations: apiAnnotations,
    genes: apiGenes,
} = storeToRefs(resultsStore);

// Computed properties for tab headers
const sldscTabHeader = computed(() => {
    return "SLDSC";
});

const magmaTabHeader = computed(() => {
    return "MAGMA";
});

// Computed properties for tab visibility and workflow status
const shouldShowSldscTab = computed(() => {
    // Only show if workflow succeeded OR if we have data (fallback)
    const sldscStatus =
        workflowStatus.value.ldsc?.ldsc?.status ||
        workflowStatus.value.sldsc?.sldsc?.status;

    if (hasWorkflowData.value) {
        // If we have workflow data, only show if succeeded
        return sldscStatus === "SUCCEEDED" || hasSldscResults.value;
    } else {
        // Fallback: show if we have results data
        return hasSldscResults.value;
    }
});

const shouldShowMagmaTab = computed(() => {
    // Only show if workflow succeeded OR if we have data (fallback)
    const magmaStatus = workflowStatus.value.magma?.magma?.status;

    if (hasWorkflowData.value) {
        // If we have workflow data, only show if succeeded
        return magmaStatus === "SUCCEEDED" || hasMagmaResults.value;
    } else {
        // Fallback: show if we have results data
        return hasMagmaResults.value;
    }
});

const sldscWorkflowStatus = computed(() => {
    return (
        workflowStatus.value.ldsc?.ldsc?.status ||
        workflowStatus.value.sldsc?.sldsc?.status ||
        null
    );
});

const magmaWorkflowStatus = computed(() => {
    return workflowStatus.value.magma?.magma?.status || null;
});

const sldscWorkflowRunning = computed(() => {
    const status = sldscWorkflowStatus.value;
    return (
        status &&
        ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
            status.toUpperCase(),
        )
    );
});

const magmaWorkflowRunning = computed(() => {
    const status = magmaWorkflowStatus.value;
    return (
        status &&
        ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
            status.toUpperCase(),
        )
    );
});
const canDownloadCurrentTab = computed(() => {
    if (activeTab.value === "magma") {
        return hasMagmaResults.value;
    } else {
        return hasSldscResults.value;
    }
});

// Computed property to find a job ID for viewing logs
const jobId = computed(() => {
    // Use the job ID from the API response based on active tab
    if (activeTab.value === "magma" && magmaJobId.value) {
        return magmaJobId.value;
    } else if (activeTab.value === "sldsc" && sldscJobId.value) {
        return sldscJobId.value;
    }

    // Fallback to dataset name if no job ID available
    return dataset.value;
});

const downloadButtonLabel = computed(() => {
    return `Download ${activeTab.value.toUpperCase()} Results`;
});

const formatNumber = (value) => {
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
    }).format(value);
};

const config = useRuntimeConfig();
const downloadUrl = computed(() => {
    // Backend expects "magma" or "ldsc" (not "sldsc")
    const resultTypeParam = activeTab.value === "magma" ? "magma" : "ldsc";
    return `${config.public.apiBaseUrl}/api/download/${dataset.value}?result_type=${resultTypeParam}`;
});

function openDownloadLink() {
    window.open(
        downloadUrl.value + `&token=${localStorage.getItem("authToken")}`,
        "_blank",
    );
}

const formatPValue = (value) => {
    if (value < 0.001) {
        return value.toExponential(2);
    }
    return value.toFixed(3);
};

const getStatusClass = (status) => {
    if (!status) return "bg-gray-200 text-gray-700";

    switch (status.toUpperCase()) {
        case "SUCCEEDED":
            return "bg-green-200 text-green-800";
        case "FAILED":
            return "bg-red-200 text-red-800";
        case "RUNNING":
            return "bg-yellow-200 text-yellow-800";
        case "PENDING":
            return "bg-blue-200 text-blue-800";
        case "SUBMITTED":
            return "bg-yellow-200 text-yellow-800";
        default:
            return "bg-gray-200 text-gray-700";
    }
};

// Define options for dropdowns
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

// Get tissues from API response
const tissueOptions = computed(() => {
    if (!apiTissues.value || apiTissues.value.length === 0) {
        if (!sldscResults.value?.length)
            return [{ label: "All Tissues", value: null }];

        // Fall back to generating from results if API didn't provide tissues
        const uniqueTissues = [
            ...new Set(sldscResults.value.map((item) => item.tissue)),
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

// Search biosamples for autocomplete
const searchBiosamples = (event) => {
    const query = event.query.toLowerCase();

    // When the query is empty, show all biosamples
    if (query === "") {
        if (apiBiosamples.value && apiBiosamples.value.length > 0) {
            filteredBiosamples.value = apiBiosamples.value;
        } else if (sldscResults.value?.length) {
            // Fall back to generating from results if API didn't provide biosamples
            filteredBiosamples.value = [
                ...new Set(sldscResults.value.map((item) => item.biosample)),
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
    } else if (sldscResults.value?.length) {
        // Fall back to filtering from results if API didn't provide biosamples
        const uniqueBiosamples = [
            ...new Set(sldscResults.value.map((item) => item.biosample)),
        ];
        filteredBiosamples.value = uniqueBiosamples.filter((biosample) =>
            biosample.toLowerCase().includes(query),
        );
    } else {
        filteredBiosamples.value = [];
    }
};

// biosample selection
const onBiosampleSelect = (event) => {
    filters.value.biosample.value = event.value;
    onSldscFilter();
};

// clearing the autocomplete
const onBiosampleClear = () => {
    filters.value.biosample.value = null;
    onSldscFilter();
};

// Search genes for autocomplete (MAGMA)
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

// Gene selection (MAGMA)
const onGeneSelect = (event) => {
    magmaFilters.value.gene.value = event.value;
    onMagmaFilter();
};

// Clearing the gene autocomplete
const onGeneClear = () => {
    magmaFilters.value.gene.value = null;
    onMagmaFilter();
};

const filters = ref({
    annotation: { value: null, matchMode: "equals" },
    tissue: { value: null, matchMode: "equals" },
    biosample: { value: null, matchMode: "equals" },
    enrichment: { value: null, matchMode: "gte" },
    pValue: { value: null, matchMode: "lte" },
});

const magmaFilters = ref({
    gene: { value: null, matchMode: "equals" },
    pValue: { value: null, matchMode: "lte" },
});

const transformFilters = (filters) => {
    const transformedFilters = {};
    Object.entries(filters).forEach(([key, filter]) => {
        if (filter.value !== null && filter.value !== "") {
            if (key === "pValue") {
                transformedFilters[`filter_${key}`] = `<=${filter.value}`;
            } else if (key === "enrichment") {
                transformedFilters[`filter_${key}`] = `>=${filter.value}`;
            } else if (key === "start") {
                transformedFilters[`filter_${key}`] = `>=${filter.value}`;
            } else if (key === "end") {
                transformedFilters[`filter_${key}`] = `<=${filter.value}`;
            } else if (
                key === "biosample" ||
                key === "annotation" ||
                key === "tissue" ||
                key === "gene" ||
                key === "chr"
            ) {
                transformedFilters[`filter_${key}`] = `eq:${filter.value}`;
            } else {
                transformedFilters[`filter_${key}`] =
                    `contains:${filter.value}`;
            }
        }
    });
    return transformedFilters;
};

// Tab change handler
const onTabChange = (event) => {
    // Handle different event formats from PrimeVue
    let newValue;
    if (typeof event === "string") {
        newValue = event;
    } else if (event && typeof event.index !== "undefined") {
        // Map index to value
        newValue = event.index === 0 ? "sldsc" : "magma";
    } else if (event && event.value) {
        newValue = event.value;
    } else {
        console.error("Unexpected event format:", event);
        return;
    }

    // Only allow switching to tabs that should be shown and have results
    if (
        newValue === "sldsc" &&
        (!shouldShowSldscTab.value || !hasSldscResults.value)
    ) {
        return;
    }
    if (
        newValue === "magma" &&
        (!shouldShowMagmaTab.value || !hasMagmaResults.value)
    ) {
        return;
    }

    activeTab.value = newValue;
    tab.value = newValue;

    // Update URL parameter to reflect the current tab
    router.replace({
        query: { ...route.query, tab: newValue },
    });

    // Load data for the active tab if not already loaded and workflow succeeded
    if (
        newValue === "sldsc" &&
        sldscResults.value.length === 0 &&
        hasSldscResults.value
    ) {
        loadSldscResults();
    } else if (
        newValue === "magma" &&
        magmaResults.value.length === 0 &&
        hasMagmaResults.value
    ) {
        loadMagmaResults();
    }
};

// SLDSC Results functions
const loadSldscResults = async () => {
    try {
        sldscLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: sldscFirst.value,
            rows: sldscRows.value,
            sort_field: sldscSortField.value,
            sort_order: sldscSortOrder.value,
        });

        // Add any filter parameters
        const transformedFilters = transformFilters(filters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            sldscResults.value = data.items;
            hasSldscResults.value = data.items.length > 0;
        }
        if (data.totalRecords) sldscTotalRecords.value = data.totalRecords;
        if (data.tissues) apiTissues.value = data.tissues;
        if (data.biosamples) apiBiosamples.value = data.biosamples;
        if (data.annotations) apiAnnotations.value = data.annotations;
        if (data.jobId) sldscJobId.value = data.jobId;
    } catch (err) {
        console.error("Failed to load SLDSC results:", err);
    } finally {
        sldscLoading.value = false;
    }
};

const onSldscPage = (event) => {
    sldscFirst.value = event.first;
    sldscRows.value = event.rows;
    loadSldscResults();
};

const onSldscSort = (event) => {
    sldscSortField.value = event.sortField;
    sldscSortOrder.value = event.sortOrder;
    loadSldscResults();
};

const onSldscFilter = () => {
    sldscFirst.value = 0;
    loadSldscResults();
};

// MAGMA Results functions
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

        // Add any filter parameters
        const transformedFilters = transformFilters(magmaFilters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/magma-results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            magmaResults.value = data.items;
            hasMagmaResults.value = data.items.length > 0;
        }
        if (data.totalRecords) magmaTotalRecords.value = data.totalRecords;
        if (data.genes) apiGenes.value = data.genes;
        if (data.jobId) magmaJobId.value = data.jobId;
    } catch (err) {
        console.error("Failed to load MAGMA results:", err);
    } finally {
        magmaLoading.value = false;
    }
};

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

// Check both result types availability and set initial tab
const checkResultsAvailability = async () => {
    try {
        resultsStore.init();

        // Check workflow status to determine what results are available
        const workflowResponse = await resultsStore.axios.get(
            `/api/workflow-status/${dataset.value}`,
        );
        const workflows = workflowResponse.data;

        // Store workflow status for potential display to user
        workflowStatus.value = workflows;
        hasWorkflowData.value = Object.keys(workflows).length > 0;

        console.log("Workflow status for dataset:", dataset.value, workflows);

        // Check if LDSC/SLDSC workflows are available and completed successfully
        const sldscStatus =
            workflows.ldsc?.ldsc?.status || workflows.sldsc?.sldsc?.status;
        const hasSldscWorkflow = !!sldscStatus;
        const sldscSucceeded = sldscStatus === "SUCCEEDED";

        // Check if MAGMA workflows are available and completed successfully
        const magmaStatus = workflows.magma?.magma?.status;
        const hasMagmaWorkflow = !!magmaStatus;
        const magmaSucceeded = magmaStatus === "SUCCEEDED";

        // Set results availability based on workflow status
        if (sldscSucceeded) {
            hasSldscResults.value = true;
        } else if (hasSldscWorkflow) {
            // Workflow exists but hasn't succeeded - don't show results
            hasSldscResults.value = false;
        } else {
            // No workflow info - fallback to checking for existing data
            try {
                const sldscResponse = await resultsStore.axios.get(
                    `/api/results/${dataset.value}?first=0&rows=1`,
                );
                hasSldscResults.value =
                    sldscResponse.data.items &&
                    sldscResponse.data.items.length > 0;
            } catch (e) {
                hasSldscResults.value = false;
            }
        }

        if (magmaSucceeded) {
            hasMagmaResults.value = true;
            console.log(
                "MAGMA workflow succeeded, marking results as available",
            );
        } else if (hasMagmaWorkflow) {
            // Workflow exists but hasn't succeeded - don't show results
            hasMagmaResults.value = false;
        } else {
            // No workflow info - fallback to checking for existing data
            try {
                console.log("Checking MAGMA data availability via API...");
                const magmaResponse = await resultsStore.axios.get(
                    `/api/magma-results/${dataset.value}?first=0&rows=1`,
                );
                hasMagmaResults.value =
                    magmaResponse.data.items &&
                    magmaResponse.data.items.length > 0;
                console.log(
                    "MAGMA API check result:",
                    hasMagmaResults.value,
                    magmaResponse.data,
                );
            } catch (e) {
                console.log("MAGMA API check failed:", e);
                hasMagmaResults.value = false;
            }
        }

        // Ensure we have a valid active tab
        // If current active tab shouldn't be shown, switch to the first available tab
        await nextTick(); // Wait for computed properties to update

        const currentTabValid =
            (activeTab.value === "sldsc" && shouldShowSldscTab.value) ||
            (activeTab.value === "magma" && shouldShowMagmaTab.value);

        if (!currentTabValid) {
            if (shouldShowSldscTab.value) {
                activeTab.value = "sldsc";
            } else if (shouldShowMagmaTab.value) {
                activeTab.value = "magma";
            }
        }

        // Load data for successful workflows only
        if (sldscSucceeded && sldscResults.value.length === 0) {
            loadSldscResults();
        }

        if (magmaSucceeded && magmaResults.value.length === 0) {
            console.log("MAGMA results detected as available, loading data...");
            loadMagmaResults();
        }
    } catch (err) {
        console.error("Failed to check results availability:", err);
        // Fallback to trying to load results directly
        try {
            const sldscResponse = await resultsStore.axios.get(
                `/api/results/${dataset.value}?first=0&rows=1`,
            );
            hasSldscResults.value =
                sldscResponse.data.items && sldscResponse.data.items.length > 0;
        } catch (e) {
            hasSldscResults.value = false;
        }

        try {
            const magmaResponse = await resultsStore.axios.get(
                `/api/magma-results/${dataset.value}?first=0&rows=1`,
            );
            hasMagmaResults.value =
                magmaResponse.data.items && magmaResponse.data.items.length > 0;
        } catch (e) {
            hasMagmaResults.value = false;
        }
    }
};

// Watch for activeTab changes to ensure content is displayed
watch(activeTab, (newTab) => {
    if (
        newTab === "sldsc" &&
        hasSldscResults.value &&
        sldscResults.value.length === 0
    ) {
        loadSldscResults();
    } else if (
        newTab === "magma" &&
        hasMagmaResults.value &&
        magmaResults.value.length === 0
    ) {
        loadMagmaResults();
    }
});

// Watch for route query parameter changes
watch(
    () => route.query.tab,
    (newTab) => {
        if (newTab && (newTab === "sldsc" || newTab === "magma")) {
            activeTab.value = newTab;
            tab.value = newTab;
        }
    },
    { immediate: true },
);

onMounted(async () => {
    // First check workflow availability to determine what tabs to show
    await checkResultsAvailability();

    // Then load data for the active tab if it has results available
    if (
        activeTab.value === "magma" &&
        hasMagmaResults.value &&
        magmaResults.value.length === 0
    ) {
        loadMagmaResults();
    } else if (
        activeTab.value === "sldsc" &&
        hasSldscResults.value &&
        sldscResults.value.length === 0
    ) {
        loadSldscResults();
    }
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

:deep(.p-column-header-content) {
    display: flex;
    align-items: center;
    justify-content: space-between;
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
