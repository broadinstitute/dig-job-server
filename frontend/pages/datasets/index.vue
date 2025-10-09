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
const bedFiles = ref([]);
const totalBedFiles = ref(0);
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
        title: "Run Analysis",
        description: "Select analysis to run",
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

    // Fetch BED annotation files
    await fetchBedFiles();
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

// Helper function to get available workflows that can be run
function getAvailableWorkflows(data) {
    const workflows = [];

    // Check SLDSC
    if (!getJobStatus(data, "sldsc")) {
        workflows.push({
            label: "Run SLDSC",
            icon: "pi pi-chart-line",
            method: "sldsc",
            command: () => runSldsc(data),
        });
    }

    // Check MAGMA
    if (!getJobStatus(data, "magma")) {
        workflows.push({
            label: "Run MAGMA",
            icon: "pi pi-chart-bar",
            method: "magma",
            command: () => runMagma(data),
        });
    }

    return workflows;
}

// Helper function to get all workflow options for dropdown (including failed as disabled)
function getAllWorkflowOptions(data) {
    const options = [];

    // Check SLDSC
    const sldscStatus = getJobStatus(data, "sldsc");
    const sldscWorkflow = data.workflows?.sldsc?.sldsc;

    if (!sldscStatus) {
        // Not run yet - available to run
        options.push({
            label: "Run SLDSC",
            icon: "pi pi-chart-line",
            method: "sldsc",
            status: "available",
            severity: "secondary",
            command: () => runSldsc(data),
            disabled: false,
        });
    } else if (sldscStatus === "FAILED") {
        // Failed - show as failed option
        options.push({
            label: "SLDSC (Failed)",
            icon: "pi pi-times-circle",
            method: "sldsc",
            status: "failed",
            severity: "danger",
            command: () =>
                showWorkflowDialog(data, "sldsc", "failed", sldscWorkflow),
            disabled: false,
        });
    } else if (sldscStatus === "SUCCEEDED") {
        // Succeeded - show as succeeded option
        options.push({
            label: "SLDSC (Completed)",
            icon: "pi pi-check-circle",
            method: "sldsc",
            status: "succeeded",
            severity: "success",
            command: () =>
                showWorkflowDialog(data, "sldsc", "succeeded", sldscWorkflow),
            disabled: false,
        });
    } else if (sldscStatus === "RUNNING") {
        // Running - show as running option
        options.push({
            label: "SLDSC (Running)",
            icon: "pi pi-spin pi-spinner",
            method: "sldsc",
            status: "running",
            severity: "warn",
            command: () => {},
            disabled: true,
        });
    }

    // Check MAGMA
    const magmaStatus = getJobStatus(data, "magma");
    const magmaWorkflow = data.workflows?.magma?.magma;

    if (!magmaStatus) {
        // Not run yet - available to run
        options.push({
            label: "Run MAGMA",
            icon: "pi pi-chart-bar",
            method: "magma",
            status: "available",
            severity: "secondary",
            command: () => runMagma(data),
            disabled: false,
        });
    } else if (magmaStatus === "FAILED") {
        // Failed - show as failed option
        options.push({
            label: "MAGMA (Failed)",
            icon: "pi pi-times-circle",
            method: "magma",
            status: "failed",
            severity: "danger",
            command: () =>
                showWorkflowDialog(data, "magma", "failed", magmaWorkflow),
            disabled: false,
        });
    } else if (magmaStatus === "SUCCEEDED") {
        // Succeeded - show as succeeded option
        options.push({
            label: "MAGMA (Completed)",
            icon: "pi pi-check-circle",
            method: "magma",
            status: "succeeded",
            severity: "success",
            command: () =>
                showWorkflowDialog(data, "magma", "succeeded", magmaWorkflow),
            disabled: false,
        });
    } else if (magmaStatus === "RUNNING") {
        // Running - show as running option
        options.push({
            label: "MAGMA (Running)",
            icon: "pi pi-spin pi-spinner",
            method: "magma",
            status: "running",
            severity: "warn",
            command: () => {},
            disabled: true,
        });
    }

    return options;
}

// Helper function to get running workflows
function getRunningWorkflows(data) {
    const workflows = [];

    // Check SLDSC
    if (getJobStatus(data, "sldsc") === "RUNNING") {
        workflows.push({
            label: "SLDSC Running",
            icon: "pi pi-spin pi-spinner",
            method: "sldsc",
        });
    }

    // Check MAGMA
    if (getJobStatus(data, "magma") === "RUNNING") {
        workflows.push({
            label: "MAGMA Running",
            icon: "pi pi-spin pi-spinner",
            method: "magma",
        });
    }

    return workflows;
}

// Helper function to get successful workflows
function getSuccessfulWorkflows(data) {
    const workflows = [];

    // Check SLDSC
    if (getJobStatus(data, "sldsc") === "SUCCEEDED") {
        workflows.push({
            label: "View SLDSC",
            icon: "pi pi-eye",
            method: "sldsc",
        });
    }

    // Check MAGMA
    if (getJobStatus(data, "magma") === "SUCCEEDED") {
        workflows.push({
            label: "View MAGMA",
            icon: "pi pi-eye",
            method: "magma",
        });
    }

    return workflows;
}

