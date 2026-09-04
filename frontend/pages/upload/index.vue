<template>
    <div class="bg-gray-100 dark:bg-gray-900 min-h-screen flex flex-col">
        <!-- Fix the container width and ensure proper display -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
            <Button
                label="Back to Datasets"
                icon="pi pi-arrow-left"
                @click="$router.push('/datasets')"
                class="mt-6"
                outlined
                size="small"
            />
            <Stepper :value="currentStep" class="basis-[50rem] my-6" linear>
                <StepList>
                    <Step value="1">Enter Metadata</Step>
                    <Step value="2">Select File</Step>
                    <Step value="3">Map Columns</Step>
                    <Step value="4">Upload</Step>
                </StepList>
            </Stepper>
            <!-- Improved flex container with more explicit responsive control -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Left Column -->
                <div class="col-span-1">
                    <Card class="h-full shadow-sm">
                        <template #content>
                            <Fieldset
                                legend="Metadata"
                                class="mb-4"
                                :class="{
                                    'border-primary-500 border-2':
                                        currentStep === '1',
                                }"
                            >
                                <div class="field">
                                    <label
                                        for="dataset"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Dataset Name
                                        <span style="color: darkred"
                                            >*</span
                                        ></label
                                    >
                                    <InputText
                                        id="dataset"
                                        autofocus
                                        type="text"
                                        v-model.trim="dataSetName"
                                        placeholder="Enter dataset name"
                                        class="w-full"
                                    />
                                </div>
                                <div class="field mt-2">
                                    <label
                                        for="ancestry"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Ancestry
                                        <span style="color: darkred"
                                            >*</span
                                        ></label
                                    >
                                    <Select
                                        id="ancestry"
                                        v-model="ancestry"
                                        :options="ancestryOptions"
                                        class="w-full"
                                        option-value="value"
                                        option-label="name"
                                        placeholder="Select ancestry"
                                    />
                                </div>
                                <div class="field mt-2">
                                    <label
                                        for="phenotype"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Phenotype</label
                                    >
                                    <div class="p-fluid">
                                        <AutoComplete
                                            id="phenotype"
                                            v-model="phenotype"
                                            :suggestions="filteredPhenotypes"
                                            @complete="searchPhenotypes($event)"
                                            placeholder="Enter or select a phenotype (optional)"
                                            optionLabel="description"
                                            field="description"
                                            class="w-full"
                                            inputClass="w-full"
                                            :loading="phenotypeStore.loading"
                                            :dropdown="
                                                phenotype &&
                                                filteredPhenotypes.length > 0
                                            "
                                            dropdown-mode="current"
                                        >
                                            <template #option="slotProps">
                                                <div>
                                                    <div>
                                                        {{
                                                            slotProps.option
                                                                .description ||
                                                            slotProps.option
                                                                .name
                                                        }}
                                                    </div>
                                                </div>
                                            </template>
                                        </AutoComplete>
                                    </div>
                                </div>
                                <div class="field mt-2">
                                    <label
                                        for="effectiveN"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Effective N</label
                                    >
                                    <InputText
                                        id="effectiveN"
                                        v-model="effectiveN"
                                        type="number"
                                        placeholder="Enter effective N (optional if already in data file)"
                                        class="w-full"
                                    />
                                </div>
                                <div class="field mt-2">
                                    <label
                                        for="genomeBuild"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Genome Build
                                        <span style="color: darkred"
                                            >*</span
                                        ></label
                                    >
                                    <Select
                                        id="genomeBuild"
                                        v-model="genomeBuild"
                                        :options="['GRCh37', 'GRCh38']"
                                        class="w-full"
                                        placeholder="Select genome build"
                                    />
                                </div>
                            </Fieldset>
                            <div class="text-right">
                                <small
                                    ><span style="color: darkred">*</span>
                                    Required fields</small
                                >
                            </div>
                            <Fieldset
                                legend="File Upload"
                                class="mb-4"
                                :class="{
                                    'border-primary-500 border-2':
                                        currentStep === '2',
                                }"
                            >
                                <div class="field">
                                    <label
                                        for="file"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Select a delimited file (comma or tab
                                        separated, optionally .gz
                                        compressed)</label
                                    >
                                    <FileUpload
                                        ref="fileInput"
                                        id="file"
                                        :multiple="false"
                                        @select="sampleFile"
                                        @clear="resetFile"
                                        @remove="resetFile"
                                        :previewWidth="0"
                                        :show-upload-button="false"
                                        :disabled="file !== null"
                                        class="file-upload"
                                    />
                                </div>
                            </Fieldset>
                        </template>
                    </Card>
                </div>

                <!-- Right Column -->
                <div class="col-span-1">
                    <Card class="h-full shadow-sm">
                        <template #content>
                            <Fieldset
                                legend="Column Mapping"
                                class="mb-4"
                                :class="{
                                    'border-primary-500 border-2':
                                        currentStep === '3',
                                }"
                            >
                                <h5>
                                    Map column names to their representations.
                                </h5>
                                <small
                                    >Match all the required fields<span
                                        style="color: darkred"
                                        >*</span
                                    >, n (or manually entered effective n)<span
                                        style="color: darkred"
                                        >^</span
                                    >, and any optional field to upload
                                    file.</small
                                >
                                <div
                                    class="card flex flex-wrap gap-1 required-card"
                                >
                                    <h6 class="w-full">Required fields:</h6>
                                    <template v-for="field in REQUIRED_FIELDS">
                                        <Chip
                                            v-if="
                                                Object.values(
                                                    selectedFields,
                                                ).includes(field.value)
                                            "
                                            :key="field.value"
                                            icon="pi pi-check"
                                            :label="field.name"
                                            class="selected-chip"
                                        />

                                        <Chip
                                            v-else
                                            :label="field.name"
                                            :key="'else-' + field.name"
                                        />
                                    </template>
                                    <Chip
                                        v-if="requiredEffectFields"
                                        icon="pi pi-check"
                                        label="beta | oddsRatio"
                                        class="selected-chip"
                                    />
                                    <Chip v-else label="beta | oddsRatio" />
                                    <Chip
                                        v-if="effectiveN || colMap.n"
                                        label="n"
                                        icon="pi pi-check"
                                        class="selected-chip"
                                    />
                                    <Chip v-else label="n" />
                                </div>
                                <ColumnMappingTable
                                    :columns="fileInfo.columns || []"
                                    :options="colOptions"
                                    v-model="selectedFields"
                                />
                            </Fieldset>
                            <div class="field">
                                <Button
                                    label="Upload Dataset"
                                    class="w-full mt-4"
                                    icon="pi pi-upload"
                                    :disabled="formIncomplete"
                                    @click="uploadData"
                                    raised
                                    v-tooltip.top="{
                                        value: tooltipContent,
                                        disabled: !formIncomplete,
                                        escape: false,
                                        pt: {
                                            root: {
                                                style: 'max-width: 450px;',
                                            },
                                        },
                                    }"
                                />
                            </div>
                        </template>
                    </Card>
                </div>
            </div>
        </div>

        <div v-if="uploadProgress > 0" class="overlay">
            <div class="content">
                <ProgressBar :value="uploadProgress" class="progress-bar" />
                <p class="text-white">Uploading...</p>
            </div>
        </div>
        <Toast position="top-center" />
    </div>
