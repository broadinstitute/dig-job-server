<template>
    <div class="auth-controls">
        <Button
            icon="pi pi-file"
            label="Datasets"
            class="p-button-text"
            size="small"
            as="a"
            href="/datasets"
        />
        <Button
            v-if="!isLoggedIn"
            icon="pi pi-user"
            label="Login"
            class="p-button-text"
            size="small"
            as="a"
            href="/login"
        />
        <Button
            v-else
            icon="pi pi-sign-out"
            label="Sign out"
            class="p-button-text"
            @click="signOut"
            size="small"
        />
    </div>
</template>

<script setup>
// Header-right controls shared by every layout (default and gwas-hub).
import { useUserStore } from "~/stores/UserStore";

const userStore = useUserStore();
const isLoggedIn = ref(false);

onMounted(async () => {
    // Initialize userStore to check isDefaultUser status
    userStore.init();
    isLoggedIn.value = await userStore.isUserLoggedIn();
});

function signOut() {
    // logout() clears authToken / isDefaultUser and any cached GWAS-Hub
    // membership. hasSignedOut stops tryDefaultLogin() from re-creating an
    // anonymous session on the next page load.
    userStore.logout();
    localStorage.setItem("hasSignedOut", "true");
    window.location.href = "/";
}
</script>

<style scoped>
.auth-controls {
    flex: 0 0 auto;
}
</style>
