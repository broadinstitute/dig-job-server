import { defineStore } from "pinia";

export const useUserStore = defineStore("UserStore", {
    state: () => {
        return {
            user: null,
            axios: null,
            loginError: null,
            isDefaultUser: false,
        };
    },
    actions: {
        init() {
            const config = useRuntimeConfig();
            this.axios = useAxios(config);
            this.isDefaultUser = localStorage.getItem("isDefaultUser") === "true";
        },
        async isUserLoggedIn() {
            try {
                const token = localStorage.getItem('authToken');
                if (!token) {
                    // If not logged in and we don't have any token, try default login
                    await this.tryDefaultLogin();
                    return this.user !== null;
                }

                // Verify token with user service
                const config = useRuntimeConfig();
                const response = await $fetch(`${config.public.userServiceUrl}/api/auth/verify/?group=${config.public.userGroup}`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                this.user = response.user;
                return true;
            } catch (error) {
                // Clear token if it has expired (401 response)
                if (error.status === 401) {
                    // If we were using default credentials, relogin automatically
                    const wasDefaultUser = localStorage.getItem('isDefaultUser') === 'true';
                    
                    // Clear invalid token
                    localStorage.removeItem('authToken');
                    this.user = null;
                    
                    // For default user, try to login again automatically
                    if (wasDefaultUser) {
                        await this.tryDefaultLogin();
                    }
                }
                
                // If not logged in and we don't have any token, try default login
                if (!localStorage.getItem('authToken')) {
                    await this.tryDefaultLogin();
                }
                
                return this.user !== null;
            }
        },
        async tryDefaultLogin() {
            try {
                const config = useRuntimeConfig();
                if (config.public.defaultUsername && config.public.defaultPassword) {
                    await this.login(
                        config.public.defaultUsername,
                        config.public.defaultPassword,
                        true
                    );
                    return true;
                }
            } catch (error) {
                console.error("Failed to login with default credentials", error);
            }
            return false;
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
        async login(username, password, isDefault = false) {
            try {
                const config = useRuntimeConfig();
                
                const response = await $fetch(`${config.public.userServiceUrl}/api/auth/login/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: {
                        username,
                        password,
                        group: config.public.userGroup
                    }
                });

                if (response && response.access) {
                    localStorage.setItem("authToken", response.access);
                    this.user = response.user;
                    this.isDefaultUser = isDefault;
                    
                    if (isDefault) {
                        localStorage.setItem("isDefaultUser", "true");
                    } else {
                        localStorage.removeItem("isDefaultUser");
                    }
                    
                    return true;
                }
            } catch (error) {
                this.loginError = error.data?.error || error.message || 'Login failed';
                throw error;
            }
        },
        logout() {
            localStorage.removeItem("authToken");
            localStorage.removeItem("isDefaultUser");
            this.user = null;
            this.isDefaultUser = false;
            this.loginError = null;
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
