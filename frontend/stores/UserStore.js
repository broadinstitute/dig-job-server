import { defineStore } from "pinia";

export const useUserStore = defineStore("UserStore", {
    state: () => {
        return {
            user: null,
            axios: null,
            loginError: null,
        };
    },
    actions: {
        init() {
            const config = useRuntimeConfig();
            this.axios = useAxios(config);
        },
        async isUserLoggedIn() {
            try {
                if (!this.axios) {
                    this.init();
                }
                const { data } = await this.axios.get("/api/is-logged-in");
                this.user = data;
                return true;
            } catch (error) {
                return false;
            }
        },
        async sampleTextFile(file) {
            const part = await readFilePart(file, 2048);
            const formData = new FormData();
            formData.append("file", new Blob([part]), file.name);

            const { data } = await this.axios.post(
                "/api/preview-delimited-file",
                formData,
                {
                    headers: { "Content-Type": "multipart/form-data" },
                },
            );
            return data;
        },
        async retrieveDatasets(orderBy = null, orderDir = null) {
            let url = `/api/datasets`;
            const params = [];

            if (orderBy) {
                params.push(`orderBy=${orderBy}`);
            }

            if (orderDir) {
                params.push(`orderDir=${orderDir}`);
            }

            if (params.length > 0) {
                url += `?${params.join("&")}`;
            }

            const { data } = await this.axios.get(url);
            return data;
        },
        async login(username, password) {
            if (!this.axios) {
                this.init();
            }
            const response = await this.axios.post(
                "/api/login",
                JSON.stringify({ username, password }),
            );
            if (response.data && response.data.access_token) {
                localStorage.setItem("authToken", response.data.access_token);
            }
        },
        async getPresignedUrl(fileName, dataset) {
            const { data } = await this.axios.get(
                `/api/get-pre-signed-url/${dataset}?filename=${fileName}`,
            );
            return data;
        },
        async finalizeUpload(dataset) {
            console.log(JSON.stringify(dataset));
            await this.axios.post(
                "/api/finalize-upload",
                JSON.stringify(dataset),
            );
        },
        async startAnalysis(dataset, method) {
            const { data } = await this.axios.post(
                "/api/start-analysis",
                JSON.stringify({ dataset, method }),
            );
            return data;
        },
        async deleteDataset(dataset) {
            await this.axios.delete(`/api/delete-dataset/${dataset}`);
        },
        async getLogInfo(job_id) {
            const { data } = await this.axios.get(`/api/log-info/${job_id}`);
            return data;
        },
    },
});

function readFilePart(file, partSize) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsArrayBuffer(file.slice(0, partSize));
    });
}
