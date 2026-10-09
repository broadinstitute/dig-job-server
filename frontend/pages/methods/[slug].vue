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
                    class="space-y-4 rounded-lg border border-surface-200 bg-surface-0 p-6 leading-relaxed text-surface-700 shadow-sm dark:border-surface-700 dark:bg-surface-800 dark:text-surface-200"
                >
                    <p
                        v-if="section.example"
                        class="text-sm text-surface-500 dark:text-surface-400"
                    >
                        Example dataset:
                        <a
                            :href="EXAMPLE_DATASET.url"
                            class="text-primary hover:underline"
                            >{{ EXAMPLE_DATASET.label }}</a
                        >
                    </p>
                    <template
                        v-for="(block, i) in section.blocks"
                        :key="i"
                    >
                        <!-- Trusted, source-controlled copy from utils/methods/docs.js -->
                        <p v-if="typeof block === 'string'" v-html="block"></p>
                        <figure v-else class="py-2">
                            <a
                                :href="block.src"
                                target="_blank"
                                rel="noopener"
                                title="Open full-size image"
                            >
                                <img
                                    :src="block.src"
                                    :alt="block.alt"
                                    loading="lazy"
                                    class="w-full rounded-md border border-surface-200 bg-white dark:border-surface-700"
                                />
                            </a>
                            <figcaption
                                class="mt-2 text-center text-sm text-surface-500 dark:text-surface-400"
                            >
                                {{ block.caption }}
                            </figcaption>
                        </figure>
                    </template>
                    <ul v-if="section.references" class="space-y-2">
                        <li
                            v-for="ref in section.references"
                            :key="ref.url"
                            class="flex items-start gap-2"
                        >
                            <i
                                class="pi pi-external-link mt-1 text-xs text-surface-400"
                            ></i>
                            <a
                                :href="ref.url"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="text-primary hover:underline"
                                >{{ ref.label }}</a
                            >
                        </li>
                    </ul>
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
// Description page for one post-processing method. Copy lives in
// utils/methods/docs.js; card metadata in utils/methods/catalog.js.
import { getMethod } from "~/utils/methods/catalog";
import { EXAMPLE_DATASET, getMethodDocs } from "~/utils/methods/docs";

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

const docs = getMethodDocs(method.slug);

const SECTIONS = docs
    ? [
          { title: "Overview", blocks: docs.overview },
          { title: "Example output", blocks: docs.output, example: true },
          { title: "References", references: docs.references },
      ]
    : [];
</script>
