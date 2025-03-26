<script setup>
import { useUserStore } from "~/stores/UserStore.js";
import pako from "pako";
import { useTheme } from "~/composables/useTheme";

const { isDarkMode, toggleDarkMode } = useTheme();

const route = useRoute();
const id = route.params.id;
const userStore = useUserStore();
const log = ref(null);
const dataset = ref("");
const loadingLog = ref(false);

onMounted(async () => {
    loadingLog.value = true;
    const { log: rawLog, dataset: datasetValue } =
        await userStore.getLogInfo(id);
    dataset.value = datasetValue;
    const compressed = new Uint8Array(
        rawLog.split("").map((char) => char.charCodeAt(0)),
    );
    log.value = pako.inflate(compressed, { to: "string" });
    loadingLog.value = false;
});
</script>

<template>
    <div class="columns-1 m-6">
        <h2 class="text-2xl font-bold text-center mb-4" v-if="!loadingLog">
            Log for {{ dataset }}
        </h2>
        <Button
            label="Back to Datasets"
            icon="pi pi-arrow-left"
            @click="$router.push('/')"
            class="mb-4"
            outlined
            size="small"
        />
        <Card>
            <template #title>Log Output</template>
            <template #content>
                <template v-if="loadingLog">
                    <div class="skeleton-container">
                        <Skeleton
                            class="mb-2"
                            height="1.5rem"
                            v-for="n in 10"
                            :key="n"
                        />
                    </div>
                </template>
                <template v-else>
                    <Shiki
                        :code="log"
                        lang="log"
                        style="
                            height: 400px;
                            overflow-y: scroll;
                            white-space: pre-wrap;
                        "
                    />
                </template>
            </template>
        </Card>
    </div>
</template>

<style scoped>
.log-container {
    width: 100%;
    min-height: 100vh;
    background-color: #2e3440;
    padding: 20px;
    box-sizing: border-box;
}

.full-width-shiki {
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
}

.full-width-shiki :deep(pre) {
    width: 100%;
    margin: 0;
    padding: 20px;
    box-sizing: border-box;
    white-space: pre-wrap;
    word-break: break-all;
}

.skeleton-container {
    height: 400px;
    overflow-y: hidden;
}
</style>
