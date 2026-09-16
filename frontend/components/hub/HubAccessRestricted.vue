<template>
    <div class="flex flex-1 items-center justify-center px-6 py-16">
        <Card class="w-full max-w-xl text-center">
            <template #content>
                <div class="flex flex-col items-center gap-4 p-6">
                    <i
                        class="pi text-5xl"
                        :class="
                            isError
                                ? 'pi-exclamation-triangle text-orange-500'
                                : 'pi-lock text-primary'
                        "
                    ></i>
                    <h2
                        class="text-2xl font-semibold text-gray-900 dark:text-white"
                    >
                        {{
                            isError
                                ? "We couldn't verify your access"
                                : "GWAS-Hub access is restricted"
                        }}
                    </h2>
                    <p class="text-gray-600 dark:text-gray-300">
                        <template v-if="isError">
                            The user service did not respond. Please try
                            again in a moment.
                        </template>
                        <template v-else>
                            GWAS-Hub is a shared workspace for consortium
                            members. Your account is signed in to GWAS-CE but
                            has not yet been granted GWAS-Hub access.
                        </template>
                    </p>
                    <Button
                        v-if="isError"
                        label="Retry"
                        icon="pi pi-refresh"
                        size="large"
                        @click="emit('retry')"
                    />
                    <ContactAdminButton v-else />
                </div>
            </template>
        </Card>
    </div>
</template>

<script setup>
// Shown by layouts/gwas-hub.vue in place of the page when the signed-in user
// is not a hub member (status "denied") or membership could not be checked
// (status "error").
import { HUB_STATUS } from "~/utils/auth/hubMembership";

const props = defineProps({
    status: { type: String, required: true },
});
const emit = defineEmits(["retry"]);

const isError = computed(() => props.status === HUB_STATUS.ERROR);
</script>
