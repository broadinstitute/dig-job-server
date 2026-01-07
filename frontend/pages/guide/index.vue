<template>
    <div class="w-full max-w-5xl mx-auto py-10 px-6">
        <div
            class="mb-10 border-b border-surface-200 dark:border-surface-700 pb-6"
        >
            <h1
                class="text-4xl font-bold text-surface-900 dark:text-surface-0 mb-3"
            >
                Getting Started
            </h1>
            <p class="text-xl text-surface-600 dark:text-surface-400">
                A quick guide to using the GWAS Analysis Platform.
            </p>
        </div>

        <div class="space-y-12">
            <!-- Account Setup -->
            <section>
                <h2
                    class="text-2xl font-semibold text-primary-600 dark:text-primary-400 mb-4 flex items-center gap-2"
                >
                    <span
                        class="bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 w-8 h-8 rounded-full flex items-center justify-center text-sm"
                        >1</span
                    >
                    Account Setup
                </h2>
                <div
                    class="bg-surface-0 dark:bg-surface-800 p-6 rounded-lg shadow-sm border border-surface-200 dark:border-surface-700"
                >
                    <ul
                        class="space-y-3 text-surface-700 dark:text-surface-200"
                    >
                        <li class="flex items-start gap-2">
                            <i class="pi pi-check mt-1 text-green-500"></i>
                            <div>
                                <span class="font-medium">Sign Up:</span>
                                Navigate to the Sign Up page. You can create a
                                local account or use
                                <strong>GitHub Login</strong> for quick access.
                            </div>
                        </li>
                        <li class="flex items-start gap-2">
                            <i class="pi pi-check mt-1 text-green-500"></i>
                            <div>
                                <span class="font-medium">Login:</span> Use your
                                credentials to access your private workspace.
                            </div>
                        </li>
                    </ul>
                </div>
            </section>

            <!-- Uploading Data -->
            <section>
                <h2
                    class="text-2xl font-semibold text-primary-600 dark:text-primary-400 mb-4 flex items-center gap-2"
                >
                    <span
                        class="bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 w-8 h-8 rounded-full flex items-center justify-center text-sm"
                        >2</span
                    >
                    Uploading Data
                </h2>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- GWAS Data -->
                    <div
                        class="bg-surface-0 dark:bg-surface-800 p-6 rounded-lg shadow-sm border border-surface-200 dark:border-surface-700"
                    >
                        <h3
                            class="text-xl font-medium mb-3 text-surface-900 dark:text-surface-0 flex items-center gap-2"
                        >
                            <i class="pi pi-file text-blue-500"></i> GWAS
                            Summary Statistics
                        </h3>
                        <p
                            class="text-sm text-surface-500 dark:text-surface-400 mb-4"
                        >
                            Use this for running enrichment analyses (SLDSC,
                            MAGMA, PIGEAN).
                        </p>
                        <ol
                            class="list-decimal pl-5 space-y-2 text-surface-700 dark:text-surface-200"
                        >
                            <li>
                                Click <strong>"Upload GWAS"</strong> on the
                                Welcome or Datasets page.
                            </li>
                            <li>
                                <strong>Select Ancestry</strong> (e.g.,
                                European, East Asian) and
                                <strong>Genome Build</strong> (GRCh37/38).
                            </li>
                            <li>
                                <strong>Upload File</strong>: Accepts
                                <code>.txt</code>, <code>.csv</code>,
                                <code>.tsv</code> (optionally
                                <code>.gz</code> compressed).
                            </li>
                            <li>
                                <strong>Map Columns</strong>: Ensure your file
                                has essential columns (Chromosome, Position,
                                Alleles, P-Value, Beta/OR).
                            </li>
                        </ol>
                    </div>

                    <!-- BED Files -->
                    <div
                        class="bg-surface-0 dark:bg-surface-800 p-6 rounded-lg shadow-sm border border-surface-200 dark:border-surface-700"
                    >
                        <h3
                            class="text-xl font-medium mb-3 text-surface-900 dark:text-surface-0 flex items-center gap-2"
                        >
                            <i class="pi pi-list text-purple-500"></i> BED
                            Annotation Files
                        </h3>
                        <p
                            class="text-sm text-surface-500 dark:text-surface-400 mb-4"
                        >
                            Use this for custom genomic region analysis.
                        </p>
                        <ol
                            class="list-decimal pl-5 space-y-2 text-surface-700 dark:text-surface-200"
                        >
                            <li>
                                Click <strong>"Upload Annotation"</strong> (or
                                "Upload BED File").
                            </li>
                            <li>
                                Provide a name and select your
                                <code>.bed</code> file.
                            </li>
                            <li>
                                The system automatically validates the file
                                format upon upload.
                            </li>
                        </ol>
                    </div>
                </div>
            </section>

            <!-- Running Analyses -->
            <section>
                <h2
                    class="text-2xl font-semibold text-primary-600 dark:text-primary-400 mb-4 flex items-center gap-2"
                >
                    <span
                        class="bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 w-8 h-8 rounded-full flex items-center justify-center text-sm"
                        >3</span
                    >
                    Running Analyses
                </h2>
                <div
                    class="bg-surface-0 dark:bg-surface-800 p-6 rounded-lg shadow-sm border border-surface-200 dark:border-surface-700"
                >
                    <p class="mb-4 text-surface-700 dark:text-surface-200">
                        Navigate to the <strong>Datasets</strong> page to manage
                        your files. Click the play icon
                        <i
                            class="pi pi-play text-xs bg-green-100 text-green-700 p-1 rounded-full"
                        ></i>
                        on a dataset tile to start.
                    </p>

                    <div class="space-y-4">
                        <div
                            class="flex flex-col sm:flex-row gap-4 border-l-4 border-blue-500 pl-4 bg-surface-50 dark:bg-surface-900/50 py-2 rounded-r"
                        >
                            <div
                                class="font-bold text-surface-900 dark:text-surface-0 w-32 shrink-0"
                            >
                                SLDSC
                            </div>
                            <div class="text-surface-700 dark:text-surface-300">
                                Stratified LD Score Regression. Calculates
                                tissue enrichment for your GWAS traits.
                            </div>
                        </div>
                        <div
                            class="flex flex-col sm:flex-row gap-4 border-l-4 border-orange-500 pl-4 bg-surface-50 dark:bg-surface-900/50 py-2 rounded-r"
                        >
                            <div
                                class="font-bold text-surface-900 dark:text-surface-0 w-32 shrink-0"
                            >
                                MAGMA
                            </div>
                            <div class="text-surface-700 dark:text-surface-300">
                                Performs gene level analysis and gene-set
                                enrichment based on your summary statistics.
                            </div>
                        </div>
                        <div
                            class="flex flex-col sm:flex-row gap-4 border-l-4 border-indigo-500 pl-4 bg-surface-50 dark:bg-surface-900/50 py-2 rounded-r"
                        >
                            <div
                                class="font-bold text-surface-900 dark:text-surface-0 w-32 shrink-0"
                            >
                                PIGEAN
                            </div>
                            <div class="text-surface-700 dark:text-surface-300">
                                Gene prioritization using Bayesian inference.
                                Helps identify likely causal genes and sets.
                            </div>
                        </div>
                        <div
                            class="flex flex-col sm:flex-row gap-4 border-l-4 border-gray-500 pl-4 bg-surface-50 dark:bg-surface-900/50 py-2 rounded-r"
                        >
                            <div
                                class="font-bold text-surface-900 dark:text-surface-0 w-32 shrink-0"
                            >
                                Annot-SLDSC
                            </div>
                            <div
                                class="text-surface-700 dark:text-surface-300 font-italic"
                            >
                                For BED files only.
                            </div>
                            <div class="text-surface-700 dark:text-surface-300">
                                Calculates enrichment for your specific genomic
                                regions against baseline genomics data.
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Results -->
            <section class="pb-10">
                <h2
                    class="text-2xl font-semibold text-primary-600 dark:text-primary-400 mb-4 flex items-center gap-2"
                >
                    <span
                        class="bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 w-8 h-8 rounded-full flex items-center justify-center text-sm"
                        >4</span
                    >
                    Viewing Results
                </h2>
                <div
                    class="bg-surface-0 dark:bg-surface-800 p-6 rounded-lg shadow-sm border border-surface-200 dark:border-surface-700"
                >
                    <ul
                        class="space-y-4 text-surface-700 dark:text-surface-200"
                    >
                        <li class="flex gap-3">
                            <i
                                class="pi pi-spinner text-primary-500 text-xl"
                            ></i>
                            <div>
                                <strong
                                    class="block text-surface-900 dark:text-surface-0"
                                    >Status Tracking</strong
                                >
                                Watch for
                                <span
                                    class="text-blue-600 font-mono text-sm bg-blue-50 px-1 rounded"
                                    >RUNNING</span
                                >,
                                <span
                                    class="text-green-600 font-mono text-sm bg-green-50 px-1 rounded"
                                    >SUCCEEDED</span
                                >, or
                                <span
                                    class="text-red-600 font-mono text-sm bg-red-50 px-1 rounded"
                                    >FAILED</span
                                >
                                tags on your dataset cards.
                            </div>
                        </li>
                        <li class="flex gap-3">
                            <i
                                class="pi pi-chart-bar text-primary-500 text-xl"
                            ></i>
                            <div>
                                <strong
                                    class="block text-surface-900 dark:text-surface-0"
                                    >Interactive Dashboards</strong
                                >
                                Click a dataset to open the Results Dashboard.
                                Explore <strong>Volcano Plots</strong>,
                                <strong>Scatter Plots</strong>, and filterable
                                <strong>Data Tables</strong>.
                            </div>
                        </li>
                        <li class="flex gap-3">
                            <i
                                class="pi pi-download text-primary-500 text-xl"
                            ></i>
                            <div>
                                <strong
                                    class="block text-surface-900 dark:text-surface-0"
                                    >Downloads</strong
                                >
                                Export your analysis results as
                                <code>.tsv</code> files or download high-quality
                                plot images for publication.
                            </div>
                        </li>
                    </ul>
                </div>
            </section>
        </div>
    </div>
</template>

<script setup>
useHead({
    title: "Getting Started - GWAS Platform",
});
</script>
