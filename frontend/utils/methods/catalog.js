// Single source of truth for the GWAS post-processing methods shown on the
// landing page (MethodCard) and described at /methods/<slug>.
//
// Tailwind v4 only generates classes it can see as literal strings, so the
// color classes are spelled out in full here rather than assembled from a
// color name at render time.

export const METHODS = [
    {
        slug: "sldsc",
        title: "SLDSC",
        blurb: "Stratified Linkage Disequilibrium Score Regression for heritability analysis",
        icon: "pi pi-chart-line",
        iconWrapClass: "bg-blue-100 dark:bg-blue-900/20",
        iconClass: "text-blue-600 dark:text-blue-400",
        tags: [
            { value: "Heritability", severity: "primary" },
            { value: "SNP-based", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "magma",
        title: "MAGMA",
        blurb: "Multi-marker Analysis of GenoMic Annotation for gene-set analysis",
        icon: "pi pi-sitemap",
        iconWrapClass: "bg-green-100 dark:bg-green-900/20",
        iconClass: "text-green-600 dark:text-green-400",
        tags: [
            { value: "Gene-based", severity: "success" },
            { value: "Pathway", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "cojo",
        title: "COJO",
        blurb: "Conditional & Joint association analysis using GWAS summary statistics",
        icon: "pi pi-link",
        iconWrapClass: "bg-teal-100 dark:bg-teal-900/20",
        iconClass: "text-teal-600 dark:text-teal-400",
        tags: [
            { value: "Conditional", severity: "info" },
            { value: "Joint", severity: "secondary" },
        ],
        implemented: false,
    },
    {
        slug: "pigean",
        title: "PIGEAN",
        blurb: "Priors Inferred from GEne ANnotations for gene prioritization",
        icon: "pi pi-sparkles",
        iconWrapClass: "bg-orange-100 dark:bg-orange-900/20",
        iconClass: "text-orange-600 dark:text-orange-400",
        tags: [
            { value: "Gene Priors", severity: "warn" },
            { value: "Annotation", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "falcon",
        title: "FALCON",
        // TODO: replace with the agreed one-line description of FALCON.
        blurb: "Locus-level analysis of GWAS results run locally via Docker",
        icon: "pi pi-bolt",
        iconWrapClass: "bg-rose-100 dark:bg-rose-900/20",
        iconClass: "text-rose-600 dark:text-rose-400",
        tags: [
            { value: "Locus", severity: "danger" },
            { value: "Local run", severity: "info" },
        ],
        implemented: true,
    },
];

export const getMethod = (slug) => METHODS.find((m) => m.slug === slug);

export const methodPath = (slug) => `/methods/${slug}`;
