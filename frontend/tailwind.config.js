/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["selector", '[class*="dark"]'],
    content: [
        "./components/**/*.{js,vue,ts}",
        "./layouts/**/*.vue",
        "./pages/**/*.vue",
        "./plugins/**/*.{js,ts}",
        "./nuxt.config.{js,ts}",
        "./app.vue",
    ],
    plugins: [require("tailwindcss-primeui")],
};