</template>

<script setup>
import { useUserStore } from "~/stores/UserStore";
import { usePhenotypeStore } from "~/stores/PhenotypeStore";
import { suggestColumnMap } from "~/utils/upload/suggestColumnMap";
import {
    REQUIRED_FIELDS,
    missingRequiredFields,
} from "~/utils/upload/requiredFields";
import { selectedFieldsToColMap } from "~/utils/upload/colMap";
import axios from "axios";
const fileInfo = ref({});
const fileInput = ref(null);
const dataSetName = ref("");
const toast = useToast();
const route = useRouter();
const store = useUserStore();
const phenotypeStore = usePhenotypeStore();
let fileName = null;
const uploadProgress = ref(0);
let file = ref(null);
const selectedFields = ref({});
const missingMappingError = ref("");
const ancestry = ref("");
const effectiveN = ref(null);
const genomeBuild = ref("");
const phenotype = ref(null);
const filteredPhenotypes = ref([]);
const currentStep = ref("1");

const colMap = computed(() => selectedFieldsToColMap(selectedFields.value));

watch(
    [dataSetName, ancestry, genomeBuild, file, colMap, effectiveN],
    () => {
        if (!dataSetName.value || !ancestry.value || !genomeBuild.value) {
            currentStep.value = "1";
            return;
        }

        if (!file.value) {
            currentStep.value = "2";
            return;
        }

        const hasRequiredFields = REQUIRED_FIELDS.every(
            (field) => field.value in colMap.value,
        );
        const hasEffectSize =
            "beta" in colMap.value || "oddsRatio" in colMap.value;
        const hasSampleSize =
            "n" in colMap.value ||
            (effectiveN.value && effectiveN.value.trim !== "");

        if (!hasRequiredFields || !hasEffectSize || !hasSampleSize) {
            currentStep.value = "3";
            return;
        }

        currentStep.value = "4";
    },
    { immediate: true },
);

