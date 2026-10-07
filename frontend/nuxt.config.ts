// https://nuxt.com/docs/api/configuration/nuxt-config
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";
import { rollup as unwasm } from "unwasm/plugin";
// GWAS-CE coral palette, taken from the portal banner (#f7835c).
const GwasCeAura = definePreset(Aura, {
    semantic: {
        primary: {
            50: "#fff4ef",
            100: "#ffe8df",
            200: "#fecfbd",
            300: "#fcb094",
            400: "#fa9674",
            500: "#f7835c",
            600: "#dc4c34",
            700: "#b83d29",
            800: "#953325",
            900: "#782d22",
            950: "#41150f",
        },
        colorScheme: {
            light: {
                primary: {
                    color: "{primary.600}",
                    contrastColor: "#ffffff",
                    hoverColor: "{primary.700}",
                    activeColor: "{primary.800}",
                },
                highlight: {
                    background: "{primary.100}",
                    focusBackground: "{primary.200}",
                    color: "#2c2422",
                    focusColor: "#2c2422",
                },
                surface: {
                    0: "#ffffff",
                    50: "#f4f1ee",
                    100: "#ece6e1",
                    200: "#e4ddd8",
                    300: "#cfc6c0",
                    400: "#9a918c",
                    500: "#636466",
                    600: "#554d4a",
                    700: "#443b38",
                    800: "#2c2422",
                    900: "#211b19",
                    950: "#171211",
                },
            },
        },
    },
});
export default defineNuxtConfig({
    compatibilityDate: "2024-04-03",
    devtools: { enabled: process.env.NUXT_DEVTOOLS === "true" },
    ssr: false,
    experimental: {
        // Every deploy wipes the previous /_nuxt/<Date.now()>/ build dir, so a
        // tab opened before it 404s on the first page chunk it lazy-loads. The
        // default ("automatic") only reloads when a JS chunk fails; Nuxt
        // swallows a failed CSS chunk, so the page rendered unstyled (e.g. the
        // upload progress overlay fell to the bottom of the page). Reload on
        // any chunk error instead. reloadNuxtApp's 10 s guard prevents loops.
        emitRouteChunkError: "automatic-immediate",
    },
    components: [
        {
            path: "~/components",
            pathPrefix: false,
        },
    ],
    css: [
        "primeicons/primeicons.css",
        "~/assets/css/tailwind.css",
        "~/assets/css/shiki.css",
        "~/assets/css/global.css",
    ],
    modules: [
        "@pinia/nuxt",
        "@primevue/nuxt-module",
        "nuxt-shiki",
    ],

    app: {
        buildAssetsDir: `/_nuxt/${Date.now()}/`,
        head: {
            htmlAttrs: {
                lang: "en",
            },
            title: "GWAS-CE",
        },
    },
    primevue: {
        options: {
            ripple: true,
            theme: {
                preset: GwasCeAura,
                options: {
                    darkModeSelector: ".dark",
                    cssLayer: {
                        name: "primevue",
                        order: "theme, base, primevue, components, utilities",
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
            phenotypesUrl: process.env.NUXT_PUBLIC_PHENOTYPES_URL || "",
            // Portal Variant Sifter page. The dataset id is passed as a `token`
            // query parameter (utils/sifter/portalSifterLink.js). Empty hides
            // the datasets-page button.
            portalSifterUrl: process.env.NUXT_PUBLIC_PORTAL_SIFTER_URL || "",
            // GWAS-Hub is gated by a role on the gwas-ce user, read from the
            // roles/permissions in the verify response
            // (utils/auth/hubMembership.js). Empty means nobody is a member.
            gwasHubRole: process.env.NUXT_PUBLIC_GWAS_HUB_ROLE || "gwas-hub-user",
            // mailto target for the hub "Contact admin" button
            gwasHubContactEmail:
                process.env.NUXT_PUBLIC_GWAS_HUB_CONTACT_EMAIL || "",
            defaultUsername: process.env.NUXT_PUBLIC_DEFAULT_USERNAME || "",
            defaultPassword: process.env.NUXT_PUBLIC_DEFAULT_PASSWORD || "",
            enableDefaultLogin:
                process.env.NUXT_PUBLIC_ENABLE_DEFAULT_LOGIN === "true",
            githubAuthClientId: "",
            githubAuthRedirectUri: "",
            userServiceUrl: "",
            userGroup: "",
            userServiceToken: "",
            finalRedirectUri: "",
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

    nitro: {
        experimental: {
            // fix #29 inject onig.wasm warning
            wasm: true,
        },
        // fix #45 cannot find module core.mjs
        externals: { traceInclude: ["shiki/dist/core.mjs"] },
    },
    vite: {
        // fix #41 [vite:wasm-fallback] Could not load
        plugins:
            import.meta.env.NODE_ENV === "production"
                ? [unwasm({})]
                : undefined,
    },
});
