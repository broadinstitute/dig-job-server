<template>
    <div class="layout-header">
        <div class="header-container">
            <div class="brand-and-nav">
                <div class="logo-container">
                    <slot name="brand">
                        <a href="/datasets">
                            <img
                                src="/images/gwas_ce_logo_header.png"
                                alt="GWAS-CE"
                                class="logo-image"
                            />
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

.logo-image {
    max-width: 300px;
    max-height: 50px;
    width: auto;
    height: auto;
}
</style>
