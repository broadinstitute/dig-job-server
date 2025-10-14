<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "nuxt/app";
import { useUserStore } from "~/stores/UserStore.js";
import { usePhenotypeStore } from "~/stores/PhenotypeStore.js";

const userStore = useUserStore();
const phenotypeStore = usePhenotypeStore();
const route = useRoute();
const router = useRouter();
const toast = useToast();

// Ancestry mapping from codes to descriptive names
const ancestryMapping = {
    AFR: "African",
    AMR: "Ad Mixed American",
    EAS: "East Asian",
    EUR: "European",
    SAS: "South Asian",
    MID: "Middle Eastern",
};

// Function to get descriptive name for ancestry code
function getAncestryName(code) {
    return ancestryMapping[code] || code; // Return the code itself if no mapping exists
}

// Get dataset from query parameter
const dataset = computed(() => route.query.dataset);

// Data refs
const results = ref([]);
const totalRecords = ref(0);
const loading = ref(false);
const phenotypes = ref([]);
const jobId = ref("");

// DataTable state
const first = ref(0);
const rows = ref(10);
const sortField = ref("pValue");
const sortOrder = ref(1); // 1 for ascending, -1 for descending

// Fetch results from API
async function fetchResults() {
    if (!dataset.value) {
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "No dataset specified",
            life: 5000,
        });
        return;
    }

    loading.value = true;
    try {
        const response = await userStore.axios.get(
            `/api/annot-sldsc-results/${dataset.value}`,
            {
                params: {
                    first: first.value,
                    rows: rows.value,
                    sort_field: sortField.value,
                    sort_order: sortOrder.value,
                },
            },
        );

        results.value = response.data.items || [];
        totalRecords.value = response.data.totalRecords || 0;
        phenotypes.value = response.data.phenotypes || [];
        jobId.value = response.data.jobId || "";
    } catch (error) {
        console.error("Error fetching annotation results:", error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to fetch annotation results",
            life: 5000,
        });
    } finally {
        loading.value = false;
    }
}

// Handle page change
function onPage(event) {
    first.value = event.first;
    rows.value = event.rows;
    fetchResults();
}

// Handle sort
function onSort(event) {
    sortField.value = event.sortField;
    sortOrder.value = event.sortOrder;
    fetchResults();
}

// Format p-value for display
function formatPValue(value) {
    if (!value) return "N/A";
    if (value < 0.0001) {
        return value.toExponential(2);
    }
    return value.toFixed(6);
}

// Format enrichment value
function formatEnrichment(value) {
    if (!value) return "N/A";
    return value.toFixed(2);
}

// Get severity for p-value display
function getPValueSeverity(pValue) {
    if (pValue < 0.00001) return "success";
    if (pValue < 0.001) return "info";
    if (pValue < 0.05) return "warn";
    return "secondary";
}

// Navigate back to datasets page
function goBack() {
    router.push("/datasets");
}

// Initialize
onMounted(async () => {
    // Fetch phenotypes for tooltips
    await phenotypeStore.fetchPhenotypes();

    // Fetch results
    await fetchResults();
});
</script>

