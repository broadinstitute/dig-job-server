<script setup>
import { METHODS, methodPath } from "~/utils/methods/catalog";

const router = useRouter();

useHead({ title: "Welcome - GWAS-CE" });

// Methods come from the shared catalog so this page tracks the landing page.
// Variant Sifter has no expanded name, so it gets a short description instead.
const METHOD_ITEMS = METHODS.map((m) => ({
    term: m.title,
    text: m.fullName ?? "Variant and annotation prioritization",
    to: methodPath(m.slug),
}));

const METHOD_NAMES = new Intl.ListFormat("en", { type: "disjunction" }).format(
    METHODS.map((m) => m.title),
);

// Upload paths offered to a user with no data yet. `accent` is the tile's top
// edge, as on the landing page method cards.
const UPLOAD_OPTIONS = [
    {
        title: "GWAS Summary Statistics",
        icon: "pi pi-chart-line",
        accent: "var(--gwas-theme-deep)",
        blurb: "Upload genome-wide association study summary statistics to run post-processing methods and services.",
        listTitle: "Available methods",
        items: METHOD_ITEMS,
        action: "Upload GWAS Data",
        to: "/upload",
    },
    {
        title: "BED Annotation Files",
        icon: "pi pi-map",
        accent: "var(--gwas-plum)",
        blurb: "Upload genomic region annotations in BED format for custom enrichment analysis.",
        listTitle: "Use cases",
        items: [
            { text: "Custom genomic region annotations" },
            { text: "Tissue-specific regulatory elements" },
            { text: "Functional genomic annotations" },
        ],
        action: "Upload BED File",
        to: "/bed-upload",
    },
];

const STEPS = [
    {
        title: "Upload Data",
        text: "Choose your data type and upload GWAS summary statistics or BED annotation files.",
    },
    {
        title: "Run Analysis",
        text: `Select a method (${METHOD_NAMES}) and start the computation.`,
    },
    {
        title: "View Results",
        text: "Explore enrichment results, download reports, and visualize findings.",
    },
];
</script>

<template>
    <div class="welcome-page">
        <!-- Hero mirrors the GWAS-CE landing hero (pages/index.vue). -->
        <section class="hero-banner">
            <div class="welcome-container">
                <div class="hero-content">
                    <div class="hero-identity">
                        <span class="hero-kicker">Welcome to</span>
                        <!-- C and E are emphasized to spell out GWAS-CE -->
                        <h1 class="portal-name">
                            GWAS
                            <span class="font-light"
                                ><span class="portal-initial">C</span
                                >ollaborative<br /><span class="portal-initial"
                                    >E</span
                                >nvironment</span
                            >
                        </h1>
                    </div>
                    <div class="hero-tagline">
                        Get started by uploading your data
                        <span class="hero-tagline-sub">
                            Pick the kind of data you have below; you can add
                            more of either type at any time.
                        </span>
                    </div>
                </div>
            </div>
        </section>

        <div class="welcome-container flex flex-col gap-5 pt-5 pb-8">
            <!-- Upload options -->
            <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <section
                    v-for="option in UPLOAD_OPTIONS"
                    :key="option.to"
                    class="upload-tile"
                    :style="{ borderTopColor: option.accent }"
                >
                    <div class="flex items-center gap-3">
                        <i
                            :class="option.icon"
                            class="tile-icon"
                            :style="{ color: option.accent }"
                        ></i>
                        <h2 class="welcome-heading">{{ option.title }}</h2>
                    </div>
                    <p class="welcome-lead">{{ option.blurb }}</p>

                    <div class="flex-auto">
                        <div class="tile-list-title">
                            {{ option.listTitle }}
                        </div>
                        <ul class="tile-list">
                            <li
                                v-for="item in option.items"
                                :key="item.text"
                                class="flex items-start gap-2.5"
                            >
                                <i class="pi pi-check tile-check"></i>
                                <span>
                                    <NuxtLink
                                        v-if="item.to"
                                        :to="item.to"
                                        class="welcome-link"
                                        >{{ item.term }}:</NuxtLink
                                    >
                                    <strong
                                        v-else-if="item.term"
                                        class="font-medium"
                                        >{{ item.term }}:</strong
                                    >
                                    {{ item.text }}
                                </span>
                            </li>
                        </ul>
                    </div>

                    <Button
                        :label="option.action"
                        icon="pi pi-upload"
                        rounded
                        class="w-full"
                        @click="router.push(option.to)"
                    />
                </section>
            </div>

            <!-- Quick start -->
            <section class="welcome-card">
                <div class="welcome-card-header">
                    <h2>Quick Start Guide</h2>
                    <NuxtLink to="/guide" class="welcome-hint-link">
                        Read the full guide
                    </NuxtLink>
                </div>
                <div
                    class="welcome-card-body grid grid-cols-1 gap-6 md:grid-cols-3"
                >
                    <div
                        v-for="(step, i) in STEPS"
                        :key="step.title"
                        class="flex gap-3"
                    >
                        <div class="step-number">{{ i + 1 }}</div>
                        <div>
                            <h3 class="step-title">{{ step.title }}</h3>
                            <p class="welcome-copy">{{ step.text }}</p>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Already have data -->
            <p class="welcome-copy text-center">
                Already have data uploaded?
                <NuxtLink to="/datasets" class="welcome-link">
                    Go to Datasets
                </NuxtLink>
            </p>
        </div>
    </div>