// Helper function to get result button configuration
function getResultButtonConfig(data) {
    const successfulWorkflows = getSuccessfulWorkflows(data);

    if (successfulWorkflows.length === 0) {
        return null;
    }

    // Always show "View Results" for any successful workflows
    return {
        label: "View Results",
        icon: "pi pi-eye",
        command: () => viewResults(data.dataset), // Results page will handle showing appropriate tabs
        dropdownItems: [
            {
                label: "Open in new tab",
                icon: "pi pi-external-link",
                command: () => openInNewTab(data.dataset),
            },
        ],
    };
}

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

// Helper function to get overall workflow status for analysis button styling
function getOverallWorkflowStatus(data) {
    if (!data.workflows && !data.status) return null;

    const workflowMethods = ["sldsc", "magma"]; // Main analysis workflows
    const statuses = [];

    // Collect all workflow statuses from workflows structure
    for (const method of workflowMethods) {
        const status = getJobStatus(data, method);
        if (status) {
            statuses.push(status);
        }
    }

    // Also check the general status field for sumstats or other workflows
    if (data.status) {
        // Extract status from patterns like "sumstats SUCCEEDED", "sldsc RUNNING", etc.
        const statusParts = data.status.split(" ");
        if (statusParts.length >= 2) {
            const method = statusParts[0];
            const status = statusParts[1];
            // Only add if it's not already captured in workflows structure
            if (
                !workflowMethods.includes(method) ||
                !getJobStatus(data, method)
            ) {
                statuses.push(status);
            }
        }
    }

    if (statuses.length === 0) return null;

    // If all workflows failed, return 'all-failed'
    if (statuses.every((status) => status === "FAILED")) {
        return "all-failed";
    }

    // If some workflows failed, return 'some-failed'
    if (statuses.some((status) => status === "FAILED")) {
        return "some-failed";
    }

    // If all workflows succeeded, return 'all-succeeded'
    if (statuses.every((status) => status === "SUCCEEDED")) {
        return "all-succeeded";
    }

    // If any are running, return 'running'
    if (statuses.some((status) => status === "RUNNING")) {
        return "running";
    }

    // Default to partial success/mixed state
    return "mixed";
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

async function confirmAndRunWorkflow(data, workflow) {
    const workflowDescriptions = {
        sldsc: "SLDSC (Stratified LD Score Regression) analysis will calculate heritability and genetic correlations for your dataset.",
        magma: "MAGMA analysis will perform gene-based association testing and pathway analysis on your dataset.",
    };

    confirm.require({
        group: "workflow-confirmation",
        header: "Confirm analysis to run.",
        icon: "pi pi-question-circle",
        acceptClass: "p-button-primary",
        rejectClass: "p-button-secondary",
        data: {
            workflow: workflow,
            dataset: data.dataset,
            description:
                workflowDescriptions[workflow.method] ||
                `${workflow.method} analysis will be performed on your dataset.`,
        },
        accept: async () => {
            try {
                await workflow.command();
                toast.add({
                    severity: "success",
                    summary: "Analysis Started",
                    detail: `${workflow.method.toUpperCase()} analysis started successfully`,
                    life: 5000,
                });
            } catch (error) {
                toast.add({
                    severity: "error",
                    summary: "Error",
                    detail: `Failed to start ${workflow.method.toUpperCase()} analysis`,
                    life: 5000,
                });
            }
        },
        reject: () => {
            toast.add({
                severity: "info",
                summary: "Cancelled",
                detail: "Analysis cancelled",
                life: 3000,
            });
        },
    });
}

function showWorkflowDialog(data, method, status, workflowData) {
    if (status === "failed") {
        // Show dialog for failed workflows
        confirm.require({
            group: "workflow-status",
            header: `${method.toUpperCase()} Analysis Failed`,
            icon: "pi pi-times-circle",
            acceptClass: "p-button-primary",
            rejectClass: "p-button-secondary",
            acceptLabel: "Upload New Dataset",
            rejectLabel: "View Log",
            data: {
                method: method,
                dataset: data.dataset,
                status: status,
                workflowData: workflowData,
                isFailure: true,
            },
            accept: () => {
                // Navigate to upload page
                router.push("/upload");
            },
            reject: () => {
                // Navigate to log page with method context
                router.push(`/log/${data.id}?method=${method}`);
            },
        });
    } else if (status === "succeeded") {
        // Show dialog for successful workflows
        const updatedAt = workflowData?.updated_at
            ? new Date(workflowData.updated_at).toLocaleString()
            : "Unknown";

        confirm.require({
            group: "workflow-status",
            header: `${method.toUpperCase()} Analysis Completed`,
            icon: "pi pi-check-circle",
            acceptClass: "p-button-primary",
            rejectClass: "p-button-secondary",
            acceptLabel: "View Results",
            rejectLabel: "View Log",
            data: {
                method: method,
                dataset: data.dataset,
                status: status,
                workflowData: workflowData,
                updatedAt: updatedAt,
                isFailure: false,
            },
            accept: () => {
                // Navigate to results page with specific tab selected
                router.push(`/results?dataset=${data.dataset}&tab=${method}`);
            },
            reject: () => {
                // Navigate to log page with method context
                router.push(`/log/${data.id}?method=${method}`);
            },
        });
    }
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

// BED Files Functions
async function fetchBedFiles() {
    try {
        const response = await userStore.getBedFiles();
        bedFiles.value = response || [];

        // Check for running jobs and reconnect to their status streams
        bedFiles.value.forEach((bedFile) => {
            // Check if any workflow is running
            if (bedFile.workflows) {
                for (const [method, workflows] of Object.entries(
                    bedFile.workflows,
                )) {
                    for (const [workflowName, workflowData] of Object.entries(
                        workflows,
                    )) {
                        if (workflowData.status === "RUNNING") {
                            console.log(
                                `Reconnecting to running ${method} job for BED file: ${bedFile.dataset_name}`,
                            );
                            bedFile.status = `RUNNING ${method}`;
                            listenForJobStatus(bedFile.id, bedFile);
                        } else if (
                            workflowData.status === "SUCCEEDED" ||
                            workflowData.status === "FAILED"
                        ) {
                            // Set the status for display
                            bedFile.status = `${method} ${workflowData.status}`;
                        }
                    }
                }
            }
        });

        totalBedFiles.value = bedFiles.value.length;
    } catch (error) {
        console.error("Error fetching BED files:", error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to fetch BED annotation files",
            life: 5000,
        });
    }
}

function formatFileSize(bytes) {
    if (!bytes) return "N/A";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

async function downloadBedFile(datasetName, filename) {
    try {
        await userStore.downloadBedFile(datasetName);
        toast.add({
            severity: "success",
            summary: "Success",
            detail: `Downloading ${filename}`,
            life: 3000,
        });
    } catch (error) {
        console.error("Error downloading BED file:", error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to download file",
            life: 5000,
        });
    }
}

async function handleDeleteBedFile(datasetName, filename) {
    confirm.require({
        message: `Are you sure you want to delete ${filename}?`,
        header: "Delete Confirmation",
        icon: "pi pi-exclamation-triangle",
        acceptClass: "p-button-danger",
        accept: async () => {
            try {
                await userStore.deleteBedFile(datasetName);
                await fetchBedFiles();
                toast.add({
                    severity: "success",
                    summary: "Success",
                    detail: "BED file deleted successfully",
                    life: 3000,
                });
            } catch (error) {
                console.error("Error deleting BED file:", error);
                toast.add({
                    severity: "error",
                    summary: "Error",
                    detail: "Failed to delete BED file",
                    life: 5000,
                });
            }
        },
    });
}

// BED File Workflow Functions
function getBedWorkflowOptions(data) {
    const options = [];

    // Check if annot-sldsc has been run
    const annotSldscStatus =
        data.workflows?.["annot-sldsc"]?.["annot-sldsc"]?.status;

    if (!annotSldscStatus) {
        // Not run yet - available to run
        options.push({
            label: "Run Annot-SLDSC",
            icon: "pi pi-chart-line",
            method: "annot-sldsc",
            status: "available",
            severity: "secondary",
            command: () => runBedAnalysis(data, "annot-sldsc"),
            disabled: false,
        });
    } else if (annotSldscStatus === "FAILED") {
        // Failed - show as failed option
        options.push({
            label: "Annot-SLDSC (Failed)",
            icon: "pi pi-times-circle",
            method: "annot-sldsc",
            status: "failed",
            severity: "danger",
            command: () => {
                // Navigate to log page
                router.push(`/log/${data.id}?method=annot-sldsc`);
            },
            disabled: false,
        });
    } else if (annotSldscStatus === "SUCCEEDED") {
        // Succeeded - show as succeeded option
        options.push({
            label: "Annot-SLDSC (Completed)",
            icon: "pi pi-check-circle",
            method: "annot-sldsc",
            status: "succeeded",
            severity: "success",
            command: () => {
                // Navigate to results or log page
                router.push(`/log/${data.id}?method=annot-sldsc`);
            },
            disabled: false,
        });
    } else if (annotSldscStatus === "RUNNING") {
        // Running - show as running option
        options.push({
            label: "Annot-SLDSC (Running)",
            icon: "pi pi-spin pi-spinner",
            method: "annot-sldsc",
            status: "running",
            severity: "warn",
            command: () => {},
            disabled: true,
        });
    }

    return options;
}

async function runBedAnalysis(data, method) {
    try {
        const { job_id } = await userStore.startAnalysis(
            data.dataset_name,
            method,
        );

        // Update status and start listening for updates
        data.status = `RUNNING ${method}`;
        listenForJobStatus(job_id, data);

        toast.add({
            severity: "success",
            summary: "Success",
            detail: `${method.toUpperCase()} analysis started successfully`,
            life: 5000,
        });
    } catch (error) {
        console.error("Error starting BED analysis:", error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to start analysis",
            life: 5000,
        });
    }
}

