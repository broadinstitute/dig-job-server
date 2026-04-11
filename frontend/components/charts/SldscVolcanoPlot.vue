<template>
    <div class="sldsc-volcano-card">
        <div class="sldsc-card-header">
            <div>
                <h3>SLDSC Annotation Volcano Plot</h3>
                <p>log₁₀(Enrichment) vs -log₁₀(p-value) for annotation bins</p>
            </div>
            <div class="sldsc-card-actions">
                <div class="sldsc-legend">
                    <div
                        v-for="legend in annotationLegend"
                        :key="legend.value"
                        class="legend-item"
                    >
                        <span
                            class="legend-dot"
                            :style="{ backgroundColor: legend.color }"
                        ></span>
                        <span>{{ legend.label }}</span>
                    </div>
                </div>
                <Menu ref="downloadMenu" :model="downloadMenuItems" popup />
                <Button
                    icon="pi pi-download"
                    rounded
                    text
                    size="small"
                    aria-label="Download chart"
                    @click="toggleDownloadMenu"
                    v-tooltip.left="'Download Chart'"
                />
            </div>
        </div>

        <div
            v-if="chartData.datasets[0]?.data.length === 0"
            class="empty-state"
        >
            No data available for volcano plot.
        </div>
        <div v-else class="chart-wrapper">
            <canvas ref="chartCanvas"></canvas>

            <div
                v-if="tooltip.visible"
                ref="tooltipEl"
                class="absolute rounded shadow-lg p-3 z-[9999] border"
                :class="{ 'pointer-events-none': !tooltip.pinned }"
                :style="tooltipStyle"
            >
                <div class="text-sm">
                    <div class="flex items-start justify-between gap-2">
                        <span
                            class="font-semibold"
                            :style="{
                                color: isDarkMode ? '#60a5fa' : '#2563eb',
                            }"
                        >
                            {{ tooltip.annotation }}
                        </span>
                        <button
                            v-if="tooltip.pinned"
                            @click="closeTooltip"
                            class="-mt-1 -mr-1 text-xs"
                            :style="{
                                color: isDarkMode ? '#9ca3af' : '#6b7280',
                            }"
                            aria-label="Close"
                        >
                            <i class="pi pi-times"></i>
                        </button>
                    </div>
                    <div
                        class="mt-1 space-y-0.5"
                        :style="{ color: isDarkMode ? '#d1d5db' : '#4b5563' }"
                    >
                        <div v-if="tooltip.tissue">
                            Tissue: {{ tooltip.tissue }}
                        </div>
                        <div v-if="tooltip.biosample">
                            Biosample: {{ tooltip.biosample }}
                        </div>
                        <div>
                            Enrichment: {{ formatNumber(tooltip.enrichment) }}
                        </div>
                        <div>
                            p-Value: {{ formatScientific(tooltip.pValue) }}
                        </div>
                        <div>
                            -log₁₀(p): {{ formatNumber(tooltip.logPValue) }}
                        </div>
                    </div>
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

// Dark mode detection - use the app's theme composable for reactivity
const { isDarkMode } = useTheme();

const props = defineProps({
    annotationResults: {
        type: Array,
        default: () => [],
    },
});

const chartCanvas = ref(null);
let chartInstance = null;

const tooltipEl = ref(null);
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

const toggleDownloadMenu = (event) => {
    downloadMenu.value.toggle(event);
};

const downloadChart = (format) => {
    if (!chartCanvas.value || !chartInstance) return;

    const canvas = chartCanvas.value;
    const filename = `sldsc-volcano.${format}`;

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
    } else if (format === "svg") {
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
    }
};

const tooltip = ref({
    visible: false,
    pinned: false,
    canvasX: 0,
    canvasY: 0,
    showOnLeft: false,
    annotation: "",
    tissue: "",
    biosample: "",
    enrichment: 0,
    pValue: 0,
    logPValue: 0,
});

const tooltipStyle = computed(() => {
    if (!chartCanvas.value) return {};

    const offset = 10;
    const tooltipWidth = tooltipEl.value?.offsetWidth || 200;

    let left;
    if (tooltip.value.showOnLeft) {
        left = tooltip.value.canvasX - tooltipWidth - offset;
    } else {
        left = tooltip.value.canvasX + offset;
    }

    const top = tooltip.value.canvasY - 10;

    // Use reactive dark mode state
    const dark = isDarkMode.value;

    return {
        left: left + "px",
        top: top + "px",
        backgroundColor: dark ? "#1f2937" : "#ffffff",
        borderColor: dark ? "#374151" : "#e5e7eb",
        color: dark ? "#f3f4f6" : "#111827",
    };
});

