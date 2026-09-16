import { isVerifyRejection } from "~/utils/auth/verifyFailure.js";
import {
    HUB_STATUS,
    hubVerifyUrl,
    isHubCacheFresh,
    resolveHubStatus,
} from "~/utils/auth/hubMembership";

export const useUserStore = defineStore("UserStore", {
    state: () => {
        return {
            user: null,
            axios: null,
            loginError: null,
            isDefaultUser: false,
            // GWAS-Hub membership for this session; see utils/auth/hubMembership.js
            hubStatus: HUB_STATUS.UNKNOWN,
            // The authToken hubStatus was resolved for. A different current
            // token (e.g. account switched in another tab) invalidates it.
            hubVerifiedToken: null,
        };
    },
    getters: {
        isHubMember: (state) => state.hubStatus === HUB_STATUS.MEMBER,
    },
    actions: {
        // ---- GWAS-Hub membership ----
        // Verifies the current token against the hub group (a second KPN
        // user-service group). Cached per session and per token: MEMBER/DENIED
        // are stable for the token they were resolved with, UNKNOWN/ERROR are
        // re-checked. This path never writes localStorage, so a hub 401 cannot
        // log the user out of GWAS-CE.
        async checkHubMembership({ force = false } = {}) {
            const token = localStorage.getItem("authToken");
            if (
                isHubCacheFresh({
                    status: this.hubStatus,
                    verifiedToken: this.hubVerifiedToken,
                    token,
                    force,
                })
            ) {
                return this.hubStatus;
            }
            const config = useRuntimeConfig();
            const group = config.public.gwasHubGroup;
            const verify = () =>
                $fetch(hubVerifyUrl(config.public.userServiceUrl, group), {
                    headers: { Authorization: `Bearer ${token}` },
                });
            const status = await resolveHubStatus({
                skipAuth: config.public.skipAuth,
                token,
                group,
                verify,
            });
            if (localStorage.getItem("authToken") !== token) {
                // The identity changed while the request was in flight (another
                // tab signed in/out). The answer belongs to the old token;
                // discard it and resolve for the current one instead.
                this.resetHubMembership();
                return this.checkHubMembership({ force: true });
            }
            this.hubStatus = status;
            this.hubVerifiedToken = token;
            return status;
        },
        resetHubMembership() {
            this.hubStatus = HUB_STATUS.UNKNOWN;
            this.hubVerifiedToken = null;
        },
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
                // Clear the token on a 401 (expired/malformed JWT) or 403
                // (token minted for a different group, or no longer a
                // member) -- retrying with the same token can never succeed.
                if (isVerifyRejection(error)) {
                    // If we were using default credentials, relogin automatically
                    const wasDefaultUser =
                        localStorage.getItem("isDefaultUser") === "true";

                    // Clear invalid token
                    localStorage.removeItem("authToken");
                    this.user = null;
                    this.resetHubMembership();

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
                    // A new identity must not inherit a cached hub answer
                    this.resetHubMembership();

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
            this.resetHubMembership();
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
        async startVariantSifter(dataset) {
            const { data } = await this.axios.post(
                `/api/variant-sifter/run/${encodeURIComponent(dataset)}`,
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
        // ---- credible sets attached to a GWAS ----
        async validateCredibleSet(formData) {
            const { data } = await this.axios.post(
                "/api/validate-credible-set",
                formData,
                { headers: { "Content-Type": "multipart/form-data" } },
            );
            return data;
        },
        async uploadCredibleSet(dataset, formData) {
            const { data } = await this.axios.post(
                `/api/credible-sets/${encodeURIComponent(dataset)}`,
                formData,
                { headers: { "Content-Type": "multipart/form-data" } },
            );
            return data;
        },
        async listCredibleSets(dataset) {
            const { data } = await this.axios.get(
                `/api/credible-sets/${encodeURIComponent(dataset)}`,
            );
            return data;
        },
        async deleteCredibleSet(dataset, slug) {
            const { data } = await this.axios.delete(
                `/api/credible-sets/${encodeURIComponent(dataset)}/${encodeURIComponent(slug)}`,
            );
            return data;
        },
        async downloadCredibleSet(dataset, slug) {
            const { data } = await this.axios.get(
                `/api/credible-sets/${encodeURIComponent(dataset)}/${encodeURIComponent(slug)}/download`,
            );
            // Same trick as downloadBedFile: a real anchor so the browser
            // follows the presigned URL itself (no CORS, no blob).
            const link = document.createElement("a");
            link.href = data.url;
            link.setAttribute("download", data.filename);
            link.target = "_blank";
            document.body.appendChild(link);
            link.click();
            link.remove();
        },
        async reindexCredibleSets(dataset) {
            const { data } = await this.axios.post(
                `/api/credible-sets/${encodeURIComponent(dataset)}/reindex`,
            );
            return data;
        },
        async getFalconResultUrls(dataset) {
            // Returns: { files: { [name]: { url, etag, size } } }
            const { data } = await this.axios.get(
                `/api/falcon/${encodeURIComponent(dataset)}/result-urls`,
            );
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
