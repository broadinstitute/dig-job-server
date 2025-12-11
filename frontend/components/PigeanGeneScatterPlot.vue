<template>
    <div class="pigean-scatter-container">
        <div
            v-if="chartData.datasets[0].data.length === 0"
            class="text-center p-4 text-gray-500"
        >
            No data available for scatter plot.
        </div>
        <div v-else class="chart-wrapper">
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
                class="absolute bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg p-3 z-[9999]"
                :class="{ 'pointer-events-none': !tooltip.pinned }"
                :style="tooltipStyle"
            >
                <div class="text-sm">
                    <div class="flex items-start justify-between gap-2">
                        <a
                            :href="`https://a2f.hugeamp.org/gene.html?gene=${tooltip.gene}`"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold hover:underline"
                        >
                            {{ tooltip.gene }}
                        </a>
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
                        <div>
                            Combined Score: {{ formatNumber(tooltip.combined) }}
                        </div>
                        <div>
                            HuGE Score: {{ formatNumber(tooltip.huge_score) }}
                        </div>
                        <div>
                            Direct Score: {{ formatNumber(tooltip.log_bf) }}
                        </div>
                        <div>
                            Indirect Score: {{ formatNumber(tooltip.prior) }}
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
    geneResults: {
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
    const filename = `pigean-gene-scatter.${format}`;

    if (format === "png") {
        // Create a new canvas with white background for PNG
        const tempCanvas = document.createElement("canvas");
        tempCanvas.width = canvas.width;
        tempCanvas.height = canvas.height;
        const ctx = tempCanvas.getContext("2d");

        // Fill with white background
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Draw the chart on top
        ctx.drawImage(canvas, 0, 0);

        const link = document.createElement("a");
        link.download = filename;
        link.href = tempCanvas.toDataURL("image/png");
        link.click();
    } else if (format === "svg") {
        // Create SVG from canvas
        const svgNS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNS, "svg");
        svg.setAttribute("width", canvas.width);
        svg.setAttribute("height", canvas.height);
        svg.setAttribute("xmlns", svgNS);

        // Add white background
        const rect = document.createElementNS(svgNS, "rect");
        rect.setAttribute("width", "100%");
        rect.setAttribute("height", "100%");
        rect.setAttribute("fill", "#ffffff");
        svg.appendChild(rect);

        // Embed the canvas as an image in SVG
        const image = document.createElementNS(svgNS, "image");
        image.setAttribute("width", canvas.width);
        image.setAttribute("height", canvas.height);
        image.setAttribute("href", canvas.toDataURL("image/png"));
        svg.appendChild(image);

        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], {
            type: "image/svg+xml;charset=utf-8",
        });
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
    gene: "",
    combined: 0,
    huge_score: 0,
    log_bf: 0,
    prior: 0,
});

const tooltipStyle = computed(() => {
    if (!chartCanvas.value) return {};

    const offset = 10;

    // Get actual tooltip width if available, otherwise use estimate
    const tooltipWidth = tooltipEl.value?.offsetWidth || 200;

    let left;
    if (tooltip.value.showOnLeft) {
        // Show tooltip on left side of the point
        left = tooltip.value.canvasX - tooltipWidth - offset;
    } else {
        // Show tooltip on right side of the point
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
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
    }).format(value);
};

const chartData = computed(() => {
    const dataPoints = props.geneResults
        .filter(
            (item) =>
                typeof item.prior === "number" &&
                typeof item.log_bf === "number",
        )
        .map((item) => ({
            x: item.prior,
            y: item.log_bf,
            gene: item.gene,
            combined: item.combined,
            huge_score: item.huge_score,
        }));

    return {
        datasets: [
            {
                label: "Genes",
                data: dataPoints,
                backgroundColor: "rgba(59, 130, 246, 0.6)",
                borderColor: "rgba(59, 130, 246, 1)",
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

            // Determine if point is on right half of chart
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
                gene: rawData.gene,
                combined: rawData.combined,
                huge_score: rawData.huge_score,
                log_bf: rawData.y,
                prior: rawData.x,
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

                if (tooltipModel.opacity === 0) {
                    tooltip.value.visible = false;
                    return;
                }

                if (
                    tooltipModel.dataPoints &&
                    tooltipModel.dataPoints.length > 0
                ) {
                    const dataPoint = tooltipModel.dataPoints[0];
                    const rawData = dataPoint.raw;

                    // Determine if point is on right half of chart
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
                        gene: rawData.gene,
                        combined: rawData.combined,
                        huge_score: rawData.huge_score,
                        log_bf: rawData.y,
                        prior: rawData.x,
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
                text: "Indirect Score", //Prior
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
                text: "Direct Score", //log10 BF
                font: {
                    size: 14,
                    weight: "bold",
                },
            },
            grid: {
                color: "rgba(0, 0, 0, 0.1)",
            },
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
    () => props.geneResults,
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
.pigean-scatter-container {
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
