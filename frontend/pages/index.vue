<script setup>
import { ref } from "vue";
import { useUserStore } from "~/stores/UserStore.js";
import { useToast } from "primevue/usetoast";
const userStore = useUserStore();
const router = useRouter();
const toast = useToast();
const datasets = ref([]);
const config = useRuntimeConfig();
const eventSources = ref({});

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
            <Stepper class="basis-[50rem] mb-8" linear>
                <StepList>
                    <Step value="1">Upload</Step>
                    <Step value="2">Run SumStats</Step>
                    <Step value="3">Run SLDSC</Step>
                    <Step value="4">View Results</Step>
                </StepList>
            </Stepper>
            <div class="flex justify-between items-center">
                <Button
                    @click="router.push('/upload')"
                    icon="pi pi-upload"
                    label="Upload Dataset"
                    size="small"
                    class="mx-4"
                ></Button>
            </div>
            <Card class="m-4">
                <template #header> </template>
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
                        <Column header="Uploaded At">
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
                                            severity="secondary"
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
                                        label="Run Sum Stats"
                                        size="small"
                                        icon="pi pi-play"
                                    ></Button>
                                    <Button
                                        v-if="
                                            data.status === 'sumstats SUCCEEDED'
                                        "
                                        @click.prevent="runSldsc(data)"
                                        label="Run SLDSC"
                                        size="small"
                                        icon="pi pi-forward"
                                    ></Button>
                                    <Button
                                        v-if="data.status === 'sldsc SUCCEEDED'"
                                        @click="
                                            router.push(
                                                `/results?dataset=${data.dataset}`,
                                            )
                                        "
                                        label="View Results"
                                        size="small"
                                        outlined
                                        icon="pi pi-eye"
                                    ></Button>
                                </span>
                            </template>
                        </Column>
                        <Column header="Progress" :style="{ width: '10rem' }">
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
            </Card>
        </div>
    </div>
</template>
