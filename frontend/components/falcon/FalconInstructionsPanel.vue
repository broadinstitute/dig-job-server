<template>
  <Drawer v-model:visible="visibleModel" position="right" :style="{ width: '40rem' }">
    <template #header>
      <div class="flex items-center gap-2">
        <i class="pi pi-cog"></i>
        <span class="font-semibold">Run FALCON for: {{ dataset }}</span>
      </div>
    </template>

    <div class="space-y-4 text-sm">
      <Message severity="info" :closable="false">
        FALCON runs locally on your machine via Docker. The web app will
        guide you through it and verify the results when you upload them.
      </Message>

      <section>
        <h3 class="font-semibold mb-1">1. Create the working directory</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-2">
          Everything you give to the docker container lives here. The
          container mounts it at <code>/work</code> when it runs.
        </p>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">mkdir -p ~/falcon-work
cd ~/falcon-work</pre>
      </section>

      <section>
        <h3 class="font-semibold mb-1">2. Put this dataset's GWAS file in the working directory</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-2">
          Use the exact file you uploaded — the docker image hashes its bytes
          and the server checks that hash against this dataset's GWAS. No
          decompression or re-compression in between. The file must be named
          <code>{{ filename }}</code> so the config below points to it.
        </p>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto"># copy your local GWAS into the working dir, naming it as below:
cp /path/to/your/copy ~/falcon-work/{{ filename }}</pre>
      </section>

      <section>
        <h3 class="font-semibold mb-1">3. Pull the docker image</h3>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">docker pull sagehen03/falcon:latest</pre>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Full image docs:
          <a
            href="https://hub.docker.com/r/sagehen03/falcon"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary-600 hover:underline"
          >hub.docker.com/r/sagehen03/falcon</a>
        </p>
      </section>

      <section>
        <h3 class="font-semibold mb-1">4. Save this as ~/falcon-work/config.ini</h3>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">{{ configSnippet }}</pre>
        <Button
          icon="pi pi-copy"
          label="Copy config"
          @click="copyConfig"
          size="small"
          outlined
          class="mt-2"
        />
        <p class="text-gray-600 dark:text-gray-400 mt-2">
          <strong>Important:</strong> <code>chr-to-update</code> must match the
          chromosomes actually present in your GWAS. If your file only has chr
          22, set <code>chr-to-update = 22</code> — leaving it at
          <code>1-22</code> spawns workers for every chromosome and any worker
          that finds no data will fail the run (non-zero exit, no upload).
          Syntax is the same as <code>fetch-reference --chrs</code>:
          <code>"22"</code>, <code>"1-3"</code>, <code>"1,3,5-7,22"</code>.
        </p>
      </section>

      <section>
        <h3 class="font-semibold mb-1">5. Fetch reference data (one-time)</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-2">
          The full reference bundle (LD, genes, V2G) is about 60 GB. If you
          only need a subset of chromosomes — e.g. for a debug run or a
          single-chr pilot — pass <code>--chrs</code> with the same syntax
          as the config's <code>chr-to-update</code>
          (<code>"22"</code>, <code>"1-3"</code>, <code>"1,3,5-7,22"</code>).
          Re-running is idempotent, so you can expand later.
        </p>
        <p class="text-gray-600 dark:text-gray-400 mb-1">
          <strong>Whole genome</strong> (~60 GB, takes a while):
        </p>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">mkdir -p ~/falcon-data
docker run --rm -v ~/falcon-data:/falcon-data \
  sagehen03/falcon:latest fetch-reference /falcon-data</pre>
        <p class="text-gray-600 dark:text-gray-400 mt-2 mb-1">
          <strong>Just chromosome 22</strong> (~280 MB, ~30 s — good for smoke testing):
        </p>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">mkdir -p ~/falcon-data
docker run --rm -v ~/falcon-data:/falcon-data \
  sagehen03/falcon:latest fetch-reference /falcon-data --chrs 22</pre>
      </section>

      <section>
        <h3 class="font-semibold mb-1">6. Run FALCON</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-2">
          Mounts your working dir at <code>/work</code> and the reference
          dir at <code>/falcon-data</code>:
        </p>
        <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto">docker run --rm \
  -v ~/falcon-data:/falcon-data:ro \
  -v ~/falcon-work:/work \
  sagehen03/falcon:latest run /work/config.ini</pre>
        <p class="text-gray-600 dark:text-gray-400 mt-1">
          Whole-genome runs take 4–12 hours on a modern laptop. Results
          land in <code>~/falcon-work/results/</code>.
        </p>
      </section>

      <section>
        <h3 class="font-semibold mb-1">7. Upload your results</h3>
        <p class="text-gray-600 dark:text-gray-400 mb-2">
          When the run finishes, the container prints an upload URL — or
          click below.
        </p>
        <Button
          icon="pi pi-upload"
          label="Upload FALCON results"
          @click="emit('openUpload')"
          severity="primary"
          size="small"
        />
      </section>
    </div>
  </Drawer>
</template>

<script setup>
import { computed } from "vue";

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

const webAppBaseUrl = computed(() => {
  if (typeof window !== "undefined") return window.location.origin;
  return "https://gwas-ce.kpndataregistry.org";
});

const configSnippet = computed(() => `[Settings]
out-base-name      = /work/results/run1
ld-folder          = /falcon-data/LD/
gene-folder        = /falcon-data/genes/
s2g-folder         = /falcon-data/V2G/

sumstats-file      = /work/${props.filename}
dataset-name       = ${props.dataset}
web-app-base-url   = ${webAppBaseUrl.value}

sample-size        = 625000
inf-heritability   = 0.1212
chr-to-update      = 1-22

sumstats-id-col    = rsID
sumstats-chr-col   = CHROM
ld-chrom1-col      = CHR_A
s2g-rsid-col       = SNP
s2g-score-col      = cS2G
`);

function copyConfig() {
  navigator.clipboard.writeText(configSnippet.value);
  toast.add({
    severity: "success",
    summary: "Copied",
    detail: "config.ini copied to clipboard",
    life: 2000,
  });
}
</script>
