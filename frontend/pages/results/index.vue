<template>
    <div class="results-container">
        <div
            v-if="error"
            class="error-message p-6 bg-red-100 text-red-700 rounded"
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
                <Tabs :value="activeTab" @update:value="onTabChange">
                    <TabList>
                        <Tab
                            v-if="shouldShowSldscTab"
                            value="sldsc"
                            :disabled="!hasSldscResults"
                            @click="() => onTabChange('sldsc')"
                            >{{ sldscTabHeader }}</Tab
                        >
                        <Tab
                            v-if="shouldShowMagmaTab"
                            value="magma"
                            :disabled="!hasMagmaResults"
                            @click="() => onTabChange('magma')"
                            >{{ magmaTabHeader }}</Tab
                        >
                        <Tab
                            v-if="shouldShowPigeanTab"
                            value="pigean"
                            :disabled="!hasPigeanResults"
                            @click="() => onTabChange('pigean')"
                            >{{ pigeanTabHeader }}</Tab
                        >
                    </TabList>
                    <TabPanels>
                        <TabPanel v-if="shouldShowSldscTab" value="sldsc">
                            <SldscResultsTab
                                :dataset="dataset"
                                :jobId="jobId"
                                :sldscWorkflowRunning="sldscWorkflowRunning"
                                :sldscWorkflowStatus="sldscWorkflowStatus"
                                :hasSldscResults="hasSldscResults"
                                @refresh="checkResultsAvailability"
                                @dataLoaded="onSldscDataLoaded"
                                ref="sldscTab"
                            />
                        </TabPanel>

                        <TabPanel v-if="shouldShowMagmaTab" value="magma">
                            <MagmaResultsTab
                                :dataset="dataset"
                                :jobId="jobId"
                                :magmaWorkflowRunning="magmaWorkflowRunning"
                                :magmaWorkflowStatus="magmaWorkflowStatus"
                                :hasMagmaResults="hasMagmaResults"
                                :hasMagmaPathwaysResults="
                                    hasMagmaPathwaysResults
                                "
                                @refresh="checkResultsAvailability"
                                @dataLoaded="onMagmaDataLoaded"
                                ref="magmaTab"
                            />
                        </TabPanel>

                        <TabPanel v-if="shouldShowPigeanTab" value="pigean">
                            <PigeanResultsTab
                                :dataset="dataset"
                                :jobId="jobId"
                                :pigeanWorkflowRunning="pigeanWorkflowRunning"
                                :pigeanWorkflowStatus="pigeanWorkflowStatus"
                                :hasPigeanGeneResults="hasPigeanGeneResults"
                                :hasPigeanGeneSetResults="
                                    hasPigeanGeneSetResults
                                "
                                @refresh="checkResultsAvailability"
                                @dataLoaded="onPigeanDataLoaded"
                                ref="pigeanTab"
                            />
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useResultsStore } from "~/stores/ResultsStore.js";
import SldscResultsTab from "~/components/results/SldscResultsTab.vue";
import MagmaResultsTab from "~/components/results/MagmaResultsTab.vue";
import PigeanResultsTab from "~/components/results/PigeanResultsTab.vue";

const route = useRoute();
const router = useRouter();
const resultsStore = useResultsStore();

// Refs for child components
const sldscTab = ref(null);
const magmaTab = ref(null);
const pigeanTab = ref(null);

// Core state
const dataset = ref(route.query.dataset);
const activeTab = ref(route.query.tab || "sldsc");
const error = ref(null);

// Workflow status tracking
const workflowStatus = ref({});
const hasWorkflowData = ref(false);

// Results availability flags
const hasSldscResults = ref(false);
const hasMagmaResults = ref(false);
const hasMagmaPathwaysResults = ref(false);
const hasPigeanGeneResults = ref(false);
const hasPigeanGeneSetResults = ref(false);

// Workflow running states
const sldscWorkflowRunning = ref(false);
const magmaWorkflowRunning = ref(false);
const pigeanWorkflowRunning = ref(false);
const sldscWorkflowStatus = ref("");
const magmaWorkflowStatus = ref("");
const pigeanWorkflowStatus = ref("");

// Computed properties for tab visibility
const shouldShowSldscTab = computed(() => {
    const status =
        workflowStatus.value.ldsc?.ldsc?.status ||
        workflowStatus.value.sldsc?.sldsc?.status;

    if (hasWorkflowData.value) {
        return status === "SUCCEEDED" || hasSldscResults.value;
    }
    return hasSldscResults.value;
});

const shouldShowMagmaTab = computed(() => {
    const status = workflowStatus.value.magma?.magma?.status;

    if (hasWorkflowData.value) {
        return status === "SUCCEEDED" || hasMagmaResults.value;
    }
    return hasMagmaResults.value || hasMagmaPathwaysResults.value;
});

