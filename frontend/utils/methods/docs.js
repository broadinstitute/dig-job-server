// Long-form copy for /methods/<slug>, adapted from the "GWAS-CE Methods
// Descriptions and Outputs" doc. Kept apart from catalog.js so the card
// metadata stays scannable.
//
// `overview` and `output` are lists of blocks: a string is a paragraph, an
// object is a screenshot ({ src, alt, caption }) served from public/methods/.
// Paragraphs are trusted, source-controlled HTML (only <strong>, <em>, <sup>,
// <a>) and are rendered with v-html. Never put user-supplied text here.

// Every worked example was produced by running the method on this dataset.
export const EXAMPLE_DATASET = {
    label: "BMI-adjusted adiponectin, European ancestry (bottom-line summary statistics)",
    url: "https://dig-open-bottom-line-analysis.s3.amazonaws.com/bottom-line/EU/AdiponectinadjBMI.sumstats.tsv.gz",
};

export const METHOD_DOCS = {
    sldsc: {
        overview: [
            "The <strong>S</strong>tratified <strong>L</strong>inkage <strong>D</strong>isequilibrium <strong>SC</strong>ore regression method (S-LDSC) is commonly used to detect tissue-specific regions where genomic annotations are enriched for a given phenotype. The outputs of this method, identifying which tissues have enriched genetic association signals, can be used to direct researchers to specific tissues that may be relevant for the phenotype of interest.",
        ],
        output: [
            {
                src: "/methods/sldsc-output.png",
                alt: "S-LDSC annotation volcano plot with a tooltip for the subcutaneous adipose tissue enhancer biosample",
                caption: "S-LDSC volcano plot: log10(enrichment) vs -log10(p-value), colored by annotation.",
            },
            "This example looks at the bottom-line S-LDSC output for the BMI-adjusted adiponectin trait filtered for European ancestry. When examining the S-LDSC output, users can hover over different biosamples across annotations such as enhancers and promoters to view contrasting enrichment levels.",
            "Here, the <em>subcutaneous_adipose_tissue</em> biosample from the <em>adipose_tissue</em> tissue type across the enhancer annotation is examined. This biosample has an enrichment of 9.89 and a most significant p-value of 3.61 &times; 10<sup>-5</sup>.",
        ],
        references: [
            {
                label: "Finucane et al. (2015). Partitioning heritability by functional annotation using genome-wide association summary statistics. Nat Genet.",
                url: "https://pubmed.ncbi.nlm.nih.gov/26414678/",
            },
            {
                label: "Bulik-Sullivan et al. (2015). An atlas of genetic correlations across human diseases and traits. Nat Genet.",
                url: "https://pubmed.ncbi.nlm.nih.gov/26414676/",
            },
            {
                label: "LDSC software (GitHub)",
                url: "https://github.com/bulik/LDSC",
            },
            {
                label: "A2F Knowledge Portal: S-LDSC documentation",
                url: "https://a2f.hugeamp.org/help.html?page=1094",
            },
        ],
    },
    magma: {
        overview: [
            "The <strong>M</strong>ultimarker <strong>A</strong>nalysis of <strong>G</strong>eno<strong>M</strong>ic <strong>A</strong>nnotation (MAGMA) method uses genetic association data to calculate associations at the gene level. MAGMA is run for bottom-line association results, using default parameters, with a window size of 50kb. A generally accepted threshold for significance of gene-level MAGMA results is p &le; 2.5 &times; 10<sup>-6</sup>.",
            "Note that a significant MAGMA result indicates that the gene is close to a significantly associated variant, but this should not be taken to mean that the gene itself is necessarily causal for the phenotype. If multiple genes are near an association, MAGMA assigns low p-values to all of them.",
        ],
        output: [
            {
                src: "/methods/magma-output.png",
                alt: "MAGMA gene results table sorted by p-value, with ADIPOQ, EIF4A2 and RFC4 highlighted",
                caption: "MAGMA gene results, sorted by p-value.",
            },
            "This example looks at the bottom-line MAGMA output for the BMI-adjusted adiponectin trait filtered for European ancestry. Here, the genes that are most significantly associated with the trait are reported, with <em>ADIPOQ</em> (p-value of 1.84 &times; 10<sup>-49</sup>), <em>EIF4A2</em> (p-value of 1.61 &times; 10<sup>-36</sup>), and <em>RFC4</em> (p-value of 6.17 &times; 10<sup>-28</sup>) being the three most significantly associated genes (highlighted in the red box).",
        ],
        references: [
            {
                label: "de Leeuw et al. (2015). MAGMA: Generalized gene-set analysis of GWAS data. PLoS Comput Biol.",
                url: "https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1004219",
            },
            {
                label: "A2F Knowledge Portal: MAGMA gene-level associations",
                url: "https://a2f.hugeamp.org/help.html?page=955",
            },
            {
                label: "A2F Knowledge Portal: MAGMA documentation",
                url: "https://a2f.hugeamp.org/help.html?page=949",
            },
        ],
    },
    pigean: {
        overview: [
            "The <strong>P</strong>riors <strong>I</strong>nferred from <strong>GE</strong>ne <strong>AN</strong>notations (PIGEAN) method is used to assess the probability that a gene is involved in a trait of interest.",
            "Specifically, PIGEAN is a Bayesian method that jointly models the probability that each gene is involved in a phenotype of interest, given the gene sets that contain the gene (indirect evidence of involvement in a trait) and the GWAS genetic association statistics for variants near the gene (direct evidence of involvement in a trait).",
        ],
        output: [
            {
                src: "/methods/pigean-output.png",
                alt: "PIGEAN gene scatter plot of direct vs indirect score, with a tooltip for ADIPOQ",
                caption: "PIGEAN gene results: direct vs indirect genetic support.",
            },
            "This example looks at the bottom-line PIGEAN output for the BMI-adjusted adiponectin trait filtered for European ancestry. At the top right of the graph, the gene <em>ADIPOQ</em> is reported to have the highest combined score of direct and indirect genetic support, 9.310. This result is consistent with the fact that <em>ADIPOQ</em> encodes adiponectin, the trait assessed in this analysis.",
        ],
        references: [
            {
                label: "PIGEAN software (GitHub)",
                url: "https://github.com/flannick/pigean",
            },
            {
                label: "CFDE Knowledge Center: gene set browser",
                url: "https://cfdeknowledge.org/r/kc_gene_set_browser_gene?gene=CHST15&model=cfde",
            },
        ],
    },
    falcon: {
        overview: [
            "The <strong>F</strong>ramework for <strong>A</strong>nalysis of <strong>L</strong>inkage and <strong>C</strong>ombined <strong>O</strong>mics using <strong>N</strong>etworks (FALCON) method integrates multiple genetic data sources, including summary statistics from GWAS or EWAS, linkage disequilibrium, variant annotations, and variant-to-gene maps, to calculate genetic support scores for a set of genes of interest.",
            "FALCON's final output includes genetic support scores, fine-mapped effect sizes, and fine-linked variant-to-gene connections. Together, these results can help researchers estimate how individual genetic variants influence a trait as well as identify the most likely gene targets for trait-relevant variants.",
        ],
        output: [
            {
                src: "/methods/falcon-output.png",
                alt: "FALCON genes plot of -log10(p-value) vs probability, with a tooltip for the lead gene LYPLAL1",
                caption: "FALCON genes plot, one of six result tabs.",
            },
            "This example looks at a subset of the bottom-line FALCON output for the BMI-adjusted adiponectin trait filtered for European ancestry. Users can click through six tabs to examine the FALCON outputs, including an executive summary of the method output, a genes plot, and a variants plot.",
            "In the genes plot, the gene <em>LYPLAL1</em> is reported to have the highest genetic support, which is consistent with the gene's known role in influencing adiponectin levels (Spracklen et al. 2019).",
        ],
        references: [
            {
                label: "FALCON",
                url: "https://d26k96aakgfksz.cloudfront.net/#home",
            },
            {
                label: "Spracklen et al. (2019). Exome-derived adiponectin-associated variants implicate obesity and lipid biology. Am J Hum Genet.",
                url: "https://pubmed.ncbi.nlm.nih.gov/31178129/",
            },
        ],
    },
    "variant-sifter": {
        overview: [
            "The Variant Sifter is a service offered by the Knowledge Portal Network that allows users to explore genetic associations, credible sets, and variant-to-gene links across shared genomic loci to prioritize variants for downstream analysis.",
            "In GWAS-CE, upload a GWAS summary statistics file and select <strong>Run Variant Sifter</strong> under analysis. Once Variant Sifter has finished running, click <strong>Open Variant Sifter</strong> to be taken to the Variant Sifter page in the Knowledge Portal:",
            {
                src: "/methods/variant-sifter-start.png",
                alt: "Variant Sifter start page with the GWAS-CE token, phenotype, ancestry and gene fields filled in",
                caption: "Variant Sifter start page, opened from GWAS-CE.",
            },
            "From there, select your phenotype, ancestry, and gene or variant of interest to begin exploring.",
        ],
        output: [
            "This example looks at the bottom-line output in Variant Sifter for the BMI-adjusted adiponectin trait filtered for European ancestry, with the gene <em>ADIPOQ</em> selected for examination.",
            {
                src: "/methods/variant-sifter-output.png",
                alt: "Variant Sifter global enrichment plot by annotation, with adipose tissue highlighted at the far right",
                caption: "Variant Sifter global enrichment plot.",
            },
            "One of the Variant Sifter outputs is the global enrichment plot, which reports the tissue types and annotations that are most significantly enriched for the trait. In this example, adipose tissue for the enhancer annotation (the right-most point in the graph, highlighted in the red box) has the most significant p-value, consistent with adipose tissue being the tissue that produces adiponectin.",
        ],
        references: [
            {
                label: "Knowledge Portal Network: Variant Sifter",
                url: "https://hugeamp.org/research.html?pageid=kp_variant_sifter",
            },
        ],
    },
};

export const getMethodDocs = (slug) => METHOD_DOCS[slug];
