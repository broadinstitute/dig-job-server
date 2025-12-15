<template>
    <div class="bg-gray-100 dark:bg-gray-900 min-h-screen flex flex-col">
        <!-- Fix the container width and ensure proper display -->
        <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
            <Button
                label="Back to Datasets"
                icon="pi pi-arrow-left"
                @click="$router.push('/datasets')"
                class="mt-6"
                outlined
                size="small"
            />
            <h1
                class="text-3xl font-bold text-center my-8 text-surface-900 dark:text-surface-50"
            >
                Upload BED File
            </h1>

            <!-- Single Column Layout for BED Upload -->
            <div class="max-w-2xl mx-auto">
                <Card class="shadow-sm">
                    <template #content>
                        <Fieldset legend="BED File Details" class="mb-4">
                            <div class="field">
                                <label
                                    for="bedDatasetName"
                                    class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                >
                                    Dataset Name
                                    <span style="color: darkred">*</span>
                                </label>
                                <InputText
                                    id="bedDatasetName"
                                    autofocus
                                    type="text"
                                    v-model.trim="bedDatasetName"
                                    placeholder="Enter a name for this BED dataset"
                                    class="w-full"
                                />
                                <small class="text-surface-500 ml-2">
                                    Choose a descriptive name for your BED file
                                    dataset
                                </small>
                            </div>

                            <div class="field mt-4">
                                <label
                                    for="bedFile"
                                    class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                                >
                                    Select BED File
                                    <span style="color: darkred">*</span>
                                </label>
                                <FileUpload
                                    ref="bedFileInput"
                                    id="bedFile"
                                    accept=".bed, .tsv"
                                    @select="selectBedFile"
                                    @clear="resetBedFile"
                                    @remove="resetBedFile"
                                    :previewWidth="0"
                                    :show-upload-button="false"
                                    class="file-upload"
                                />
                                <small class="text-surface-500 ml-2 block mt-2">
                                    Supported formats: .bed or .tsv files
                                    (tab-separated values with chromosome,
                                    start, end positions)
                                </small>

                                <!-- Validation Status -->
                                <div
                                    v-if="isValidating"
                                    class="mt-3 p-2 bg-blue-50 dark:bg-blue-900 rounded border"
                                >
                                    <div class="flex items-center">
                                        <ProgressSpinner
                                            style="width: 20px; height: 20px"
                                            strokeWidth="4"
                                            class="mr-2"
                                        />
                                        <span class="text-sm"
                                            >Validating BED file...</span
                                        >
                                    </div>
                                </div>

                                <!-- Validation Results -->
                                <div v-if="validationResult" class="mt-3">
                                    <!-- Success case -->
                                    <div
                                        v-if="validationResult.valid"
                                        class="p-3 bg-green-50 dark:bg-green-900 rounded border border-green-200 dark:border-green-800"
                                    >
                                        <div class="flex items-center">
                                            <i
                                                class="pi pi-check-circle text-green-600 mr-2"
                                            ></i>
                                            <span
                                                class="font-medium text-green-800 dark:text-green-200"
                                                >Valid BED file</span
                                            >
                                        </div>
                                    </div>

                                    <!-- Error case -->
                                    <div
                                        v-else
                                        class="p-3 bg-red-50 dark:bg-red-900 rounded border border-red-200 dark:border-red-800"
                                    >
                                        <div class="flex items-center mb-2">
                                            <i
                                                class="pi pi-exclamation-triangle text-red-600 mr-2"
                                            ></i>
                                            <span
                                                class="font-medium text-red-800 dark:text-red-200"
                                                >BED File Issues Found</span
                                            >
                                        </div>
                                        <div
                                            class="text-sm text-red-700 dark:text-red-300 max-h-32 overflow-y-auto"
                                        >
                                            <ul
                                                class="list-disc list-inside"
                                                v-if="validationResult.errors"
                                            >
                                                <li
                                                    v-for="error in validationResult.errors.slice(
                                                        0,
                                                        5,
                                                    )"
                                                    :key="error"
                                                >
                                                    {{ error }}
                                                </li>
                                                <li
                                                    v-if="
                                                        validationResult.errors
                                                            .length > 5
                                                    "
                                                    class="text-xs italic"
                                                >
                                                    ...and
                                                    {{
                                                        validationResult.errors
                                                            .length - 5
                                                    }}
                                                    more errors
                                                </li>
                                            </ul>
                                        </div>
                                    </div>

                                    <!-- Warnings (if any) -->
                                    <div
                                        v-if="
                                            validationResult.warnings &&
                                            validationResult.warnings.length > 0
                                        "
                                        class="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900 rounded border border-yellow-200 dark:border-yellow-800"
                                    >
                                        <div class="flex items-center mb-1">
                                            <i
                                                class="pi pi-exclamation-triangle text-yellow-600 mr-2 text-xs"
                                            ></i>
                                            <span
                                                class="font-medium text-yellow-800 dark:text-yellow-200 text-sm"
                                                >Warnings</span
                                            >
                                        </div>
                                        <div
                                            class="text-xs text-yellow-700 dark:text-yellow-300 max-h-20 overflow-y-auto"
                                        >
                                            <ul class="list-disc list-inside">
                                                <li
                                                    v-for="warning in validationResult.warnings.slice(
                                                        0,
                                                        3,
                                                    )"
                                                    :key="warning"
                                                >
                                                    {{ warning }}
                                                </li>
                                                <li
                                                    v-if="
                                                        validationResult
                                                            .warnings.length > 3
                                                    "
                                                    class="italic"
                                                >
                                                    ...and
                                                    {{
                                                        validationResult
                                                            .warnings.length - 3
                                                    }}
                                                    more warnings
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Fieldset>

                        <div class="text-right mb-4">
                            <small>
                                <span style="color: darkred">*</span>
                                Required field
                            </small>
                        </div>

                        <div class="field">
                            <Button
                                label="Upload BED Dataset"
                                class="w-full mt-4"
                                icon="pi pi-upload"
                                :disabled="formIncomplete"
                                @click="uploadBedData"
                                raised
                                :loading="uploading"
                            />
                        </div>
                    </template>
                </Card>
            </div>
        </div>

        <div v-if="uploadProgress > 0" class="overlay">
            <div class="content">
                <ProgressBar :value="uploadProgress" class="progress-bar" />
                <p class="text-white">Uploading BED file...</p>
            </div>
        </div>
        <Toast position="top-center" />
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
import { useUserStore } from "~/stores/UserStore";
import axios from "axios";

