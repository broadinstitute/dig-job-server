<template>
    <NuxtLink
        :to="methodPath(method.slug)"
        class="method-card flex h-full flex-col border border-t-[3px] border-x-surface-200 border-b-surface-200 bg-surface-0 px-3.5 pt-3.5 pb-3 no-underline dark:border-x-surface-600 dark:border-b-surface-600 dark:bg-surface-800"
        :style="{ borderTopColor: method.accent }"
    >
        <!-- Only the side and bottom borders are themed so the accent top
             edge shows in both light and dark mode. -->
        <MethodIcon :slug="method.slug" :accent="method.accent" class="mb-3 self-center" />
        <h3 class="method-title text-surface-900 dark:text-surface-0">
            {{ method.title }}
        </h3>
        <div
            v-if="method.fullName"
            class="method-expand text-surface-500 dark:text-surface-400"
        >
            {{ method.fullName }}
        </div>
        <p
            class="method-blurb flex-auto text-surface-600 dark:text-surface-300"
        >
            {{ method.blurb }}
        </p>
        <!-- <div v-if="!method.implemented || method.external" class="mt-3">
            <Tag
                :value="method.implemented ? 'External service' : 'Coming soon'"
                severity="secondary"
            />
        </div> -->
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
/* Elevation. In dark mode a shadow alone barely registers against the dark
   page, so the card also sits on a lighter surface (surface-800, set in the
   template) with a faint top highlight. */
.method-card {
    box-shadow:
        0 1px 2px rgb(44 36 34 / 0.08),
        0 3px 8px rgb(44 36 34 / 0.1);
    transition:
        box-shadow 150ms ease,
        transform 150ms ease;
}

.method-card:hover {
    box-shadow:
        0 4px 8px rgb(44 36 34 / 0.12),
        0 12px 24px rgb(44 36 34 / 0.14);
    transform: translateY(-2px);
}

html.dark .method-card {
    box-shadow:
        inset 0 1px 0 rgb(255 255 255 / 0.06),
        0 2px 4px rgb(0 0 0 / 0.5),
        0 6px 14px rgb(0 0 0 / 0.45);
}

html.dark .method-card:hover {
    box-shadow:
        inset 0 1px 0 rgb(255 255 255 / 0.1),
        0 6px 12px rgb(0 0 0 / 0.55),
        0 16px 32px rgb(0 0 0 / 0.5);
}

@media (prefers-reduced-motion: reduce) {
    .method-card,
    .method-card:hover {
        transition: none;
        transform: none;
    }
}

/* Typography from the GWAS-CE landing mock-up (fonts loaded in nuxt.config.ts). */
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
