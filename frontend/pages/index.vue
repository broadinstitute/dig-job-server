<script setup>
import { ref } from "vue";
import { useUserStore } from "~/stores/UserStore.js";
import { usePhenotypeStore } from "~/stores/PhenotypeStore.js";

const userStore = useUserStore();
const phenotypeStore = usePhenotypeStore();
const router = useRouter();
const toast = useToast();
const confirm = useConfirm();
const datasets = ref([]);
const totalRecords = ref(0);
const config = useRuntimeConfig();
const eventSources = ref({});
const helpPopover = ref(null);
const toggleHelp = (event) => {
    helpPopover.value.toggle(event);
};

// Ancestry mapping from codes to descriptive names
const ancestryMapping = {
    AFR: "African",
    AMR: "Native American",
    EAS: "East Asian",
    EUR: "European",
    SAS: "South Asian",
    MID: "Middle Eastern",
};

// Function to get descriptive name for ancestry code
function getAncestryName(code) {
    return ancestryMapping[code] || code; // Return the code itself if no mapping exists
}

// Timeline events for the workflow steps
const timelineEvents = [
    {
        title: "Upload",
        description: "Upload your dataset to begin analysis",
        icon: "pi pi-upload",
    },
    {
        title: "Run SumStats",
        description: "Process summary statistics for your dataset",
        icon: "pi pi-play",
    },
    {
        title: "Run SLDSC",
        description: "Run stratified LD score regression analysis",
        icon: "pi pi-forward",
    },
    {
        title: "View Results",
        description: "Analyze the output of the pipeline",
        icon: "pi pi-eye",
    },
];

onMounted(async () => {
    // Handle OAuth callback if present
    const route = useRoute();
    if (route.query.access_token && route.query.success === "true") {
        try {
            // Store the access token
            localStorage.setItem("authToken", route.query.access_token);
            localStorage.removeItem("isDefaultUser");

            // Show success message
            const wasCreated = route.query.created === "true";
            toast.add({
                severity: "success",
                summary: "Success",
                detail: wasCreated
                    ? "Account created and logged in successfully!"
                    : "Logged in successfully!",
                life: 3000,
            });

            // Clean up the URL by removing query parameters
            await navigateTo("/", { replace: true });
        } catch (error) {
            console.error("OAuth callback error:", error);
            toast.add({
                severity: "error",
                summary: "Error",
                detail: "Failed to complete login",
                life: 3000,
            });
        }
    } else if (route.query.success === "false" && route.query.error) {
        // Handle OAuth error
        toast.add({
            severity: "error",
            summary: "Login Failed",
            detail: decodeURIComponent(route.query.error),
            life: 5000,
        });

        // Clean up the URL
        await navigateTo("/", { replace: true });
    }

    datasets.value = await userStore.retrieveDatasets();
    datasets.value.forEach((data) => {
        if (data.status?.includes("RUNNING")) {
            console.log(
                `Connecting to running job for dataset: ${data.dataset}`,
            );
            listenForJobStatus(data.id, data);
        }
    });
    totalRecords.value = datasets.value.length;

    // Fetch phenotypes data
    await phenotypeStore.fetchPhenotypes();
});

onUnmounted(() => {
    Object.values(eventSources.value).forEach((es) => es.close());
    eventSources.value = {};
});

const listenForJobStatus = (jobId, data) => {
    // Close existing connection for this job if it exists
    if (eventSources.value[jobId]) {
        eventSources.value[jobId].close();
    }

    const eventSource = new EventSource(
        `${config.public.apiBaseUrl}/api/job-status/${jobId}`,
    );
    eventSources.value[jobId] = eventSource;

    eventSource.onmessage = async (event) => {
        if (!event.data) return; // Ignore keepalive messages

        const statusData = JSON.parse(event.data);
        console.log("Job status update:", statusData);

        // Update the status in the datasets table
        data.status = statusData.status;

        // Update the workflows data structure for button state
        const parts = statusData.status.split(" ");
        if (parts.length >= 1) {
            let method, status;
            if (statusData.status.startsWith("RUNNING ")) {
                method = parts[1]; // "RUNNING sldsc" -> method = "sldsc"
                status = "RUNNING";
            } else {
                method = parts[0]; // "sldsc SUCCEEDED" -> method = "sldsc"
                status = parts[1]; // "sldsc SUCCEEDED" -> status = "SUCCEEDED"
            }

            // Initialize workflows structure if needed
            if (!data.workflows) {
                data.workflows = {};
            }
            if (!data.workflows[method]) {
                data.workflows[method] = {};
            }

            // Update the status for this method
            data.workflows[method][method] = {
                status: status,
                updated_at: new Date().toISOString(),
            };
        }

        if (statusData.status.endsWith("SUCCEEDED")) {
            eventSource.close();
            delete eventSources.value[jobId];
            toast.add({
                severity: "success",
                summary: "Success",
                detail: `${statusData.status.split(" ")[0]} completed successfully`,
                life: 5000,
            });
        } else if (statusData.status.endsWith("FAILED")) {
            eventSource.close();
            delete eventSources.value[jobId];
            toast.add({
                severity: "error",
                summary: "Error",
                detail: `${statusData.status.split(" ")[0]} failed`,
                life: 5000,
            });
        }
    };

    eventSource.onerror = (error) => {
        console.error("EventSource failed:", error);
        eventSource?.close();
        delete eventSources.value[jobId];
    };
};

