<script setup>
import { useToast } from "primevue/usetoast";

const toast = useToast();
import { useUserStore } from "~/stores/UserStore";
import { useTheme } from "~/composables/useTheme";

const username = ref("");
const password = ref("");

const route = useRoute();
const userStore = useUserStore();
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
            detail: error.response?.data?.detail || error.message,
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
        class="flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden"
    >
        <div class="flex flex-col items-center justify-center">
            <div class="w-full bg-surface-0 dark:bg-surface-900">
                <div class="text-center mb-4">
                    <img 
                        src="/images/gwas-ce-logo.png" 
                        alt="Logo" 
                        class="max-w-xs w-full h-auto"
                    />
                </div>
                <form id="login-form" class="p-8">
                    <div class="field">
                        <label
                            for="username"
                            class="block text-surface-900 dark:text-surface-0 text-l font-medium mb-2"
                            >Username</label
                        >
                        <InputText
                            id="username"
                            autofocus
                            v-model="username"
                            type="text"
                            placeholder="Enter username"
                            class="w-full"
                            style="padding: 1rem"
                            autocomplete="username"
                        />
                    </div>
                    <div class="field">
                        <label
                            for="password"
                            class="block text-surface-900 dark:text-surface-0 font-medium text-l mb-2"
                            >Password</label
                        >
                        <Password
                            id="password"
                            type="password"
                            v-model="password"
                            placeholder="Enter password"
                            :toggleMask="true"
                            class="w-full"
                            inputClass="w-full"
                            :inputStyle="{ padding: '1rem' }"
                            @keydown.enter="submitForm()"
                            :feedback="false"
                            autocomplete="current-password"
                            :inputProps="{ autocomplete: 'current-password' }"
                        ></Password>
                    </div>

                    <Button
                        label="Sign In"
                        class="w-full p-4 text-xl mt-4"
                        icon="bi-person"
                        @click="submitForm()"
                    ></Button>
                </form>
                <div class="flex justify-center mb-4">
                    <Button
                        :icon="isDarkMode ? 'pi pi-sun' : 'pi pi-moon'"
                        :aria-label="isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'"
                        class="p-button-rounded p-button-text theme-toggle-btn mt-4"
                        :class="{ 'sun-icon': isDarkMode }"
                        @click="toggleDarkMode"
                        v-tooltip.top="isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'"
                        size="small"
                    />
                </div>
            </div>
        </div>
    </div>
    <Toast position="top-center" />
</template>

<style scoped>
label {
    white-space: nowrap;
}

.theme-toggle-btn.sun-icon :deep(.pi-sun) {
    color: #ffd700;
}
</style>
