export const useTheme = () => {
    // Check if we're in browser environment
    const isDarkMode = useState("darkMode", () => {
        if (typeof window !== "undefined") {
            // Check for saved preference or system preference
            const savedTheme = localStorage.getItem("theme");
            if (savedTheme) {
                return savedTheme === "dark";
            }
            return window.matchMedia("(prefers-color-scheme: dark)").matches;
        }
        return false;
    });

    function toggleDarkMode() {
        isDarkMode.value = !isDarkMode.value;
        updateTheme();
    }

    function updateTheme() {
        if (typeof window !== "undefined") {
            if (isDarkMode.value) {
                document.documentElement.classList.add("dark");
                localStorage.setItem("theme", "dark");
            } else {
                document.documentElement.classList.remove("dark");
                localStorage.setItem("theme", "light");
            }
        }
    }

    // Initialize theme when composable is used
    onMounted(() => {
        updateTheme();
    });

    return {
        isDarkMode,
        toggleDarkMode,
    };
};