async function runSldsc(data) {
    const { job_id } = await userStore.startAnalysis(data.dataset, "sldsc");
    data.status = "RUNNING sldsc";
    listenForJobStatus(job_id, data);
    toast.add({
        severity: "success",
        summary: "Success",
        detail: "SLDSC analysis started successfully",
        life: 5000,
    });
}

async function runMagma(data) {
    const { job_id } = await userStore.startAnalysis(data.dataset, "magma");
    data.status = "RUNNING magma";
    listenForJobStatus(job_id, data);
    toast.add({
        severity: "success",
        summary: "Success",
        detail: "MAGMA analysis started successfully",
        life: 5000,
    });
}

// Helper function to get simple job status for sldsc or magma
function getJobStatus(data, method) {
    if (
        !data.workflows ||
        !data.workflows[method] ||
        !data.workflows[method][method]
    )
        return null;
    return data.workflows[method][method].status;
}

async function handleDelete(dataSet) {
    confirm.require({
        message: `Are you sure you want to delete the dataset "${dataSet}"?`,
        header: "Delete Confirmation",
        icon: "pi pi-exclamation-triangle",
        acceptClass: "p-button-danger",
        accept: async () => {
            await userStore.deleteDataset(dataSet);
            datasets.value = datasets.value.filter(
                (dataset) => dataset.dataset !== dataSet,
            );
            toast.add({
                severity: "success",
                summary: "Success",
                detail: "Dataset deleted successfully",
                life: 5000,
            });
        },
        reject: () => {
            toast.add({
                severity: "info",
                summary: "Cancelled",
                detail: "Dataset deletion cancelled",
                life: 5000,
            });
        },
    });
}

function progress(data) {
    if (data.status === "sumstats SUCCEEDED") {
        return 50;
    } else if (data.status === "sldsc SUCCEEDED") {
        return 100;
    }
    return 0; // Default
}

function viewResults(dataset) {
    router.push(`/results?dataset=${dataset}`);
}

function openInNewTab(dataset) {
    window.open(`/results?dataset=${dataset}`, "_blank");
}

function viewMagmaResults(dataset) {
    router.push(`/results?dataset=${dataset}&type=magma`);
}

