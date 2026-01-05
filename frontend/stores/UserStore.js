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
            this.isDefaultUser =
                localStorage.getItem("isDefaultUser") === "true";
        },
        async isUserLoggedIn() {
            try {
                // Ensure axios is initialized for pages that bypass the default layout
                if (!this.axios) {
                    this.init();
                }

                const token = localStorage.getItem("authToken");
                if (!token) {
                    // Only try default login if we haven't explicitly signed out
                    // (isDefaultUser would be cleared on sign out)
                    const hasSignedOut =
                        localStorage.getItem("hasSignedOut") === "true";
                    if (!hasSignedOut) {
                        await this.tryDefaultLogin();
                    }
                    return this.user !== null;
                }

                // Verify token with user service
                const config = useRuntimeConfig();
                const response = await $fetch(
                    `${config.public.userServiceUrl}/api/auth/verify/?group=${config.public.userGroup}`,
                    {
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                    },
                );

                this.user = response.user;
                return true;
            } catch (error) {
                // Clear token if it has expired (401 response)
                if (error.status === 401) {
                    // If we were using default credentials, relogin automatically
                    const wasDefaultUser =
                        localStorage.getItem("isDefaultUser") === "true";

                    // Clear invalid token
                    localStorage.removeItem("authToken");
                    this.user = null;

                    // For default user, try to login again automatically
                    // But only if they haven't explicitly signed out
                    const hasSignedOut =
                        localStorage.getItem("hasSignedOut") === "true";
                    if (wasDefaultUser && !hasSignedOut) {
                        await this.tryDefaultLogin();
                    }
                }

                // If not logged in and we don't have any token, try default login
                // But only if they haven't explicitly signed out
                const hasSignedOut =
                    localStorage.getItem("hasSignedOut") === "true";
                if (!localStorage.getItem("authToken") && !hasSignedOut) {
                    await this.tryDefaultLogin();
                }

                return this.user !== null;
            }
        },
        async tryDefaultLogin() {
            try {
                const config = useRuntimeConfig();
                // Only attempt default login if explicitly enabled via environment variable
                if (
                    config.public.enableDefaultLogin &&
                    config.public.defaultUsername &&
                    config.public.defaultPassword
                ) {
                    await this.login(
                        config.public.defaultUsername,
                        config.public.defaultPassword,
                        true,
                    );
                    return true;
                }
            } catch (error) {
                console.error(
                    "Failed to login with default credentials",
                    error,
                );
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
        async validateBedFile(formData) {
            const { data } = await this.axios.post(
                "/api/validate-bed-file",
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

                const response = await $fetch(
                    `${config.public.userServiceUrl}/api/auth/login/`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: {
                            username,
                            password,
                            group: config.public.userGroup,
                        },
                    },
                );

                if (response && response.access) {
                    localStorage.setItem("authToken", response.access);
                    this.user = response.user;
                    this.isDefaultUser = isDefault;

                    if (isDefault) {
                        localStorage.setItem("isDefaultUser", "true");
                    } else {
                        localStorage.removeItem("isDefaultUser");
                    }

                    // Clear the hasSignedOut flag when user logs in
                    localStorage.removeItem("hasSignedOut");

                    return true;
                }
            } catch (error) {
                this.loginError =
                    error.data?.error || error.message || "Login failed";
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
        async getLogInfo(job_id, method_name = null) {
            const params = method_name ? `?method_name=${method_name}` : "";
            const { data } = await this.axios.get(
                `/api/log-info/${job_id}${params}`,
            );
            return data;
        },
        async getBedPresignedUrl(fileName, dataset) {
            const { data } = await this.axios.get(
                `/api/get-bed-presigned-url/${dataset}?filename=${fileName}`,
            );
            return data;
        },
        async finalizeBedUpload(datasetName, fileName) {
            await this.axios.post("/api/finalize-bed-upload", null, {
                params: {
                    dataset_name: datasetName,
                    filename: fileName,
                },
            });
        },
        async getBedFiles() {
            try {
                const { data } = await this.axios.get("/api/bed-files");
                return data;
            } catch (error) {
                console.error("Error fetching BED files:", error);
                throw error;
            }
        },
        async downloadBedFile(datasetName) {
            try {
                // Get presigned URL from backend
                const response = await this.axios.get(
                    `/api/bed-files/${datasetName}/download`,
                );

                // Use the presigned URL to download the file
                const downloadUrl = response.data.download_url;
                const filename = response.data.filename;

                // Create a download link and trigger it
                // This avoids CORS issues by letting the browser handle the download directly
                const link = document.createElement("a");
                link.href = downloadUrl;
                link.setAttribute("download", filename);
                link.target = "_blank"; // Open in new tab as fallback
                document.body.appendChild(link);
                link.click();
                link.remove();
            } catch (error) {
                console.error("Error downloading BED file:", error);
                throw error;
            }
        },
        async deleteBedFile(datasetName) {
            try {
                await this.axios.delete(`/api/bed-files/${datasetName}`);
            } catch (error) {
                console.error("Error deleting BED file:", error);
                throw error;
            }
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
