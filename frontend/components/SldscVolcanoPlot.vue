<template>
    <div class="sldsc-volcano-container">
        <div
            v-if="chartData.datasets[0]?.data.length === 0"
            class="text-center p-4 text-gray-500"
        >
            No data available for volcano plot.
        </div>
        <div v-else>
            <!-- Download button row above plot -->
            <div class="flex items-center justify-end mb-2">
                <!-- Download button -->
                <div>
                    <Menu ref="downloadMenu" :model="downloadMenuItems" popup />
                    <Button
                        icon="pi pi-download"
                        severity="secondary"
                        size="small"
                        rounded
                        text
                        aria-label="Download chart"
                        @click="toggleDownloadMenu"
                        v-tooltip.left="'Download Chart'"
                    />
                </div>
            </div>
            <!-- Chart wrapper -->
            <div class="chart-wrapper relative">
                <canvas ref="chartCanvas"></canvas>

                <div
                    v-if="tooltip.visible"
                    ref="tooltipEl"
                    class="absolute bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg p-3 z-[9999]"
                    :class="{ 'pointer-events-none': !tooltip.pinned }"
                    :style="tooltipStyle"
                >
                    <div class="text-sm">
                        <div class="flex items-start justify-between gap-2">
                            <span
                                class="text-blue-600 dark:text-blue-400 font-semibold"
                            >
                                {{ tooltip.annotation }}
                            </span>
                            <button
                                v-if="tooltip.pinned"
                                @click="closeTooltip"
                                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 -mt-1 -mr-1"
                                aria-label="Close"
                            >
                                <i class="pi pi-times text-xs"></i>
                            </button>
                        </div>
                        <div
                            class="mt-1 space-y-0.5 text-gray-600 dark:text-gray-300"
                        >
                            <div v-if="tooltip.tissue">
                                Tissue: {{ tooltip.tissue }}
                            </div>
                            <div v-if="tooltip.biosample">
                                Biosample: {{ tooltip.biosample }}
                            </div>
                            <div>
                                Enrichment:
                                {{ formatNumber(tooltip.enrichment) }}
                            </div>
                            <div>
                                p-Value: {{ formatScientific(tooltip.pValue) }}
                            </div>
                            <div>
                                -log10(p): {{ formatNumber(tooltip.logPValue) }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import {
    Chart,
    ScatterController,
    LinearScale,
    PointElement,
    Tooltip as ChartTooltip,
} from "chart.js";

Chart.register(ScatterController, LinearScale, PointElement, ChartTooltip);

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
    const tooltipWidth = tooltipEl.value?.offsetWidth || 220;

    let left;
    if (tooltip.value.showOnLeft) {
        left = tooltip.value.canvasX - tooltipWidth - offset;
    } else {
        left = tooltip.value.canvasX + offset;
    }

    const top = tooltip.value.canvasY - 10;

    return {
        left: left + "px",
        top: top + "px",
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
        background: "rgba(33, 150, 243, 0.7)", // #2196f3
        border: "rgba(33, 150, 243, 1)",
    },
    accessible_chromatin: {
        background: "rgba(76, 175, 80, 0.7)", // #4caf50
        border: "rgba(76, 175, 80, 1)",
    },
    enhancer: {
        background: "rgba(255, 152, 0, 0.7)", // #ff9800
        border: "rgba(255, 152, 0, 1)",
    },
    promoter: {
        background: "rgba(233, 30, 99, 0.7)", // #e91e63
        border: "rgba(233, 30, 99, 1)",
    },
    default: {
        background: "rgba(156, 163, 175, 0.7)",
        border: "rgba(156, 163, 175, 1)",
    },
};

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
                if (tooltip.value.pinned) return;

                const tooltipModel = context.tooltip;

                if (tooltipModel.opacity === 0) {
                    tooltip.value.visible = false;
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
                text: "log10(Enrichment)",
                font: {
                    size: 14,
                    weight: "bold",
                },
            },
            grid: {
                color: "rgba(0, 0, 0, 0.1)",
            },
        },
        y: {
            type: "linear",
            title: {
                display: true,
                text: "-log10(p-Value)",
                font: {
                    size: 14,
                    weight: "bold",
                },
            },
            grid: {
                color: "rgba(0, 0, 0, 0.1)",
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
.sldsc-volcano-container {
    width: 100%;
    max-width: 100%;
    position: relative;
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
