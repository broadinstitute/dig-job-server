<template>
  <Dialog
    v-model:visible="visibleModel"
    :header="`Upload FALCON results for ${dataset}`"
    modal
    :style="{ width: '36rem' }"
  >
    <div class="space-y-4 text-sm">
      <Message v-if="!hasSelection" severity="info" :closable="false">
        Select your <code>results/</code> folder (or drop it below). The
        upload must include <code>manifest.json</code> — without it the
        server can't verify the results.
      </Message>

      <div
        v-if="!hasSelection"
        class="border-2 border-dashed rounded p-6 text-center"
        :class="dragOver ? 'border-primary-500 bg-primary-50 dark:bg-primary-900' : 'border-gray-300'"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="onDrop"
      >
        <i class="pi pi-cloud-upload text-2xl"></i>
        <p class="mt-2">Drop your results folder here</p>
        <p class="my-2 text-gray-500">— or —</p>
        <input
          ref="fileInput"
          type="file"
          webkitdirectory
          multiple
          class="hidden"
          @change="onFilesPicked"
        />
        <Button label="Choose folder" @click="fileInput?.click()" size="small" />
      </div>

      <div v-else>
        <p class="font-semibold mb-2">{{ files.length }} files selected:</p>
        <ul class="text-xs max-h-40 overflow-y-auto space-y-1">
          <li v-for="(f, i) in files" :key="f.name" class="flex justify-between">
            <span class="truncate">{{ f.name }}</span>
            <span v-if="progress[i] != null" class="text-gray-500 ml-2">
              {{ progress[i] }}%
            </span>
          </li>
        </ul>
        <Message v-if="!hasManifest" severity="warn" :closable="false" class="mt-2">
          <code>manifest.json</code> is not in your selection. Make sure
          you selected the <code>results/</code> folder produced by
          <code>sagehen03/falcon:0.2.0</code> or later.
        </Message>
        <Message v-if="errorMessage" severity="error" :closable="false" class="mt-2">
          {{ errorMessage }}
        </Message>
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" outlined @click="close" :disabled="busy" />
      <Button
        label="Upload"
        icon="pi pi-upload"
        @click="upload"
        :disabled="!hasSelection || !hasManifest || busy"
        :loading="busy"
      />
    </template>
  </Dialog>
</template>

<script setup>
import { computed, ref } from "vue";
import { useUserStore } from "~/stores/UserStore";
import { usePresignedS3Upload } from "~/composables/usePresignedS3Upload";

const props = defineProps({
  visible: { type: Boolean, required: true },
  dataset: { type: String, required: true },
});
const emit = defineEmits(["update:visible", "uploaded"]);

const visibleModel = computed({
  get: () => props.visible,
  set: (v) => emit("update:visible", v),
});

const fileInput = ref(null);
const files = ref([]);
const progress = ref([]);
const busy = ref(false);
const dragOver = ref(false);
const errorMessage = ref("");
const toast = useToast();
const userStore = useUserStore();
const { putToPresigned } = usePresignedS3Upload();

const hasSelection = computed(() => files.value.length > 0);

// The PEGS docker image writes the manifest as `<out-base-name>.wg.manifest.json`
// (e.g. `run1.wg.manifest.json`). The server's finalize endpoint expects the
// S3 key to be plain `manifest.json`, so we identify the manifest by suffix
// here and rename it to `manifest.json` at upload time.
function isManifestName(name) {
  return name === "manifest.json" || name.endsWith(".wg.manifest.json");
}
const hasManifest = computed(() => files.value.some((f) => isManifestName(f.name)));

function onFilesPicked(e) {
  files.value = Array.from(e.target.files || []);
  progress.value = files.value.map(() => null);
}

function onDrop(e) {
  dragOver.value = false;
  const items = e.dataTransfer.items;
  if (items && items.length && items[0].webkitGetAsEntry) {
    const out = [];
    let pending = 0;
    let scanning = 0;
    function maybeFinalize() {
      if (pending === 0 && scanning === 0) {
        files.value = out;
        progress.value = out.map(() => null);
      }
    }
    function walk(entry) {
      if (entry.isFile) {
        pending++;
        entry.file((f) => {
          // Use just the leaf name — manifest.json must be findable by name.
          out.push(new File([f], f.name));
          pending--;
          maybeFinalize();
        });
      } else if (entry.isDirectory) {
        scanning++;
        const reader = entry.createReader();
        reader.readEntries((entries) => {
          entries.forEach((c) => walk(c));
          scanning--;
          maybeFinalize();
        });
      }
    }
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) walk(entry);
    }
  } else {
    files.value = Array.from(e.dataTransfer.files);
    progress.value = files.value.map(() => null);
  }
}

function close() {
  emit("update:visible", false);
  files.value = [];
  progress.value = [];
  errorMessage.value = "";
}

async function upload() {
  busy.value = true;
  errorMessage.value = "";
  try {
    // Rename `<out-base-name>.wg.manifest.json` → `manifest.json` at upload
    // time so the backend finds it at the canonical S3 key. Other files
    // keep their original names.
    const uploadNameOf = (name) => (isManifestName(name) ? "manifest.json" : name);

    const fileMeta = files.value.map((f) => ({ name: uploadNameOf(f.name), size: f.size }));
    const { uploads } = await userStore.getFalconUploadUrls(props.dataset, fileMeta);
    const urlByName = Object.fromEntries(uploads.map((u) => [u.name, u.url]));

    await Promise.all(
      files.value.map(async (f, i) => {
        const uploadName = uploadNameOf(f.name);
        const url = urlByName[uploadName];
        if (!url) throw new Error(`server did not provide URL for ${uploadName}`);
        await putToPresigned(url, f, {
          onProgress: (pct) => { progress.value[i] = pct; },
        });
      }),
    );

    await userStore.finalizeFalconUpload(props.dataset);
    toast.add({
      severity: "success",
      summary: "FALCON upload accepted",
      detail: `Results for ${props.dataset} are now viewable.`,
      life: 4000,
    });
    emit("uploaded");
    close();
  } catch (err) {
    const body = err?.response?.data;
    if (body?.error === "input_sha256_mismatch") {
      errorMessage.value =
        `These results were computed from a different file than ` +
        `${props.dataset}'s GWAS. Re-run FALCON against the file you uploaded ` +
        `(expected sha256 ${body.expected?.slice(0, 12)}…, got ${body.got?.slice(0, 12)}…).`;
    } else if (body?.error === "dataset_name_mismatch") {
      errorMessage.value =
        `The manifest says these results are for dataset ` +
        `"${body.got}", not "${body.expected}". Switch to that dataset's row to upload.`;
    } else if (body?.error === "missing_manifest") {
      errorMessage.value = body.detail || "manifest.json missing.";
    } else if (body?.error === "gwas_sha256_missing_on_dataset") {
      errorMessage.value =
        "This dataset was uploaded before FALCON support existed. " +
        "Re-upload the GWAS to enable FALCON.";
    } else {
      errorMessage.value = err?.message || "Upload failed.";
    }
  } finally {
    busy.value = false;
  }
}
</script>
