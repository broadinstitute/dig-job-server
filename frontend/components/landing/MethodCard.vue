<template>
    <NuxtLink :to="methodPath(method.slug)" class="block h-full no-underline">
        <Card
            class="h-full text-center transition-shadow duration-300 hover:shadow-lg"
        >
            <template #content>
                <div class="p-4">
                    <div
                        class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full"
                        :class="method.iconWrapClass"
                    >
                        <i
                            class="text-2xl"
                            :class="[method.icon, method.iconClass]"
                        ></i>
                    </div>
                    <h3
                        class="mb-2 text-lg font-semibold text-gray-900 dark:text-white"
                    >
                        {{ method.title }} Analysis
                    </h3>
                    <p class="mb-4 text-sm text-gray-600 dark:text-gray-300">
                        {{ method.blurb }}
                    </p>
                    <div class="flex flex-wrap justify-center gap-2">
                        <Tag
                            v-for="tag in method.tags"
                            :key="tag.value"
                            :value="tag.value"
                            :severity="tag.severity"
                        />
                        <Tag
                            v-if="!method.implemented"
                            value="Coming soon"
                            severity="secondary"
                        />
                    </div>
                </div>
            </template>
        </Card>
    </NuxtLink>
</template>

<script setup>
// One method tile on the landing page; links to its /methods/<slug> page.
import { methodPath } from "~/utils/methods/catalog";

defineProps({
    method: { type: Object, required: true },
});
</script>
