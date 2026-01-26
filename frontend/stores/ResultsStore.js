// stores/resultsStore.js
import { defineStore } from "pinia";

export const useResultsStore = defineStore("results", {
    state: () => ({
        // Shared state across all tabs
        dataset: null,
        activeTab: "sldsc",
        workflowStatus: {},
        hasWorkflowData: false,
        error: null,
        axios: null,

        // Results availability flags
        hasSldscResults: false,
        hasMagmaResults: false,
        hasMagmaPathwaysResults: false,
        hasPigeanGeneResults: false,
        hasPigeanGeneSetResults: false,

        // Workflow running states
        sldscWorkflowRunning: false,
        magmaWorkflowRunning: false,
        pigeanWorkflowRunning: false,
        sldscWorkflowStatus: "",
        magmaWorkflowStatus: "",
        pigeanWorkflowStatus: "",

        // Job ID for log links
        jobId: null,

        // Download URLs
        sldscDownloadUrl: null,
        magmaDownloadUrl: null,
        magmaPathwaysDownloadUrl: null,
        pigeanGeneDownloadUrl: null,
        pigeanGeneSetDownloadUrl: null,

        // Legacy fields for backward compatibility
        items: [],
        totalRecords: 0,
        loading: false,
        tissues: [],
        biosamples: [],
        annotations: [],
        genes: [],
    }),

    getters: {
        // Tab visibility computed properties
        shouldShowSldscTab: (state) =>
            state.hasSldscResults || state.sldscWorkflowRunning,
        shouldShowMagmaTab: (state) =>
            state.hasMagmaResults ||
            state.hasMagmaPathwaysResults ||
            state.magmaWorkflowRunning,
        shouldShowPigeanTab: (state) =>
            state.hasPigeanGeneResults ||
            state.hasPigeanGeneSetResults ||
            state.pigeanWorkflowRunning,
        hasPigeanResults: (state) =>
            state.hasPigeanGeneResults || state.hasPigeanGeneSetResults,

        // Tab headers with status indicators
        sldscTabHeader: (state) =>
            state.sldscWorkflowRunning ? "SLDSC ⏳" : "SLDSC",
        magmaTabHeader: (state) =>
            state.magmaWorkflowRunning ? "MAGMA ⏳" : "MAGMA",
        pigeanTabHeader: (state) =>
            state.pigeanWorkflowRunning ? "PIGEAN ⏳" : "PIGEAN",

        // Download button helpers
        downloadButtonLabel: (state) => {
            switch (state.activeTab) {
                case "sldsc":
                    return "Download SLDSC Results";
                case "magma":
                    return "Download MAGMA Results";
                case "pigean":
                    return "Download PIGEAN Results";
                default:
                    return "Download Results";
            }
        },
        canDownloadCurrentTab: (state) => {
            switch (state.activeTab) {
                case "sldsc":
                    return !!state.sldscDownloadUrl;
                case "magma":
                    return !!state.magmaDownloadUrl;
                case "pigean":
                    return (
                        !!state.pigeanGeneDownloadUrl ||
                        !!state.pigeanGeneSetDownloadUrl
                    );
                default:
                    return false;
            }
        },
    },

    actions: {
        init() {
            const config = useRuntimeConfig();
            this.axios = useAxios(config);
        },

        setDataset(dataset) {
            this.dataset = dataset;
            this.jobId = dataset; // Job ID is the same as dataset name
        },

        setActiveTab(tab) {
            this.activeTab = tab;
        },

        setError(error) {
            this.error = error;
        },

        clearError() {
            this.error = null;
        },

        // Check workflow status and results availability
        async checkResultsAvailability() {
            this.init();
            if (!this.dataset) return;

            try {
                // Check workflow status first
                const encodedDataset = encodeURIComponent(this.dataset);
                const workflowResponse = await this.axios.get(
                    `/api/workflow-status/${encodedDataset}`,
                );
                this.workflowStatus = workflowResponse.data.status || {};
                this.hasWorkflowData =
                    Object.keys(this.workflowStatus).length > 0;

                // Parse workflow status for each method
                this.parseWorkflowStatus();

                // If no workflow data or all completed, check results directly
                if (!this.hasWorkflowData) {
                    await this.checkResultsDirectly();
                }

                // Determine first available tab if current tab has no results
                this.selectFirstAvailableTab();
            } catch (error) {
                console.error("Error checking results availability:", error);
                // Fall back to checking results directly
                await this.checkResultsDirectly();
            }
        },

        parseWorkflowStatus() {
            // Reset states
            this.sldscWorkflowRunning = false;
            this.magmaWorkflowRunning = false;
            this.pigeanWorkflowRunning = false;
            this.hasSldscResults = false;
            this.hasMagmaResults = false;
            this.hasMagmaPathwaysResults = false;
            this.hasPigeanGeneResults = false;
            this.hasPigeanGeneSetResults = false;

            // Process each workflow
            for (const [workflow, methods] of Object.entries(
                this.workflowStatus,
            )) {
                for (const [method, details] of Object.entries(methods)) {
                    const status = details.status;
                    const isRunning =
                        status === "RUNNING" ||
                        status === "PENDING" ||
                        status === "SUBMITTED";
                    const isSucceeded = status === "SUCCEEDED";

                    if (workflow === "sldsc" || method === "sldsc") {
                        this.sldscWorkflowRunning = isRunning;
                        this.sldscWorkflowStatus = status;
                        this.hasSldscResults = isSucceeded;
                        if (isSucceeded && details.download_url) {
                            this.sldscDownloadUrl = details.download_url;
                        }
                    }
                    if (
                        workflow === "magma" ||
                        method === "magma" ||
                        method === "gene"
                    ) {
                        this.magmaWorkflowRunning = isRunning;
                        this.magmaWorkflowStatus = status;
                        this.hasMagmaResults = isSucceeded;
                        if (isSucceeded && details.download_url) {
                            this.magmaDownloadUrl = details.download_url;
                        }
                    }
                    if (method === "pathway" || method === "pathways") {
                        this.hasMagmaPathwaysResults = isSucceeded;
                        if (isSucceeded && details.download_url) {
                            this.magmaPathwaysDownloadUrl =
                                details.download_url;
                        }
                    }
                    if (
                        workflow === "pigean" ||
                        method === "pigean" ||
                        method === "gene_results"
                    ) {
                        this.pigeanWorkflowRunning = isRunning;
                        this.pigeanWorkflowStatus = status;
                        this.hasPigeanGeneResults = isSucceeded;
                        if (isSucceeded && details.download_url) {
                            this.pigeanGeneDownloadUrl = details.download_url;
                        }
                    }
                    if (method === "gene_set_results") {
                        this.hasPigeanGeneSetResults = isSucceeded;
                        if (isSucceeded && details.download_url) {
                            this.pigeanGeneSetDownloadUrl =
                                details.download_url;
                        }
                    }
                }
            }
        },

        async checkResultsDirectly() {
            // Check each result type by attempting to fetch with limit 1
            const encodedDataset = encodeURIComponent(this.dataset);
            
            try {
                const sldscCheck = await this.axios.get(
                    `/api/results/${encodedDataset}?rows=1`,
                );
                this.hasSldscResults =
                    sldscCheck.data.totalRecords > 0 ||
                    sldscCheck.data.items?.length > 0;
            } catch {
                this.hasSldscResults = false;
            }

            try {
                const magmaCheck = await this.axios.get(
                    `/api/magma-results/${encodedDataset}?rows=1`,
                );
                this.hasMagmaResults =
                    magmaCheck.data.totalRecords > 0 ||
                    magmaCheck.data.items?.length > 0;
            } catch {
                this.hasMagmaResults = false;
            }

            try {
                const pathwayCheck = await this.axios.get(
                    `/api/magma-pathways-results/${encodedDataset}?rows=1`,
                );
                this.hasMagmaPathwaysResults =
                    pathwayCheck.data.totalRecords > 0 ||
                    pathwayCheck.data.items?.length > 0;
            } catch {
                this.hasMagmaPathwaysResults = false;
            }

            try {
                const pigeanGeneCheck = await this.axios.get(
                    `/api/pigean-gene-results/${encodedDataset}?rows=1`,
                );
                this.hasPigeanGeneResults =
                    pigeanGeneCheck.data.totalRecords > 0 ||
                    pigeanGeneCheck.data.items?.length > 0;
            } catch {
                this.hasPigeanGeneResults = false;
            }

            try {
                const pigeanGeneSetCheck = await this.axios.get(
                    `/api/pigean-gene-set-results/${encodedDataset}?rows=1`,
                );
                this.hasPigeanGeneSetResults =
                    pigeanGeneSetCheck.data.totalRecords > 0 ||
                    pigeanGeneSetCheck.data.items?.length > 0;
            } catch {
                this.hasPigeanGeneSetResults = false;
            }
        },

        selectFirstAvailableTab() {
            // If current tab has results, keep it
            if (this.activeTab === "sldsc" && this.shouldShowSldscTab) return;
            if (this.activeTab === "magma" && this.shouldShowMagmaTab) return;
            if (this.activeTab === "pigean" && this.shouldShowPigeanTab) return;

            // Otherwise select first available
            if (this.shouldShowSldscTab) {
                this.activeTab = "sldsc";
            } else if (this.shouldShowMagmaTab) {
                this.activeTab = "magma";
            } else if (this.shouldShowPigeanTab) {
                this.activeTab = "pigean";
            }
        },

        openDownloadLink() {
            let url = null;
            switch (this.activeTab) {
                case "sldsc":
                    url = this.sldscDownloadUrl;
                    break;
                case "magma":
                    url = this.magmaDownloadUrl;
                    break;
                case "pigean":
                    url =
                        this.pigeanGeneDownloadUrl ||
                        this.pigeanGeneSetDownloadUrl;
                    break;
            }
            if (url) {
                window.open(url, "_blank");
            }
        },

        getStatusClass(status) {
            switch (status) {
                case "SUCCEEDED":
                    return "bg-green-100 text-green-700";
                case "FAILED":
                    return "bg-red-100 text-red-700";
                case "RUNNING":
                case "PENDING":
                case "SUBMITTED":
                    return "bg-blue-100 text-blue-700";
                default:
                    return "bg-gray-100 text-gray-700";
            }
        },

        // Legacy method for backward compatibility
        async getResults(dataset, params = {}, resultType = "ldsc") {
            this.init();
            this.loading = true;
            this.error = null;

            try {
                // Create query params from the provided parameters
                const queryParams = new URLSearchParams({
                    first: params.first || 0,
                    rows: params.rows || 10,
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

                // Choose the appropriate endpoint based on result type
                const encodedDataset = encodeURIComponent(dataset);
                const endpoint =
                    resultType === "magma"
                        ? `/api/magma-results/${encodedDataset}?${queryParams.toString()}`
                        : `/api/results/${encodedDataset}?${queryParams.toString()}`;

                const { data} = await this.axios.get(endpoint);

                if (data.items) this.items = data.items;
                if (data.totalRecords) this.totalRecords = data.totalRecords;

                // Handle different result types
                if (resultType === "magma") {
                    if (data.genes) this.genes = data.genes;
                    // Clear LDSC-specific fields
                    this.tissues = [];
                    this.biosamples = [];
                    this.annotations = [];
                } else {
                    if (data.tissues) this.tissues = data.tissues;
                    if (data.biosamples) this.biosamples = data.biosamples;
                    if (data.annotations) this.annotations = data.annotations;
                    // Clear MAGMA-specific fields
                    this.genes = [];
                }

                return data;
            } catch (error) {
                this.error = "Failed to load results";
                throw error;
            } finally {
                this.loading = false;
            }
        },

        // Reset store state
        $reset() {
            this.dataset = null;
            this.activeTab = "sldsc";
            this.workflowStatus = {};
            this.hasWorkflowData = false;
            this.error = null;
            this.hasSldscResults = false;
            this.hasMagmaResults = false;
            this.hasMagmaPathwaysResults = false;
            this.hasPigeanGeneResults = false;
            this.hasPigeanGeneSetResults = false;
            this.sldscWorkflowRunning = false;
            this.magmaWorkflowRunning = false;
            this.pigeanWorkflowRunning = false;
            this.sldscWorkflowStatus = "";
            this.magmaWorkflowStatus = "";
            this.pigeanWorkflowStatus = "";
            this.jobId = null;
            this.sldscDownloadUrl = null;
            this.magmaDownloadUrl = null;
            this.magmaPathwaysDownloadUrl = null;
            this.pigeanGeneDownloadUrl = null;
            this.pigeanGeneSetDownloadUrl = null;
            this.items = [];
            this.totalRecords = 0;
            this.loading = false;
            this.tissues = [];
            this.biosamples = [];
            this.annotations = [];
            this.genes = [];
        },
    },
});
