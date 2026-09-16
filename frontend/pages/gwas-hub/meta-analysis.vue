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
                Meta-Analysis Pipeline
            </h1>
            <p class="text-xl text-surface-600 dark:text-surface-400">
                High-level summary of the meta-analysis pipeline
            </p>
        </header>

        <div class="space-y-6 text-surface-700 dark:text-surface-200">
            <p>
                Placeholder: describe how QC-passed cohort GWAS are combined per
                phenotype, the meta-analysis model used, and how the ignore
                list excludes cohorts from a run.
            </p>
            <PlaceholderFigure caption="Meta-analysis pipeline overview" />
            <p>
                Placeholder: describe the outputs shared back to the
                consortium and how results are versioned.
            </p>
        </div>
    </div>
</template>

<script setup>
definePageMeta({ layout: "gwas-hub" });
useHead({ title: "Meta-Analysis - GWAS-Hub" });
</script>
