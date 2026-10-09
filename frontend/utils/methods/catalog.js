// Single source of truth for the GWAS post-processing methods shown on the
// landing page (MethodCard), the getting-started guide, and described at
// /methods/<slug>.
//
// Tailwind v4 only generates classes it can see as literal strings, so the
// color classes are spelled out in full here rather than assembled from a
// color name at render time. `accent` is a GWAS-CE logo color applied as an
// inline style (landing card top edge, guide row left edge).
//
// `external` marks a method whose results open outside GWAS-CE (Variant
// Sifter runs a prep job here, then opens in the HuGeAMP portal).

export const METHODS = [
    {
        slug: "sldsc",
        title: "S-LDSC",
        fullName: "Stratified LD Score Regression",
        blurb: "Partition heritability across functional annotations and test annotation categories for enrichment.",
        icon: "pi pi-chart-line",
        iconWrapClass: "bg-blue-100 dark:bg-blue-900/20",
        iconClass: "text-blue-600 dark:text-blue-400",
        accent: "#6386c0",
        tags: [
            { value: "Heritability", severity: "primary" },
            { value: "SNP-based", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "magma",
        title: "MAGMA",
        fullName: "Multi-marker Analysis of GenoMic Annotation",
        blurb: "Aggregate variant-level signal into gene-level statistics and test gene sets and pathways.",
        icon: "pi pi-sitemap",
        iconWrapClass: "bg-green-100 dark:bg-green-900/20",
        iconClass: "text-green-600 dark:text-green-400",
        accent: "#a2c756",
        tags: [
            { value: "Gene-based", severity: "success" },
            { value: "Pathway", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "pigean",
        title: "PIGEAN",
        fullName: "Priors Inferred from GEne ANnotations",
        blurb: "Prioritize genes by combining GWAS signal with gene-set and annotation-derived priors.",
        icon: "pi pi-sparkles",
        iconWrapClass: "bg-orange-100 dark:bg-orange-900/20",
        iconClass: "text-orange-600 dark:text-orange-400",
        accent: "#f2b444",
        tags: [
            { value: "Gene Priors", severity: "warn" },
            { value: "Annotation", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "falcon",
        title: "FALCON",
        fullName:
            "Framework for Analysis of Linkage and Combined Omics using Networks",
        blurb: "Integrate multiple genetic data sources to calculate genetic support for the role of a set of genes across your trait of interest.",
        icon: "pi pi-bolt",
        iconWrapClass: "bg-rose-100 dark:bg-rose-900/20",
        iconClass: "text-rose-600 dark:text-rose-400",
        accent: "#6f415c",
        tags: [
            { value: "Gene sets", severity: "danger" },
            { value: "Multi-omic", severity: "info" },
        ],
        implemented: true,
    },
    {
        slug: "variant-sifter",
        title: "Variant Sifter",
        fullName: null,
        blurb: "Prioritize genetically associated variants, credible sets, and other tissue-specific epigenomic annotations for downstream assessment.",
        icon: "pi pi-filter",
        iconWrapClass: "bg-teal-100 dark:bg-teal-900/20",
        iconClass: "text-teal-600 dark:text-teal-400",
        accent: "#726b45",
        tags: [
            { value: "Variants", severity: "info" },
            { value: "Epigenomic", severity: "secondary" },
        ],
        implemented: true,
        external: true,
    },
];

export const getMethod = (slug) => METHODS.find((m) => m.slug === slug);

export const methodPath = (slug) => `/methods/${slug}`;
