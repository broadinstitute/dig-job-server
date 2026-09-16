<template>
    <div class="flex flex-wrap items-center justify-center gap-6">
        <component
            :is="logo.href ? 'a' : 'div'"
            v-for="logo in logos"
            :key="logo.name"
            :href="logo.href"
            :target="logo.href ? '_blank' : undefined"
            :rel="logo.href ? 'noopener' : undefined"
            class="flex items-center justify-center"
            :class="logo.bgClass"
        >
            <!--
                Explicit height, not max-height: an SVG with only a viewBox
                has no intrinsic size and would collapse to zero width in this
                shrink-to-fit flex item. Width follows the aspect ratio.
            -->
            <img
                v-if="logo.src"
                :src="logo.src"
                :alt="logo.name"
                class="h-16 w-auto object-contain"
            />
            <div
                v-else
                class="flex h-16 w-40 items-center justify-center rounded-lg border-2 border-dashed border-gray-300 px-3 text-center text-xs font-medium text-gray-500 dark:border-gray-600 dark:text-gray-400"
            >
                {{ logo.name }}
            </div>
        </component>
    </div>
</template>

<script setup>
// Row of partner / funder logos. Entries without `src` render as labelled
// placeholder tiles until the image files are provided. `bgClass` paints a
// panel behind logos whose artwork assumes a coloured background.
// See utils/partners/logos.js for the data shape.
defineProps({
    logos: { type: Array, required: true },
});
</script>
