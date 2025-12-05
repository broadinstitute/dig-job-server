<template>
    <div class="pigean-scatter-container">
        <div
            v-if="chartData.datasets[0].data.length === 0"
            class="text-center p-4 text-gray-500"
        >
            No data available for scatter plot.
        </div>
        <div v-else class="chart-wrapper">
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
                            :href="`https://a2f.hugeamp.org/pigean/geneset.html?geneset=${encodeURIComponent(tooltip.gene_set)}&genesetSize=small&traitGroup=all`"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-semibold hover:underline"
                        >
                            {{ tooltip.gene_set }}
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
                            Beta (Joint): {{ formatNumber(tooltip.beta) }}
                        </div>
                        <div>
                            Beta (Marginal):
                            {{ formatNumber(tooltip.beta_uncorrected) }}
                        </div>
                        <div>
                            # Genes: {{ tooltip.n?.toLocaleString() ?? "—" }}
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
    geneSetResults: {
        type: Array,
        default: () => [],
    },
});

const chartCanvas = ref(null);
let chartInstance = null;

const tooltipEl = ref(null);

const tooltip = ref({
    visible: false,
    pinned: false,
    canvasX: 0,
    canvasY: 0,
    showOnLeft: false,
    gene_set: "",
    beta: 0,
    beta_uncorrected: 0,
    n: 0,
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
    const dataPoints = props.geneSetResults
        .filter(
            (item) =>
                typeof item.beta_uncorrected === "number" &&
                typeof item.beta === "number",
        )
        .map((item) => ({
            x: item.beta_uncorrected,
            y: item.beta,
            gene_set: item.gene_set,
            n: item.n,
        }));

    return {
        datasets: [
            {
                label: "Gene Sets",
                data: dataPoints,
                backgroundColor: "rgba(34, 197, 94, 0.6)",
                borderColor: "rgba(34, 197, 94, 1)",
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
                gene_set: rawData.gene_set,
                beta: rawData.y,
                beta_uncorrected: rawData.x,
                n: rawData.n,
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
                        gene_set: rawData.gene_set,
                        beta: rawData.y,
                        beta_uncorrected: rawData.x,
                        n: rawData.n,
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
                text: "Beta (Marginal)",
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
                text: "Beta (Joint)",
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
    () => props.geneSetResults,
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
