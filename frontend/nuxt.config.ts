// https://nuxt.com/docs/api/configuration/nuxt-config
import Lara from "@primeuix/themes/lara";
import { definePreset } from "@primeuix/themes";
export default defineNuxtConfig({
    compatibilityDate: "2024-04-03",
    devtools: { enabled: true },
    ssr: false,
    css: ["primeflex/primeflex.scss", "primeicons/primeicons.css"],
    modules: [
        "@pinia/nuxt",
        "@nuxt/devtools",
        "@primevue/nuxt-module",
        "nuxt-shiki",
    ],
    app: {
        buildAssetsDir: `/_nuxt/${Date.now()}/`,
    },
    primevue: {
        options: {
            ripple: true,
            theme: {
                preset: definePreset(Lara, {
                    semantic: {
                        primary: {
                            50: "{stone.50}",
                            100: "{stone.100}",
                            200: "{stone.200}",
                            300: "{stone.300}",
                            400: "{stone.400}",
                            500: "{stone.500}",
                            600: "{stone.600}",
                            700: "{stone.700}",
                            800: "{stone.800}",
                            900: "{stone.900}",
                            950: "{stone.950}",
                        },
                    },
                }),
                options: {
                    // darkModeSelector: false
                },
            },
        },
    },

    runtimeConfig: {
        public: {
            apiBaseUrl: "",
            skipAuth: false,
        },
    },
    shiki: {
        bundledLangs: ["python", "log"],
    },
});