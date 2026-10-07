export const RESULT_METHODS = [
    "sldsc",
    "magma",
    "pigean",
    "falcon",
    "variant-sifter",
];

// Only completed results are destinations. A newer running/failed job must
// not displace an available result. The row status breaks timestamp ties.
export function successfulResultMethods(data, includeSifter = false) {
    const currentMethod = data.status?.split(" ")[0];
    return RESULT_METHODS.filter((method) => {
        if (method === "variant-sifter" && !includeSifter) return false;
        return workflowDetails(data.workflows, method)?.status === "SUCCEEDED";
    }).sort((a, b) => {
        const timestamp = (method) => {
            const value = Date.parse(
                workflowDetails(data.workflows, method)?.updated_at,
            );
            return Number.isFinite(value) ? value : 0;
        };
        return (
            timestamp(b) - timestamp(a) ||
            Number(b === currentMethod) - Number(a === currentMethod)
        );
    });
}

function workflowDetails(workflows, method) {
    return (
        workflows?.[method]?.[method] ||
        (method === "sldsc" ? workflows?.ldsc?.ldsc : undefined)
    );
}

export function resultsUrl(dataset, method) {
    const query = new URLSearchParams({ dataset });
    if (method) query.set("tab", method);
    return `/results?${query}`;
}

export function resultButtonConfig(
    data,
    { includeSifter, view, openNewTab, openSifter },
) {
    const methods = successfulResultMethods(data, includeSifter);
    const primary = methods[0];
    if (!primary) return null;

    const inApp = methods.filter((method) => method !== "variant-sifter");
    const sifterItem = {
        label: "Variant Sifter",
        icon: "pi pi-external-link",
        command: () => openSifter(data),
    };
    const otherResults = inApp
        .filter((method) => method !== primary)
        .map((method) => ({
            label: `View ${method.toUpperCase()} Results`,
            icon: "pi pi-eye",
            command: () => view(data.dataset, method),
        }));
    if (primary === "variant-sifter") {
        return {
            ...sifterItem,
            dropdownItems: inApp.length
                ? [
                      {
                          label: "Other Results",
                          icon: "pi pi-eye",
                          ...(inApp.length > 1
                              ? { items: otherResults }
                              : {
                                    command: () => view(data.dataset, inApp[0]),
                                }),
                      },
                  ]
                : [],
        };
    }
    return {
        label: "View Results",
        icon: "pi pi-eye",
        command: () => view(data.dataset, primary),
        dropdownItems: [
            {
                label: "Open in new tab",
                icon: "pi pi-window-maximize",
                command: () => openNewTab(data.dataset, primary),
            },
            ...otherResults,
            ...(methods.includes("variant-sifter") ? [sifterItem] : []),
        ],
    };
}