async function confirmAndRunBedWorkflow(data, workflow) {
    confirm.require({
        group: "workflow-confirmation",
        header: "Confirm analysis to run.",
        icon: "pi pi-question-circle",
        acceptClass: "p-button-primary",
        rejectClass: "p-button-secondary",
        data: {
            workflow: workflow,
            dataset: data.dataset_name,
            description:
                "Annotation-based SLDSC analysis will calculate cell-type-specific enrichment using your BED file annotations.",
        },
        accept: async () => {
            try {
                await workflow.command();
            } catch (error) {
                toast.add({
                    severity: "error",
                    summary: "Error",
                    detail: "Failed to start analysis",
                    life: 5000,
                });
            }
        },
        reject: () => {
            toast.add({
                severity: "info",
                summary: "Cancelled",
                detail: "Analysis cancelled",
                life: 3000,
            });
        },
    });
}

// Helper function to get result button configuration for BED files
function getBedResultButtonConfig(data) {
    // Check if annot-sldsc has succeeded
    const annotSldscStatus =
        data.workflows?.["annot-sldsc"]?.["annot-sldsc"]?.status;

    if (annotSldscStatus === "SUCCEEDED") {
        return {
            label: "View Results",
            icon: "pi pi-eye",
            command: () => viewBedResults(data.dataset_name),
            dropdownItems: [
                {
                    label: "Open in new tab",
                    icon: "pi pi-external-link",
                    command: () => openBedResultsInNewTab(data.dataset_name),
                },
            ],
        };
    }

    return null;
}

