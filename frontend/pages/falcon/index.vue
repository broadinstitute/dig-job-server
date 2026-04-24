<template>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-6">
        <h1 class="text-2xl font-bold mb-4">FALCON Dashboard</h1>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
            Base scaffold — tab UI arrives in the branch-specific builds.
        </p>

        <div class="flex items-center gap-3 mb-4">
            <input
                ref="folderInput"
                type="file"
                webkitdirectory
                directory
                class="block"
                @change="onFolderSelect"
            />
            <Tag
                v-if="store.folderName"
                severity="success"
                :value="`Active Dataset: ${store.folderName}`"
            />
        </div>

        <p v-if="store.status" class="text-sm text-gray-500 mb-4">
            {{ store.status }}
        </p>

        <ul class="text-sm space-y-1">
            <li>
                genes:
                <b>{{
                    store.datasets.genes.isLoaded ? "loaded" : "—"
                }}</b>
                <span
                    v-if="store.datasets.genes.isLoaded"
                    class="text-gray-500"
                >
                    ({{ store.datasets.genes.data.length }} rows)
                </span>
            </li>
            <li>
                variants:
                <b>{{
                    store.datasets.variants.isLoaded ? "loaded" : "—"
                }}</b>
                <span
                    v-if="store.datasets.variants.isLoaded"
                    class="text-gray-500"
                >
                    ({{ store.datasets.variants.data.length }} rows)
                </span>
            </li>
            <li>
                log:
                <b>{{ store.datasets.log.isLoaded ? "loaded" : "—" }}</b>
                <span
                    v-if="store.datasets.log.isLoaded"
                    class="text-gray-500"
                >
                    ({{ store.datasets.log.chromosomes.size }} chromosomes,
                    total: {{ store.datasets.log.totalTime }})
                </span>
            </li>
        </ul>
    </div>
</template>

<script setup>
import { useFalconStore } from "~/stores/FalconStore";

const store = useFalconStore();

async function onFolderSelect(e) {
    await store.loadFolder(e.target.files);
}
</script>