const closeTooltip = () => {
    tooltip.value.visible = false;
    tooltip.value.pinned = false;
};

const formatNumber = (value) => {
    if (typeof value !== "number" || isNaN(value)) return "—";
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value);
};

const formatScientific = (value) => {
    if (typeof value !== "number" || isNaN(value)) return "—";
    if (value === 0) return "0";
    if (Math.abs(value) < 0.0001) {
        return value.toExponential(2);
    }
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value);
};

// Annotation color mapping (matches table dot colors)
const ANNOTATION_COLORS = {
    binding_sites: {
        background: "rgba(33, 150, 243, 0.8)", // #2196f3
        border: "rgba(33, 150, 243, 1)",
    },
    accessible_chromatin: {
        background: "rgba(76, 175, 80, 0.8)", // #4caf50
        border: "rgba(76, 175, 80, 1)",
    },
    enhancer: {
        background: "rgba(255, 152, 0, 0.8)", // #ff9800
        border: "rgba(255, 152, 0, 1)",
    },
    promoter: {
        background: "rgba(233, 30, 99, 0.8)", // #e91e63
        border: "rgba(233, 30, 99, 1)",
    },
    default: {
        background: "rgba(156, 163, 175, 0.85)",
        border: "rgba(156, 163, 175, 1)",
    },
};

const annotationLegend = [
    { label: "Binding Sites", value: "binding_sites", color: "#2196f3" },
    {
        label: "Accessible Chromatin",
        value: "accessible_chromatin",
        color: "#4caf50",
    },
    { label: "Enhancer", value: "enhancer", color: "#ff9800" },
    { label: "Promoter", value: "promoter", color: "#e91e63" },
];

const AXIS_TITLE_COLOR = "#94a3b8";
const AXIS_TICK_COLOR = "#94a3b8";
const GRID_COLOR = "rgba(148, 163, 184, 0.35)";

const getPointColor = (annotation) => {
    const normalizedAnnotation = annotation?.toLowerCase().replace(/\s+/g, "_");
    return ANNOTATION_COLORS[normalizedAnnotation] || ANNOTATION_COLORS.default;
};

const calculateLogPValue = (pValue) => {
    if (typeof pValue !== "number" || pValue <= 0) return 0;
    return -Math.log10(pValue);
};

const chartData = computed(() => {
    const dataPoints = props.annotationResults
        .filter(
            (item) =>
                typeof item.enrichment === "number" &&
                item.enrichment > 0 &&
                typeof item.pValue === "number" &&
                item.pValue > 0,
        )
        .map((item) => {
            const logPValue = calculateLogPValue(item.pValue);
            const colors = getPointColor(item.annotation);

            return {
                x: Math.log10(item.enrichment),
                y: logPValue,
                annotation: item.annotation,
                tissue: item.tissue,
                biosample: item.biosample,
                enrichment: item.enrichment,
                logEnrichment: Math.log10(item.enrichment),
                pValue: item.pValue,
                logPValue: logPValue,
                backgroundColor: colors.background,
                borderColor: colors.border,
            };
        });

    return {
        datasets: [
            {
                label: "SLDSC Annotations",
                data: dataPoints,
                backgroundColor: dataPoints.map((p) => p.backgroundColor),
                borderColor: dataPoints.map((p) => p.borderColor),
                borderWidth: 1,
                pointRadius: 5,
                pointHoverRadius: 8,
            },
        ],
    };
});

