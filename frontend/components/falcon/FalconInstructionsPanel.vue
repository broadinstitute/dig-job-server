<template>
  <Drawer v-model:visible="visibleModel" position="right" :style="{ width: '40rem' }">
    <template #header>
      <div class="flex items-center gap-2">
        <i class="pi pi-cog"></i>
        <span class="font-semibold">Run FALCON for: {{ dataset }}</span>
      </div>
    </template>

    <div v-if="loading" class="p-4 text-sm">Preparing your run command…</div>

    <div v-else-if="prepError" class="p-4 space-y-3 text-sm">
      <Message severity="error" :closable="false">
        Couldn't prepare the run command: {{ prepError }}
      </Message>
      <Button label="Try again" size="small" outlined @click="prepare" />
    </div>

    <div v-else-if="token" class="p-4 space-y-4 text-sm">
      <Message severity="info" :closable="false">
        FALCON runs locally on your machine via Docker. Paste the line below
        into a terminal. We'll guide you through it from there and upload
        results automatically when the run finishes.
      </Message>
      <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">curl -fsSL {{ webAppBaseUrl }}/run.sh | FALCON_CHRS=22 bash -s -- {{ token }}</pre>
      <Button icon="pi pi-copy" label="Copy command" size="small" outlined @click="copyCmd" />
      <p class="text-gray-600 dark:text-gray-400 text-xs">
        <code>FALCON_CHRS</code> limits the run to specific chromosomes
        (e.g. <code>22</code>, <code>1,3,5-7</code>) — faster and far less disk.
        Change <code>22</code> to match your GWAS, or remove
        <code>FALCON_CHRS=22</code> to run the whole genome (~40&nbsp;GB).
      </p>
      <p class="text-gray-600 dark:text-gray-400 text-xs">
        Tweaking the run? See the
        <a :href="readmeUrl" target="_blank" rel="noopener noreferrer"
           class="text-primary-600 hover:underline">FALCON README</a>.
      </p>
    </div>
  </Drawer>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  visible: { type: Boolean, required: true },
  dataset: { type: String, required: true },
  filename: { type: String, default: "gwas.tsv" },
});
const emit = defineEmits(["update:visible", "openUpload"]);

const visibleModel = computed({
  get: () => props.visible,
  set: (v) => emit("update:visible", v),
});

const toast = useToast();
const config = useRuntimeConfig();
const readmeUrl = "https://github.com/LlamasCorp/PEGS#readme";

// /run.sh and the result-upload callbacks are served by the API. In prod the
// frontend and API share an origin (apiBaseUrl is empty), so fall back to the
// page origin; in local dev apiBaseUrl points at the API (e.g. :8000).
const webAppBaseUrl = computed(() => {
  if (config.public.apiBaseUrl) return config.public.apiBaseUrl;
  if (typeof window !== "undefined") return window.location.origin;
  return "https://gwas-ce.kpndataregistry.org";
});

const loading = ref(false);
const token = ref(null);
const prepError = ref(null);

// The panel is always mounted by the datasets page, so it's hidden at mount
// time — mint the run token when the drawer actually opens for a dataset
// (and re-mint if the dataset changes while the drawer is open).
async function prepare() {
  loading.value = true;
  token.value = null;
  prepError.value = null;
  try {
    const r = await fetchFalconRunToken(props.dataset);
    token.value = r.token;
  } catch (e) {
    console.error("[FalconInstructionsPanel] run-token fetch failed:", e);
    prepError.value = e?.message || "Failed to reach the server.";
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.visible, props.dataset],
  ([visible]) => {
    if (visible) prepare();
  },
  { immediate: true },
);

function copyCmd() {
  const cmd = `curl -fsSL ${webAppBaseUrl.value}/run.sh | FALCON_CHRS=22 bash -s -- ${token.value}`;
  navigator.clipboard.writeText(cmd);
  toast.add({
    severity: "success",
    summary: "Copied",
    detail: "Command copied",
    life: 2000,
  });
}
</script>
