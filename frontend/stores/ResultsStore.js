// stores/resultsStore.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useResultsStore = defineStore('results', {
    state: () => ({
        items: [],
        axios: null,
        totalRecords: 0,
        loading: false,
        error: null
    }),

    actions: {
        init() {
            const config = useRuntimeConfig()
            this.axios = useAxios(config)
        },
        async getResults(dataset, { first = 0, rows = 10, sort_field = null, sort_order = 1 } = {}) {
            this.init()
            this.loading = true
            this.error = null

            try {
                const params = new URLSearchParams({
                    first,
                    rows,
                    ...(sort_field && { sort_field, sort_order })
                })

                const { data } = await this.axios.get(`/api/results/${dataset}?${params}`)
                this.items = data.items
                this.totalRecords = data.totalRecords
                return data
            } catch (error) {
                this.error = 'Failed to load results'
                throw error
            } finally {
                this.loading = false
            }
        }
    }
})
