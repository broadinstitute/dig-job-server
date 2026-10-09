<template>
    <div class="guide-page">
        <div class="guide-container">
            <div class="page-intro">
                <h1>Getting Started</h1>
                <p>A quick guide to using the GWAS Collaborative Environment.</p>
            </div>

            <!-- 1. Account Setup -->
            <section class="guide-section">
                <div class="section-head">
                    <span class="num">1</span>
                    <h2>Account Setup</h2>
                </div>
                <div class="guide-card">
                    <ul class="check-list">
                        <li>
                            <i class="pi pi-check tick"></i>
                            <span>
                                <strong>Sign Up:</strong> Navigate to the Sign Up
                                page. You can create a local account or use
                                <strong>GitHub Login</strong> for quick access.
                            </span>
                        </li>
                        <li>
                            <i class="pi pi-check tick"></i>
                            <span>
                                <strong>Login:</strong> Use your credentials to
                                access your private workspace.
                            </span>
                        </li>
                    </ul>
                </div>
            </section>

            <!-- 2. Uploading Data -->
            <section class="guide-section">
                <div class="section-head">
                    <span class="num">2</span>
                    <h2>Uploading Data</h2>
                </div>
                <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
                    <div class="guide-card">
                        <h3 class="card-title">
                            <svg
                                width="15"
                                height="18"
                                viewBox="0 0 15 18"
                                fill="none"
                                aria-hidden="true"
                            >
                                <path
                                    d="M1.5 1h8l4 4v12a.5.5 0 0 1-.5.5H1.5a.5.5 0 0 1-.5-.5V1.5A.5.5 0 0 1 1.5 1z"
                                    stroke="currentColor"
                                    stroke-width="1.2"
                                />
                                <path
                                    d="M9.5 1v4h4"
                                    stroke="currentColor"
                                    stroke-width="1.2"
                                />
                            </svg>
                            GWAS Summary Statistics
                        </h3>
                        <p class="card-sub">
                            Use this for running enrichment analyses (S-LDSC,
                            MAGMA, PIGEAN).
                        </p>
                        <ol class="step-list">
                            <li>
                                Click <strong>&ldquo;Upload GWAS&rdquo;</strong>
                                on the Welcome or Datasets page.
                            </li>
                            <li>
                                <strong>Select Ancestry</strong> (e.g., European,
                                East Asian) and
                                <strong>Genome Build</strong> (GRCh37/38).
                            </li>
                            <li>
                                <strong>Upload File:</strong> accepts
                                <code>.txt</code>, <code>.csv</code>,
                                <code>.tsv</code> (optionally
                                <code>.gz</code> compressed).
                            </li>
                            <li>
                                <strong>Map Columns:</strong> ensure your file
                                has the essential columns (Chromosome, Position,
                                Alleles, P-Value, Beta/OR).
                            </li>
                        </ol>
                    </div>

                    <div class="guide-card">
                        <h3 class="card-title">
                            <svg
                                width="16"
                                height="16"
                                viewBox="0 0 16 16"
                                fill="none"
                                aria-hidden="true"
                            >
                                <path
                                    d="M1 3h14M1 8h14M1 13h14"
                                    stroke="currentColor"
                                    stroke-width="1.4"
                                    stroke-linecap="round"
                                />
                            </svg>
                            BED Annotation Files
                        </h3>
                        <p class="card-sub">
                            Use this for custom genomic region analysis.
                        </p>
                        <ol class="step-list">
                            <li>
                                Click
                                <strong>&ldquo;Upload Annotation&rdquo;</strong>
                                (or &ldquo;Upload BED File&rdquo;).
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

            <!-- 3. Running Analyses -->
            <section class="guide-section">
                <div class="section-head">
                    <span class="num">3</span>
                    <h2>Running Analyses</h2>
                </div>
                <div class="guide-card">
                    <p class="lede">
                        Navigate to the <strong>Datasets</strong> page to manage
                        your files. Click the play icon
                        <i class="pi pi-play play" aria-label="play"></i> on a
                        dataset tile to start.
                    </p>

                    <div
                        v-for="row in ANALYSES"
                        :key="row.name"
                        class="analysis-row"
                        :style="{ borderLeftColor: row.accent }"
                    >
                        <div class="name">{{ row.name }}</div>
                        <div class="desc">
                            <span v-if="row.qualifier" class="qualifier">{{
                                row.qualifier
                            }}</span
                            >{{ row.desc }}
                        </div>
                    </div>
                </div>
            </section>

            <!-- 4. Viewing Results -->
            <section class="guide-section">
                <div class="section-head">
                    <span class="num">4</span>
                    <h2>Viewing Results</h2>
                </div>
                <div class="guide-card">
                    <div class="result-item">
                        <span class="ico">
                            <svg
                                width="17"
                                height="17"
                                viewBox="0 0 17 17"
                                fill="none"
                                aria-hidden="true"
                            >
                                <circle
                                    cx="8.5"
                                    cy="8.5"
                                    r="7"
                                    stroke="currentColor"
                                    stroke-width="1.4"
                                    stroke-dasharray="4 3"
                                />
                            </svg>
                        </span>
                        <div>
                            <h3>Status Tracking</h3>
                            <p>
                                Watch for
                                <span class="status-tag running">RUNNING</span>,
                                <span class="status-tag succeeded"
                                    >SUCCEEDED</span
                                >, or
                                <span class="status-tag failed">FAILED</span>
                                tags on your dataset cards.
                            </p>
                        </div>
                    </div>

                    <div class="result-item">
                        <span class="ico">
                            <svg
                                width="17"
                                height="17"
                                viewBox="0 0 17 17"
                                fill="none"
                                aria-hidden="true"
                            >
                                <rect
                                    x="1"
                                    y="9"
                                    width="3.4"
                                    height="7"
                                    fill="currentColor"
                                />
                                <rect
                                    x="6.8"
                                    y="5"
                                    width="3.4"
                                    height="11"
                                    fill="var(--gwas-theme)"
                                />
                                <rect
                                    x="12.6"
                                    y="1.5"
                                    width="3.4"
                                    height="14.5"
                                    fill="currentColor"
                                />
                            </svg>
                        </span>
                        <div>
                            <h3>Interactive Dashboards</h3>
                            <p>
                                Click a dataset to open the Results Dashboard.
                                Explore <strong>Volcano Plots</strong>,
                                <strong>Scatter Plots</strong>, and filterable
                                <strong>Data Tables</strong>.
                            </p>
                        </div>
                    </div>

                    <div class="result-item">
                        <span class="ico">
                            <svg
                                width="17"
                                height="17"
                                viewBox="0 0 17 17"
                                fill="none"
                                aria-hidden="true"
                            >
                                <path
                                    d="M8.5 1v10M4.5 7.5l4 4 4-4M1.5 15.5h14"
                                    stroke="currentColor"
                                    stroke-width="1.4"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                />
                            </svg>
                        </span>
                        <div>
                            <h3>Downloads</h3>
                            <p>
                                Export your analysis results as
                                <code>.tsv</code> files or download
                                high-quality plot images for publication.
                            </p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>
