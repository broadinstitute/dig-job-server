<template>
    <div class="bg-gray-100 dark:bg-gray-900 min-h-screen flex flex-col">
        <!-- Fix the container width and ensure proper display -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
            <Button
                label="Back to Datasets"
                icon="pi pi-arrow-left"
                @click="$router.push('/')"
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
                            <Fieldset legend="Metadata" class="mb-4">
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
                                        v-model="dataSetName"
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
                                        for="effectiveN"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Effective N</label
                                    >
                                    <InputText
                                        id="effectiveN"
                                        v-model="effectiveN"
                                        type="number"
                                        placeholder="Enter effective N (optional)"
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
                            <Fieldset legend="File Upload" class="mb-4">
                                <div class="field">
                                    <label
                                        for="file"
                                        class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                        >Select a file</label
                                    >
                                    <FileUpload
                                        id="file"
                                        accept=".csv, .tsv, .gz, .bgzip, .gzip"
                                        @select="sampleFile"
                                        @clear="resetFile"
                                        @remove="resetFile"
                                        :previewWidth="0"
                                        :show-upload-button="false"
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
                            <Fieldset legend="Column Mapping" class="mb-4">
                                <DataTable
                                    :value="tableRows"
                                    v-if="fileInfo.columns"
                                    rowHover
                                    class="w-full"
                                    responsiveLayout="scroll"
                                >
                                    <Column
                                        field="column"
                                        header="Column"
                                        class="col-span-4"
                                    ></Column>
                                    <Column
                                        header=">>"
                                        class="col-span-1"
                                    ></Column>
                                    <Column
                                        header="Represents"
                                        class="col-span-7"
                                    >
                                        <template #body="{ data }">
                                            <Dropdown
                                                data-cy="column-dropdown"
                                                class="w-full"
                                                :options="colOptions"
                                                option-label="name"
                                                option-value="value"
                                                :option-disabled="
                                                    (option) => {
                                                        return (
                                                            Object.values(
                                                                selectedFields,
                                                            ).includes(
                                                                option.value,
                                                            ) &&
                                                            option.value !==
                                                                selectedFields[
                                                                    data.column
                                                                ]
                                                        );
                                                    }
                                                "
                                                v-model="
                                                    selectedFields[data.column]
                                                "
                                                showClear
                                            />
                                        </template>
                                    </Column>
                                </DataTable>
                                <div
                                    v-if="!fileInfo.columns"
                                    class="p-4 text-center text-gray-500"
                                >
                                    <i class="pi pi-file text-3xl mb-2"></i>
                                    <p>Upload a file to map columns</p>
                                </div>
                            </Fieldset>
                            <div class="field">
                                <p v-if="formIncomplete" class="mb-2 text-sm">
                                    {{
                                        `You must specify a dataset name, gwas file, ancestry, genome build, and column mapping that
                  includes ${requiredFields.join(
                      ", ",
                  )} , and either beta or odds ratio.  You also must specify n in your column mapping
                  or provide an effective n before you can upload.`
                                    }}
                                </p>
                                <Button
                                    label="Upload Dataset"
                                    class="w-full mt-4"
                                    icon="pi pi-upload"
                                    :disabled="formIncomplete"
                                    @click="uploadData"
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
import { useToast } from "primevue/usetoast";
import { useUserStore } from "~/stores/UserStore";
import axios from "axios";
const missingFileError = ref("");
const fileInfo = ref({});
const dataSetName = ref("");
const toast = useToast();
const route = useRouter();
const store = useUserStore();
let fileName = null;
const uploadProgress = ref(0);
let file = ref(null);
const selectedFields = ref({});
const missingMappingError = ref("");
const ancestry = ref("");
const effectiveN = ref(null);
const genomeBuild = ref("");
const currentStep = ref("1");

const colMap = computed(() => {
    //remove any null values from selectedFields
    const filteredSelectedFields = Object.fromEntries(
        Object.entries(selectedFields.value).filter(
            ([key, value]) => value !== null,
        ),
    );
    //transpose the object to have the value as the key and the key as the value
    //this is the format that the backend expects
    return Object.fromEntries(
        Object.entries(filteredSelectedFields).map(([key, value]) => [
            value,
            key,
        ]),
    );
});

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

        const hasRequiredFields = requiredFields.every(
            (field) => field in colMap.value && colMap.value[field],
        );
        const hasEffectSize =
            "beta" in colMap.value || "oddsRatio" in colMap.value;
        const hasSampleSize = "n" in colMap.value || effectiveN.value;

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
    { name: "Native American", value: "AMR" },
];
const colOptions = [
    { name: "chromosome", value: "chromosome" },
    { name: "position", value: "position" },
    { name: "reference", value: "reference" },
    { name: "alt", value: "alt" },
    { name: "pValue", value: "pValue" },
    { name: "beta", value: "beta" },
    { name: "oddsRatio", value: "oddsRatio" },
    { name: "n", value: "n" },
];
const requiredFields = ["chromosome", "position", "reference", "alt", "pValue"];

const tableRows = computed(() => {
    return fileInfo.value.columns
        ? fileInfo.value.columns.map((value) => ({
              column: value,
          }))
        : [];
});

function resetFile() {
    fileInfo.value = {};
    selectedFields.value = {};
    missingMappingError.value = "";
    file.value = null;
    fileName = null;
}

const formIncomplete = computed(() => {
    return (
        !file.value ||
        !dataSetName.value ||
        !requiredFields.every(
            (field) => field in colMap.value && colMap.value[field],
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
        await store.finalizeUpload({
            file: fileName,
            name: dataSetName.value,
            ancestry: ancestry.value,
            effective_n: effectiveN.value,
            separator: fileInfo.value.delimiter,
            genome_build: "GRCh37",
            col_map,
        });
        console.log("File uploaded successfully");
        await route.push("/");
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
    missingFileError.value = "";
    try {
        fileInfo.value = await store.sampleTextFile(e.files[0]);
        //copy fileInfo.columns to selectedFields
        fileInfo.value.columns.forEach((col) => {
            selectedFields.value[col] = null;
        });
    } catch (e) {
        console.log(e);
        fileInfo.value = {};
        selectedFields.value = {};
    }
}
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
    background: var(--surface-card);
    padding: 2rem;
    margin-bottom: 2rem;
    border-radius: var(--content-border-radius);
}

.card:last-child {
    margin-bottom: 0;
}
</style>