const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (event, elements) => {
        if (elements.length > 0) {
            const element = elements[0];
            const datasetIndex = element.datasetIndex;
            const index = element.index;
            const rawData =
                chartInstance.data.datasets[datasetIndex].data[index];
            const { x: canvasX, y: canvasY } = element.element;

            const chartWidth =
                chartInstance.chartArea.right - chartInstance.chartArea.left;
            const pointRelativeX = canvasX - chartInstance.chartArea.left;
            const showOnLeft = pointRelativeX > chartWidth / 2;

            tooltip.value = {
                visible: true,
                pinned: true,
                canvasX: canvasX,
                canvasY: canvasY,
                showOnLeft: showOnLeft,
                annotation: rawData.annotation,
                tissue: rawData.tissue,
                biosample: rawData.biosample,
                enrichment: rawData.enrichment,
                pValue: rawData.pValue,
                logPValue: rawData.logPValue,
            };
        }
    },
    plugins: {
        tooltip: {
            enabled: false,
            external: (context) => {
                // Don't update tooltip on hover if it's pinned
                if (tooltip.value.pinned) return;

                const tooltipModel = context.tooltip;

                // Don't hide on opacity=0 - let onClick handle pinned state
                if (tooltipModel.opacity === 0) {
                    // Only hide if not currently in a click action
                    // Small delay to let onClick fire first
                    setTimeout(() => {
                        if (!tooltip.value.pinned) {
                            tooltip.value.visible = false;
                        }
                    }, 50);
                    return;
                }

                if (tooltipModel.dataPoints?.length > 0) {
                    const dataPoint = tooltipModel.dataPoints[0];
                    const rawData = dataPoint.raw;

                    const chartWidth =
                        chartInstance.chartArea.right -
                        chartInstance.chartArea.left;
                    const pointRelativeX =
                        tooltipModel.caretX - chartInstance.chartArea.left;
                    const showOnLeft = pointRelativeX > chartWidth / 2;

                    tooltip.value = {
                        visible: true,
                        pinned: false,
                        canvasX: tooltipModel.caretX,
                        canvasY: tooltipModel.caretY,
                        showOnLeft: showOnLeft,
                        annotation: rawData.annotation,
                        tissue: rawData.tissue,
                        biosample: rawData.biosample,
                        enrichment: rawData.enrichment,
                        pValue: rawData.pValue,
                        logPValue: rawData.logPValue,
                    };
                }
            },
        },
    },
    scales: {
        x: {
            type: "linear",
            position: "bottom",
            title: {
                display: true,
                text: "log₁₀(Enrichment)",
                color: AXIS_TITLE_COLOR,
                font: {
                    size: 13,
                    weight: "600",
                },
            },
            grid: {
                color: GRID_COLOR,
            },
            ticks: {
                color: AXIS_TICK_COLOR,
            },
        },
        y: {
            type: "linear",
            title: {
                display: true,
                text: "-log₁₀(p-value)",
                color: AXIS_TITLE_COLOR,
                font: {
                    size: 13,
                    weight: "600",
                },
            },
            grid: {
                color: GRID_COLOR,
            },
            ticks: {
                color: AXIS_TICK_COLOR,
            },
            beginAtZero: true,
        },
    },
    interaction: {
        mode: "nearest",
        intersect: true,
    },
};

const createChart = () => {
    if (!chartCanvas.value) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(chartCanvas.value, {
        type: "scatter",
        data: chartData.value,
        options: chartOptions,
    });
};

const updateChart = () => {
    if (chartInstance) {
        chartInstance.data = chartData.value;
        chartInstance.update();
    } else {
        createChart();
    }
};

watch(
    () => props.annotationResults,
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
.sldsc-volcano-card {
    padding: 1.5rem;
    border: 1px solid var(--p-content-border-color);
    border-radius: 0.75rem;
    background: var(--p-content-background);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.sldsc-card-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}

.sldsc-card-header h3 {
    font-weight: 600;
    font-size: 1.125rem;
    color: var(--p-text-color);
}

.sldsc-card-header p {
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: var(--p-text-muted-color);
}

.sldsc-card-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    justify-content: flex-end;
}

.sldsc-legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.85rem;
    color: var(--p-text-muted-color);
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 9999px;
    border: 1px solid rgba(15, 23, 42, 0.2);
}

.empty-state {
    padding: 2rem;
    text-align: center;
    color: var(--p-text-muted-color);
    border: 1px dashed var(--p-content-border-color);
    border-radius: 0.75rem;
}

.chart-shell {
    position: relative;
    width: 100%;
    height: 24rem;
}

.chart-shell canvas {
    max-width: 100%;
    max-height: 100%;
}

.chart-wrapper {
    position: relative;
    width: 100%;
    height: 400px;
}

.chart-wrapper canvas {
    display: block;
    max-width: 100%;
    max-height: 100%;
}
</style>