</template>

<script setup>
// Getting-started guide. Layout and type follow the GWAS-CE guide mock-up;
// colors come from the GWAS-CE palette (assets/css/global.css). Analysis rows
// take their name and accent color from the method catalog so they match the
// landing-page cards.
import { getMethod } from "~/utils/methods/catalog";

useHead({
    title: "Getting Started - GWAS-CE",
});

const fromCatalog = (slug, desc, qualifier = null) => {
    const method = getMethod(slug);
    return {
        name: method.title,
        accent: method.accent,
        desc,
        qualifier: qualifier ?? (method.external ? "External service" : null),
    };
};

const ANALYSES = [
    fromCatalog(
        "sldsc",
        "Stratified LD Score Regression. Calculates tissue enrichment for your GWAS traits.",
    ),
    fromCatalog(
        "magma",
        "Performs gene-level analysis and gene-set enrichment based on your summary statistics.",
    ),
    fromCatalog(
        "pigean",
        "Gene prioritization using Bayesian inference. Helps identify likely causal genes and sets.",
    ),
    fromCatalog(
        "falcon",
        "Integrates multiple data sources, including GWAS summary statistics, variant annotations, and variant-to-gene maps to calculate genetic support scores.",
    ),
    {
        // Annotation-only analysis; not a landing-page method card.
        name: "Annot-SLDSC",
        accent: "#de565c",
        qualifier: "BED files only",
        desc: "Calculates enrichment for your specific genomic regions against baseline genomics data.",
    },
    fromCatalog(
        "variant-sifter",
        "Explore, annotate, and prioritize genetic variants for downstream assessment across a trait of interest.",
    ),
];
</script>

<style scoped>
.guide-page {
    font-family: "Roboto", Arial, sans-serif;
    padding: 24px 0 40px 0;
}

.guide-container {
    width: 900px;
    max-width: calc(100% - 40px);
    margin-left: auto;
    margin-right: auto;
}

/* Page intro */
.page-intro {
    border-bottom: 1px solid var(--p-content-border-color);
    padding-bottom: 18px;
    margin-bottom: 26px;
}

.page-intro h1 {
    margin: 0 0 4px 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-weight: 400;
    font-size: 40px;
    letter-spacing: 0.02em;
    color: var(--p-text-color);
}

.page-intro p {
    margin: 0;
    font-size: 16px;
    font-weight: 300;
    color: var(--p-text-muted-color);
}

/* Numbered sections */
.guide-section {
    margin-bottom: 30px;
}

.guide-section:last-child {
    margin-bottom: 0;
}

.section-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.section-head .num {
    width: 28px;
    height: 28px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: var(--gwas-theme-deep);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 15px;
    font-weight: 700;
}

