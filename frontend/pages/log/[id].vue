<script setup>
import { useUserStore } from "~/stores/UserStore.js";
import pako from "pako";
import { useTheme } from "~/composables/useTheme";
const { isDarkMode, toggleDarkMode } = useTheme();

const route = useRoute();
const id = route.params.id;
const userStore = useUserStore();
const log = ref(null);

onMounted(async () => {
    const rawLog = await userStore.getLogInfo(id);
    const compressed = new Uint8Array(
        rawLog.log.split("").map((char) => char.charCodeAt(0)),
    );
    log.value = pako.inflate(compressed, { to: "string" });
});
</script>

<template>
    <div class="columns-1 mt-6">
        <Card>
            <template #title>Log Output</template>
            <template #content>
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
</style>
