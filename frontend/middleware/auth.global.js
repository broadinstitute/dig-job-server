import { useUserStore } from "~/stores/UserStore";
import { callWithNuxt } from "#app";

// so annoying https://github.com/nuxt/nuxt/issues/14269
export default defineNuxtRouteMiddleware(async (to) => {
    const config = useRuntimeConfig();
    if (config.public.skipAuth) {
        return;
    }
    const nuxtApp = useNuxtApp();
    if(to.path.startsWith('/login')){
        return;
    }
    const userStore = useUserStore();
    const isLoggedIn = await userStore.isUserLoggedIn();


    if (userStore.user) {
        return;
    }

    if (!isLoggedIn) {

        return callWithNuxt(nuxtApp, navigateTo, ['/login?redirect=' + to.path]);
    }
});
