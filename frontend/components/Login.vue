<script setup>
const toast = useToast();
import { useUserStore } from "~/stores/UserStore";

const username = ref("");
const password = ref("");

const route = useRoute();
const userStore = useUserStore();
const config = useRuntimeConfig();
const { isDarkMode, toggleDarkMode } = useTheme();

const submitForm = async () => {
    try {
        // Clear the default user flag when explicitly logging in
        localStorage.removeItem("isDefaultUser");

        await userStore.login(username.value, password.value, false);
        await userStore.isUserLoggedIn();
        const defaultUrl = "/";
        navigateTo(route.query.redirect ? route.query.redirect : defaultUrl);
    } catch (error) {
        console.log(error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail:
                userStore.loginError ||
                error.response?.data?.detail ||
                error.message,
            life: 5000,
        });
    }
};

const loginWithGitHub = async () => {
    try {
        const state = JSON.stringify({
            action: "login",
            client: "gwas-ce",
            group: config.public.userGroup,
            redirect_uri: config.public.finalRedirectUri,
            token: config.public.userServiceToken,
        });

        const githubAuthUrl =
            `https://github.com/login/oauth/authorize?` +
            `client_id=${config.public.githubAuthClientId}&` +
            `redirect_uri=${encodeURIComponent(config.public.githubAuthRedirectUri)}&` +
            `scope=user:email&` +
            `state=${encodeURIComponent(state)}`;
        window.location.href = githubAuthUrl;
    } catch (error) {
        console.log(error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Failed to initiate GitHub login",
            life: 3000,
        });
    }
};

onMounted(async () => {
    // If we're coming from the login button click, we should clear the default user state
    if (userStore.isDefaultUser) {
        // Clear default user data so we don't auto-login again
        localStorage.removeItem("isDefaultUser");
        localStorage.removeItem("authToken");
        userStore.isDefaultUser = false;
        userStore.user = null;
    } else {
        // Normal flow - check if user is already logged in
        const isLoggedIn = await userStore.isUserLoggedIn();

        // If logged in with personal account, redirect to homepage
        if (isLoggedIn && !userStore.isDefaultUser) {
            navigateTo("/");
            return;
        }

        // If they're logged in with default account (should not happen now),
        // let them login with their own credentials
    }

    // Focus username field for better UX
    document.getElementById("username").focus();
    if (userStore.loginError) {
        toast.add({
            severity: "error",
            summary: "Error",
            detail: userStore.loginError,
            life: 3000,
        });
        userStore.loginError = null;
    }
});
</script>

<template>
    <div
        class="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900"
    >
        <Card class="w-full max-w-md shadow-2xl">
            <template #header>
                <div class="text-center pt-8 pb-4">
                    <img
                        src="/images/gwas_ce_logo.png"
                        alt="GWAS Analysis Platform"
                        class="max-w-[200px] w-full h-auto mx-auto"
                    />
                    <h2
                        class="text-2xl font-bold mt-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent dark:from-blue-400 dark:to-purple-400"
                    >
                        Welcome Back
                    </h2>
                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        Sign in to continue to your workspace
                    </p>
                </div>
            </template>

            <template #content>
                <form @submit.prevent="submitForm" class="space-y-5">
                    <div class="flex flex-col gap-2">
                        <label
                            for="username"
                            class="text-sm font-medium text-gray-700 dark:text-gray-300"
                        >
                            Username
                        </label>
                        <InputText
                            id="username"
                            v-model="username"
                            type="text"
                            placeholder="Enter your username"
                            class="w-full"
                            autocomplete="username"
                            autofocus
                        />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label
                            for="password"
                            class="text-sm font-medium text-gray-700 dark:text-gray-300"
                        >
                            Password
                        </label>
                        <Password
                            id="password"
                            v-model="password"
                            placeholder="Enter your password"
                            :toggleMask="true"
                            class="w-full"
                            inputClass="w-full"
                            :feedback="false"
                            autocomplete="current-password"
                            :inputProps="{ autocomplete: 'current-password' }"
                            @keydown.enter="submitForm"
                        />
                    </div>

                    <Button
                        type="submit"
                        label="Sign In"
                        icon="pi pi-sign-in"
                        class="w-full justify-center"
                        size="large"
                    />

                    <div class="relative">
                        <div class="absolute inset-0 flex items-center">
                            <div
                                class="w-full border-t border-gray-300 dark:border-gray-600"
                            ></div>
                        </div>
                        <div class="relative flex justify-center text-sm">
                            <span
                                class="px-2 bg-white dark:bg-surface-900 text-gray-500 dark:text-gray-400"
                            >
                                Or continue with
                            </span>
                        </div>
                    </div>

                    <Button
                        type="button"
                        label="Sign in with GitHub"
                        icon="pi pi-github"
                        class="w-full justify-center"
                        severity="secondary"
                        size="large"
                        outlined
                        @click="loginWithGitHub"
                    />
                </form>
            </template>

            <template #footer>
                <div
                    class="flex flex-col items-center gap-4 pt-4 border-t border-gray-200 dark:border-gray-700"
                >
                    <div class="text-sm text-center">
                        <span class="text-gray-600 dark:text-gray-400"
                            >Don't have an account?
                        </span>
                        <NuxtLink
                            to="/signup"
                            class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
                        >
                            Sign up
                        </NuxtLink>
                    </div>

                    <Button
                        :icon="isDarkMode ? 'pi pi-sun' : 'pi pi-moon'"
                        :label="isDarkMode ? 'Light Mode' : 'Dark Mode'"
                        class="p-button-text p-button-sm"
                        @click="toggleDarkMode"
                        v-tooltip.top="
                            isDarkMode
                                ? 'Switch to light mode'
                                : 'Switch to dark mode'
                        "
                        text
                    />
                </div>
            </template>
        </Card>

        <Toast position="top-center" />
    </div>
</template>

<style scoped>
/* Minimal custom styles - using PrimeVue and Tailwind */
</style>
