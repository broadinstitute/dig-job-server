// Resolves GWAS-Hub membership for the current session. Used by
// layouts/gwas-hub.vue, which renders the page slot only for members.
import { useUserStore } from "~/stores/UserStore";

export const useHubAccess = () => {
    const userStore = useUserStore();
    const pending = ref(false);

    const status = computed(() => userStore.hubStatus);
    const isMember = computed(() => userStore.isHubMember);

    const refresh = async (force = false) => {
        pending.value = true;
        try {
            await userStore.checkHubMembership({ force });
        } finally {
            pending.value = false;
        }
    };

    // The token is shared across tabs via localStorage. When another tab signs
    // in or out, re-resolve membership for the new identity right away rather
    // than waiting for this layout to remount. `storage` only fires in OTHER
    // tabs, so this never loops on our own writes.
    const onStorage = (event) => {
        if (event.key === "authToken" || event.key === null) {
            refresh(true);
        }
    };

    onMounted(() => {
        window.addEventListener("storage", onStorage);
        refresh();
    });
    onBeforeUnmount(() => {
        window.removeEventListener("storage", onStorage);
    });

    return { status, isMember, pending, refresh };
};