</template>

<style scoped>
/* Layout and type follow the GWAS-CE landing page (pages/index.vue); colors
   come from the GWAS-CE palette in assets/css/global.css. */
.welcome-page {
    font-family: "Roboto", Arial, sans-serif;
}

.welcome-container {
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
    padding: 40px 0 30px 0;
}

.hero-identity {
    flex: 0 0 auto;
    padding-right: 34px;
    margin-right: 34px;
    border-right: 1px solid rgba(255, 255, 255, 0.55);
}

.hero-kicker {
    display: block;
    margin-bottom: 4px;
    font-size: 15px;
    font-weight: 400;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.9;
}

.portal-name {
    margin: 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-weight: 400;
    font-size: 44px;
    line-height: 1.04;
    letter-spacing: 0.015em;
    text-transform: uppercase;
}

.portal-initial {
    font-weight: 400;
}

.hero-tagline {
    width: 470px;
    max-width: 100%;
    font-size: 28px;
    font-weight: 300;
    line-height: 1.25;
}

.hero-tagline-sub {
    display: block;
    font-size: 17px;
    line-height: 1.5;
    opacity: 0.9;
    margin-top: 10px;
}

/* Upload tiles: flat card with an accent top edge, like MethodCard.vue. */
.upload-tile {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 20px 22px 22px 22px;
    background-color: var(--p-content-background);
    border: 1px solid var(--p-content-border-color);
    border-top-width: 3px;
    border-radius: 3px;
    transition: box-shadow 150ms;
}

.upload-tile:hover {
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

.tile-icon {
    font-size: 22px;
}

.welcome-heading,
.welcome-card-header h2 {
    margin: 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-size: 22px;
    font-weight: 400;
    letter-spacing: 0.02em;
    color: var(--p-text-color);
}

.welcome-lead {
    margin: 0;
    font-size: 15px;
    font-weight: 300;
    color: var(--p-text-muted-color);
}

.tile-list-title {
    margin-bottom: 8px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--p-text-muted-color);
}

.tile-list {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 14px;
    font-weight: 300;
    color: var(--p-text-color);
}

.tile-check {
    margin-top: 3px;
    font-size: 12px;
    color: var(--p-primary-color);
}

.welcome-card {
    background-color: var(--p-content-background);
    border: 1px solid var(--p-content-border-color);
    border-radius: 3px;
}

.welcome-card-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 4px 16px;
    padding: 14px 20px;
    border-bottom: 1px solid var(--p-content-border-color);
    background-color: var(--p-surface-50);
}

html.dark .welcome-card-header {
    background-color: var(--p-surface-800);
}

.welcome-card-body {
    padding: 20px;
}

.step-number {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 9999px;
    background-color: var(--p-primary-color);
    color: var(--p-primary-contrast-color);
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-size: 17px;
}

.step-title {
    margin: 4px 0 4px 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-size: 18px;
    font-weight: 400;
    letter-spacing: 0.02em;
    color: var(--p-text-color);
}

.welcome-copy {
    margin: 0;
    font-size: 15px;
    font-weight: 300;
    color: var(--p-text-color);
}

.welcome-link,
.welcome-hint-link {
    color: var(--p-primary-color);
    font-weight: 500;
    text-decoration: none;
}

.welcome-hint-link {
    font-size: 14px;
    font-weight: 400;
}

.welcome-link:hover,
.welcome-hint-link:hover {
    text-decoration: underline;
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
        font-size: 34px;
    }

    .hero-tagline {
        width: auto;
        font-size: 24px;
    }
}
</style>
