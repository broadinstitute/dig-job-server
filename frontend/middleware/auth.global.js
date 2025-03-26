import { useUserStore } from "~/stores/UserStore";
// so annoying https://github.com/nuxt/nuxt/issues/14269
// Fixed now! https://github.com/unjs/unctx/pull/28
export default defineNuxtRouteMiddleware(async (to) => {
    const config = useRuntimeConfig();
    if (config.public.skipAuth) {
        return;
    }

    if (to.path.startsWith("/login")) {
        return;
    }
    const userStore = useUserStore();
    const isLoggedIn = await userStore.isUserLoggedIn();

    if (userStore.user) {
        return;
    }

    if (!isLoggedIn) {
        return navigateTo("/login?redirect=" + to.path);
    }
});
