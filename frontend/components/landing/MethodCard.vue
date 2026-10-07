<template>
    <NuxtLink
        :to="methodPath(method.slug)"
        class="method-card flex h-full flex-col border border-t-[3px] border-x-surface-200 border-b-surface-200 bg-surface-0 px-3.5 pt-3.5 pb-3 no-underline transition-shadow duration-150 hover:shadow-md dark:border-x-surface-700 dark:border-b-surface-700 dark:bg-surface-900"
        :class="method.accentClass"
    >
        <!-- Only the side and bottom borders are themed so the accent top
             edge (accentClass) shows in both light and dark mode. -->
        <h3 class="method-title text-surface-900 dark:text-surface-0">
            {{ method.title }}
        </h3>
        <div
            v-if="method.fullName"
            class="method-expand text-surface-500 dark:text-surface-400"
        >
            {{ method.fullName }}
        </div>
        <p class="method-blurb flex-auto text-surface-600 dark:text-surface-300">
            {{ method.blurb }}
        </p>
        <div v-if="!method.implemented" class="mt-3">
            <Tag value="Coming soon" severity="secondary" />
        </div>
    </NuxtLink>
</template>

<script setup>
// One method tile on the landing page; links to its /methods/<slug> page.
import { methodPath } from "~/utils/methods/catalog";

defineProps({
    method: { type: Object, required: true },
});
</script>

<style scoped>
/* Typography from the GWAS-CE landing mock-up (fonts loaded by pages/index.vue). */
.method-title {
    margin: 0 0 4px 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-weight: 400;
    font-size: 19px;
    letter-spacing: 0.02em;
}

.method-expand {
    margin-bottom: 8px;
    font-family: "Roboto", Arial, sans-serif;
    font-size: 12px;
    font-weight: 400;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.method-blurb {
    margin: 0;
    font-family: "Roboto", Arial, sans-serif;
    font-size: 13.5px;
    font-weight: 300;
    line-height: 1.45;
}
</style>
