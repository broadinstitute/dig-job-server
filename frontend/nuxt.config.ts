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
    css: [
        "primeicons/primeicons.css",
        "~/assets/css/tailwind.css",
        "~/assets/css/shiki.css",
    ],
    modules: [
        "@pinia/nuxt",
        "@nuxt/devtools",
        "@primevue/nuxt-module",
        "nuxt-shiki",
        //"@nuxtjs/tailwindcss", //not yet compatible with tailwind 4
    ],

    app: {
        buildAssetsDir: `/_nuxt/${Date.now()}/`,
        head: {
            htmlAttrs: {
                lang: "en",
            },
        },
    },
    primevue: {
        options: {
            ripple: true,
            theme: {
                preset: IndigoAura,
                options: {
                    darkModeSelector: "html.dark",
                    cssLayer: {
                        name: "primevue",
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
        bundledThemes: ["min-light", "min-dark"],
        defaultTheme: {
            light: "min-light",
            dark: "min-dark",
        },
    },

    postcss: {
        plugins: {
            "@tailwindcss/postcss": {},
            autoprefixer: {},
        },
    },
});
