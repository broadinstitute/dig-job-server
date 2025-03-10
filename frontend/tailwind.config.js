module.exports = {
    darkMode: ["selector", '[class*="app-dark"]'],
    content: [
        "./pages/**/*.{vue,js}",
        "./components/**/*.{vue,js}",
        "./layouts/**/*.{vue,js}",
    ],
    plugins: [require("tailwindcss-primeui")],
};
