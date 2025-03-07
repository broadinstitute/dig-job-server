<script setup>
import { useToast } from "primevue/usetoast";

const toast = useToast();
import { useUserStore } from "~/stores/UserStore";
const username = ref("");
const password = ref("");

const route = useRoute();
const userStore = useUserStore();

const submitForm = async () => {
    try {
        await userStore.login(username.value, password.value);
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

onMounted(() => {
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
        class="flex align-items-center justify-content-center min-h-screen min-w-screen overflow-hidden"
    >
        <div class="flex flex-column align-items-center justify-content-center">
            <div class="w-full surface-card">
                <div class="text-center">
                    <img src="/images/logo.png" alt="Logo" />
                </div>
                <form id="login-form" class="p-5">
                    <div class="field">
                        <label
                            for="username"
                            class="block text-900 text-l font-medium mb-2"
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
                            class="block text-900 font-medium text-l mb-2"
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
                        class="w-full p-3 text-xl mt-3"
                        icon="bi-person"
                        @click="submitForm()"
                    ></Button>
                </form>
            </div>
        </div>
    </div>
    <Toast position="top-center" />
</template>

<style scoped>
label {
    white-space: nowrap;
}
</style>
