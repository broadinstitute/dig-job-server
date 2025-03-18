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
                // Convert filter object to API-compatible format
                const apiFilters = {};
                if (params.filters) {
                    Object.entries(params.filters).forEach(
                        ([field, filter]) => {
                            // Handle text search and dropdown equals filters
                            if (
                                filter.matchMode === "contains" &&
                                filter.value
                            ) {
                                apiFilters[field] = filter.value;
                            }
                            // Handle dropdown equals filter
                            else if (
                                filter.matchMode === "equals" &&
                                filter.value
                            ) {
                                apiFilters[field + "_exact"] = filter.value;
                            }
                            // Handle less than or equal filters
                            else if (
                                filter.matchMode === "lte" &&
                                filter.value !== null
                            ) {
                                apiFilters[field + "_max"] = filter.value;
                            }
                            // Handle between filters
                            else if (filter.matchMode === "between") {
                                if (filter.value !== null) {
                                    apiFilters[`${field}_min`] = filter.value;
                                }
                                if (filter.value2 !== null) {
                                    apiFilters[`${field}_max`] = filter.value2;
                                }
                            }
                        },
                    );
                }

                const queryParams = new URLSearchParams({
                    offset: params.first || 0,
                    limit: params.rows || 10,
                    sort_field: params.sort_field || "pValue",
                    sort_order: params.sort_order || -1,
                    ...apiFilters,
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
