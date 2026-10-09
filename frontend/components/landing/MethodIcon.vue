<template>
    <div class="method-icon" :style="{ '--accent': accent }" aria-hidden="true">
        <svg
            viewBox="0 0 48 48"
            fill="none"
            stroke="currentColor"
            stroke-width="2.25"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
            <!-- S-LDSC: regression line through annotation scatter -->
            <template v-if="slug === 'sldsc'">
                <path d="M8 7v33h33" />
                <g fill="currentColor" stroke="none" opacity="0.45">
                    <circle cx="15" cy="33" r="2.25" />
                    <circle cx="20" cy="27" r="2.25" />
                    <circle cx="25" cy="29" r="2.25" />
                    <circle cx="29" cy="21" r="2.25" />
                    <circle cx="34" cy="18" r="2.25" />
                    <circle cx="38" cy="11" r="2.25" />
                </g>
                <path d="M12 36L41 10" />
            </template>

            <!-- MAGMA: variants roll up into genes, genes into a pathway -->
            <template v-else-if="slug === 'magma'">
                <path
                    d="M24 13l-10 9M24 13l10 9M14 26l-6 10M14 26l5 10M34 26l-5 10M34 26l6 10"
                />
                <circle cx="24" cy="9.5" r="4" fill="currentColor" />
                <circle cx="14" cy="24" r="3.25" />
                <circle cx="34" cy="24" r="3.25" />
                <g fill="currentColor" stroke="none" opacity="0.45">
                    <circle cx="8" cy="38.5" r="2.5" />
                    <circle cx="19" cy="38.5" r="2.5" />
                    <circle cx="29" cy="38.5" r="2.5" />
                    <circle cx="40" cy="38.5" r="2.5" />
                </g>
            </template>

            <!-- PIGEAN: genes ranked by prior-informed support -->
            <template v-else-if="slug === 'pigean'">
                <path d="M8 7v34" />
                <g stroke="none" fill="currentColor">
                    <rect x="12" y="9" width="28" height="6" rx="2" />
                    <rect
                        x="12"
                        y="18"
                        width="21"
                        height="6"
                        rx="2"
                        opacity="0.55"
                    />
                    <rect
                        x="12"
                        y="27"
                        width="15"
                        height="6"
                        rx="2"
                        opacity="0.4"
                    />
                    <rect
                        x="12"
                        y="36"
                        width="9"
                        height="5"
                        rx="2"
                        opacity="0.25"
                    />
                </g>
            </template>

            <!-- FALCON: network integrating several data sources -->
            <template v-else-if="slug === 'falcon'">
                <path
                    d="M24 24L24 10M24 24L36.5 17M24 24L36.5 31M24 24L24 38M24 24L11.5 31M24 24L11.5 17"
                    opacity="0.55"
                />
                <path d="M24 10L36.5 17M36.5 31L24 38M11.5 31L11.5 17" />
                <circle cx="24" cy="24" r="4.5" fill="currentColor" />
                <g fill="var(--tile-bg)">
                    <circle cx="24" cy="8" r="3" />
                    <circle cx="38" cy="16" r="3" />
                    <circle cx="38" cy="32" r="3" />
                    <circle cx="24" cy="40" r="3" />
                    <circle cx="10" cy="32" r="3" />
                    <circle cx="10" cy="16" r="3" />
                </g>
            </template>

            <!-- Variant Sifter: many variants in, a prioritized few out -->
            <template v-else-if="slug === 'variant-sifter'">
                <g fill="currentColor" stroke="none" opacity="0.45">
                    <circle cx="13" cy="7.5" r="2.25" />
                    <circle cx="20.5" cy="6" r="2.25" />
                    <circle cx="28" cy="7.5" r="2.25" />
                    <circle cx="35.5" cy="6" r="2.25" />
                </g>
                <path d="M8 13h32L28 27v9l-8 4V27L8 13z" />
                <circle
                    cx="24"
                    cy="31"
                    r="2.25"
                    fill="currentColor"
                    stroke="none"
                />
            </template>

            <!-- Fallback for a method without artwork yet -->
            <circle v-else cx="24" cy="24" r="12" />
        </svg>
    </div>
</template>

<script setup>
// Monotone line icon for one method, drawn in the method's catalog accent
// color on a tinted tile. Artwork is keyed by slug; unknown slugs get a plain
// circle so a new catalog entry never renders an empty tile.
defineProps({
    slug: { type: String, required: true },
    accent: { type: String, required: true },
});
</script>

<style scoped>
.method-icon {
    --tile-bg: color-mix(in srgb, var(--accent) 13%, white);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 53px;
    height: 53px;
    border-radius: 7px;
    background-color: var(--tile-bg);
    /* Deepened with the GWAS-CE ink so light accents (green, gold) keep
       contrast against their pale tile. */
    color: color-mix(in srgb, var(--accent) 80%, var(--gwas-ink-strong));
}

.method-icon svg {
    width: 38px;
    height: 38px;
}

/* Darker accents (plum, olive) disappear on a dark card, so dark mode lifts
   the stroke toward white and gives the tile more of the accent. */
html.dark .method-icon {
    --tile-bg: color-mix(in srgb, var(--accent) 32%, #27272a);
    color: color-mix(in srgb, var(--accent) 55%, white);
}
</style>
