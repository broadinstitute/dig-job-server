import { describe, it, expect, vi } from "vitest";
import {
    resultButtonConfig,
    resultsUrl,
    successfulResultMethods,
} from "../../utils/results/resultNavigation.js";

const job = (method, updated_at, status = "SUCCEEDED") => ({
    [method]: { [method]: { status, updated_at } },
});
const row = (workflows, status) => ({
    dataset: "trait A&B/#",
    workflows,
    status,
});
const actions = () => ({
    includeSifter: true,
    view: vi.fn(),
    openNewTab: vi.fn(),
    openSifter: vi.fn(),
});

describe("result navigation", () => {
    it.each(["sldsc", "magma", "pigean", "falcon"])(
        "opens the matching %s tab",
        (method) => {
            const data = row(job(method));
            const handlers = actions();
            const config = resultButtonConfig(data, handlers);
            config.command();
            config.dropdownItems[0].command();
            expect(handlers.view).toHaveBeenCalledWith(data.dataset, method);
            expect(handlers.openNewTab).toHaveBeenCalledWith(
                data.dataset,
                method,
            );
            const url = new URL(
                resultsUrl(data.dataset, method),
                "https://example.org",
            );
            expect(url.searchParams.get("dataset")).toBe(data.dataset);
            expect(url.searchParams.get("tab")).toBe(method);
        },
    );

    it("promotes the latest in-app result and targets older tabs individually", () => {
        const data = row({
            ...job("sldsc", "2026-10-01"),
            ...job("pigean", "2026-10-03"),
            ...job("variant-sifter", "2026-10-02"),
        });
        const handlers = actions();
        const config = resultButtonConfig(data, handlers);
        expect(config.label).toBe("View Results");
        config.command();
        expect(handlers.view).toHaveBeenLastCalledWith(data.dataset, "pigean");
        config.dropdownItems
            .find((item) => item.label === "View SLDSC Results")
            .command();
        expect(handlers.view).toHaveBeenLastCalledWith(data.dataset, "sldsc");
        config.dropdownItems
            .find((item) => item.label === "Variant Sifter")
            .command();
        expect(handlers.openSifter).toHaveBeenCalledWith(data);
    });

    it("promotes Variant Sifter and offers other results with matching tabs", () => {
        const data = row({
            ...job("magma", "2026-10-01"),
            ...job("falcon", "2026-10-02"),
            ...job("variant-sifter", "2026-10-03"),
        });
        const handlers = actions();
        const config = resultButtonConfig(data, handlers);
        expect(config.label).toBe("Variant Sifter");
        config.command();
        expect(handlers.openSifter).toHaveBeenCalledWith(data);
        const other = config.dropdownItems[0];
        expect(other.label).toBe("Other Results");
        other.items[0].command();
        expect(handlers.view).toHaveBeenLastCalledWith(data.dataset, "falcon");
        other.items
            .find((item) => item.label === "View MAGMA Results")
            .command();
        expect(handlers.view).toHaveBeenLastCalledWith(data.dataset, "magma");
    });

    it("shows a plain sifter action when it is the only result", () => {
        expect(
            resultButtonConfig(row(job("variant-sifter")), actions())
                .dropdownItems,
        ).toEqual([]);
    });

    it("opens the sole other result directly from the sifter dropdown", () => {
        const data = row({
            ...job("magma", "2026-10-01"),
            ...job("variant-sifter", "2026-10-02"),
        });
        const handlers = actions();
        resultButtonConfig(data, handlers).dropdownItems[0].command();
        expect(handlers.view).toHaveBeenCalledWith(data.dataset, "magma");
    });

    it.each(["RUNNING", "PENDING", "FAILED"])(
        "ignores a newer %s job",
        (status) => {
            expect(
                successfulResultMethods(
                    row({
                        ...job("magma", "2026-10-01"),
                        ...job("variant-sifter", "2026-10-03", status),
                    }),
                    true,
                ),
            ).toEqual(["magma"]);
        },
    );

    it("uses current status to break ties and handles missing or invalid timestamps", () => {
        expect(
            successfulResultMethods(
                row(
                    {
                        ...job("sldsc"),
                        ...job("falcon", "invalid"),
                        ...job("variant-sifter"),
                    },
                    "variant-sifter SUCCEEDED",
                ),
                true,
            )[0],
        ).toBe("variant-sifter");
    });

    it("excludes an unconfigured portal and unavailable results", () => {
        expect(
            resultButtonConfig(row(job("variant-sifter")), {
                ...actions(),
                includeSifter: false,
            }),
        ).toBeNull();
        expect(
            resultButtonConfig(
                row(job("magma", undefined, "FAILED")),
                actions(),
            ),
        ).toBeNull();
    });

    it("supports the legacy ldsc workflow with the sldsc tab", () => {
        expect(successfulResultMethods(row(job("ldsc")))).toEqual(["sldsc"]);
    });
});
