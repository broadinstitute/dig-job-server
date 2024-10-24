<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();
import { useUserStore } from "~/stores/UserStore";
const email = ref("");
const password = ref("");
const remember = ref(false);

const route = useRoute();
const config = useRuntimeConfig();
const userStore = useUserStore();

defineProps({
    tenantLogo: {
        type: String,
        required: true,
    },
    tenantWebsite: {
        type: String,
        required: true,
    },
});

const submitForm = async () => {
    try {
        await userStore.login(email.value, password.value);
        await userStore.isUserLoggedIn();
        const defaultUrl = "/upload";
        navigateTo(route.query.redirect ? route.query.redirect : defaultUrl);
    } catch (error) {
        console.log(error);
        toast.add({
            severity: "error",
            summary: "Error",
            detail: error.message,
            life: 3000,
        });
    }
};

onMounted(() => {
    document.getElementById("email").focus();
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
        class="surface-ground flex align-items-center justify-content-center min-h-screen min-w-screen overflow-hidden"
    >
        <div class="flex flex-column align-items-center justify-content-center">
            <div
                style="
                    border-radius: 56px;
                    padding: 0.3rem;
                    background: linear-gradient(
                        180deg,
                        var(--primary-color) 10%,
                        rgba(33, 150, 243, 0) 30%
                    );
                "
            >
                <div
                    class="w-full surface-card py-8 px-5 sm:px-8"
                    style="border-radius: 53px"
                >
                    <div class="text-center mb-5">
                        <template v-if="tenantWebsite !== '/'"
                            ><NuxtLink :to="tenantWebsite" target="_blank">
                                <img
                                    :src="tenantLogo"
                                    alt="logo"
                                    class="mb-5 flex-shrink-0"
                                    height="100"
                                />
                            </NuxtLink>
                        </template>
                        <template v-else>
                            <img
                                :src="tenantLogo"
                                alt="logo"
                                class="mb-5 flex-shrink-0"
                                height="100"
                            />
                        </template>
                    </div>
                    <div>
                        <label
                            for="email"
                            class="block text-900 text-xl font-medium mb-2"
                            >Email</label
                        >
                        <InputText
                            id="email"
                            autofocus
                            v-model="email"
                            type="text"
                            placeholder="Enter username or email"
                            class="w-full md:w-30rem mb-5"
                            style="padding: 1rem"
                        />

                        <label
                            for="password"
                            class="block text-900 font-medium text-xl mb-2"
                            >Password</label
                        >
                        <Password
                            id="password"
                            v-model="password"
                            placeholder="Enter password"
                            :toggleMask="true"
                            class="w-full mb-3"
                            inputClass="w-full"
                            :inputStyle="{ padding: '1rem' }"
                            @keydown.enter="submitForm()"
                            :feedback="false"
                        ></Password>

                        <div
                            class="flex align-items-center justify-content-between mb-5 gap-5"
                        >
                        </div>
                        <Button
                            label="Sign In"
                            class="w-full p-3 text-xl"
                            icon="bi-person"
                            @click="submitForm()"
                        ></Button>
                    </div>
                </div>
            </div>
        </div>
        <Toast position="top-center" />
    </div>
</template>

<style scoped>
label {
    white-space: nowrap;
}
</style>
