<template>
    <aside class="flex flex-col gap-10">
        <section class="text-center">
            <h2
                class="mb-4 text-2xl font-semibold text-gray-900 dark:text-white"
            >
                {{ heading }}
            </h2>
            <p class="text-lg leading-relaxed text-gray-600 dark:text-gray-300">
                {{ text }}
            </p>
        </section>

        <section v-if="logos && logos.length" class="text-center">
            <h3
                class="mb-6 text-xl font-semibold text-gray-900 dark:text-white"
            >
                {{ logosHeading }}
            </h3>
            <LogoStrip :logos="logos" />
        </section>
    </aside>
</template>

<script setup>
// Left column shared by the landing page and the GWAS-Hub page:
// an "About the workspace" blurb followed by a logo strip.
defineProps({
    heading: { type: String, default: "About the workspace" },
    text: { type: String, required: true },
    logosHeading: { type: String, default: "" },
    logos: { type: Array, default: () => [] },
});
</script>
