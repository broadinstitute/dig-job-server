<template>
    <component
        :is="disabled ? 'div' : NuxtLink"
        :to="disabled ? undefined : to"
        class="block h-full no-underline"
        :class="{ 'cursor-not-allowed': disabled }"
        :aria-disabled="disabled || undefined"
    >
        <Card
            class="h-full border-2 border-transparent transition-all duration-300"
            :class="
                disabled
                    ? 'opacity-60'
                    : 'cursor-pointer hover:-translate-y-1 hover:border-primary hover:shadow-xl'
            "
        >
            <template #content>
                <div class="flex flex-col items-center p-4 text-center">
                    <div
                        v-if="icon"
                        class="mb-4 flex h-14 w-14 items-center justify-center rounded-full"
                        :class="iconWrapClass"
                    >
                        <i class="text-2xl" :class="[icon, iconClass]"></i>
                    </div>
                    <h3
                        class="mb-2 text-2xl font-semibold text-gray-900 dark:text-white"
                    >
                        {{ title }}
                    </h3>
                    <p
                        v-if="description"
                        class="text-base text-gray-600 dark:text-gray-300"
                    >
                        {{ description }}
                    </p>
                </div>
            </template>
        </Card>
    </component>
</template>

<script setup>
// A large clickable card that routes somewhere in the app (GWAS-Hub,
// Post-Processing Methods, Genomic Annotation, Quality Control, ...).
// NuxtLink rather than @click so middle-click / open-in-new-tab work.
// With `disabled` the card renders as a plain, dimmed block with no link.
import { NuxtLink } from "#components";

defineProps({
    title: { type: String, required: true },
    description: { type: String, default: "" },
    to: { type: String, required: true },
    icon: { type: String, default: "" },
    iconWrapClass: {
        type: String,
        default: "bg-primary-100 dark:bg-primary-900/30",
    },
    iconClass: { type: String, default: "text-primary" },
    disabled: { type: Boolean, default: false },
});
</script>
