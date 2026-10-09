<template>
    <div class="layout-header">
        <div class="header-container">
            <div class="brand-and-nav">
                <div class="logo-container">
                    <slot name="brand">
                        <NuxtLink to="/" class="portal-mark">
                            <GwasCeLogo class="logo-image" />
                        </NuxtLink>
                    </slot>
                </div>
                <slot name="nav" />
            </div>
            <AuthControls />
        </div>
    </div>
</template>

<script setup>
// App header shared by every layout. The default layout uses the default
// slot content (GWAS-CE logo). A layout can override the brand and add a tab
// bar through the #brand and #nav slots.
</script>

<style scoped>
/* Layout is shared by both themes; only colors differ (light-theme overrides
   at the bottom). */
.layout-header {
    width: 100%;
    border-bottom: 1px solid var(--p-content-border-color);
    background-color: var(--p-content-background);
}

.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.brand-and-nav {
    display: flex;
    align-items: center;
    gap: 1rem;
    min-width: 0;
}

.logo-container {
    flex: 0 0 auto;
}

/* The logo SVG has only a viewBox (no intrinsic size), so it needs an
   explicit height or it collapses to 0x0 inside the shrink-to-fit wrapper.
   The wordmark uses currentColor. */
.logo-image {
    display: block;
    height: 46px;
    width: auto;
    max-width: 300px;
    color: var(--p-text-color);
}

.portal-mark {
    display: inline-flex;
    align-items: center;
    line-height: 0;
    margin-left: 15px;
    padding: 5px 0;
}

/* Header buttons (auth controls and hub tabs): square, with dividers between
   the auth controls. */
.layout-header :deep(.p-button) {
    font-weight: 500;
    border-radius: 0;
}

.layout-header :deep(.auth-controls) {
    margin-right: 15px;
}

.layout-header :deep(.auth-controls .p-button + .p-button) {
    border-left: 1px solid var(--p-content-border-color);
}

/* Light theme colors: coral banner, white logo text and buttons, gold
   dividers (GWAS-CE guide). */
html:not(.dark) .layout-header {
    background-color: var(--gwas-theme);
    border-bottom-color: var(--gwas-plum);
}

html:not(.dark) .logo-image {
    color: #fff;
}

html:not(.dark) .layout-header :deep(.p-button) {
    color: #fff;
}

html:not(.dark) .layout-header :deep(.p-button:not(:disabled):hover) {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
}

html:not(.dark) .layout-header :deep(.auth-controls .p-button + .p-button) {
    border-left-color: var(--gwas-gold);
}

html:not(.dark) .layout-header :deep(.p-button:disabled) {
    color: rgba(255, 255, 255, 0.7);
    opacity: 1;
}
</style>