const hasPigeanResults = computed(() => {
    return hasPigeanGeneResults.value || hasPigeanGeneSetResults.value;
});

const shouldShowPigeanTab = computed(() => {
    const status = workflowStatus.value.pigean?.pigean?.status;

    if (hasWorkflowData.value) {
        return status === "SUCCEEDED" || hasPigeanResults.value;
    }
    return hasPigeanResults.value;
});

// Tab headers
const sldscTabHeader = computed(() =>
    sldscWorkflowRunning.value ? "SLDSC ⏳" : "SLDSC",
);
const magmaTabHeader = computed(() =>
    magmaWorkflowRunning.value ? "MAGMA ⏳" : "MAGMA",
);
const pigeanTabHeader = computed(() =>
    pigeanWorkflowRunning.value ? "PIGEAN ⏳" : "PIGEAN",
);

// Download functionality
const config = useRuntimeConfig();

const downloadButtonLabel = computed(() => {
    return `Download ${activeTab.value.toUpperCase()} Results`;
});

const canDownloadCurrentTab = computed(() => {
    if (activeTab.value === "magma") return hasMagmaResults.value;
    if (activeTab.value === "pigean") return hasPigeanResults.value;
    return hasSldscResults.value;
});

const downloadUrl = computed(() => {
    let resultTypeParam = "ldsc";
    if (activeTab.value === "magma") resultTypeParam = "magma";
    else if (activeTab.value === "pigean") resultTypeParam = "pigean";
    return `${config.public.apiBaseUrl}/api/download/${dataset.value}?result_type=${resultTypeParam}`;
});

function openDownloadLink() {
    window.open(
        downloadUrl.value + `&token=${localStorage.getItem("authToken")}`,
        "_blank",
    );
}

// Job ID for log links
const jobId = computed(() => {
    if (workflowStatus.value) {
        const workflows = workflowStatus.value;

        if (activeTab.value === "magma" && workflows.magma?.magma?.job_id) {
            return workflows.magma.magma.job_id;
        } else if (activeTab.value === "sldsc") {
            if (workflows.sldsc?.sldsc?.job_id)
                return workflows.sldsc.sldsc.job_id;
            if (workflows.ldsc?.ldsc?.job_id) return workflows.ldsc.ldsc.job_id;
        } else if (
            activeTab.value === "pigean" &&
            workflows.pigean?.pigean?.job_id
        ) {
            return workflows.pigean.pigean.job_id;
        }
    }
    return dataset.value;
});

// Status class helper
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

// Tab change handler
const onTabChange = (event) => {
    let newValue = typeof event === "string" ? event : event?.value;

    if (!newValue || newValue === activeTab.value) return;

    if (
        (newValue === "sldsc" && !shouldShowSldscTab.value) ||
        (newValue === "magma" && !shouldShowMagmaTab.value) ||
        (newValue === "pigean" && !shouldShowPigeanTab.value)
    ) {
        return;
    }

    activeTab.value = newValue;

    // Update URL with new tab parameter
    router.push({
        query: {
            ...route.query,
            tab: newValue,
        },
    });
};

// Check workflow status and results availability
const checkResultsAvailability = async () => {
    try {
        resultsStore.init();
        const encodedDataset = encodeURIComponent(dataset.value);

        const workflowResponse = await resultsStore.axios.get(
            `/api/workflow-status/${encodedDataset}`,
        );
        const workflows = workflowResponse.data;

        workflowStatus.value = workflows;
        hasWorkflowData.value = Object.keys(workflows).length > 0;

        // Parse SLDSC workflow
        const sldscStatus =
            workflows.ldsc?.ldsc?.status || workflows.sldsc?.sldsc?.status;
        sldscWorkflowRunning.value =
            sldscStatus &&
            ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
                sldscStatus.toUpperCase(),
            );
        sldscWorkflowStatus.value = sldscStatus || "";
        hasSldscResults.value = sldscStatus === "SUCCEEDED";

        // Parse MAGMA workflow
        const magmaStatus = workflows.magma?.magma?.status;
        magmaWorkflowRunning.value =
            magmaStatus &&
            ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
                magmaStatus.toUpperCase(),
            );
        magmaWorkflowStatus.value = magmaStatus || "";
        hasMagmaResults.value = magmaStatus === "SUCCEEDED";
        hasMagmaPathwaysResults.value = magmaStatus === "SUCCEEDED";

        // Parse PIGEAN workflow
        const pigeanStatus = workflows.pigean?.pigean?.status;
        pigeanWorkflowRunning.value =
            pigeanStatus &&
            ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
                pigeanStatus.toUpperCase(),
            );
        pigeanWorkflowStatus.value = pigeanStatus || "";
        hasPigeanGeneResults.value = pigeanStatus === "SUCCEEDED";
        hasPigeanGeneSetResults.value = pigeanStatus === "SUCCEEDED";

        // If no workflow data, check results directly
        if (!hasWorkflowData.value) {
            await checkResultsDirectly();
        }

        // Select first available tab if current is not available
        selectFirstAvailableTab();
    } catch (err) {
        console.error("Error checking results availability:", err);
        await checkResultsDirectly();
    }
};

