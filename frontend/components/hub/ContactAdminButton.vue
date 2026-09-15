<template>
    <Button
        v-if="email"
        as="a"
        :href="mailto"
        :label="label"
        icon="pi pi-envelope"
        :size="size"
    />
    <span
        v-else
        v-tooltip.top="'Contact address not configured'"
        class="inline-block"
    >
        <Button :label="label" icon="pi pi-envelope" :size="size" disabled />
    </span>
</template>

<script setup>
// "Contact admin" call to action for GWAS-Hub. The address comes from
// NUXT_PUBLIC_GWAS_HUB_CONTACT_EMAIL; when unset the button is disabled with
// a tooltip rather than hidden, so the gap is visible in deployments.
const props = defineProps({
    label: { type: String, default: "Contact admin to request access" },
    size: { type: String, default: "large" },
});

const config = useRuntimeConfig();
const email = computed(() => config.public.gwasHubContactEmail || "");
const mailto = computed(
    () =>
        `mailto:${email.value}?subject=${encodeURIComponent("GWAS-Hub access request")}`,
);
</script>
