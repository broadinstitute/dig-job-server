<template>
    <div class="hub-landing">
        <!-- Hero: the initiative -->
        <section class="hero-banner">
            <div class="hub-container">
                <div class="hero-content">
                    <div class="hero-identity">
                        <h1 class="portal-name">
                            GWAS<span class="font-light">&#8209;Hub</span>
                        </h1>
                    </div>
                    <div class="hero-text">
                        <p>
                            A <strong class="font-medium">GWAS-Hub</strong>
                            serves as a unified workspace for a consortium or
                            organization to conduct customizable GWAS quality
                            control processes and meta-analyses on their own
                            data.
                        </p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Consortium partners -->
        <section class="hub-container py-12">
            <div
                class="mb-10 rounded-lg border border-gray-200 bg-white px-6 py-5 text-center text-lg leading-relaxed text-gray-600 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
            >
                The Knowledge Portal Network (KPN) has worked with the Skin
                Genetics Consortium (SGC) and the Heart Failure Molecular
                Epidemiology for Therapeutic Targets (HERMES) consortium to
                develop custom GWAS-Hub workspaces for their initiatives.
            </div>

            <h2
                class="mb-6 text-center text-2xl font-semibold text-gray-900 dark:text-white"
            >
                Consortium partners
            </h2>
            <div class="grid gap-6 sm:grid-cols-2">
                <div
                    v-for="partner in PARTNER_LOGOS"
                    :key="partner.name"
                    class="flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800"
                >
                    <!-- White panel: both logos are drawn for a light background -->
                    <div
                        class="flex h-36 items-center justify-center border-b border-gray-100 bg-white px-6 py-4 dark:border-gray-700"
                    >
                        <img
                            v-if="partner.src"
                            :src="partner.src"
                            :alt="partner.name"
                            class="h-full w-auto max-w-full object-contain"
                        />
                    </div>
                    <div class="px-5 py-4">
                        <h3
                            class="text-lg font-semibold text-gray-900 dark:text-white"
                        >
                            {{ partner.fullName || partner.name }}
                        </h3>
                        <p
                            v-if="partner.fullName"
                            class="text-sm text-gray-500 dark:text-gray-400"
                        >
                            {{ partner.name }}
                        </p>
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>

<script setup>
// GWAS-Hub landing: a hero describing the initiative, then the consortia that
// have a workspace. Partner cards are informational only (no outbound links);
// the list is shared with demo.vue via utils/partners/logos.js.
import { PARTNER_LOGOS } from "~/utils/partners/logos";

definePageMeta({ layout: "gwas-hub" });

useHead({ title: "GWAS-Hub - GWAS-CE" });
</script>

<style scoped>
/* Hero mirrors the GWAS-CE landing hero (pages/index.vue). */
.hub-landing {
    font-family: "Roboto", Arial, sans-serif;
}

.hub-container {
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
}

.hero-text {
    max-width: 680px;
    font-size: 18px;
    font-weight: 300;
    line-height: 1.6;
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
}
</style>
