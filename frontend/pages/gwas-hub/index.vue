<template>
    <div class="mx-auto w-full max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <div class="flex flex-col gap-8">
            <div class="text-center">
                <h1
                    class="mb-4 text-4xl font-bold text-gray-900 md:text-5xl dark:text-white"
                >
                    GWAS-Hub
                </h1>
                <p class="text-xl text-gray-600 dark:text-gray-300">
                    Conduct and share GWAS quality control data and
                    meta-analysis results in one place
                </p>
            </div>

            <FeatureCard
                title="Quality Control"
                description="High-level summary of the canonical quality control pipeline"
                to="/gwas-hub/quality-control"
                icon="pi pi-check-square"
                iconWrapClass="bg-green-100 dark:bg-green-900/20"
                iconClass="text-green-600 dark:text-green-400"
            />

            <FeatureCard
                title="Meta-Analysis"
                description="High-level summary of the meta-analysis pipeline"
                to="/gwas-hub/meta-analysis"
                icon="pi pi-objects-column"
                iconWrapClass="bg-blue-100 dark:bg-blue-900/20"
                iconClass="text-blue-600 dark:text-blue-400"
            />

            <!--
                The hub's data tabs are not live yet, so the call to action
                is the contact button rather than a Get Started link.
            -->
            <div class="mt-4 flex flex-col items-center gap-3 text-center">
                <ContactAdminButton label="Contact admin to sign up" />
                <p class="text-sm text-gray-500 dark:text-gray-400">
                    GWAS-Hub data tools are coming soon.
                </p>
            </div>

            <!-- About + partners -->
            <div
                class="mt-6 border-t border-gray-200 pt-12 dark:border-gray-700"
            >
                <WorkspaceAbout
                    heading="About the workspace"
                    text="GWAS-Hub is your unified workspace for running GWAS quality control processes and conducting meta-analyses"
                    logosHeading="Proudly trusted by"
                    :logos="PARTNER_LOGOS"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
import { PARTNER_LOGOS } from "~/utils/partners/logos";

definePageMeta({ layout: "gwas-hub" });

useHead({ title: "GWAS-Hub - GWAS-CE" });
</script>
