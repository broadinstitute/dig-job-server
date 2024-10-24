// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },
  ssr: false,
  css: [
    "primeicons/primeicons.css",
    "primeflex/primeflex.scss",
    "primevue/resources/primevue.min.css",
    "primevue/resources/themes/aura-light-noir/theme.css",
  ],
  modules: [
    "@pinia/nuxt",
    "@nuxt/devtools",
    "nuxt-primevue",
  ],
  runtimeConfig: {
    public: {
      apiBaseUrl: "",
      skipAuth: false,
    },
  },
  build: {
    sourcemap: true,  // Ensure this is enabled
  },
  alias: {
    pinia: "/node_modules/@pinia/nuxt/node_modules/pinia/dist/pinia.mjs",
  },
})
