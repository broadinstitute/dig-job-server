<template>
    <div
        class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800"
    >
        <nav
            class="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-700"
        >
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-end h-16">
                    <div class="flex items-center gap-4">
                        <Button
                            label="View Datasets"
                            @click="$router.push('/datasets')"
                            icon="pi pi-database"
                            outlined
                        />
                        <Button
                            label="Upload Data"
                            @click="$router.push('/upload')"
                            icon="pi pi-upload"
                        />
                    </div>
                </div>
            </div>
        </nav>

        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div class="text-center">
                <h1
                    class="text-4xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6"
                >
                    Genomic Analysis
                    <span
                        class="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600"
                        >Made Simple</span
                    >
                </h1>
                <p
                    class="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-3xl mx-auto"
                >
                    Run SLDSC and MAGMA analyses on your genomic datasets with
                    ease. Upload your data, run your analysis, and get results
                    in few easy steps.
                </p>
                <div class="flex flex-col sm:flex-row gap-4 justify-center">
                    <Button
                        label="Get Started"
                        @click="handleGetStarted"
                        icon="pi pi-arrow-right"
                        size="large"
                        :loading="isCheckingUser"
                    />
                    <Button
                        label="View Datasets"
                        @click="$router.push('/datasets')"
                        icon="pi pi-database"
                        outlined
                        size="large"
                    />
                </div>
            </div>
        </div>

        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div class="text-center mb-16">
                <h2
                    class="text-3xl font-bold text-gray-900 dark:text-white mb-4"
                >
                    Powerful Analysis Tools
                </h2>
                <p class="text-lg text-gray-600 dark:text-gray-300">
                    Everything you need for genomic analysis in one platform
                </p>
            </div>

            <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                <Card class="text-center h-full">
                    <template #content>
                        <div class="p-6">
                            <div
                                class="w-16 h-16 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-4"
                            >
                                <i
                                    class="pi pi-database text-2xl text-purple-600 dark:text-purple-400"
                                ></i>
                            </div>
                            <h3
                                class="text-xl font-semibold text-gray-900 dark:text-white mb-3"
                            >
                                Data Management
                            </h3>
                            <p class="text-gray-600 dark:text-gray-300 mb-4">
                                Upload, organize, and manage your genomic
                                datasets with ease
                            </p>
                            <div class="flex flex-wrap gap-2 justify-center">
                                <Tag value="Secure" severity="warn" />
                                <Tag value="Organized" severity="info" />
                            </div>
                        </div>
                    </template>
                </Card>

                <Card class="text-center h-full">
                    <template #content>
                        <div class="p-6">
                            <div
                                class="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4"
                            >
                                <i
                                    class="pi pi-sitemap text-2xl text-green-600 dark:text-green-400"
                                ></i>
                            </div>
                            <h3
                                class="text-xl font-semibold text-gray-900 dark:text-white mb-3"
                            >
                                MAGMA Analysis
                            </h3>
                            <p class="text-gray-600 dark:text-gray-300 mb-4">
                                Multi-marker Analysis of GenoMic Annotation for
                                gene-set analysis
                            </p>
                            <div class="flex flex-wrap gap-2 justify-center">
                                <Tag value="Gene-based" severity="success" />
                                <Tag value="Pathway" severity="info" />
                            </div>
                        </div>
                    </template>
                </Card>

                <Card class="text-center h-full">
                    <template #content>
                        <div class="p-6">
                            <div
                                class="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4"
                            >
                                <i
                                    class="pi pi-chart-line text-2xl text-blue-600 dark:text-blue-400"
                                ></i>
                            </div>
                            <h3
                                class="text-xl font-semibold text-gray-900 dark:text-white mb-3"
                            >
                                SLDSC Analysis
                            </h3>
                            <p class="text-gray-600 dark:text-gray-300 mb-4">
                                Stratified Linkage Disequilibrium Score
                                Regression for heritability analysis
                            </p>
                            <div class="flex flex-wrap gap-2 justify-center">
                                <Tag value="Heritability" severity="primary" />
                                <Tag value="SNP-based" severity="info" />
                            </div>
                        </div>
                    </template>
                </Card>
            </div>
        </div>
    </div>
</template>

<script setup>
const router = useRouter();
const userStore = useUserStore();
const isCheckingUser = ref(false);

useHead({
    title: "GWAS-CE - Genomic Analysis Platform",
    meta: [
        {
            name: "description",
            content:
                "Run SLDSC and MAGMA analyses on your genomic datasets with ease.",
        },
    ],
});

const handleGetStarted = async () => {
    isCheckingUser.value = true;

    try {
        // Check if user is logged in
        const isLoggedIn = await userStore.isUserLoggedIn();

        if (!isLoggedIn) {
            // Not logged in - redirect to login page
            router.push("/signup");
            return;
        }

        // User is logged in - check if they have data
        const datasets = await userStore.retrieveDatasets();
        const bedFiles = await userStore.getBedFiles();

        if (datasets.length === 0 && bedFiles.length === 0) {
            // No data uploaded - redirect to welcome page
            router.push("/welcome");
        } else {
            // Has data - redirect to datasets page
            router.push("/datasets");
        }
    } catch (error) {
        console.error("Error checking user status:", error);
        // On error, default to login page
        router.push("/login");
    } finally {
        isCheckingUser.value = false;
    }
};
</script>