const toast = useToast();
const route = useRouter();
const store = useUserStore();

// Form data
const bedDatasetName = ref("");
const bedFile = ref(null);
const bedFileName = ref("");
const uploadProgress = ref(0);
const uploading = ref(false);

// File input reference
const bedFileInput = ref(null);

// Computed properties
const formIncomplete = computed(() => {
    return (
        !bedDatasetName.value.trim() ||
        !bedFile.value ||
        isValidating.value ||
        !validationResult.value ||
        (validationResult.value && !validationResult.value.valid)
    );
});

// Additional reactive data
const validationResult = ref(null);
const isValidating = ref(false);

// Methods
function selectBedFile(event) {
    const selectedFile = event.files[0];
    bedFile.value = selectedFile;
    bedFileName.value = selectedFile.name;
    validationResult.value = null; // Reset previous validation

    // Validate file extension
    const fileName = selectedFile.name.toLowerCase();
    const isValidFile = fileName.endsWith(".bed") || fileName.endsWith(".tsv");

    if (!isValidFile) {
        toast.add({
            severity: "error",
            summary: "Invalid File",
            detail: "Please select a valid BED or TSV file (.bed or .tsv)",
        });
        resetBedFile();
        return;
    }

    // Auto-validate the BED file
    validateBedFile();
}

async function validateBedFile() {
    if (!bedFile.value) return;

    isValidating.value = true;

    try {
        const formData = new FormData();
        formData.append("file", bedFile.value);

        const response = await store.validateBedFile(formData);
        validationResult.value = response;

        // Validation results are displayed inline below the file input
        // No toast notifications needed
    } catch (error) {
        console.error("BED validation error:", error);
        toast.add({
            severity: "error",
            summary: "Validation Failed",
            detail: "Unable to validate BED file. Please try again.",
        });
        validationResult.value = null;
    } finally {
        isValidating.value = false;
    }
}

function resetBedFile() {
    bedFile.value = null;
    bedFileName.value = "";
    validationResult.value = null;
}

async function uploadBedData() {
    if (formIncomplete.value) {
        toast.add({
            severity: "error",
            summary: "Form Incomplete",
            detail: "Please provide a dataset name and select a valid BED file",
        });
        return;
    }

    uploading.value = true;

    try {
        // Get presigned URL for BED upload
        const { presigned_url } = await store.getBedPresignedUrl(
            bedFileName.value,
            bedDatasetName.value,
        );

        // Upload file to S3
        const strippedFile = new Blob([bedFile.value], { type: "" });
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

        // Finalize BED upload with metadata
        await store.finalizeBedUpload(bedDatasetName.value, bedFileName.value);

        toast.add({
            severity: "success",
            summary: "Upload Successful",
            detail: "BED/TSV file has been uploaded successfully to annotation storage",
        });

        console.log("BED/TSV file uploaded successfully");

        // Clear the form after successful upload
        clearForm();
        // Redirect to datasets page after upload
        route.push("/datasets#annotation");
    } catch (error) {
        if (error.response?.status === 409) {
            toast.add({
                severity: "error",
                summary: "Error",
                detail: "Dataset name already exists",
            });
        } else {
            toast.add({
                severity: "error",
                summary: "Upload Failed",
                detail: "Failed to upload BED file. Please try again.",
            });
            console.error("BED file upload failed:", error);
        }
    } finally {
        uploading.value = false;
        uploadProgress.value = 0;
    }
}

function onProgress(percentCompleted) {
    uploadProgress.value = percentCompleted < 100 ? percentCompleted : 0;
}

function clearForm() {
    // Reset all form fields
    bedDatasetName.value = "";
    bedFile.value = null;
    bedFileName.value = "";
    validationResult.value = null;

    // Clear the file input component
    if (bedFileInput.value) {
        bedFileInput.value.clear();
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
</style>
