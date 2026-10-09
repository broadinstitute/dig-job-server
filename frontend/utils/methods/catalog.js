// Single source of truth for the GWAS post-processing methods shown on the
// landing page (MethodCard), the getting-started guide, and described at
// /methods/<slug>.
//
// `accent` is a GWAS-CE logo color applied as an inline style (landing card
// top edge, guide row left edge).
//
// `external` marks a method whose results open outside GWAS-CE (Variant
// Sifter runs a prep job here, then opens in the HuGeAMP portal).

export const METHODS = [
    {
        slug: "sldsc",
        title: "S-LDSC",
        fullName: "Stratified LD Score Regression",
        blurb: "Partition heritability across functional annotations and test annotation categories for enrichment.",
        accent: "#6386c0",
        implemented: true,
    },
    {
        slug: "magma",
        title: "MAGMA",
        fullName: "Multi-marker Analysis of GenoMic Annotation",
        blurb: "Aggregate variant-level signal into gene-level statistics and test gene sets and pathways.",
        accent: "#a2c756",
        implemented: true,
    },
    {
        slug: "pigean",
        title: "PIGEAN",
        fullName: "Priors Inferred from GEne ANnotations",
        blurb: "Prioritize genes by combining GWAS signal with gene-set and annotation-derived priors.",
        accent: "#f2b444",
        implemented: true,
    },
    {
        slug: "falcon",
        title: "FALCON",
        fullName:
            "Framework for Analysis of Linkage and Combined Omics using Networks",
        blurb: "Integrate multiple genetic data sources to calculate genetic support for the role of a set of genes across your trait of interest.",
        accent: "#6f415c",
        implemented: true,
    },
    {
        slug: "variant-sifter",
        title: "Variant Sifter",
        fullName: null,
        blurb: "Prioritize genetically associated variants, credible sets, and other tissue-specific epigenomic annotations for downstream assessment.",
        accent: "#726b45",
        implemented: true,
        external: true,
    },
];

export const getMethod = (slug) => METHODS.find((m) => m.slug === slug);

export const methodPath = (slug) => `/methods/${slug}`;
