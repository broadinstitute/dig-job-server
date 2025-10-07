<script setup>
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
    <div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
        <div class="flex-1 flex items-center justify-center px-6 py-12">
            <div class="max-w-6xl w-full">
                <!-- Welcome Header -->
                <div class="text-center mb-12">
                    <div class="mb-6">
                        <i
                            class="pi pi-sparkles text-7xl text-primary opacity-80 animate-pulse"
                        ></i>
                    </div>
                    <h1
                        class="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4"
                    >
                        Welcome to GWAS Analysis Platform
                    </h1>
                    <p class="text-xl text-gray-600 dark:text-gray-400">
                        Get started by uploading your data
                    </p>
                </div>

                <!-- Workflow Cards -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
                    <!-- GWAS Upload Card -->
                    <Card
                        class="hover:shadow-xl transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-primary transform hover:-translate-y-1"
                    >
                        <template #content>
                            <div
                                class="flex flex-col items-center text-center p-6"
                            >
                                <div
                                    class="w-20 h-20 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-6"
                                >
                                    <i
                                        class="pi pi-chart-line text-4xl text-blue-600 dark:text-blue-400"
                                    ></i>
                                </div>
                                <h3
                                    class="text-2xl font-semibold text-gray-900 dark:text-white mb-3"
                                >
                                    GWAS Summary Statistics
                                </h3>
                                <p
                                    class="text-base text-gray-600 dark:text-gray-400 mb-6"
                                >
                                    Upload genome-wide association study summary
                                    statistics to run enrichment analyses
                                </p>
                                <div class="text-left w-full mb-6">
                                    <p
                                        class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3"
                                    >
                                        Available Workflows:
                                    </p>
                                    <ul
                                        class="text-sm text-gray-600 dark:text-gray-400 space-y-2"
                                    >
                                        <li class="flex items-start gap-3">
                                            <i
                                                class="pi pi-check-circle text-green-500 mt-0.5 text-lg"
                                            ></i>
                                            <span
                                                ><strong>SLDSC:</strong>
                                                Stratified LD Score Regression
                                                for tissue enrichment</span
                                            >
                                        </li>
                                        <li class="flex items-start gap-3">
                                            <i
                                                class="pi pi-check-circle text-green-500 mt-0.5 text-lg"
                                            ></i>
                                            <span
                                                ><strong>MAGMA:</strong>
                                                Gene-set enrichment
                                                analysis</span
                                            >
                                        </li>
                                    </ul>
                                </div>
                                <Button
                                    @click="router.push('/upload')"
                                    label="Upload GWAS Data"
                                    icon="pi pi-upload"
                                    size="large"
                                    class="w-full"
                                    severity="primary"
                                />
                            </div>
                        </template>
                    </Card>

                    <!-- BED Upload Card -->
                    <Card
                        class="hover:shadow-xl transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-primary transform hover:-translate-y-1"
                    >
                        <template #content>
                            <div
                                class="flex flex-col items-center text-center p-6"
                            >
                                <div
                                    class="w-20 h-20 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center mb-6"
                                >
                                    <i
                                        class="pi pi-map text-4xl text-purple-600 dark:text-purple-400"
                                    ></i>
                                </div>
                                <h3
                                    class="text-2xl font-semibold text-gray-900 dark:text-white mb-3"
                                >
                                    BED Annotation Files
                                </h3>
                                <p
                                    class="text-base text-gray-600 dark:text-gray-400 mb-6"
                                >
                                    Upload genomic region annotations in BED
                                    format for custom enrichment analysis
                                </p>
                                <div class="text-left w-full mb-6">
                                    <p
                                        class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3"
                                    >
                                        Use Cases:
                                    </p>
                                    <ul
                                        class="text-sm text-gray-600 dark:text-gray-400 space-y-2"
                                    >
                                        <li class="flex items-start gap-3">
                                            <i
                                                class="pi pi-check-circle text-green-500 mt-0.5 text-lg"
                                            ></i>
                                            <span
                                                >Custom genomic region
                                                annotations</span
                                            >
                                        </li>
                                        <li class="flex items-start gap-3">
                                            <i
                                                class="pi pi-check-circle text-green-500 mt-0.5 text-lg"
                                            ></i>
                                            <span
                                                >Tissue-specific regulatory
                                                elements</span
                                            >
                                        </li>
                                        <li class="flex items-start gap-3">
                                            <i
                                                class="pi pi-check-circle text-green-500 mt-0.5 text-lg"
                                            ></i>
                                            <span
                                                >Functional genomic
                                                annotations</span
                                            >
                                        </li>
                                    </ul>
                                </div>
                                <Button
                                    @click="router.push('/bed-upload')"
                                    label="Upload BED File"
                                    icon="pi pi-upload"
                                    size="large"
                                    class="w-full"
                                    severity="secondary"
                                />
                            </div>
                        </template>
                    </Card>
                </div>

                <!-- Quick Start Guide -->
                <Card
                    class="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border border-gray-200 dark:border-gray-700"
                >
                    <template #content>
                        <div class="p-6">
                            <div class="flex items-center gap-3 mb-6">
                                <i class="pi pi-book text-2xl text-primary"></i>
                                <h4
                                    class="text-xl font-semibold text-gray-900 dark:text-white"
                                >
                                    Quick Start Guide
                                </h4>
                            </div>
                            <div
                                class="grid grid-cols-1 md:grid-cols-3 gap-6 text-base"
                            >
                                <div class="flex flex-col gap-3">
                                    <div class="flex items-center gap-3">
                                        <div
                                            class="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center text-lg font-bold shadow-md"
                                        >
                                            1
                                        </div>
                                        <span
                                            class="text-lg font-semibold text-gray-900 dark:text-white"
                                            >Upload Data</span
                                        >
                                    </div>
                                    <p
                                        class="text-gray-600 dark:text-gray-400 ml-13"
                                    >
                                        Choose your data type and upload GWAS
                                        summary statistics or BED annotation
                                        files
                                    </p>
                                </div>
                                <div class="flex flex-col gap-3">
                                    <div class="flex items-center gap-3">
                                        <div
                                            class="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center text-lg font-bold shadow-md"
                                        >
                                            2
                                        </div>
                                        <span
                                            class="text-lg font-semibold text-gray-900 dark:text-white"
                                            >Run Analysis</span
                                        >
                                    </div>
                                    <p
                                        class="text-gray-600 dark:text-gray-400 ml-13"
                                    >
                                        Select your analysis workflow (SLDSC or
                                        MAGMA) and start the computation
                                    </p>
                                </div>
                                <div class="flex flex-col gap-3">
                                    <div class="flex items-center gap-3">
                                        <div
                                            class="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center text-lg font-bold shadow-md"
                                        >
                                            3
                                        </div>
                                        <span
                                            class="text-lg font-semibold text-gray-900 dark:text-white"
                                            >View Results</span
                                        >
                                    </div>
                                    <p
                                        class="text-gray-600 dark:text-gray-400 ml-13"
                                    >
                                        Explore enrichment results, download
                                        reports, and visualize findings
                                    </p>
                                </div>
                            </div>
                        </div>
                    </template>
                </Card>

                <!-- Already have data link -->
                <div class="text-center mt-8">
                    <p class="text-gray-600 dark:text-gray-400">
                        Already have data uploaded?
                        <button
                            @click="router.push('/datasets')"
                            class="text-primary hover:underline font-semibold ml-1"
                        >
                            Go to Datasets
                        </button>
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
@keyframes pulse {
    0%,
    100% {
        opacity: 0.8;
    }
    50% {
        opacity: 1;
    }
}

.animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