const ancestryOptions = [
    { name: "European", value: "EUR" },
    { name: "African", value: "AFR" },
    { name: "East Asian", value: "EAS" },
    { name: "South Asian", value: "SAS" },
    { name: "Ad Mixed American", value: "AMR" },
];
// Anything not mapped here can never reach the Variant Sifter, so the optional
// fields matter: eaf drives its EAF filter, maf/zScore its table columns.
const colOptions = [
    { name: "chromosome", value: "chromosome" },
    { name: "position", value: "position" },
    { name: "rsID", value: "rsid" },
    { name: "other_allele", value: "reference" },
    { name: "effect_allele", value: "alt" },
    { name: "pValue", value: "pValue" },
    { name: "beta", value: "beta" },
    { name: "oddsRatio", value: "oddsRatio" },
    { name: "se", value: "se" },
    { name: "n", value: "n" },
    { name: "effect_allele_freq", value: "eaf" },
    { name: "maf", value: "maf" },
    { name: "zScore", value: "zScore" },
];
// REQUIRED_FIELDS lives in utils/ so the rule -- in particular the deliberate
// absence of `se` -- is covered by tests rather than buried in this component.

const requiredEffectFields = computed(() => {
    return (
        colMap.value["beta"] !== undefined ||
        colMap.value["oddsRatio"] !== undefined
    );
});

function resetFile() {
    fileInfo.value = {};
    selectedFields.value = {};
    missingMappingError.value = "";
    file.value = null;
    fileName = null;
}

const missingRequirementsMessages = computed(() => {
    const messages = [];

    if (!dataSetName.value) {
        messages.push("Dataset name is required");
    }
    if (!file.value) {
        messages.push("Please upload a file");
    }
    if (!ancestry.value) {
        messages.push("Ancestry is required");
    }
    if (!genomeBuild.value) {
        messages.push("Genome build is required");
    }

    const missingFields = missingRequiredFields(colMap.value);
    if (missingFields.length > 0) {
        messages.push(
            `Map required fields: ${missingFields.map((f) => f.name).join(", ")}`,
        );
    }

    if (!("beta" in colMap.value || "oddsRatio" in colMap.value)) {
        messages.push("Map either beta or oddsRatio field");
    }

    if (!("n" in colMap.value || effectiveN.value)) {
        messages.push("Map n field or provide effective N");
    }

    return messages;
});

const tooltipContent = computed(() => {
    if (!formIncomplete.value) return "";

    const msgs = missingRequirementsMessages.value;
    return `<div style="white-space: normal;">
        <div style="font-weight: 600; margin-bottom: 8px;">Missing Requirements:</div>
        <ul style="margin: 0; padding-left: 20px; font-size: 0.875rem; line-height: 1.5;">
            ${msgs.map((msg) => `<li style="margin-bottom: 4px;">${msg}</li>`).join("")}
        </ul>
    </div>`;
});

const formIncomplete = computed(() => {
    return (
        !file.value ||
        !dataSetName.value ||
        !REQUIRED_FIELDS.every(
            (field) => field.value in colMap.value && colMap.value[field.value],
        ) ||
        !("beta" in colMap.value || "oddsRatio" in colMap.value) ||
        !ancestry.value ||
        !genomeBuild.value ||
        !("n" in colMap.value || effectiveN.value)
    );
});

