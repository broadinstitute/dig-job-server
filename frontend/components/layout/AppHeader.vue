<template>
    <div class="layout-header">
        <div class="header-container">
            <div class="brand-and-nav">
                <div class="logo-container">
                    <slot name="brand">
                        <a href="/datasets" class="portal-mark">
                            <GwasCeLogo class="logo-image" />
                        </a>
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
// slot content (GWAS-CE logo); the gwas-hub layout supplies its own brand
// and a tab bar through the #brand and #nav slots.
</script>

<style scoped>
.layout-header {
    width: 100%;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--p-content-border-color);
    margin-bottom: 1rem;
    background-color: var(--p-content-background);
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.12),
        0 1px 2px rgba(0, 0, 0, 0.24);
}

.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.brand-and-nav {
    display: flex;
    align-items: center;
    gap: 1.5rem;
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

html:not(.dark) .logo-image {
    color: #fff;
}

/* Light theme: coral banner (GWAS-CE guide). Dark theme keeps the
   surface-colored header above. */
html:not(.dark) .layout-header {
    background-color: var(--gwas-theme);
    border-bottom: 1px solid var(--gwas-plum);
    box-shadow: none;
    padding: 0;
    margin-bottom: 0;
}

html:not(.dark) .header-container {
    gap: 0;
}

html:not(.dark) .brand-and-nav {
    gap: 1rem;
}

.portal-mark {
    display: inline-flex;
    align-items: center;
    line-height: 0;
}

html:not(.dark) .portal-mark {
    margin-left: 15px;
    padding: 5px 0;
}

/* Header buttons (auth controls and hub tabs): white text on the banner,
   gold dividers between items. */
html:not(.dark) .layout-header :deep(.p-button) {
    color: #fff;
    font-weight: 500;
    border-radius: 0;
}

html:not(.dark) .layout-header :deep(.p-button:not(:disabled):hover) {
    background: rgba(255, 255, 255, 0.18);
    color: #fff;
}

html:not(.dark) .layout-header :deep(.auth-controls .p-button + .p-button) {
    border-left: 1px solid var(--gwas-gold);
}

html:not(.dark) .layout-header :deep(.auth-controls) {
    margin-right: 15px;
}

html:not(.dark) .layout-header :deep(.p-button:disabled) {
    color: rgba(255, 255, 255, 0.7);
    opacity: 1;
}
</style>
