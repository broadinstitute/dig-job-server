<template>
    <figure class="my-8">
        <div
            class="flex h-64 w-full flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-gray-300 text-gray-400 dark:border-gray-600 dark:text-gray-500"
        >
            <i class="pi pi-image text-4xl"></i>
            <span class="text-sm">Figure placeholder</span>
        </div>
        <figcaption
            v-if="caption"
            class="mt-2 text-center text-sm text-gray-500 dark:text-gray-400"
        >
            {{ caption }}
        </figcaption>
    </figure>
</template>

<script setup>
// Dashed box standing in for a diagram that has not been produced yet.
defineProps({
    caption: { type: String, default: "" },
});
</script>
