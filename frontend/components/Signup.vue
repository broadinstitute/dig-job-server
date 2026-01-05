<script setup>
const toast = useToast();

const username = ref("");
const password = ref("");
const confirmPassword = ref("");
const email = ref("");

const route = useRoute();
const config = useRuntimeConfig();
const { isDarkMode, toggleDarkMode } = useTheme();

const submitForm = async () => {
    if (password.value !== confirmPassword.value) {
        toast.add({
            severity: "error",
            summary: "Error",
            detail: "Passwords do not match",
            life: 3000,
        });
        return;
    }

    try {
        // Call your user service to create account
        await $fetch(
            "https://users.kpndataregistry.org/api/auth/create-user/",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: {
                    token: "47c5488c-1660-4133-8700-23c14e942788", // Your application token
                    username: username.value,
                    password: password.value,
                    email: email.value,
                },
            },
        );

        // Automatically log in the user after successful signup
        const loginResponse = await $fetch(
            `${config.public.userServiceUrl}/api/auth/login/`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: {
                    username: username.value,
                    password: password.value,
                    group: config.public.userGroup,
                },
            },
        );

        if (loginResponse && loginResponse.access) {
            localStorage.setItem("authToken", loginResponse.access);
            localStorage.removeItem("isDefaultUser");

            toast.add({
                severity: "success",
                summary: "Success",
                detail: "Account created and logged in successfully!",
                life: 3000,
            });

            // Redirect to home page after successful signup and login
            setTimeout(() => {
                navigateTo("/");
            }, 2000);
        } else {
            toast.add({
                severity: "success",
                summary: "Success",
                detail: "Account created successfully! Please log in.",
                life: 3000,
            });

            // Redirect to login page if auto-login failed
            setTimeout(() => {
                navigateTo("/login");
            }, 2000);
        }
    } catch (error) {
        console.log(error);

        // Handle specific error messages from the user service
        let errorMessage = "Failed to create account";

        if (error.data?.error) {
            errorMessage = error.data.error;
        } else if (error.message) {
            errorMessage = error.message;
        }

        toast.add({
            severity: "error",
            summary: "Error",
            detail: errorMessage,
            life: 3000,
        });
    }
};

const signupWithGitHub = async () => {
    try {
        const state = JSON.stringify({
            action: "signup",
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
            detail: "Failed to initiate GitHub signup",
            life: 3000,
        });
    }
};

onMounted(() => {
    // Focus username field for better UX
    document.getElementById("username").focus();
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
                        Create Account
                    </h2>
                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-2">
                        Join the platform to start analyzing your data
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
                            placeholder="Choose a username"
                            class="w-full"
                            autocomplete="username"
                            autofocus
                            required
                        />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label
                            for="email"
                            class="text-sm font-medium text-gray-700 dark:text-gray-300"
                        >
                            Email
                        </label>
                        <InputText
                            id="email"
                            v-model="email"
                            type="email"
                            placeholder="Enter your email"
                            class="w-full"
                            autocomplete="email"
                            required
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
                            placeholder="Create a password"
                            :toggleMask="true"
                            class="w-full"
                            inputClass="w-full"
                            :feedback="true"
                            autocomplete="new-password"
                            :inputProps="{ autocomplete: 'new-password' }"
                            required
                        />
                    </div>

                    <div class="flex flex-col gap-2">
                        <label
                            for="confirmPassword"
                            class="text-sm font-medium text-gray-700 dark:text-gray-300"
                        >
                            Confirm Password
                        </label>
                        <Password
                            id="confirmPassword"
                            v-model="confirmPassword"
                            placeholder="Confirm your password"
                            :toggleMask="true"
                            class="w-full"
                            inputClass="w-full"
                            :feedback="false"
                            autocomplete="new-password"
                            :inputProps="{ autocomplete: 'new-password' }"
                            @keydown.enter="submitForm"
                            required
                        />
                    </div>

                    <Button
                        type="submit"
                        label="Create Account"
                        icon="pi pi-user-plus"
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
                                Or sign up with
                            </span>
                        </div>
                    </div>

                    <Button
                        type="button"
                        label="Sign up with GitHub"
                        icon="pi pi-github"
                        class="w-full justify-center"
                        severity="secondary"
                        size="large"
                        outlined
                        @click="signupWithGitHub"
                    />
                </form>
            </template>

            <template #footer>
                <div
                    class="flex flex-col items-center gap-4 pt-4 border-t border-gray-200 dark:border-gray-700"
                >
                    <div class="text-sm text-center">
                        <span class="text-gray-600 dark:text-gray-400"
                            >Already have an account?
                        </span>
                        <NuxtLink
                            to="/login"
                            class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
                        >
                            Sign in
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
