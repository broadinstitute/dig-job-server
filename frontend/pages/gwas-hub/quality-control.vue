<template>
    <div class="mx-auto w-full max-w-4xl px-6 py-10">
        <NuxtLink
            to="/gwas-hub"
            class="mb-6 inline-flex items-center gap-2 text-sm text-primary hover:underline"
        >
            <i class="pi pi-arrow-left"></i> Back to GWAS-Hub
        </NuxtLink>

        <header
            class="mb-10 border-b border-surface-200 pb-6 dark:border-surface-700"
        >
            <h1
                class="mb-3 text-4xl font-bold text-surface-900 dark:text-surface-0"
            >
                Quality Control Pipeline
            </h1>
            <p class="text-xl text-surface-600 dark:text-surface-400">
                High-level summary of the canonical quality control pipeline
            </p>
        </header>

        <div class="space-y-6 text-surface-700 dark:text-surface-200">
            <p>
                Placeholder: describe the steps a submitted GWAS goes through
                before it is accepted into the hub, such as column
                harmonization, allele and build checks, variant filtering, and
                summary QC plots.
            </p>
            <PlaceholderFigure caption="Quality control pipeline overview" />
            <p>
                Placeholder: describe what the QC report contains and how
                cohorts are flagged for follow-up.
            </p>
        </div>
    </div>
</template>

<script setup>
definePageMeta({ layout: "gwas-hub" });
useHead({ title: "Quality Control - GWAS-Hub" });
</script>