// Fallback: check results by attempting API calls
const checkResultsDirectly = async () => {
    const encodedDataset = encodeURIComponent(dataset.value);
    
    try {
        const sldscResponse = await resultsStore.axios.get(
            `/api/results/${encodedDataset}?first=0&rows=1`,
        );
        hasSldscResults.value =
            sldscResponse.data.items && sldscResponse.data.items.length > 0;
    } catch {
        hasSldscResults.value = false;
    }

    try {
        const magmaResponse = await resultsStore.axios.get(
            `/api/magma-results/${encodedDataset}?first=0&rows=1`,
        );
        hasMagmaResults.value =
            magmaResponse.data.items && magmaResponse.data.items.length > 0;
    } catch {
        hasMagmaResults.value = false;
    }

    try {
        const pathwaysResponse = await resultsStore.axios.get(
            `/api/magma-pathways-results/${encodedDataset}?first=0&rows=1`,
        );
        hasMagmaPathwaysResults.value =
            pathwaysResponse.data.items &&
            pathwaysResponse.data.items.length > 0;
    } catch {
        hasMagmaPathwaysResults.value = false;
    }

    try {
        const pigeanGeneResponse = await resultsStore.axios.get(
            `/api/pigean-gene-results/${encodedDataset}?first=0&rows=1`,
        );
        hasPigeanGeneResults.value =
            pigeanGeneResponse.data.items &&
            pigeanGeneResponse.data.items.length > 0;
    } catch {
        hasPigeanGeneResults.value = false;
    }

    try {
        const pigeanGeneSetResponse = await resultsStore.axios.get(
            `/api/pigean-gene-set-results/${encodedDataset}?first=0&rows=1`,
        );
        hasPigeanGeneSetResults.value =
            pigeanGeneSetResponse.data.items &&
            pigeanGeneSetResponse.data.items.length > 0;
    } catch {
        hasPigeanGeneSetResults.value = false;
    }
};

// Select first available tab
const selectFirstAvailableTab = () => {
    if (activeTab.value === "sldsc" && shouldShowSldscTab.value) return;
    if (activeTab.value === "magma" && shouldShowMagmaTab.value) return;
    if (activeTab.value === "pigean" && shouldShowPigeanTab.value) return;

    if (shouldShowSldscTab.value) {
        activeTab.value = "sldsc";
    } else if (shouldShowMagmaTab.value) {
        activeTab.value = "magma";
    } else if (shouldShowPigeanTab.value) {
        activeTab.value = "pigean";
    }
};

// Event handlers from child components
const onSldscDataLoaded = (data) => {
    if (data.hasResults !== undefined) {
        hasSldscResults.value = data.hasResults;
    }
};

const onMagmaDataLoaded = (data) => {
    if (data.type === "gene" && data.hasResults !== undefined) {
        hasMagmaResults.value = data.hasResults;
    }
    if (data.type === "pathway" && data.hasResults !== undefined) {
        hasMagmaPathwaysResults.value = data.hasResults;
    }
};

const onPigeanDataLoaded = (data) => {
    if (data.type === "gene" && data.hasResults !== undefined) {
        hasPigeanGeneResults.value = data.hasResults;
    }
    if (data.type === "geneSet" && data.hasResults !== undefined) {
        hasPigeanGeneSetResults.value = data.hasResults;
    }
};

// Watch for route changes
watch(
    () => route.query.dataset,
    (newDataset) => {
        if (newDataset && newDataset !== dataset.value) {
            dataset.value = newDataset;
            // Reset availability flags
            hasSldscResults.value = false;
            hasMagmaResults.value = false;
            hasMagmaPathwaysResults.value = false;
            hasPigeanGeneResults.value = false;
            hasPigeanGeneSetResults.value = false;
            checkResultsAvailability();
        }
    },
);

watch(
    () => route.query.tab,
    (newTab) => {
        if (newTab && newTab !== activeTab.value) {
            activeTab.value = newTab;
        }
    },
);

// On mount
onMounted(async () => {
    await checkResultsAvailability();
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

:deep(.dark .p-autocomplete .p-autocomplete-clear-icon),
:deep(.dark .p-inputnumber .p-inputnumber-clear-icon) {
    color: #cbd5f5;
}

:deep(.p-autocomplete .p-autocomplete-clear-icon:hover),
:deep(.p-inputnumber .p-inputnumber-clear-icon:hover) {
    color: #111827;
}
</style>
