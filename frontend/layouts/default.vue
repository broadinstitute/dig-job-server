<template>
    <div id="app">
        <div class="layout-header">
            <div class="header-container">
                <div class="logo-container">
                    <a href="/">
                        <img
                            src="https://kpndataregistry.org/tenants/default/dr-logo.png"
                            alt="Logo"
                            class="logo-image"
                        />
                    </a>
                </div>
                <div class="auth-controls">
                    <Button
                        icon="pi pi-file"
                        label="Datasets"
                        class="p-button-text"
                        size="small"
                        as="a"
                        href="/"
                    />
                    <Button
                        icon="pi pi-sign-out"
                        label="Sign out"
                        class="p-button-text"
                        @click="signOut"
                        size="small"
                    />
                </div>
            </div>
        </div>

        <slot />

        <div class="layout-footer">
            <span> Powered by KPN Data Registry </span>
            <Button
                :icon="isDarkMode ? 'pi pi-sun' : 'pi pi-moon'"
                :aria-label="
                    isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'
                "
                class="p-button-rounded p-button-text theme-toggle-btn"
                :class="{ 'sun-icon': isDarkMode }"
                @click="toggleDarkMode"
                v-tooltip.top="
                    isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'
                "
                size="small"
            />
        </div>
    </div>
</template>
<style scoped>
#app {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: var(--surface-background);
    color: var(--text-primary);
}
.layout-header {
    width: 100%;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--surface-border);
    margin-bottom: 1rem;
    background-color: var(--surface-elevation-1);
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.12),
        0 1px 2px rgba(0, 0, 0, 0.24);
}

.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo-container {
    flex: 0 0 auto;
}

.logo-image {
    max-width: 300px;
    max-height: 50px;
    width: auto;
    height: auto;
}

.auth-controls {
    flex: 0 0 auto;
}

.layout-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem 0 1rem 0;
    gap: 0.5rem;
    border-top: 1px solid var(--surface-border);
}

.theme-toggle-btn.sun-icon :deep(.pi-sun) {
    color: #ffd700;
}
</style>
<script setup>
import { useTheme } from "~/composables/useTheme";

const { isDarkMode, toggleDarkMode } = useTheme();

function signOut() {
    console.log("Signing out...");
    localStorage.removeItem("authToken");
    window.location.href = "/login";
}
</script>