async function uploadData() {
    const { presigned_url } = await store.getPresignedUrl(
        fileName,
        dataSetName.value,
    );
    const strippedFile = new Blob([file.value], { type: "" });
    try {
        await axios.put(presigned_url, strippedFile, {
            headers: {
                "Content-Type": "",
            },
            onUploadProgress: (progressEvent) => {
                const percentCompleted = Math.round(
                    (progressEvent.loaded * 100) / progressEvent.total,
                );
                onProgress(percentCompleted);
            },
        });
        const col_map = JSON.parse(JSON.stringify(colMap.value));
        // Extract just the name from the phenotype object if it exists
        const phenotypeName = phenotype.value?.name || phenotype.value;

        await store.finalizeUpload({
            file: fileName,
            name: dataSetName.value,
            ancestry: ancestry.value,
            effective_n: effectiveN.value,
            separator: fileInfo.value.delimiter,
            genome_build: genomeBuild.value,
            phenotype: phenotypeName,
            col_map,
        });
        console.log("File uploaded successfully");
        await route.push("/datasets");
    } catch (error) {
        if (error.response.status === 409) {
            toast.add({
                severity: "error",
                summary: "Error",
                detail: "Dataset name already exists",
            });
            return;
        }
        console.error("File upload failed:", error);
        throw error;
    }
}

function onProgress(percentCompleted) {
    uploadProgress.value = percentCompleted < 100 ? percentCompleted : 0;
}

async function sampleFile(e) {
    file.value = e.files[0];
    fileName = e.files[0].name;

    // No file extension validation - backend will infer delimiter from content
    try {
        fileInfo.value = await store.sampleTextFile(e.files[0]);
        // Pre-fill the mapping from the header names. Allele and effect fields
        // are matched by explicit alias only (see suggestColumnMap), so a guess
        // there is never a similarity match. Everything stays editable, and the
        // toast tells the user to check it.
        const guessed = suggestColumnMap(
            fileInfo.value.columns,
            colOptions.map((o) => o.value),
        );
        fileInfo.value.columns.forEach((col) => {
            selectedFields.value[col] = guessed[col] ?? null;
        });
        const n = Object.keys(guessed).length;
        if (n > 0) {
            toast.add({
                severity: "info",
                summary: "Columns pre-filled",
                detail: `Matched ${n} of ${fileInfo.value.columns.length} columns. Please review before continuing.`,
                life: 6000,
            });
        }
    } catch (e) {
        console.log(e);
        toast.add({
            severity: "error",
            summary: "Error",
            detail:
                e.response?.data?.detail ||
                "Could not parse file. Please ensure it is comma or tab delimited.",
        });
        fileInfo.value = {};
        selectedFields.value = {};
        fileInput.value.clear();
    }
}

async function searchPhenotypes(event) {
    const query = event.query;

    if (!phenotypeStore.phenotypes.length) {
        await phenotypeStore.fetchPhenotypes();
    }

    if (query) {
        filteredPhenotypes.value = phenotypeStore.phenotypes.filter(
            (phenotype) =>
                (phenotype.description &&
                    phenotype.description
                        .toLowerCase()
                        .includes(query.toLowerCase())) ||
                phenotype.name.toLowerCase().includes(query.toLowerCase()),
        );
    } else {
        filteredPhenotypes.value = phenotypeStore.phenotypes;
    }
}

// Initialize phenotype data when component is mounted
onMounted(async () => {
    await phenotypeStore.fetchPhenotypes();
});
</script>

<style scoped>
.file-upload {
    max-width: 500px;
    margin: 0 auto;
}

.overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: rgba(0, 0, 0, 0.2);
    z-index: 1000;
}

.content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 2px solid #fff;
    border-radius: 8px;
    padding: 20px;
    background-color: #333;
}

.progress-bar {
    width: 20rem;
}

.text-white {
    color: white;
}

/* Force column sizing for PrimeVue tables */
:deep(.p-datatable-wrapper) {
    overflow-x: auto;
}

/* Make sure the Card components take the full height */
:deep(.p-card) {
    height: 100%;
    display: flex;
    flex-direction: column;
}

:deep(.p-card-body) {
    flex: 1;
    display: flex;
    flex-direction: column;
}

:deep(.p-card-content) {
    flex: 1;
}

@media (max-width: 768px) {
    .grid-cols-1 > div {
        margin-bottom: 1.5rem;
    }
}

.card {
    background: var(--p-content-background);
    padding: 2rem;
    margin-bottom: 2rem;
    border-radius: var(--p-content-border-radius);
}

.card:last-child {
    margin-bottom: 0;
}

.required-card {
    border: 1px dashed #ccc;
    padding: 0.5rem;
    margin-top: 1rem;
}
.required-card h6 {
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
}
.p-chip.selected-chip {
    background-color: #24cb67;
    color: white;
}
:deep(.p-chip.selected-chip > .p-chip-icon.pi) {
    color: white;
}
.p-chip {
    padding-block: unset;
}
</style>
