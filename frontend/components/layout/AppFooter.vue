<template>
    <div class="layout-footer">
        <span
            >GWAS Collaborative Environment&nbsp;&nbsp;|&nbsp;&nbsp;Powered by
            the HuGeAMP</span
        >
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
</template>

<script setup>
const { isDarkMode, toggleDarkMode } = useTheme();
</script>

<style scoped>
.layout-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem 0 1rem 0;
    gap: 0.5rem;
    border-top: 1px solid var(--p-content-border-color);
    font-size: small;
}

.theme-toggle-btn.sun-icon :deep(.pi-sun) {
    color: #ffd700;
}

/* Light theme: coral banner matching the header (GWAS-CE guide). */
html:not(.dark) .layout-footer {
    background-color: var(--gwas-theme);
    border-top: none;
    padding: 0.5rem 0;
    color: #fff;
    font-size: 14px;
}

html:not(.dark) .theme-toggle-btn {
    color: #fff;
}

html:not(.dark) .theme-toggle-btn:hover {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
}
</style>