function openMagmaResultsInNewTab(dataset) {
    window.open(`/results?dataset=${dataset}&type=magma`, "_blank");
}
</script>
<template>
    <div class="grid grid-cols-12 gap-4 grid-cols-12 gap-6 m-6">
        <div class="col-span-12">
            <Toast position="top-center" />
            <ConfirmDialog />

            <div class="flex justify-between items-center">
                <Button
                    icon="pi pi-question-circle"
                    label="Help"
                    size="small"
                    class="help-button ml-4"
                    aria-haspopup="true"
                    aria-controls="help-popover"
                    @click="toggleHelp"
                    outlined
                />
                <Button
                    @click="router.push('/upload')"
                    icon="pi pi-upload"
                    label="Upload Dataset"
                    size="small"
                    class="mx-4"
                ></Button>
            </div>

            <Popover ref="helpPopover">
                <div class="p-4 w-[500px]">
                    <h3 class="mb-3 text-lg font-bold">Workflow Steps</h3>
                    <Timeline :value="timelineEvents" class="w-full">
                        <template #marker="slotProps">
                            <span
                                class="flex w-8 h-8 items-center justify-center text-white rounded-full shadow-md"
                                :class="'bg-primary'"
                            >
                                <i :class="slotProps.item.icon"></i>
                            </span>
                        </template>
                        <template #content="slotProps">
                            <div class="flex flex-col ml-4">
                                <span class="font-bold mb-1">{{
                                    slotProps.item.title
                                }}</span>
                                <p class="text-sm">
                                    {{ slotProps.item.description }}
                                </p>
                            </div>
                        </template>
                    </Timeline>
                </div>
            </Popover>

            <Card class="m-4">
                <template #header></template>
                <template #content>
                    <DataTable
                        :value="datasets"
                        class="mb-4"
                        :paginator="true"
                        rowHover
                        :rows="10"
                        :rowsPerPageOptions="[5, 10, 20]"
                        stripedRows
                        size="small"
                        sortField="uploaded_at"
                        :sortOrder="-1"
                    >
                        <Column field="dataset" header="Dataset">
                            <template #body="{ data }">
                                <span
                                    class="filename"
                                    v-tooltip.right="{
                                        value: `${data.file_name}`,
                                        class: 'filename-tooltip',
                                    }"
                                    >{{ data.dataset }}</span
                                >
                            </template>
                        </Column>
                        <Column field="ancestry" header="Ancestry">
                            <template #body="{ data }">
                                {{ getAncestryName(data.ancestry) }}
                            </template>
                        </Column>
                        <Column field="phenotype" header="Phenotype">
                            <template #body="{ data }">
                                <template v-if="data.phenotype">
                                    <span
                                        v-tooltip.top="
                                            phenotypeStore.getPhenotypeByName(
                                                data.phenotype,
                                            )?.description || ''
                                        "
                                    >
                                        {{ data.phenotype }}
                                    </span>
                                </template>
                            </template>
                        </Column>
                        <Column field="genome_build" header="Genome Build">
                            <template #body="{ data }">
                                {{ data.genome_build }}
                            </template>
                        </Column>
                        <Column
                            header="Uploader"
                            v-if="userStore.user.username !== 'demo'"
                        >
                            <template #body="{ data }">
                                {{ data.uploaded_by }}
                            </template>
                        </Column>
                        <Column header="Date Uploaded">
                            <template #body="{ data }">
                                {{
                                    data.uploaded_at
                                        ? new Date(
                                              data.uploaded_at,
                                          ).toLocaleDateString()
                                        : ""
                                }}
                            </template>
                        </Column>
                        <Column header="Status">
                            <template #body="{ data }">
                                <template
                                    v-if="
                                        data.status &&
                                        (data.status.includes('RUNNING') ||
                                            data.status.endsWith('SUCCEEDED') ||
                                            data.status.endsWith('FAILED'))
                                    "
                                >
                                    <router-link
                                        :to="`/log/${data.id}`"
                                        v-tooltip.top="'View log'"
                                    >
                                        <Tag
                                            v-if="
                                                data.status.includes('RUNNING')
                                            "
                                            severity="warn"
                                            rounded
                                        >
                                            <i
                                                class="pi pi-spin pi-spinner mr-2"
                                            ></i>
                                            {{ data.status }}
                                        </Tag>
                                        <Tag
                                            v-else
                                            :severity="
                                                data.status ===
                                                'sumstats SUCCEEDED'
                                                    ? 'info'
                                                    : data.status.endsWith(
                                                            'SUCCEEDED',
                                                        )
                                                      ? 'success'
                                                      : 'danger'
                                            "
                                            rounded
                                        >
                                            {{ data.status }}
                                        </Tag>
                                    </router-link>
                                </template>
                                <template v-else-if="!data.status">
                                    <Tag severity="secondary" rounded>
                                        uploaded
                                    </Tag>
                                </template>
                                <template v-else>
                                    {{ data.status }}
                                </template>
                            </template>
                        </Column>
                        <Column header="Analysis" :style="{ width: '15rem' }">
                            <template #body="{ data }">
                                <div class="flex gap-2 flex-wrap">
                                    <!-- SLDSC Analysis -->
                                    <Button
                                        v-if="!getJobStatus(data, 'sldsc')"
                                        @click.prevent="runSldsc(data)"
                                        label="Run SLDSC"
                                        size="small"
                                        icon="pi pi-chart-line"
                                        outlined
                                        class="flex-1 min-w-0"
                                    />
                                    <Button
                                        v-else-if="
                                            getJobStatus(data, 'sldsc') ===
                                            'RUNNING'
                                        "
                                        label="SLDSC Running"
                                        size="small"
                                        icon="pi pi-spin pi-spinner"
                                        severity="warn"
                                        outlined
                                        disabled
                                        class="flex-1 min-w-0"
                                    />
                                    <SplitButton
                                        v-else-if="
                                            getJobStatus(data, 'sldsc') ===
                                            'SUCCEEDED'
                                        "
                                        label="SLDSC Results"
                                        class="whitespace-nowrap flex-1 min-w-0"
                                        icon="pi pi-eye"
                                        size="small"
                                        outlined
                                        @click="viewResults(data.dataset)"
                                        :model="[
                                            {
                                                label: 'Open in new tab',
                                                icon: 'pi pi-external-link',
                                                command: () =>
                                                    openInNewTab(data.dataset),
                                            },
                                        ]"
                                    />
                                    <Button
                                        v-else-if="
                                            getJobStatus(data, 'sldsc') ===
                                            'FAILED'
                                        "
                                        label="SLDSC Failed"
                                        size="small"
                                        icon="pi pi-times"
                                        severity="danger"
                                        outlined
                                        disabled
                                        class="flex-1 min-w-0"
                                    />

                                    <!-- MAGMA Analysis -->
                                    <Button
                                        v-if="!getJobStatus(data, 'magma')"
                                        @click.prevent="runMagma(data)"
                                        label="Run MAGMA"
                                        size="small"
                                        icon="pi pi-chart-bar"
                                        outlined
                                        class="flex-1 min-w-0"
                                    />
                                    <Button
                                        v-else-if="
                                            getJobStatus(data, 'magma') ===
                                            'RUNNING'
                                        "
                                        label="MAGMA Running"
                                        size="small"
                                        icon="pi pi-spin pi-spinner"
                                        severity="warn"
                                        outlined
                                        disabled
                                        class="flex-1 min-w-0"
                                    />
                                    <SplitButton
                                        v-else-if="
                                            getJobStatus(data, 'magma') ===
                                            'SUCCEEDED'
                                        "
                                        label="MAGMA Results"
                                        class="whitespace-nowrap flex-1 min-w-0"
                                        icon="pi pi-eye"
                                        size="small"
                                        outlined
                                        @click="viewMagmaResults(data.dataset)"
                                        :model="[
                                            {
                                                label: 'Open in new tab',
                                                icon: 'pi pi-external-link',
                                                command: () =>
                                                    openMagmaResultsInNewTab(
                                                        data.dataset,
                                                    ),
                                            },
                                        ]"
                                    />
                                    <Button
                                        v-else-if="
                                            getJobStatus(data, 'magma') ===
                                            'FAILED'
                                        "
                                        label="MAGMA Failed"
                                        size="small"
                                        icon="pi pi-times"
                                        severity="danger"
                                        outlined
                                        disabled
                                        class="flex-1 min-w-0"
                                    />
                                </div>
                            </template>
                        </Column>

                        <Column
                            header="Delete"
                            :style="{ width: '4rem' }"
                            class="ml-4 text-right"
                            v-if="userStore.user.username !== 'demo'"
                        >
                            <template #body="{ data }">
                                <Button
                                    icon="pi pi-trash"
                                    size="small"
                                    @click="handleDelete(data.dataset)"
                                    v-tooltip.top="'Delete this dataset?'"
                                    outlined
                                    severity="danger"
                                />
                            </template>
                        </Column>
                    </DataTable>
                </template>
                <template #footer
                    ><small>Total records: {{ totalRecords }}</small></template
                >
            </Card>
        </div>
    </div>
</template>
<style scoped>
/* Timeline styling */
:deep(.p-timeline-event-opposite) {
    flex: 0;
    padding: 0 1rem;
}

:deep(.p-timeline-event-content) {
    padding: 0 1rem;
}

:deep(.p-timeline .p-timeline-event-marker) {
    border-color: var(--p-primary-color);
}

/* Step dots styling */
.step-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: #e0e0e0;
    border: 1px solid #bdbdbd;
    transition: all 0.2s ease;
}

.step-dot.step-completed {
    background-color: var(--p-primary-color);
    border-color: var(--p-primary-color);
    box-shadow: 0 0 3px rgba(0, 0, 0, 0.2);
}

.step-dot.step-running {
    background-color: #f59e0b;
    border-color: #f59e0b;
    animation: pulse 2s infinite;
}

.step-dot.step-failed {
    background-color: #ef4444;
    border-color: #ef4444;
}

@keyframes pulse {
    0%,
    100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}

/* Add additional styling for the popover itself */
:deep(.p-popover) {
    max-width: 550px;
}
</style>
