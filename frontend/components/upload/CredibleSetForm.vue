<script setup>
// One credible-set upload form, hosted by the GWAS upload wizard (optional
// step) and by the datasets page's Attach dialog. It validates against the API
// but never uploads: the host decides when (the wizard after the GWAS is
// finalized; the dialog on its Upload button) and calls
// store.uploadCredibleSet(dataset, buildFormData(model)).
import { useUserStore } from "~/stores/UserStore";
import {
    CS_REQUIRED_FIELDS,
    CS_COL_OPTIONS,
    suggestCredibleSetMap,
} from "~/utils/upload/credibleSetFields";
import { selectedFieldsToColMap } from "~/utils/upload/colMap";
import {
    canValidate,
    buildFormData,
    summarizeReport,
    describeUploadError,
} from "~/utils/upload/credibleSetForm";

const props = defineProps({
    // Null in the wizard (the dataset does not exist yet); used only for copy.
    dataset: { type: String, default: null },
});
const emit = defineEmits(["update:modelValue"]);

const store = useUserStore();
const toast = useToast();

const fileInput = ref(null);
const name = ref("");
const file = ref(null);
const fileInfo = ref(null); // { columns, delimiter } from /preview-delimited-file
const selectedFields = ref({});
const report = ref(null);
const validating = ref(false);

const colMap = computed(() => selectedFieldsToColMap(selectedFields.value));
const model = computed(() => ({
    name: name.value,
    file: file.value,
    separator: fileInfo.value?.delimiter ?? null,
    colMap: colMap.value,
    report: report.value,
}));
const validateEnabled = computed(() => canValidate(model.value) && !validating.value);

// Any change to the inputs invalidates the last report; the host's Upload
// button keys off report.ok, so this is what forces a re-validate.
watch([name, file, colMap], () => {
    report.value = null;
});
watch(model, (value) => emit("update:modelValue", value), { immediate: true, deep: true });

async function onSelect(event) {
    file.value = event.files[0];
    try {
        fileInfo.value = await store.sampleTextFile(file.value);
        const guessed = suggestCredibleSetMap(fileInfo.value.columns);
        selectedFields.value = Object.fromEntries(
            fileInfo.value.columns.map((col) => [col, guessed[col] ?? null]),
        );
        const n = Object.keys(guessed).length;
        if (n > 0) {
            toast.add({
                severity: "info",
                summary: "Columns pre-filled",
                detail: `Matched ${n} of ${fileInfo.value.columns.length} columns. Please review before validating.`,
                life: 6000,
            });
        }
    } catch (error) {
        toast.add({
            severity: "error",
            summary: "Error",
            detail:
                error.response?.data?.detail ||
                "Could not parse file. Please ensure it is comma or tab delimited.",
        });
        clear();
    }
}

function clear() {
    file.value = null;
    fileInfo.value = null;
    selectedFields.value = {};
    report.value = null;
    fileInput.value?.clear();
}

async function validate() {
    validating.value = true;
    try {
        report.value = await store.validateCredibleSet(buildFormData(model.value));
    } catch (error) {
        toast.add({
            severity: "error",
            summary: "Validation failed",
            detail: describeUploadError(error),
            life: 8000,
        });
    } finally {
        validating.value = false;
    }
}

defineExpose({ clear });
</script>

<template>
    <div class="credible-set-form">
        <div class="field">
            <label
                for="credible-set-name"
                class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                >Name <span style="color: darkred">*</span></label
            >
            <InputText
                id="credible-set-name"
                v-model.trim="name"
                :maxlength="30"
                placeholder="e.g. SuSiE v1"
                class="w-full"
            />
            <small class="ml-2 text-surface-500">{{ name.length }}/30 · shown in the sifter's set picker</small>
        </div>

        <div class="field mt-3">
            <label
                for="credible-set-file"
                class="block text-surface-600 dark:text-surface-50 text-l font-medium ml-2"
                >File <span style="color: darkred">*</span></label
            >
            <FileUpload
                ref="fileInput"
                id="credible-set-file"
                :multiple="false"
                @select="onSelect"
                @clear="clear"
                @remove="clear"
                :previewWidth="0"
                :show-upload-button="false"
                :disabled="file !== null"
                class="file-upload"
            />
            <small class="ml-2 text-surface-500 block mt-1">
                Comma or tab delimited, optionally .gz. One row per variant with its
                credible set id and posterior probability, on the same genome build as the GWAS.
            </small>
        </div>

        <div class="card flex flex-wrap gap-1 required-card">
            <h6 class="w-full">Required fields:</h6>
            <template v-for="field in CS_REQUIRED_FIELDS" :key="field.value">
                <Chip
                    v-if="Object.values(selectedFields).includes(field.value)"
                    icon="pi pi-check"
                    :label="field.name"
                    class="selected-chip"
                />
                <Chip v-else :label="field.name" />
            </template>
        </div>

        <ColumnMappingTable
            :columns="fileInfo?.columns || []"
            :options="CS_COL_OPTIONS"
            v-model="selectedFields"
        />

        <div class="mt-3 flex items-center gap-3">
            <Button
                type="button"
                label="Validate"
                icon="pi pi-check-square"
                :disabled="!validateEnabled"
                :loading="validating"
                @click="validate"
                outlined
            />
            <small v-if="!file" class="text-surface-500">Choose a file to validate.</small>
        </div>

        <Message v-if="report?.ok" severity="success" class="mt-3" :closable="false">
            {{ summarizeReport(report) }}
            <ul v-if="report.warnings.length" class="mt-2 text-sm list-disc pl-5">
                <li v-for="(w, i) in report.warnings" :key="i">{{ w.message }}</li>
            </ul>
        </Message>
        <Message v-else-if="report" severity="error" class="mt-3" :closable="false">
            <div class="font-medium">The file has problems that must be fixed before upload.</div>
            <table class="mt-2 text-sm">
                <tbody>
                    <tr v-for="(e, i) in report.errors" :key="i">
                        <td class="pr-3 text-right whitespace-nowrap">{{ e.line ? `line ${e.line}` : "" }}</td>
                        <td>{{ e.message }}</td>
                    </tr>
                </tbody>
            </table>
        </Message>
    </div>
</template>

<style scoped>
.required-card {
    border: 1px dashed #ccc;
    padding: 0.5rem;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
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
