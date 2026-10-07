<template>
    <div class="landing-page">
        <!-- Hero banner. In dark mode the header keeps its 1rem bottom margin;
             pull the banner up so it still meets the header. -->
        <section class="hero-banner dark:-mt-4">
            <div class="landing-container">
                <div class="hero-content">
                    <div class="hero-identity">
                        <div class="portal-name">
                            GWAS <span class="font-light">Collaborative</span
                            ><br />Environment
                        </div>
                    </div>
                    <div class="hero-tagline">
                        Genomic analysis made simple
                        <span class="hero-tagline-sub">
                            A unified workspace for GWAS quality control,
                            meta-analysis, post-processing and annotation.
                        </span>
                    </div>
                </div>
            </div>
        </section>

        <div class="landing-container flex flex-col gap-5 pt-5 pb-8">
            <!-- Post-processing methods -->
            <section class="landing-card">
                <div class="landing-card-header">
                    <h2>GWAS Post-Processing Methods and Services</h2>
                    <span class="landing-hint">
                        Upload GWAS summary statistics to run downstream
                        methods and services
                    </span>
                </div>
                <div class="landing-card-body">
                    <p class="section-lead">
                        Each method and service takes standard GWAS summary
                        statistics as input and returns results you can utilize
                        in your downstream research workflows.
                    </p>
                    <div
                        class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5"
                    >
                        <MethodCard
                            v-for="method in METHODS"
                            :key="method.slug"
                            :method="method"
                        />
                    </div>
                </div>
            </section>

            <!-- Genomic annotation -->
            <section class="landing-card">
                <div class="landing-card-header">
                    <h2>Genomic Annotation</h2>
                    <span class="landing-hint">
                        Annotate genomic regions for custom enrichment analysis
                    </span>
                </div>
                <div class="landing-card-body">
                    <p class="section-lead mb-0!">
                        Build and upload custom region sets, annotate them
                        against reference tracks, and feed the result into
                        enrichment analyses alongside your post-processing
                        output.
                    </p>
                </div>
            </section>

            <!-- CTA -->
            <div class="pt-4 pb-1 text-center">
                <Button
                    v-if="!isLoggedIn"
                    label="Create Account"
                    @click="$router.push('/signup')"
                    size="large"
                    rounded
                    class="cta-button"
                />
                <Button
                    v-else
                    label="Get Started"
                    @click="handleGetStarted"
                    size="large"
                    rounded
                    class="cta-button"
                    :disabled="isCheckingUser"
                />
            </div>

            <!-- GWAS-Hub -->
            <section class="landing-card">
                <div
                    class="landing-card-body flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:justify-between sm:gap-8"
                >
                    <div>
                        <h2 class="landing-heading mb-1.5 text-2xl">
                            GWAS-Hub
                        </h2>
                        <p class="landing-copy max-w-3xl">
                            Upload your own data to run quality control methods
                            and conduct meta-analyses for your traits of
                            interest, then hand the results straight to the
                            post-processing methods above.
                        </p>
                    </div>
                    <Button
                        label="Open GWAS-Hub"
                        outlined
                        rounded
                        class="shrink-0 whitespace-nowrap"
                        @click="$router.push('/gwas-hub')"
                    />
                </div>
            </section>

            <!-- About -->
            <section class="landing-card">
                <div class="landing-card-header justify-center!">
                    <h2>About the workspace</h2>
                </div>
                <div class="landing-card-body py-6!">
                    <p
                        class="landing-copy mx-auto max-w-4xl text-center leading-relaxed"
                    >
                        GWAS-CE is your unified workspace for GWAS analysis. Run
                        custom quality control and meta-analysis pipelines,
                        leverage cutting-edge post-processing methods, and
                        annotate your data for downstream prioritization and
                        assessment.
                    </p>
                </div>
            </section>
        </div>
    </div>
</template>

<script setup>
import { METHODS } from "~/utils/methods/catalog";

definePageMeta({ requiresAuth: false });

const router = useRouter();
const userStore = useUserStore();
const isCheckingUser = ref(false);
const isLoggedIn = ref(false);

useHead({
    title: "GWAS-CE - Genomic Analysis Platform",
    // Fonts from the GWAS-CE landing mock-up (HuGeAMP Knowledge Portal type).
    link: [
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        {
            rel: "preconnect",
            href: "https://fonts.gstatic.com",
            crossorigin: "",
        },
        {
            rel: "stylesheet",
            href: "https://fonts.googleapis.com/css2?family=Oswald:wght@300;400;700&family=Roboto:wght@300;400;700&display=swap",
        },
    ],
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

<style scoped>
/* Layout and type follow the GWAS-CE landing mock-up; colors come from the
   GWAS-CE palette in assets/css/global.css. */
.landing-page {
    font-family: "Roboto", Arial, sans-serif;
}

.landing-container {
    width: 1160px;
    max-width: calc(100% - 40px);
    margin-left: auto;
    margin-right: auto;
}

.hero-banner {
    background-image: linear-gradient(
        var(--gwas-theme),
        var(--gwas-theme-deep)
    );
    padding-bottom: 20px;
    color: #fff;
}

.hero-content {
    display: flex;
    align-items: center;
    padding: 44px 0 34px 0;
}

.hero-identity {
    flex: 0 0 auto;
    padding-right: 34px;
    margin-right: 34px;
    border-right: 1px solid rgba(255, 255, 255, 0.55);
}

.portal-name {
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-weight: 400;
    font-size: 52px;
    line-height: 1.04;
    letter-spacing: 0.015em;
    text-transform: uppercase;
    max-width: 520px;
}

.hero-tagline {
    width: 470px;
    max-width: 100%;
    font-size: 32px;
    font-weight: 300;
    line-height: 1.25;
}

.hero-tagline-sub {
    display: block;
    font-size: 18px;
    line-height: 1.5;
    opacity: 0.9;
    margin-top: 12px;
}

.landing-card {
    background-color: var(--p-content-background);
    border: 1px solid var(--p-content-border-color);
    border-radius: 3px;
}

.landing-card-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 4px 16px;
    padding: 14px 20px;
    border-bottom: 1px solid var(--p-content-border-color);
    background-color: var(--p-surface-50);
}

html.dark .landing-card-header {
    background-color: var(--p-surface-800);
}

.landing-card-header h2,
.landing-heading {
    margin: 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-size: 22px;
    font-weight: 400;
    letter-spacing: 0.02em;
    color: var(--p-text-color);
}

.landing-hint {
    font-size: 14px;
    font-weight: 300;
    color: var(--p-text-muted-color);
}

.landing-card-body {
    padding: 20px;
}

.section-lead {
    font-size: 15px;
    font-weight: 300;
    color: var(--p-text-muted-color);
    margin: 0 0 18px 0;
    max-width: 820px;
}

.landing-copy {
    margin: 0;
    font-size: 15px;
    font-weight: 300;
    color: var(--p-text-color);
}

.cta-button {
    font-family: "Roboto", Arial, sans-serif;
    font-size: 19px;
    letter-spacing: 0.01em;
    padding-left: 52px;
    padding-right: 52px;
}

@media (max-width: 820px) {
    .hero-content {
        display: block;
        padding-top: 30px;
    }

    .hero-identity {
        border-right: none;
        margin: 0 0 20px 0;
        padding: 0;
    }

    .portal-name {
        font-size: 38px;
    }

    .hero-tagline {
        width: auto;
    }
}
</style>
