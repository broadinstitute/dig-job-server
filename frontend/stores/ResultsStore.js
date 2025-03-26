// stores/resultsStore.js
import { defineStore } from "pinia";
import axios from "axios";

export const useResultsStore = defineStore("results", {
    state: () => ({
        items: [],
        axios: null,
        totalRecords: 0,
        loading: false,
        error: null,
    }),

    actions: {
        init() {
            const config = useRuntimeConfig();
            this.axios = useAxios(config);
        },
        async getResults(dataset, params = {}) {
            this.init();
            this.loading = true;
            this.error = null;

            try {
                // Create query params from the provided parameters
                const queryParams = new URLSearchParams({
                    first: params.first || 0,
                    limit: params.rows || 10,
                    sort_field: params.sort_field || "pValue",
                    sort_order: params.sort_order || -1,
                });

                // Add any filter parameters that were passed
                Object.entries(params).forEach(([key, value]) => {
                    if (
                        key.startsWith("filter_") &&
                        value !== null &&
                        value !== ""
                    ) {
                        queryParams.append(key, value);
                    }
                });

                const { data } = await this.axios.get(
                    `/api/results/${dataset}?${queryParams.toString()}`,
                );
                this.items = data.items;
                this.totalRecords = data.totalRecords;
                return data;
            } catch (error) {
                this.error = "Failed to load results";
                throw error;
            } finally {
                this.loading = false;
            }
        },
    },
});
