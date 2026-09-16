<template>
    <div id="app" class="app-shell">
        <!-- Default #brand slot content: the shared GWAS-CE logo -->
        <AppHeader>
            <template #nav>
                <HubNav v-if="showPage" />
            </template>
        </AppHeader>

        <main class="flex flex-1 flex-col">
            <div
                v-if="!isDemo && (pending || status === HUB_STATUS.UNKNOWN)"
                class="flex flex-1 items-center justify-center py-24"
            >
                <ProgressSpinner style="width: 3rem; height: 3rem" />
            </div>
            <slot v-else-if="showPage" />
            <HubAccessRestricted
                v-else
                :status="status"
                @retry="refresh(true)"
            />
        </main>

        <AppFooter />
    </div>
</template>

<script setup>
// The GWAS-Hub layout doubles as the access gate. auth.global.js has already
// redirected anonymous users to /login; here we resolve membership in the hub
// group and only render the page (and the tab bar) for members. Because the
// slot is withheld, deep links to sub-pages are covered without a per-page
// guard, and the URL stays put for the restricted view.
//
// ?mode=demo bypasses the membership check so the landing page can be shown
// to non-members. Pages read the same flag (utils/hub/demoMode.js) to render
// their links inert; following any link drops the query and the gate returns.
import { HUB_STATUS } from "~/utils/auth/hubMembership";
import { isHubDemo } from "~/utils/hub/demoMode";

const route = useRoute();
const isDemo = computed(() => isHubDemo(route.query));

const { status, isMember, pending, refresh } = useHubAccess();
const showPage = computed(() => isDemo.value || isMember.value);
</script>
