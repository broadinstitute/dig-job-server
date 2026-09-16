<template>
    <div
        class="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800"
    >
        <div class="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
            <div class="flex flex-col gap-10">
                <div class="text-center">
                    <p
                        class="mb-3 text-sm font-semibold tracking-widest text-primary uppercase"
                    >
                        GWAS Collaborative Environment
                    </p>
                    <h1
                        class="text-4xl font-bold text-gray-900 md:text-6xl dark:text-white"
                    >
                        Genomic Analysis
                        <span
                            class="bg-linear-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent"
                            >Made Simple</span
                        >
                    </h1>
                </div>

                <!-- GWAS-Hub -->
                <FeatureCard
                    title="GWAS-Hub"
                    description="With GWAS-Hub, you can upload your own data to run quality control methods and conduct meta-analyses for your traits of interest"
                    to="/gwas-hub"
                    icon="pi pi-users"
                />

                <!-- Post-processing methods -->
                <section class="flex flex-col gap-6">
                    <FeatureCard
                        title="GWAS Post-Processing Methods"
                        description="Upload GWAS summary statistics and run the methods below"
                        to="/upload"
                        icon="pi pi-cog"
                    />
                    <div
                        class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5"
                    >
                        <MethodCard
                            v-for="method in METHODS"
                            :key="method.slug"
                            :method="method"
                        />
                    </div>
                </section>

                <!-- Genomic annotation -->
                <FeatureCard
                    title="Genomic Annotation"
                    description="Annotate genomic regions for custom enrichment analysis"
                    to="/bed-upload"
                    icon="pi pi-map"
                    iconWrapClass="bg-purple-100 dark:bg-purple-900/20"
                    iconClass="text-purple-600 dark:text-purple-400"
                />

                <!-- CTA -->
                <div class="mt-4 text-center">
                    <div class="flex flex-col justify-center gap-4 sm:flex-row">
                        <Button
                            v-if="!isLoggedIn"
                            label="Create Account"
                            @click="$router.push('/signup')"
                            icon="pi pi-user-plus"
                            size="large"
                        />
                        <Button
                            v-else
                            label="Get Started"
                            @click="handleGetStarted"
                            icon="pi pi-arrow-right"
                            size="large"
                            :disabled="isCheckingUser"
                        />
                    </div>
                </div>

                <!-- About + funders -->
                <div
                    class="mt-6 border-t border-gray-200 pt-12 dark:border-gray-700"
                >
                    <WorkspaceAbout
                        heading="About the workspace"
                        text="GWAS-CE is your unified workspace for GWAS analysis. Run QC and meta-analyses, leverage cutting-edge post processing methods, and annotate your data for downstream dissemination."
                        logosHeading="GWAS-CE is proudly supported by"
                        :logos="FUNDER_LOGOS"
                    />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { METHODS } from "~/utils/methods/catalog";
import { FUNDER_LOGOS } from "~/utils/partners/logos";

definePageMeta({ requiresAuth: false });

const router = useRouter();
const userStore = useUserStore();
const isCheckingUser = ref(false);
const isLoggedIn = ref(false);

useHead({
    title: "GWAS-CE - Genomic Analysis Platform",
    meta: [
        {
            name: "description",
            content:
                "GWAS-CE is your unified workspace for GWAS analysis: quality control, meta-analysis, post-processing methods, and genomic annotation.",
        },
    ],
});

onMounted(async () => {
    // Check login status on mount
    isLoggedIn.value = await userStore.isUserLoggedIn();
});

const handleGetStarted = async () => {
    isCheckingUser.value = true;

    try {
        // Check if user is logged in
        const loggedIn = await userStore.isUserLoggedIn();

        if (!loggedIn) {
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
