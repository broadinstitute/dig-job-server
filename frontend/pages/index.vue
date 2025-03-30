<script setup>
import { ref } from "vue";
import { useUserStore } from "~/stores/UserStore.js";
import { useToast } from "primevue/usetoast";

const userStore = useUserStore();
const router = useRouter();
const toast = useToast();
const datasets = ref([]);
const totalRecords = ref(0);
const config = useRuntimeConfig();
const eventSources = ref({});
const helpPopover = ref(null);
const toggleHelp = (event) => {
    helpPopover.value.toggle(event);
};

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

        if (statusData.status.endsWith("SUCCEEDED")) {
            eventSource.close();
            delete eventSources.value[jobId];
            toast.add({
                severity: "success",
                summary: "Success",
                detail: `${statusData.method} completed successfully`,
            });
        } else if (statusData.status.endsWith("FAILED")) {
            eventSource.close();
            delete eventSources.value[jobId];
            toast.add({
                severity: "error",
                summary: "Error",
                detail: `${statusData.method} failed`,
            });
        }
    };

    eventSource.onerror = (error) => {
        console.error("EventSource failed:", error);
        eventSource?.close();
        delete eventSources.value[jobId];
    };
};

async function runSumstats(data) {
    const { job_id } = await userStore.startAnalysis(data.dataset, "sumstats");
    data.status = "RUNNING sumstats";
    listenForJobStatus(job_id, data);
    toast.add({
        severity: "success",
        summary: "Success",
        detail: "sumstats started successfully",
        life: 5000,
    });
}

async function runSldsc(data) {
    const { job_id } = await userStore.startAnalysis(data.dataset, "sldsc");
    data.status = "RUNNING sldsc";
    listenForJobStatus(job_id, data);
    toast.add({
        severity: "success",
        summary: "Success",
        detail: "SLDSC started successfully",
        life: 5000,
    });
}

async function handleDelete(dataSet) {
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
}

function progress(data) {
    if (data.status === "sumstats SUCCEEDED") {
        return 50;
    } else if (data.status === "sldsc SUCCEEDED") {
        return 100;
    }
    return 0; // Default
}
</script>
<template>
    <div class="grid grid-cols-12 gap-4 grid-cols-12 gap-6 m-6">
        <div class="col-span-12">
            <Toast position="top-center" />

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

            <!-- Popover with Timeline component -->
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
                                {{ data.ancestry }}
                            </template>
                        </Column>
                        <Column field="genome_build" header="Genome Build">
                            <template #body="{ data }">
                                {{ data.genome_build }}
                            </template>
                        </Column>
                        <Column header="Uploader">
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
                        <Column header="Analysis">
                            <template #body="{ data }">
                                <span>
                                    <Button
                                        v-if="!data.status"
                                        @click.prevent="runSumstats(data)"
                                        label="Run SumStats"
                                        size="small"
                                        icon="pi pi-play"
                                        outlined
                                    ></Button>
                                    <Button
                                        v-if="
                                            data.status === 'sumstats SUCCEEDED'
                                        "
                                        @click.prevent="runSldsc(data)"
                                        label="Run SLDSC"
                                        size="small"
                                        icon="pi pi-forward"
                                        outlined
                                    ></Button>
                                    <router-link
                                        v-if="data.status === 'sldsc SUCCEEDED'"
                                        :to="`/results?dataset=${data.dataset}`"
                                        target="_blank"
                                    >
                                        <Button
                                            label="View Results"
                                            size="small"
                                            outlined
                                            icon="pi pi-eye"
                                        ></Button>
                                    </router-link>
                                </span>
                            </template>
                        </Column>
                        <Column
                            header="Steps Completed"
                            :style="{ width: '10rem' }"
                        >
                            <template #body="{ data }">
                                <ProgressBar
                                    :showValue="false"
                                    :value="progress(data)"
                                    style="height: 6px"
                                />
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
    border-color: var(--primary-color);
}

/* :deep(.p-timeline .p-timeline-event-connector) {
    background-color: var(--primary-color);
} */

/* Add additional styling for the popover itself */
:deep(.p-popover) {
    max-width: 550px;
}
</style>
