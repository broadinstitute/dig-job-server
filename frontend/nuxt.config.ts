// https://nuxt.com/docs/api/configuration/nuxt-config
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";
const IndigoAura = definePreset(Aura, {
    semantic: {
        primary: {
            50: "{indigo.50}",
            100: "{indigo.100}",
            200: "{indigo.200}",
            300: "{indigo.300}",
            400: "{indigo.400}",
            500: "{indigo.500}",
            600: "{indigo.600}",
            700: "{indigo.700}",
            800: "{indigo.800}",
            900: "{indigo.900}",
            950: "{indigo.950}",
        },
    },
});
export default defineNuxtConfig({
    compatibilityDate: "2024-04-03",
    devtools: { enabled: true },
    ssr: false,
    css: ["primeicons/primeicons.css"],
    modules: [
        "@pinia/nuxt",
        "@nuxt/devtools",
        "@primevue/nuxt-module",
        "nuxt-shiki",
        "@nuxtjs/tailwindcss",
    ],
    app: {
        buildAssetsDir: `/_nuxt/${Date.now()}/`,
    },
    primevue: {
        options: {
            ripple: true,
            theme: {
                preset: IndigoAura,
                options: {
                    darkModeSelector: ".app-dark",
                    cssLayer: {
                        name: "primevue",
                        //order: "tailwind-base, primevue, tailwind-utilities",
                        order: "theme, base, primevue",
                    },
                },
            },
        },
        autoImport: true,
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