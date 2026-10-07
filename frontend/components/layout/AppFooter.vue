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
    padding: 0.5rem 0;
    gap: 0.5rem;
    border-top: 1px solid var(--p-content-border-color);
    font-size: 14px;
}

.theme-toggle-btn.sun-icon :deep(.pi-sun) {
    color: #ffd700;
}

/* Light theme: coral banner matching the header (GWAS-CE guide). Only colors
   change between themes; size and spacing come from .layout-footer. */
html:not(.dark) .layout-footer {
    background-color: var(--gwas-theme);
    border-top: none;
    color: #fff;
}

html:not(.dark) .theme-toggle-btn {
    color: #fff;
}

html:not(.dark) .theme-toggle-btn:hover {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
}
</style>
