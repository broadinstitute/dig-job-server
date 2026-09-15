<template>
    <nav class="hub-nav" aria-label="GWAS-Hub sections">
        <!--
            A disabled <button> swallows pointer events, so the tooltip has to
            sit on a wrapper element.
        -->
        <span
            v-for="tab in TABS"
            :key="tab"
            v-tooltip.bottom="'Coming soon'"
            class="inline-block"
        >
            <Button :label="tab" text size="small" disabled />
        </span>

        <Button
            label="More"
            icon="pi pi-chevron-down"
            iconPos="right"
            text
            size="small"
            aria-haspopup="true"
            aria-controls="hub-more-menu"
            @click="toggleMore"
        />
        <Menu id="hub-more-menu" ref="moreMenu" :model="moreItems" popup />
    </nav>
</template>

<script setup>
// GWAS-Hub tab bar. Every destination is a future feature, so the tabs are
// rendered for layout fidelity but disabled. Enable a tab by giving it a
// route once the page exists.
const TABS = [
    "Cohorts",
    "Phenotypes",
    "GWAS Files",
    "GWAS QC Plots",
    "Meta-analysis",
];

const moreMenu = ref(null);
const moreItems = [
    { label: "Phenotype Case Totals", disabled: true },
    { label: "MA Ignore List", disabled: true },
    { label: "User Management", disabled: true },
];

const toggleMore = (event) => moreMenu.value?.toggle(event);
</script>

<style scoped>
.hub-nav {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.25rem;
}
</style>