<template>
    <div class="grid grid-cols-12 gap-6 m-6">
        <div class="col-span-12">
            <Toast position="top-center" />

            <!-- Header -->
            <div>
                <h2 class="text-2xl font-bold mb-4 text-center">
                    Annotation SLDSC Results
                </h2>
            </div>

            <div class="flex justify-between items-center">
                <Button
                    label="Back to Datasets"
                    icon="pi pi-arrow-left"
                    @click="goBack"
                    class="mb-4"
                    outlined
                    size="small"
                />
                <Button
                    icon="pi pi-download"
                    label="Download Annotation Results"
                    size="small"
                />
            </div>

            <!-- Dataset Info Card -->
            <Card class="mb-4">
                <template #content>
                    <div class="flex flex-col gap-2">
                        <div class="flex items-center gap-2">
                            <span class="font-semibold">Dataset:</span>
                            <span class="font-mono text-primary">{{
                                dataset
                            }}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="font-semibold">Total Results:</span>
                            <span>{{ totalRecords }}</span>
                        </div>
                        <div
                            v-if="phenotypes.length > 0"
                            class="flex items-center gap-2"
                        >
                            <span class="font-semibold">Phenotypes:</span>
                            <span>{{ phenotypes.length }}</span>
                        </div>
                    </div>
                </template>
            </Card>

            <!-- Results Table -->
            <Card>
                <template #header>
                    <div class="p-4 border-b border-surface-border">
                        <div class="flex flex-wrap gap-6 text-sm justify-end">
                            <!-- Enrichment Legend -->
                            <div class="flex items-center gap-3">
                                <span
                                    class="font-medium text-gray-700 dark:text-gray-300"
                                    >Enrichment:</span
                                >
                                <div class="flex items-center gap-2">
                                    <span class="text-green-600 font-bold"
                                        >+</span
                                    >
                                    <span
                                        class="text-gray-600 dark:text-gray-400"
                                        >Positive</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <span class="text-red-600 font-bold"
                                        >−</span
                                    >
                                    <span
                                        class="text-gray-600 dark:text-gray-400"
                                        >Negative</span
                                    >
                                </div>
                            </div>

                            <!-- P-Value Legend -->
                            <div class="flex items-center gap-3 flex-wrap">
                                <span
                                    class="font-medium text-gray-700 dark:text-gray-300"
                                    >P-Value:</span
                                >
                                <div class="flex items-center gap-2">
                                    <Tag
                                        value="< 0.00001"
                                        severity="success"
                                        rounded
                                        size="small"
                                    />
                                    <span
                                        class="text-gray-600 dark:text-gray-400 text-xs"
                                        >Highly sig.</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <Tag
                                        value="< 0.001"
                                        severity="info"
                                        rounded
                                        size="small"
                                    />
                                    <span
                                        class="text-gray-600 dark:text-gray-400 text-xs"
                                        >Significant</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <Tag
                                        value="< 0.05"
                                        severity="warn"
                                        rounded
                                        size="small"
                                    />
                                    <span
                                        class="text-gray-600 dark:text-gray-400 text-xs"
                                        >Marginal</span
                                    >
                                </div>
                                <div class="flex items-center gap-2">
                                    <Tag
                                        value="≥ 0.05"
                                        severity="secondary"
                                        rounded
                                        size="small"
                                    />
                                    <span
                                        class="text-gray-600 dark:text-gray-400 text-xs"
                                        >Not sig.</span
                                    >
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
                <template #content>
                    <DataTable
                        :value="results"
                        :lazy="true"
                        :paginator="true"
                        :rows="rows"
                        :totalRecords="totalRecords"
                        :loading="loading"
                        :first="first"
                        @page="onPage"
                        @sort="onSort"
                        :rowsPerPageOptions="[10, 25, 50]"
                        :sortField="sortField"
                        :sortOrder="sortOrder"
                        stripedRows
                        size="small"
                    >
                        <template #empty>
                            <div class="text-center p-4">No results found.</div>
                        </template>

                        <template #loading>
                            <div class="text-center p-4">
                                Loading results...
                            </div>
                        </template>

                        <!-- Phenotype Column -->
                        <Column
                            field="phenotype"
                            header="Phenotype"
                            sortable
                            :style="{ minWidth: '12rem', maxWidth: '20rem' }"
                        >
                            <template #body="{ data }">
                                <a
                                    :href="`https://a2f.hugeamp.org/phenotype.html?phenotype=${data.phenotype}`"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    v-tooltip.top="{
                                        value:
                                            phenotypeStore.getPhenotypeByName(
                                                data.phenotype,
                                            )?.description || data.phenotype,
                                        showDelay: 500,
                                    }"
                                    class="overflow-hidden text-ellipsis whitespace-nowrap block text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                >
                                    {{
                                        phenotypeStore.getPhenotypeByName(
                                            data.phenotype,
                                        )?.description || data.phenotype
                                    }}
                                </a>
                            </template>
                        </Column>

                        <!-- Ancestry Column -->
                        <Column
                            field="ancestry"
                            header="Ancestry"
                            sortable
                            :style="{ width: '10rem' }"
                        >
                            <template #body="{ data }">
                                {{ getAncestryName(data.ancestry) }}
                            </template>
                        </Column>

                        <!-- Enrichment Column -->
                        <Column
                            field="enrichment"
                            header="Enrichment"
                            sortable
                            :style="{ width: '10rem' }"
                        >
                            <template #body="{ data }">
                                <span
                                    :class="{
                                        'text-green-600': data.enrichment > 0,
                                        'text-red-600': data.enrichment < 0,
                                    }"
                                    class="font-medium"
                                >
                                    {{ formatEnrichment(data.enrichment) }}
                                </span>
                            </template>
                        </Column>

                        <!-- P-Value Column -->
                        <Column
                            field="pValue"
                            header="P-Value"
                            sortable
                            :style="{ width: '12rem' }"
                        >
                            <template #body="{ data }">
                                <Tag
                                    :value="formatPValue(data.pValue)"
                                    :severity="getPValueSeverity(data.pValue)"
                                    rounded
                                />
                            </template>
                        </Column>
                    </DataTable>
                </template>
            </Card>
        </div>
    </div>
</template>

<style scoped>
.p-column-filter {
    width: 100%;
}

:deep(.p-datatable-thead > tr > th) {
    background-color: var(--surface-elevation-1);
}

:deep(.p-paginator) {
    padding: 1rem;
}
</style>
