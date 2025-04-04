import { defineStore } from "pinia";

export const usePhenotypeStore = defineStore("phenotype", {
    state: () => ({
        phenotypes: [],
        loading: false,
        error: null,
    }),
    getters: {
        getPhenotypeByName: (state) => (name) => {
            return state.phenotypes.find((p) => p.name === name);
        },
        getAllPhenotypes: (state) => {
            return state.phenotypes;
        },
        getPhenotypeOptions: (state) => {
            return state.phenotypes.map((p) => ({
                name: p.name,
                description: p.description,
            }));
        },
    },
    actions: {
        async fetchPhenotypes() {
            const config = useRuntimeConfig();
            const phenotypesUrl = config.public.phenotypesUrl;

            if (!phenotypesUrl) {
                console.error(
                    "NUXT_PUBLIC_PHENOTYPES_URL is not defined in environment variables",
                );
                this.error = "Phenotypes URL is not configured";
                return;
            }

            this.loading = true;
            this.error = null;

            try {
                const response = await fetch(phenotypesUrl);

                if (!response.ok) {
                    throw new Error(
                        `Failed to fetch phenotypes: ${response.status}`,
                    );
                }

                const data = await response.json();
                this.phenotypes = data.data;
            } catch (err) {
                console.error("Error fetching phenotypes:", err);
                this.error = err.message || "Failed to fetch phenotypes";
            } finally {
                this.loading = false;
            }
        },
    },
});
