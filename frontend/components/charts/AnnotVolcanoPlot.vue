<template>
    <div class="annot-volcano-card">
        <div class="card-header">
            <div>
                <h3>Annotation Enrichment Volcano Plot</h3>
                <p>
                    log₁₀(Enrichment) vs -log₁₀(p-value) for all annotation
                    results
                </p>
            </div>
        </div>
        <div class="chart-shell">
            <!-- Download button -->
            <div class="absolute top-3 right-3 z-10">
                <Menu ref="downloadMenu" :model="downloadMenuItems" popup />
                <Button
                    icon="pi pi-download"
                    severity="secondary"
                    size="small"
                    rounded
                    text
                    aria-label="Download chart"
                    @click="toggleDownloadMenu"
                    class="!bg-white/80 dark:!bg-gray-800/80 hover:!bg-white dark:hover:!bg-gray-700"
                    v-tooltip.left="'Download Chart'"
                />
            </div>
            <canvas ref="chartCanvas"></canvas>
            <div
                v-if="tooltip.visible"
                ref="tooltipEl"
                class="chart-tooltip"
                :class="{ 'pointer-events-auto': tooltip.pinned }"
                :style="tooltipStyle"
            >
                <div class="tooltip-header">
                    <a
                        :href="`https://a2f.hugeamp.org/phenotype.html?phenotype=${tooltip.phenotype}`"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="tooltip-title hover:underline"
                        :style="{ color: isDarkMode ? '#60a5fa' : '#2563eb' }"
                    >
                        {{
                            tooltip.phenotypeDescription || "Unknown phenotype"
                        }}
                    </a>
                    <button
                        v-if="tooltip.pinned"
                        @click="closeTooltip"
                        class="tooltip-close"
                        :style="{ color: isDarkMode ? '#9ca3af' : '#6b7280' }"
                        aria-label="Close"
                    >
                        <i class="pi pi-times"></i>
                    </button>
                </div>
                <div
                    class="tooltip-row"
                    :style="{ color: isDarkMode ? '#d1d5db' : '#4b5563' }"
                >
                    log₁₀(Enrichment): {{ formatNumber(tooltip.logEnrichment) }}
                </div>
                <div
                    class="tooltip-row"
                    :style="{ color: isDarkMode ? '#d1d5db' : '#4b5563' }"
                >
                    Enrichment: {{ formatNumber(tooltip.enrichment) }}
                </div>
                <div
                    class="tooltip-row"
                    :style="{ color: isDarkMode ? '#d1d5db' : '#4b5563' }"
                >
                    p-Value: {{ formatScientific(tooltip.pValue) }}
                </div>
                <div
                    class="tooltip-row"
                    :style="{ color: isDarkMode ? '#d1d5db' : '#4b5563' }"
                >
                    -log₁₀(p): {{ formatNumber(tooltip.negLogP) }}
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import {
    Chart,
    ScatterController,
    LinearScale,
    PointElement,
    Tooltip as ChartTooltip,
} from "chart.js";

Chart.register(ScatterController, LinearScale, PointElement, ChartTooltip);

// Dark mode detection
const { isDarkMode } = useTheme();

const props = defineProps({
    results: {
        type: Array,
        default: () => [],
    },
});

const POINT_COLOR = "rgba(37, 99, 235, 0.85)";
const POINT_BORDER = "rgba(37, 99, 235, 1)";

const chartCanvas = ref(null);
const tooltipEl = ref(null);
let chartInstance = null;

const downloadMenu = ref(null);
const downloadMenuItems = [
    {
        label: "Save as PNG",
        icon: "pi pi-image",
        command: () => downloadChart("png"),
    },
    {
        label: "Save as SVG",
        icon: "pi pi-file",
        command: () => downloadChart("svg"),
    },
];

const tooltip = ref({
    visible: false,
    pinned: false,
    phenotype: "",
    phenotypeDescription: "",
    ancestry: "",
    enrichment: 0,
    logEnrichment: 0,
    pValue: 0,
    negLogP: 0,
    canvasX: 0,
    canvasY: 0,
    showOnLeft: false,
});

const closeTooltip = () => {
    tooltip.value.visible = false;
    tooltip.value.pinned = false;
};

const toggleDownloadMenu = (event) => {
    downloadMenu.value?.toggle(event);
};

const downloadChart = (format) => {
    if (!chartCanvas.value || !chartInstance) return;

    const canvas = chartCanvas.value;
    const filename = `annot-volcano.${format}`;

    if (format === "png") {
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = canvas.width;
        tempCanvas.height = canvas.height;
        const ctx = tempCanvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
        ctx.drawImage(canvas, 0, 0);
        const link = document.createElement("a");
        link.download = filename;
        link.href = tempCanvas.toDataURL("image/png");
        link.click();
        return;
    }

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", canvas.width);
    svg.setAttribute("height", canvas.height);
    svg.setAttribute("xmlns", svgNS);

    const rect = document.createElementNS(svgNS, "rect");
    rect.setAttribute("width", "100%");
    rect.setAttribute("height", "100%");
    rect.setAttribute("fill", "#ffffff");
    svg.appendChild(rect);

    const image = document.createElementNS(svgNS, "image");
    image.setAttribute("width", canvas.width);
    image.setAttribute("height", canvas.height);
    image.setAttribute("href", canvas.toDataURL("image/png"));
    svg.appendChild(image);

    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = filename;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
};