.section-head h2 {
    margin: 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-weight: 400;
    font-size: 26px;
    letter-spacing: 0.02em;
    color: var(--gwas-plum);
}

html.dark .section-head h2 {
    color: #d9a7c4;
}

/* Cards */
.guide-card {
    background-color: var(--p-content-background);
    border: 1px solid var(--p-content-border-color);
    border-radius: 3px;
    padding: 20px;
    display: flex;
    flex-direction: column;
}

.card-title {
    display: flex;
    align-items: center;
    gap: 9px;
    margin: 0 0 4px 0;
    font-family: "Oswald", "Roboto", Arial, sans-serif;
    font-weight: 400;
    font-size: 19px;
    letter-spacing: 0.02em;
    color: var(--p-text-color);
}

.card-title svg,
.result-item .ico {
    flex: 0 0 auto;
    color: var(--gwas-theme-deep);
}

.card-sub {
    font-size: 13px;
    font-weight: 300;
    color: var(--p-text-muted-color);
    margin: 0 0 14px 0;
}

/* Shared body copy */
.check-list,
.step-list,
.lede,
.analysis-row .desc,
.result-item p {
    font-weight: 300;
    color: var(--p-text-color);
}

.guide-page strong {
    font-weight: 500;
}

.guide-page code {
    font-family:
        SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
        "Courier New", monospace;
    font-size: 0.88em;
    background: var(--p-surface-100);
    border: 1px solid var(--p-content-border-color);
    border-radius: 2px;
    padding: 1px 5px;
    color: var(--gwas-plum);
}

html.dark .guide-page code {
    background: var(--p-surface-800);
    color: #d9a7c4;
}

/* Check list (Account Setup) */
.check-list {
    list-style: none;
    margin: 0;
    padding: 0;
    font-size: 14.5px;
    line-height: 1.55;
}

.check-list li {
    display: flex;
    gap: 10px;
}

.check-list li + li {
    margin-top: 10px;
}

.check-list .tick {
    flex: 0 0 auto;
    color: #5f7f22;
    font-size: 13px;
    line-height: 1.75;
}

html.dark .check-list .tick {
    color: #a2c756;
}

/* Numbered steps inside the upload cards */
.step-list {
    margin: 0;
    padding-left: 20px;
    list-style: decimal;
    font-size: 14px;
    line-height: 1.6;
}

.step-list li + li {
    margin-top: 7px;
}

/* Analysis rows (Running Analyses) */
.lede {
    font-size: 14.5px;
    margin: 0 0 16px 0;
}

.play {
    font-size: 11px;
    color: #5f7f22;
}

html.dark .play {
    color: #a2c756;
}

.analysis-row {
    display: flex;
    align-items: baseline;
    gap: 18px;
    border-left: 3px solid var(--p-surface-400);
    background: var(--p-surface-50);
    padding: 11px 16px;
}

html.dark .analysis-row {
    background: var(--p-surface-800);
}

.analysis-row + .analysis-row {
    margin-top: 8px;
}

.analysis-row .name {
    flex: 0 0 120px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.03em;
    color: var(--p-text-color);
}

.analysis-row .desc {
    font-size: 14px;
    line-height: 1.5;
}

.qualifier {
    display: inline-block;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gwas-plum);
    background: rgba(111, 65, 92, 0.12);
    border-radius: 2px;
    padding: 2px 7px;
    margin-right: 8px;
    vertical-align: 1px;
}

html.dark .qualifier {
    color: #d9a7c4;
    background: rgba(217, 167, 196, 0.15);
}

/* Viewing Results */
.result-item {
    display: flex;
    gap: 13px;
}

.result-item + .result-item {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--p-content-border-color);
}

.result-item .ico {
    padding-top: 2px;
}

.result-item h3 {
    margin: 0 0 2px 0;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--p-text-color);
}

.result-item p {
    margin: 0;
    font-size: 14px;
    line-height: 1.55;
}

/* Status tags use the GWAS-CE badge colors (blue / lime / coral). */
.status-tag {
    font-family:
        SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono",
        "Courier New", monospace;
    font-size: 12px;
    border-radius: 2px;
    padding: 1px 7px;
}

.status-tag.running {
    color: #3d5d90;
    background: #e7eef8;
}

.status-tag.succeeded {
    color: #4d6424;
    background: #eef6dc;
}

.status-tag.failed {
    color: #8d3036;
    background: #fdeced;
}

html.dark .status-tag.running {
    color: #a9bfe3;
    background: rgba(99, 134, 192, 0.2);
}

html.dark .status-tag.succeeded {
    color: #c3dc8f;
    background: rgba(162, 199, 86, 0.18);
}

html.dark .status-tag.failed {
    color: #f0a3a7;
    background: rgba(222, 86, 92, 0.2);
}

/* Narrow viewports */
@media (max-width: 860px) {
    .analysis-row {
        display: block;
    }

    .analysis-row .name {
        margin-bottom: 4px;
    }

    .page-intro h1 {
        font-size: 32px;
    }
}
</style>
