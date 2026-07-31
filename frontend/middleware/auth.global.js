import { useUserStore } from "~/stores/UserStore";
import {
    captureOAuthCallback,
    stripOAuthParams,
} from "~/utils/auth/captureOAuthCallback";
// so annoying https://github.com/nuxt/nuxt/issues/14269
// Fixed now! https://github.com/unjs/unctx/pull/28
export default defineNuxtRouteMiddleware(async (to) => {
    const config = useRuntimeConfig();
    if (config.public.skipAuth) {
        return;
    }

    // The OAuth callback returns to NUXT_PUBLIC_FINAL_REDIRECT_URI, which is the
    // site root -- a public route. This MUST stay above the publicRoutes
    // early-return below, or the token is dropped and GitHub sign-in silently
    // does nothing. See utils/auth/captureOAuthCallback.js for the full story.
    if (captureOAuthCallback(to.query, localStorage)) {
        return navigateTo(
            { path: to.path, query: stripOAuthParams(to.query) },
            { replace: true },
        );
    }

    // Public routes that don't require authentication
    const publicRoutes = ["/", "/login", "/signup"];
    if (publicRoutes.includes(to.path)) {
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