const tooltipStyle = computed(() => {
    if (!chartCanvas.value) return {};
    const offset = 12;
    const tooltipWidth = tooltipEl.value?.offsetWidth || 220;
    const left = tooltip.value.showOnLeft
        ? tooltip.value.canvasX - tooltipWidth - offset
        : tooltip.value.canvasX + offset;
    const top = tooltip.value.canvasY - 10;

    const dark = isDarkMode.value;
    return {
        left: `${left}px`,
        top: `${top}px`,
        backgroundColor: dark ? "#1f2937" : "#ffffff",
        borderColor: dark ? "#374151" : "#e5e7eb",
        color: dark ? "#f3f4f6" : "#111827",
    };
});

const formatNumber = (value) => {
    if (typeof value !== "number" || Number.isNaN(value)) return "—";
    return value.toFixed(3);
};

const formatScientific = (value) => {
    if (typeof value !== "number" || Number.isNaN(value)) return "—";
    if (value === 0) return "0";
    if (value < 0.001) return value.toExponential(2);
    return value.toFixed(6);
};

const chartData = computed(() => {
    const points = props.results
        .filter(
            (item) =>
                typeof item.enrichment === "number" &&
                item.enrichment > 0 &&
                typeof item.pValue === "number" &&
                item.pValue > 0,
        )
        .map((item) => {
            const logEnrichment = Math.log10(item.enrichment);
            const negLogP = -Math.log10(item.pValue);
            return {
                x: logEnrichment,
                y: negLogP,
                phenotype: item.phenotype,
                phenotypeDescription:
                    item.phenotypeDescription || item.phenotype,
                ancestry: item.ancestry,
                enrichment: item.enrichment,
                logEnrichment,
                pValue: item.pValue,
                negLogP,
            };
        });

    return {
        datasets: [
            {
                label: "Annotation results",
                data: points,
                backgroundColor: POINT_COLOR,
                borderColor: POINT_BORDER,
                borderWidth: 1,
                pointRadius: 5,
                pointHoverRadius: 7,
            },
        ],
    };
});

const showTooltip = (rawPoint, canvasX, canvasY, pinned = false) => {
    const chartArea = chartInstance?.chartArea;
    if (!chartArea) return;
    const showOnLeft =
        canvasX - chartArea.left > (chartArea.right - chartArea.left) / 2;

    tooltip.value = {
        visible: true,
        pinned,
        phenotype: rawPoint.phenotype,
        phenotypeDescription:
            rawPoint.phenotypeDescription || rawPoint.phenotype,
        ancestry: rawPoint.ancestry,
        enrichment: rawPoint.enrichment,
        logEnrichment: rawPoint.logEnrichment,
        pValue: rawPoint.pValue,
        negLogP: rawPoint.negLogP,
        canvasX,
        canvasY,
        showOnLeft,
    };
};

const createChart = () => {
    if (!chartCanvas.value) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(chartCanvas.value, {
        type: "scatter",
        data: chartData.value,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: false,
                    external: ({ tooltip: model }) => {
                        // Don't update tooltip on hover if it's pinned
                        if (tooltip.value.pinned) return;

                        if (model.opacity === 0) {
                            tooltip.value.visible = false;
                            return;
                        }
                        const dataPoint = model.dataPoints?.[0];
                        if (!dataPoint) return;
                        showTooltip(
                            dataPoint.raw,
                            model.caretX,
                            model.caretY,
                            false,
                        );
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: "log₁₀(Enrichment)" },
                    grid: { color: "rgba(148, 163, 184, 0.25)" },
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "-log₁₀(p-value)" },
                    grid: { color: "rgba(148, 163, 184, 0.25)" },
                },
            },
            interaction: { mode: "nearest", intersect: true },
            onClick: (_, elements) => {
                if (!elements.length) {
                    // Click on empty space closes pinned tooltip
                    if (tooltip.value.pinned) {
                        closeTooltip();
                    }
                    return;
                }
                const element = elements[0];
                const rawPoint =
                    chartInstance.data.datasets[element.datasetIndex].data[
                        element.index
                    ];
                // Pin the tooltip on click
                showTooltip(
                    rawPoint,
                    element.element.x,
                    element.element.y,
                    true,
                );
            },
        },
    });
};

const updateChart = () => {
    if (!chartInstance) {
        createChart();
        return;
    }
    chartInstance.data = chartData.value;
    chartInstance.update();
};

watch(
    () => props.results,
    () => {
        nextTick(() => {
            updateChart();
        });
    },
    { deep: true },
);

onMounted(() => {
    nextTick(() => {
        createChart();
    });
});

onUnmounted(() => {
    if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
    }
});
</script>

<style scoped>
.annot-volcano-card {
    padding: 1.5rem;
    border: 1px solid var(--surface-border);
    border-radius: 0.75rem;
    background: var(--surface-card);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}

.card-header h3 {
    font-weight: 600;
    font-size: 1.125rem;
    color: var(--text-color);
}

.card-header p {
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: var(--text-color-secondary);
}

.chart-shell {
    position: relative;
    height: 24rem;
}

.chart-shell canvas {
    max-width: 100%;
    max-height: 100%;
}

.chart-tooltip {
    position: absolute;
    background: var(--surface-overlay, #ffffff);
    border: 1px solid var(--surface-border);
    border-radius: 0.5rem;
    padding: 0.75rem;
    width: 14rem;
    font-size: 0.85rem;
    box-shadow: 0 10px 20px rgba(15, 23, 42, 0.1);
    pointer-events: none;
}

.chart-tooltip.pointer-events-auto {
    pointer-events: auto;
}

.tooltip-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem;
}

.tooltip-title {
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--text-color);
}

.tooltip-close {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    color: var(--text-color-secondary);
    font-size: 0.75rem;
    line-height: 1;
}

.tooltip-close:hover {
    color: var(--text-color);
}

.tooltip-row {
    color: var(--text-color-secondary);
    line-height: 1.3;
}
</style>
