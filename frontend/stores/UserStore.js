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
        async logout(redirectUrl) {
            await this.axios.post("/api/logout");
            this.user = null;
            navigateTo(redirectUrl);
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
        async retrieveDatasets(){
            const { data } = await this.axios.get("/api/datasets");
            return data;
        },
        async login(username, password) {
            if (!this.axios) {
                this.init();
            }
            await this.axios.post(
                "/api/login",
                JSON.stringify({ username, password }),
            );
        },
        async getPresignedUrl(fileName, dataset){
            const {data} = await this.axios.get(`/api/get-pre-signed-url/${dataset}?filename=${fileName}`);
            return data;
        },
        async finalizeUpload(dataset){
            console.log(JSON.stringify(dataset));
            await this.axios.post('/api/finalize-upload', JSON.stringify(dataset));
        },
        async startAnalysis(dataset, method){
            await this.axios.post('/api/start-analysis', JSON.stringify({dataset, method}));
        },
        async getResults(dataset){
            const {data} = await this.axios.get(`/api/results/${dataset}`);
            return data;
        }
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
