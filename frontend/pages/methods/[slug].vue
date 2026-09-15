<template>
    <div class="mx-auto w-full max-w-4xl px-6 py-10">
        <NuxtLink
            to="/"
            class="mb-6 inline-flex items-center gap-2 text-sm text-primary hover:underline"
        >
            <i class="pi pi-arrow-left"></i> Back to home
        </NuxtLink>

        <header
            class="mb-10 flex items-start gap-5 border-b border-surface-200 pb-6 dark:border-surface-700"
        >
            <div
                class="flex h-16 w-16 shrink-0 items-center justify-center rounded-full"
                :class="method.iconWrapClass"
            >
                <i class="text-3xl" :class="[method.icon, method.iconClass]"></i>
            </div>
            <div>
                <h1
                    class="mb-2 text-4xl font-bold text-surface-900 dark:text-surface-0"
                >
                    {{ method.title }}
                </h1>
                <p class="text-xl text-surface-600 dark:text-surface-400">
                    {{ method.blurb }}
                </p>
                <div class="mt-3 flex flex-wrap gap-2">
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
        </header>

        <Message
            v-if="!method.implemented"
            severity="info"
            :closable="false"
            class="mb-8"
        >
            {{ method.title }} is not yet available to run in GWAS-CE.
        </Message>

        <div class="space-y-10">
            <section v-for="section in SECTIONS" :key="section.title">
                <h2
                    class="mb-3 text-2xl font-semibold text-primary-600 dark:text-primary-400"
                >
                    {{ section.title }}
                </h2>
                <div
                    class="rounded-lg border border-surface-200 bg-surface-0 p-6 text-surface-700 shadow-sm dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200"
                >
                    <p>{{ section.placeholder }}</p>
                </div>
            </section>
        </div>

        <div class="mt-12 text-center">
            <Button
                v-if="method.implemented"
                label="Upload GWAS data to run this method"
                icon="pi pi-upload"
                size="large"
                @click="$router.push('/upload')"
            />
        </div>
    </div>
</template>

<script setup>
// Description page for one post-processing method. Content is placeholder
// text for now; the structure (Overview / Inputs / Outputs / References) is
// what the final copy will slot into.
import { getMethod } from "~/utils/methods/catalog";

definePageMeta({ requiresAuth: false });

const route = useRoute();
const method = getMethod(route.params.slug);

if (!method) {
    throw createError({
        statusCode: 404,
        statusMessage: `Unknown method: ${route.params.slug}`,
        fatal: true,
    });
}

useHead({ title: `${method.title} - GWAS-CE` });

const SECTIONS = [
    {
        title: "Overview",
        placeholder: `Placeholder: what ${method.title} does, the question it answers, and when to use it.`,
    },
    {
        title: "Inputs",
        placeholder: `Placeholder: the GWAS summary statistics columns and reference data ${method.title} requires.`,
    },
    {
        title: "Outputs",
        placeholder: `Placeholder: the result tables and plots produced by ${method.title} and how to read them.`,
    },
    {
        title: "References",
        placeholder: "Placeholder: primary publication and software links.",
    },
];
</script>
