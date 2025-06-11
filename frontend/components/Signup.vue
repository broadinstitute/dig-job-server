<script setup>
import { useToast } from "primevue/usetoast";

const toast = useToast();
import { useTheme } from "~/composables/useTheme";

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
    await $fetch('https://users.kpndataregistry.org/api/auth/create-user/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: {
        token: '47c5488c-1660-4133-8700-23c14e942788', // Your application token
        username: username.value,
        password: password.value,
        email: email.value
      }
    });

    // Automatically log in the user after successful signup
    const loginResponse = await $fetch(`${config.public.userServiceUrl}/api/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: {
        username: username.value,
        password: password.value,
        group: config.public.userGroup
      }
    });

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
        action: 'signup',
        client: 'gwas-ce',
        group: config.public.userGroup,
        redirect_uri: config.public.finalRedirectUri,
        token: config.public.userServiceToken
      });

      const githubAuthUrl = `https://github.com/login/oauth/authorize?` +
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
                <form id="signup-form" class="p-8">
                    <h2 class="text-center text-2xl font-bold text-surface-900 dark:text-surface-0 mb-6">Create Account</h2>
                    
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
                            required
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
                            :feedback="false"
                            autocomplete="new-password"
                            :inputProps="{ autocomplete: 'new-password' }"
                            required
                        ></Password>
                    </div>

                    <div class="field">
                        <label
                            for="confirmPassword"
                            class="block text-surface-900 dark:text-surface-0 font-medium text-l mb-2"
                            >Confirm Password</label
                        >
                        <Password
                            id="confirmPassword"
                            type="password"
                            v-model="confirmPassword"
                            placeholder="Confirm password"
                            :toggleMask="true"
                            class="w-full"
                            inputClass="w-full"
                            :inputStyle="{ padding: '1rem' }"
                            @keydown.enter="submitForm()"
                            :feedback="false"
                            autocomplete="new-password"
                            :inputProps="{ autocomplete: 'new-password' }"
                            required
                        ></Password>
                    </div>

                    <Button
                        label="Create Account"
                        class="w-full p-4 text-xl mt-4"
                        icon="bi-person-plus"
                        @click="submitForm()"
                    ></Button>

                    <div class="text-center my-4">
                        <span class="text-surface-600 dark:text-surface-300">or</span>
                    </div>

                    <Button
                        label="Sign up with GitHub"
                        class="w-full p-4 text-xl"
                        icon="pi pi-github"
                        severity="secondary"
                        @click="signupWithGitHub()"
                    ></Button>

                    <div class="text-center mt-6">
                        <span class="text-surface-600 dark:text-surface-300">Already have an account? </span>
                        <NuxtLink to="/login" class="text-primary-500 hover:text-primary-400">Sign in</NuxtLink>
                    </div>
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