function viewBedResults(dataset) {
    router.push(`/annot-results?dataset=${dataset}`);
}

function openBedResultsInNewTab(dataset) {
    window.open(`/annot-results?dataset=${dataset}`, "_blank");
}
</script>
<template>
    <div class="grid grid-cols-12 gap-4 grid-cols-12 gap-6 m-6">
        <div class="col-span-12">
            <Toast position="top-center" />
            <ConfirmDialog />
            <ConfirmDialog group="workflow-confirmation">
                <template #message="slotProps">
                    <div class="flex flex-col gap-4 p-4">
                        <div class="flex items-center gap-3">
                            <i
                                class="pi pi-question-circle text-xl text-primary"
                            ></i>
                            <div>
                                <p
                                    class="text-sm text-gray-600 dark:text-gray-300 mb-3"
                                >
                                    {{ slotProps.message.data.description }}
                                </p>
                            </div>
                        </div>
                        <div
                            class="bg-gray-50 dark:bg-gray-800 p-3 rounded border-l-4 border-primary"
                        >
                            <div class="flex items-center gap-2 mb-1">
                                <i
                                    class="pi pi-database text-sm dark:text-gray-300"
                                ></i>
                                <span
                                    class="font-medium text-sm dark:text-gray-200"
                                    >Dataset:</span
                                >
                            </div>
                            <span
                                class="text-sm font-mono bg-white dark:bg-gray-700 dark:text-gray-200 px-2 py-1 rounded"
                            >
                                {{ slotProps.message.data.dataset }}
                            </span>
                        </div>
                        <div class="flex justify-end mt-2">
                            <span
                                class="text-md text-gray-600 dark:text-gray-300"
                                >Do you want to proceed with this
                                analysis?</span
                            >
                        </div>
                    </div>
                </template>
            </ConfirmDialog>

            <ConfirmDialog group="workflow-status">
                <template #message="slotProps">
                    <div class="flex flex-col gap-4 p-4">
                        <!-- Failed workflow dialog -->
                        <div
                            v-if="slotProps.message.data.isFailure"
                            class="flex flex-col gap-3"
                        >
                            <div class="flex items-center gap-3">
                                <i
                                    class="pi pi-times-circle text-2xl text-red-500"
                                ></i>
                                <div>
                                    <h4
                                        class="font-semibold text-lg text-red-700 dark:text-red-400 mb-2"
                                    >
                                        {{
                                            slotProps.message.data.method.toUpperCase()
                                        }}
                                        Analysis Failed
                                    </h4>
                                    <p
                                        class="text-sm text-gray-600 dark:text-gray-300"
                                    >
                                        The
                                        {{
                                            slotProps.message.data.method.toUpperCase()
                                        }}
                                        analysis failed to complete
                                        successfully.
                                    </p>
                                </div>
                            </div>

                            <div
                                class="bg-red-50 dark:bg-red-900/20 p-3 rounded border-l-4 border-red-500"
                            >
                                <h5
                                    class="font-medium text-sm mb-2 text-red-700 dark:text-red-400"
                                >
                                    How to fix this:
                                </h5>
                                <ul
                                    class="text-sm text-gray-700 dark:text-gray-300 space-y-1 ml-4"
                                >
                                    <li>
                                        • Check your dataset format and ensure
                                        it meets the requirements
                                    </li>
                                    <li>
                                        • Verify your data has the correct
                                        columns and headers
                                    </li>
                                    <li>
                                        • Consider uploading a new, properly
                                        formatted dataset
                                    </li>
                                    <li>
                                        • Review the log file for specific error
                                        details
                                    </li>
                                </ul>
                            </div>

                            <div
                                class="bg-gray-50 dark:bg-gray-800 p-3 rounded border-l-4 border-gray-400"
                            >
                                <div class="flex items-center gap-2 mb-1">
                                    <i
                                        class="pi pi-database text-sm dark:text-gray-300"
                                    ></i>
                                    <span
                                        class="font-medium text-sm dark:text-gray-200"
                                        >Dataset:</span
                                    >
                                </div>
                                <span
                                    class="text-sm font-mono bg-white dark:bg-gray-700 dark:text-gray-200 px-2 py-1 rounded"
                                >
                                    {{ slotProps.message.data.dataset }}
                                </span>
                            </div>
                        </div>

                        <!-- Successful workflow dialog -->
                        <div v-else class="flex flex-col gap-3">
                            <div class="flex items-center gap-3">
                                <i
                                    class="pi pi-check-circle text-2xl text-green-500"
                                ></i>
                                <div>
                                    <h4
                                        class="font-semibold text-lg text-green-700 dark:text-green-400 mb-2"
                                    >
                                        {{
                                            slotProps.message.data.method.toUpperCase()
                                        }}
                                        Analysis Completed
                                    </h4>
                                    <p
                                        class="text-sm text-gray-600 dark:text-gray-300"
                                    >
                                        Your
                                        {{
                                            slotProps.message.data.method.toUpperCase()
                                        }}
                                        analysis has completed successfully!
                                    </p>
                                </div>
                            </div>

                            <div
                                class="bg-green-50 dark:bg-green-900/20 p-3 rounded border-l-4 border-green-500"
                            >
                                <div class="flex items-center gap-2 mb-2">
                                    <i
                                        class="pi pi-clock text-sm text-green-600 dark:text-green-400"
                                    ></i>
                                    <span
                                        class="font-medium text-sm text-green-700 dark:text-green-400"
                                        >Completed:</span
                                    >
                                </div>
                                <span
                                    class="text-sm text-gray-700 dark:text-gray-300"
                                >
                                    {{ slotProps.message.data.updatedAt }}
                                </span>
                            </div>

                            <div
                                class="bg-gray-50 dark:bg-gray-800 p-3 rounded border-l-4 border-gray-400"
                            >
                                <div class="flex items-center gap-2 mb-1">
                                    <i
                                        class="pi pi-database text-sm dark:text-gray-300"
                                    ></i>
                                    <span
                                        class="font-medium text-sm dark:text-gray-200"
                                        >Dataset:</span
                                    >
                                </div>
                                <span
                                    class="text-sm font-mono bg-white dark:bg-gray-700 dark:text-gray-200 px-2 py-1 rounded"
                                >
                                    {{ slotProps.message.data.dataset }}
                                </span>
                            </div>
                        </div>
                    </div>
                </template>
            </ConfirmDialog>

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
                    label="Upload GWAS"
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
                    <!-- Show welcome message for new users with no datasets -->
                    <Message
                        v-if="datasets.length === 0"
                        severity="info"
                        :closable="false"
                        class="mb-4"
                    >
                        <div class="flex flex-col gap-3">
                            <div class="flex items-center gap-2">
                                <i class="pi pi-info-circle"></i>
                                <span class="font-semibold"
                                    >Welcome! Get started by uploading your
                                    first dataset</span
                                >
                            </div>
                            <p class="text-sm text-gray-700 ml-6">
                                Upload your GWAS summary statistics to begin
                                running analyses like SLDSC and MAGMA. Click the
                                "Upload Dataset" button above to get started.
                            </p>
                        </div>
                    </Message>

                    <DataTable
                        v-if="datasets.length > 0"
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
                        <Column header="Uploaded">
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
                        <Column
                            header="Run Analysis"
                            :style="{ width: '15rem' }"
                        >
                            <template #body="{ data }">
                                <div class="flex gap-2 flex-wrap">
                                    <!-- Show select with all workflow options -->
                                    <Select
                                        v-if="
                                            getAllWorkflowOptions(data).length >
                                            0
                                        "
                                        :options="getAllWorkflowOptions(data)"
                                        optionLabel="label"
                                        optionDisabled="disabled"
                                        placeholder="Select Analysis"
                                        class="flex-1 min-w-0"
                                        @change="
                                            (event) => {
                                                if (
                                                    event.value &&
                                                    !event.value.disabled
                                                ) {
                                                    if (
                                                        event.value.status ===
                                                        'available'
                                                    ) {
                                                        confirmAndRunWorkflow(
                                                            data,
                                                            event.value,
                                                        );
                                                    } else {
                                                        event.value.command();
                                                    }
                                                    // Clear the selection after action
                                                    event.target.writeValue(
                                                        null,
                                                    );
                                                }
                                            }
                                        "
                                    >
                                        <template #option="slotProps">
                                            <div
                                                class="flex items-center gap-1.5 px-3 py-1.5"
                                                :class="{
                                                    'opacity-50 cursor-not-allowed':
                                                        slotProps.option
                                                            .disabled,
                                                    'text-blue-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'primary',
                                                    'text-red-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'danger',
                                                    'text-green-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'success',
                                                    'text-orange-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'warn',
                                                }"
                                            >
                                                <i
                                                    :class="
                                                        slotProps.option.icon
                                                    "
                                                    class="w-4 text-center"
                                                    style="
                                                        font-size: 14px;
                                                        line-height: 1;
                                                    "
                                                    :style="{
                                                        color:
                                                            slotProps.option
                                                                .severity ===
                                                            'primary'
                                                                ? '#3b82f6'
                                                                : slotProps
                                                                        .option
                                                                        .severity ===
                                                                    'danger'
                                                                  ? '#ef4444'
                                                                  : slotProps
                                                                          .option
                                                                          .severity ===
                                                                      'success'
                                                                    ? '#10b981'
                                                                    : slotProps
                                                                            .option
                                                                            .severity ===
                                                                        'warn'
                                                                      ? '#f59e0b'
                                                                      : 'inherit',
                                                    }"
                                                ></i>
                                                <span
                                                    class="font-medium flex-1"
                                                >
                                                    {{ slotProps.option.label }}
                                                </span>
                                            </div>
                                        </template>

                                        <template #value="slotProps">
                                            <div
                                                v-if="slotProps.value"
                                                class="flex items-center gap-1.5"
                                            >
                                                <i
                                                    :class="
                                                        slotProps.value.icon
                                                    "
                                                    class="w-4 text-center"
                                                    style="
                                                        font-size: 14px;
                                                        line-height: 1;
                                                    "
                                                    :style="{
                                                        color:
                                                            slotProps.value
                                                                .severity ===
                                                            'primary'
                                                                ? '#3b82f6'
                                                                : slotProps
                                                                        .value
                                                                        .severity ===
                                                                    'danger'
                                                                  ? '#ef4444'
                                                                  : slotProps
                                                                          .value
                                                                          .severity ===
                                                                      'success'
                                                                    ? '#10b981'
                                                                    : slotProps
                                                                            .value
                                                                            .severity ===
                                                                        'warn'
                                                                      ? '#f59e0b'
                                                                      : 'inherit',
                                                    }"
                                                ></i>
                                                <span>{{
                                                    slotProps.value.label
                                                }}</span>
                                            </div>
                                            <span v-else class="text-gray-500"
                                                >Select Analysis</span
                                            >
                                        </template>
                                    </Select>
                                </div>
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
                                    <!-- Show Tag/link for FAILED status -->
                                    <router-link
                                        v-if="data.status.endsWith('FAILED')"
                                        :to="`/log/${data.id}?method=${data.status.split(' ')[0]}`"
                                        v-tooltip.top="'View log'"
                                    >
                                        <Tag severity="danger" rounded>
                                            {{ data.status }}
                                        </Tag>
                                    </router-link>

                                    <!-- Plain text for RUNNING status -->
                                    <span
                                        v-else-if="
                                            data.status.includes('RUNNING')
                                        "
                                        class="text-orange-600 font-medium"
                                    >
                                        <i
                                            class="pi pi-spin pi-spinner mr-2"
                                        ></i>
                                        {{ data.status }}
                                    </span>

                                    <!-- Clickable Tag for SUCCEEDED status -->
                                    <router-link
                                        v-else-if="
                                            data.status.endsWith('SUCCEEDED')
                                        "
                                        :to="`/log/${data.id}?method=${data.status.split(' ')[0]}`"
                                        v-tooltip.top="'View log'"
                                    >
                                        <Tag
                                            :severity="
                                                data.status ===
                                                'sumstats SUCCEEDED'
                                                    ? 'info'
                                                    : 'success'
                                            "
                                            rounded
                                        >
                                            {{ data.status }}
                                        </Tag>
                                    </router-link>
                                </template>
                                <template v-else-if="!data.status">
                                    <span class="text-gray-500 font-medium"
                                        >uploaded</span
                                    >
                                </template>
                                <template v-else>
                                    {{ data.status }}
                                </template>
                            </template>
                        </Column>

                        <Column header="Results" :style="{ width: '15rem' }">
                            <template #body="{ data }">
                                <div class="flex gap-2 flex-wrap">
                                    <SplitButton
                                        v-if="getResultButtonConfig(data)"
                                        :label="
                                            getResultButtonConfig(data).label
                                        "
                                        class="whitespace-nowrap flex-1 min-w-0"
                                        :icon="getResultButtonConfig(data).icon"
                                        size="small"
                                        outlined
                                        @click="
                                            getResultButtonConfig(
                                                data,
                                            ).command()
                                        "
                                        severity="primary"
                                        :model="
                                            getResultButtonConfig(data)
                                                .dropdownItems
                                        "
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
                <template #footer v-if="datasets.length > 0"
                    ><small>Total records: {{ totalRecords }}</small></template
                >
            </Card>
        </div>

        <!-- BED Annotation Files Table -->
        <div class="col-span-12">
            <Card class="m-4">
                <template #title>
                    <div class="flex items-center justify-between">
                        <span>Annotation Files</span>
                        <Button
                            label="Upload Annotation"
                            icon="pi pi-upload"
                            @click="router.push('/bed-upload')"
                            size="small"
                            severity="primary"
                        />
                    </div>
                </template>
                <template #content>
                    <DataTable
                        :value="bedFiles"
                        :paginator="true"
                        :rows="10"
                        :rowsPerPageOptions="[5, 10, 20]"
                        sortField="uploaded_at"
                        :sortOrder="-1"
                        dataKey="filename"
                        filterDisplay="menu"
                        :loading="false"
                        :globalFilterFields="[
                            'dataset_name',
                            'filename',
                            'uploader',
                        ]"
                    >
                        <Column
                            field="dataset_name"
                            header="Dataset"
                            :style="{ minWidth: '12rem' }"
                        >
                            <template #body="{ data }">
                                <span
                                    class="filename"
                                    v-tooltip.right="{
                                        value: `${data.filename}`,
                                        class: 'filename-tooltip',
                                    }"
                                    >{{ data.dataset_name }}</span
                                >
                            </template>
                        </Column>

                        <Column
                            field="uploader"
                            header="Uploader"
                            :style="{ width: '10rem' }"
                        >
                            <template #body="{ data }">
                                <span class="text-sm">{{
                                    data.uploader || "N/A"
                                }}</span>
                            </template>
                        </Column>

                        <Column
                            field="uploaded_at"
                            header="Uploaded"
                            :style="{ width: '12rem' }"
                        >
                            <template #body="{ data }">
                                <span class="text-sm">{{
                                    data.uploaded_at
                                        ? new Date(
                                              data.uploaded_at,
                                          ).toLocaleDateString()
                                        : ""
                                }}</span>
                            </template>
                        </Column>

                        <Column
                            field="file_size"
                            header="Size"
                            :style="{ width: '8rem' }"
                        >
                            <template #body="{ data }">
                                <span class="text-sm">{{
                                    formatFileSize(data.file_size)
                                }}</span>
                            </template>
                        </Column>
                        <Column
                            header="Run Analysis"
                            :style="{ width: '15rem' }"
                        >
                            <template #body="{ data }">
                                <div class="flex gap-2 flex-wrap">
                                    <Select
                                        v-if="
                                            getBedWorkflowOptions(data).length >
                                            0
                                        "
                                        :options="getBedWorkflowOptions(data)"
                                        optionLabel="label"
                                        optionDisabled="disabled"
                                        placeholder="Select Analysis"
                                        class="flex-1 min-w-0"
                                        @change="
                                            (event) => {
                                                if (
                                                    event.value &&
                                                    !event.value.disabled
                                                ) {
                                                    if (
                                                        event.value.status ===
                                                        'available'
                                                    ) {
                                                        confirmAndRunBedWorkflow(
                                                            data,
                                                            event.value,
                                                        );
                                                    } else {
                                                        event.value.command();
                                                    }
                                                    // Clear the selection after action
                                                    event.target.writeValue(
                                                        null,
                                                    );
                                                }
                                            }
                                        "
                                    >
                                        <template #option="slotProps">
                                            <div
                                                class="flex items-center gap-1.5 px-3 py-1.5"
                                                :class="{
                                                    'opacity-50 cursor-not-allowed':
                                                        slotProps.option
                                                            .disabled,
                                                    'text-blue-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'primary',
                                                    'text-red-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'danger',
                                                    'text-green-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'success',
                                                    'text-orange-600':
                                                        slotProps.option
                                                            .severity ===
                                                        'warn',
                                                }"
                                            >
                                                <i
                                                    :class="
                                                        slotProps.option.icon
                                                    "
                                                    class="w-4 text-center"
                                                    style="
                                                        font-size: 14px;
                                                        line-height: 1;
                                                    "
                                                    :style="{
                                                        color:
                                                            slotProps.option
                                                                .severity ===
                                                            'primary'
                                                                ? '#3b82f6'
                                                                : slotProps
                                                                        .option
                                                                        .severity ===
                                                                    'danger'
                                                                  ? '#ef4444'
                                                                  : slotProps
                                                                          .option
                                                                          .severity ===
                                                                      'success'
                                                                    ? '#10b981'
                                                                    : slotProps
                                                                            .option
                                                                            .severity ===
                                                                        'warn'
                                                                      ? '#f59e0b'
                                                                      : 'inherit',
                                                    }"
                                                ></i>
                                                <span
                                                    class="font-medium flex-1"
                                                >
                                                    {{ slotProps.option.label }}
                                                </span>
                                            </div>
                                        </template>

                                        <template #value="slotProps">
                                            <div
                                                v-if="slotProps.value"
                                                class="flex items-center gap-1.5"
                                            >
                                                <i
                                                    :class="
                                                        slotProps.value.icon
                                                    "
                                                    class="w-4 text-center"
                                                    style="
                                                        font-size: 14px;
                                                        line-height: 1;
                                                    "
                                                    :style="{
                                                        color:
                                                            slotProps.value
                                                                .severity ===
                                                            'primary'
                                                                ? '#3b82f6'
                                                                : slotProps
                                                                        .value
                                                                        .severity ===
                                                                    'danger'
                                                                  ? '#ef4444'
                                                                  : slotProps
                                                                          .value
                                                                          .severity ===
                                                                      'success'
                                                                    ? '#10b981'
                                                                    : slotProps
                                                                            .value
                                                                            .severity ===
                                                                        'warn'
                                                                      ? '#f59e0b'
                                                                      : 'inherit',
                                                    }"
                                                ></i>
                                                <span>{{
                                                    slotProps.value.label
                                                }}</span>
                                            </div>
                                            <span v-else class="text-gray-500"
                                                >Select Analysis</span
                                            >
                                        </template>
                                    </Select>
                                </div>
                            </template>
                        </Column>
                        <Column
                            field="status"
                            header="Status"
                            :style="{ width: '12rem' }"
                        >
                            <template #body="{ data }">
                                <template
                                    v-if="
                                        data.status &&
                                        (data.status.includes('RUNNING') ||
                                            data.status.endsWith('SUCCEEDED') ||
                                            data.status.endsWith('FAILED'))
                                    "
                                >
                                    <!-- Show Tag/link for FAILED status -->
                                    <router-link
                                        v-if="data.status.endsWith('FAILED')"
                                        :to="`/log/${data.id}?method=${data.status.split(' ')[0]}`"
                                        v-tooltip.top="'View log'"
                                    >
                                        <Tag severity="danger" rounded>
                                            {{ data.status }}
                                        </Tag>
                                    </router-link>

                                    <!-- Plain text for RUNNING status -->
                                    <span
                                        v-else-if="
                                            data.status.includes('RUNNING')
                                        "
                                        class="text-orange-600 font-medium"
                                    >
                                        <i
                                            class="pi pi-spin pi-spinner mr-2"
                                        ></i>
                                        {{ data.status }}
                                    </span>

                                    <!-- Clickable Tag for SUCCEEDED status -->
                                    <router-link
                                        v-else-if="
                                            data.status.endsWith('SUCCEEDED')
                                        "
                                        :to="`/log/${data.id}?method=${data.status.split(' ')[0]}`"
                                        v-tooltip.top="'View log'"
                                    >
                                        <Tag severity="success" rounded>
                                            {{ data.status }}
                                        </Tag>
                                    </router-link>
                                </template>
                                <template v-else>
                                    <Tag
                                        :value="data.status || 'active'"
                                        :severity="
                                            data.status === 'active'
                                                ? 'info'
                                                : 'secondary'
                                        "
                                        rounded
                                    />
                                </template>
                            </template>
                        </Column>
                        <Column header="Results" :style="{ width: '15rem' }">
                            <template #body="{ data }">
                                <div class="flex gap-2 flex-wrap">
                                    <SplitButton
                                        v-if="getBedResultButtonConfig(data)"
                                        :label="
                                            getBedResultButtonConfig(data).label
                                        "
                                        class="whitespace-nowrap flex-1 min-w-0"
                                        :icon="
                                            getBedResultButtonConfig(data).icon
                                        "
                                        size="small"
                                        outlined
                                        @click="
                                            getBedResultButtonConfig(
                                                data,
                                            ).command()
                                        "
                                        severity="primary"
                                        :model="
                                            getBedResultButtonConfig(data)
                                                .dropdownItems
                                        "
                                    />
                                </div>
                            </template>
                        </Column>
                        <Column
                            header="Actions"
                            :style="{ width: '10rem' }"
                            class="text-center"
                        >
                            <template #body="{ data }">
                                <div class="flex gap-2 justify-center">
                                    <Button
                                        icon="pi pi-download"
                                        size="small"
                                        @click="
                                            downloadBedFile(
                                                data.dataset_name,
                                                data.filename,
                                            )
                                        "
                                        v-tooltip.top="'Download file'"
                                        outlined
                                        severity="secondary"
                                    />
                                    <Button
                                        v-if="
                                            userStore.user.username !== 'demo'
                                        "
                                        icon="pi pi-trash"
                                        size="small"
                                        @click="
                                            handleDeleteBedFile(
                                                data.dataset_name,
                                                data.filename,
                                            )
                                        "
                                        v-tooltip.top="'Delete file'"
                                        outlined
                                        severity="danger"
                                    />
                                </div>
                            </template>
                        </Column>
                    </DataTable>
                </template>
                <template #footer v-if="bedFiles.length > 0"
                    ><small>Total records: {{ totalBedFiles }}</small></template
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
