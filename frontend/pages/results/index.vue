<template>
    <div class="results-container">
        <div
            v-if="error"
            class="error-message p-6 bg-red-100 text-red-700 rounded"
        >
            class="error-message p-6 bg-yellow-100 text-yellow-700 rounded" >
            <div v-if="hasWorkflowData">
                <h3 class="font-semibold mb-2">
                    Workflow Status for Dataset: {{ dataset }}
                </h3>
                <div
                    v-for="(methods, workflow) in workflowStatus"
                    :key="workflow"
                    class="mb-2"
                >
                    <div
                        v-for="(details, method) in methods"
                        :key="method"
                        class="flex justify-between items-center"
                    >
                        <span class="capitalize"
                            >{{ workflow }}/{{ method }}:</span
                        >
                        <span
                            :class="getStatusClass(details.status)"
                            class="px-2 py-1 rounded text-sm"
                        >
                            {{ details.status }}
                        </span>
                    </div>
                </div>
                <p class="mt-3 text-sm">
                    Results will be available once workflows complete
                    successfully.
                    <Button
                        label="Refresh"
                        @click="checkResultsAvailability"
                        class="ml-2"
                        size="small"
                    />
                </p>
            </div>
            <div v-else>
                <p>
                    No results or workflow information available for this
                    dataset.
                </p>
                <Button
                    label="Refresh"
                    @click="checkResultsAvailability"
                    class="ml-2"
                    size="small"
                />
            </div>
        </div>

        <div>
            <h2 class="text-2xl font-bold mb-4 text-center">
                Results for Dataset: {{ dataset }}
            </h2>
        </div>

        <div class="flex justify-between items-center">
            <Button
                label="Back to Datasets"
                icon="pi pi-arrow-left"
                @click="$router.push('/datasets')"
                class="mb-4"
                outlined
                size="small"
            />
            <Button
                icon="pi pi-download"
                :label="downloadButtonLabel"
                @click="openDownloadLink"
                :disabled="!canDownloadCurrentTab"
                size="small"
            />
        </div>

        <Card>
            <template #content>
                <Tabs :value="activeTab" @update:value="onTabChange">
                    <TabList>
                        <Tab
                            v-if="shouldShowSldscTab"
                            value="sldsc"
                            :disabled="!hasSldscResults"
                            @click="() => onTabChange({ value: 'sldsc' })"
                            >{{ sldscTabHeader }}</Tab
                        >
                        <Tab
                            v-if="shouldShowMagmaTab"
                            value="magma"
                            :disabled="!hasMagmaResults"
                            @click="() => onTabChange({ value: 'magma' })"
                            >{{ magmaTabHeader }}</Tab
                        >
                        <Tab
                            v-if="shouldShowPigeanTab"
                            value="pigean"
                            :disabled="!hasPigeanResults"
                            @click="() => onTabChange({ value: 'pigean' })"
                            >{{ pigeanTabHeader }}</Tab
                        >
                    </TabList>
                    <TabPanels>
                        <TabPanel v-if="shouldShowSldscTab" value="sldsc">
                            <!-- Show loading skeleton while workflow is running -->
                            <div v-if="sldscWorkflowRunning" class="p-4">
                                <div
                                    class="mb-4 p-4 bg-blue-100 text-blue-700 rounded"
                                >
                                    <div
                                        class="flex items-center justify-between"
                                    >
                                        <div>
                                            <h3 class="font-semibold mb-1">
                                                SLDSC Analysis Running
                                            </h3>
                                            <p class="text-sm">
                                                The SLDSC workflow is currently
                                                processing. Results will be
                                                available once complete.
                                            </p>
                                            <p class="text-sm mt-1">
                                                Status:
                                                {{ sldscWorkflowStatus }}
                                            </p>
                                        </div>
                                        <Button
                                            label="Refresh"
                                            @click="checkResultsAvailability"
                                            class="ml-2"
                                            size="small"
                                        />
                                    </div>
                                </div>
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>

                            <div v-else>
                                <!-- SLDSC Results Section -->
                                <div
                                    class="mb-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
                                >
                                    <div
                                        class="flex items-center justify-between mb-4"
                                    >
                                        <h3
                                            class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                                        >
                                            SLDSC Results
                                        </h3>
                                        <Tag
                                            v-if="sldscTotalRecords > 0"
                                            :value="`${sldscTotalRecords} results`"
                                            severity="info"
                                        />
                                    </div>

                                    <!-- Loading skeleton -->
                                    <div
                                        v-if="
                                            sldscLoading &&
                                            sldscResults.length === 0
                                        "
                                        class="p-4"
                                    >
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading SLDSC results...</span
                                            >
                                        </div>
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>

                                    <!-- SLDSC Results Table -->
                                    <DataTable
                                        v-else-if="sldscResults.length > 0"
                                        :first="sldscFirst"
                                        :rows="sldscRows"
                                        :sortField="sldscSortField"
                                        :sortOrder="sldscSortOrder"
                                        :value="sldscResults"
                                        ref="sldscDt"
                                        :lazy="true"
                                        :totalRecords="sldscTotalRecords"
                                        :loading="sldscLoading"
                                        paginator
                                        :rows-per-page-options="[10, 20, 50]"
                                        @page="onSldscPage"
                                        @sort="onSldscSort"
                                        :filters="filters"
                                        @filter="onSldscFilter"
                                        stripedRows
                                        class="p-datatable-sm"
                                        filterDisplay="row"
                                        :showFilterOperator="false"
                                        :showFilterMatchModes="false"
                                        :showFilterMenu="false"
                                        :showClearButton="false"
                                    >
                                        <Column
                                            field="annotation"
                                            header="Annotation"
                                            sortable
                                            filterMatchMode="equals"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <Select
                                                    v-model="
                                                        filters['annotation']
                                                            .value
                                                    "
                                                    :options="annotationOptions"
                                                    optionLabel="label"
                                                    optionValue="value"
                                                    placeholder="Select annotation"
                                                    class="p-column-filter w-full"
                                                    @change="onSldscFilter"
                                                />
                                            </template>
                                            <template #body="{ data }">
                                                <div class="flex items-center">
                                                    <div
                                                        :class="
                                                            'color-dot ' +
                                                            data.annotation
                                                        "
                                                    ></div>
                                                    <span class="ml-2">{{
                                                        data.annotation
                                                    }}</span>
                                                </div>
                                            </template>
                                        </Column>
                                        <Column
                                            field="tissue"
                                            header="Tissue"
                                            sortable
                                            filterMatchMode="equals"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <Select
                                                    v-model="
                                                        filters['tissue'].value
                                                    "
                                                    :options="tissueOptions"
                                                    optionLabel="label"
                                                    optionValue="value"
                                                    placeholder="Select tissue"
                                                    class="p-column-filter w-full"
                                                    @change="onSldscFilter"
                                                />
                                            </template>
                                        </Column>
                                        <Column
                                            field="biosample"
                                            header="Biosample"
                                            sortable
                                            filterMatchMode="equals"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <AutoComplete
                                                    v-model="
                                                        biosampleFilterInput
                                                    "
                                                    :suggestions="
                                                        filteredBiosamples
                                                    "
                                                    @complete="searchBiosamples"
                                                    placeholder="Search biosample"
                                                    class="p-column-filter w-full"
                                                    @item-select="
                                                        onBiosampleSelect
                                                    "
                                                    @clear="onBiosampleClear"
                                                    :delay="300"
                                                    dropdown
                                                    forceSelection
                                                />
                                            </template>
                                        </Column>
                                        <Column
                                            field="enrichment"
                                            header="Enrichment"
                                            sortable
                                            filterMatchMode="gte"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <div
                                                    class="flex items-center gap-2"
                                                >
                                                    <InputNumber
                                                        v-model="
                                                            filters[
                                                                'enrichment'
                                                            ].value
                                                        "
                                                        placeholder="≥ Value"
                                                        class="p-column-filter w-full"
                                                        :minFractionDigits="3"
                                                        :maxFractionDigits="3"
                                                        @keydown.enter="
                                                            onSldscFilter
                                                        "
                                                    />
                                                </div>
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data
                                                            .enrichment,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="pValue"
                                            header="P-Value"
                                            sortable
                                            filterMatchMode="lte"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <div
                                                    class="flex items-center gap-2"
                                                >
                                                    <InputNumber
                                                        v-model="
                                                            filters['pValue']
                                                                .value
                                                        "
                                                        placeholder="≤ Value"
                                                        class="p-column-filter w-full"
                                                        mode="decimal"
                                                        :minFractionDigits="3"
                                                        :maxFractionDigits="3"
                                                        @keydown.enter="
                                                            onSldscFilter
                                                        "
                                                    />
                                                </div>
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatPValue(
                                                        slotProps.data.pValue,
                                                    )
                                                }}
                                            </template>
                                        </Column>

                                        <template #empty>
                                            <div class="text-center p-4">
                                                No SLDSC results found.
                                            </div>
                                        </template>
                                        <template #loading>
                                            <div class="p-4">
                                                <div
                                                    class="mb-2"
                                                    v-for="i in 5"
                                                    :key="i"
                                                >
                                                    <Skeleton height="3rem" />
                                                </div>
                                            </div>
                                        </template>
                                    </DataTable>

                                    <!-- No results message -->
                                    <div
                                        v-else-if="!sldscLoading"
                                        class="text-center p-4"
                                    >
                                        <p class="text-gray-500">
                                            No SLDSC results available for this
                                            dataset.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div class="mt-4 flex justify-end">
                                <Button
                                    label="View SLDSC Log"
                                    icon="pi pi-file-check"
                                    @click="
                                        $router.push(
                                            `/log/${jobId}?method=sldsc`,
                                        )
                                    "
                                    size="small"
                                    outlined
                                />
                            </div>
                        </TabPanel>

                        <TabPanel v-if="shouldShowMagmaTab" value="magma">
                            <!-- Show loading skeleton while workflow is running -->
                            <div v-if="magmaWorkflowRunning" class="p-4">
                                <div
                                    class="mb-4 p-4 bg-blue-100 text-blue-700 rounded"
                                >
                                    <div
                                        class="flex items-center justify-between"
                                    >
                                        <div>
                                            <h3 class="font-semibold mb-1">
                                                MAGMA Analysis Running
                                            </h3>
                                            <p class="text-sm">
                                                The MAGMA workflow is currently
                                                processing. Results will be
                                                available once complete.
                                            </p>
                                            <p class="text-sm mt-1">
                                                Status:
                                                {{ magmaWorkflowStatus }}
                                            </p>
                                        </div>
                                        <Button
                                            label="Refresh"
                                            @click="checkResultsAvailability"
                                            class="ml-2"
                                            size="small"
                                        />
                                    </div>
                                </div>
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>

                            <div v-else>
                                <!-- MAGMA Gene Results Section -->
                                <div
                                    class="mb-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
                                >
                                    <div
                                        class="flex items-center justify-between mb-4"
                                    >
                                        <h3
                                            class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                                        >
                                            Gene Results
                                        </h3>
                                        <Tag
                                            v-if="magmaTotalRecords > 0"
                                            :value="`${magmaTotalRecords} genes`"
                                            severity="info"
                                        />
                                    </div>

                                    <!-- Gene table loading skeleton -->
                                    <div
                                        v-if="
                                            magmaLoading &&
                                            magmaResults.length === 0
                                        "
                                        class="p-4"
                                    >
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading MAGMA gene
                                                results...</span
                                            >
                                        </div>
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>

                                    <!-- Gene table -->
                                    <DataTable
                                        v-else-if="magmaResults.length > 0"
                                        :first="magmaFirst"
                                        :rows="magmaRows"
                                        :sortField="magmaSortField"
                                        :sortOrder="magmaSortOrder"
                                        :value="magmaResults"
                                        ref="magmaDt"
                                        :lazy="true"
                                        :totalRecords="magmaTotalRecords"
                                        :loading="magmaLoading"
                                        paginator
                                        :rows-per-page-options="[10, 20, 50]"
                                        @page="onMagmaPage"
                                        @sort="onMagmaSort"
                                        :filters="magmaFilters"
                                        @filter="onMagmaFilter"
                                        stripedRows
                                        class="p-datatable-sm"
                                        filterDisplay="row"
                                        :showFilterOperator="false"
                                        :showFilterMatchModes="false"
                                        :showFilterMenu="false"
                                        :showClearButton="false"
                                    >
                                        <Column
                                            field="gene"
                                            header="Gene"
                                            sortable
                                            filterMatchMode="equals"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <AutoComplete
                                                    v-model="
                                                        magmaGeneFilterInput
                                                    "
                                                    :suggestions="filteredGenes"
                                                    @complete="searchGenes"
                                                    placeholder="Search gene"
                                                    class="p-column-filter w-full"
                                                    @item-select="onGeneSelect"
                                                    @clear="onGeneClear"
                                                    :delay="300"
                                                    dropdown
                                                    forceSelection
                                                />
                                            </template>
                                            <template #body="{ data }">
                                                <a
                                                    :href="`https://a2f.hugeamp.org/gene.html?gene=${data.gene}`"
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                                >
                                                    {{ data.gene }}
                                                </a>
                                            </template>
                                        </Column>
                                        <Column
                                            field="pValue"
                                            header="P-Value"
                                            sortable
                                            filterMatchMode="lte"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        magmaFilters['pValue']
                                                            .value
                                                    "
                                                    placeholder="≤ Value"
                                                    class="p-column-filter w-full"
                                                    mode="decimal"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="9"
                                                    @keydown.enter="
                                                        onMagmaFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatPValue(
                                                        slotProps.data.pValue,
                                                    )
                                                }}
                                            </template>
                                        </Column>

                                        <template #empty>
                                            <div class="text-center p-4">
                                                No MAGMA results found.
                                            </div>
                                        </template>
                                        <template #loading>
                                            <div class="p-4">
                                                <div
                                                    class="mb-2"
                                                    v-for="i in 5"
                                                    :key="i"
                                                >
                                                    <Skeleton height="3rem" />
                                                </div>
                                            </div>
                                        </template>
                                    </DataTable>

                                    <!-- No gene results message -->
                                    <div
                                        v-else-if="!magmaLoading"
                                        class="text-center p-4 text-gray-500"
                                    >
                                        No MAGMA gene results available.
                                    </div>
                                </div>

                                <!-- MAGMA Pathway Results Section -->
                                <div
                                    class="mt-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
                                >
                                    <div
                                        class="flex items-center justify-between mb-4"
                                    >
                                        <h3
                                            class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                                        >
                                            Pathway Results
                                        </h3>
                                        <Tag
                                            v-if="magmaPathwaysTotalRecords > 0"
                                            :value="`${magmaPathwaysTotalRecords} pathways`"
                                            severity="info"
                                        />
                                    </div>

                                    <!-- Pathway table loading skeleton -->
                                    <div
                                        v-if="
                                            magmaPathwaysLoading &&
                                            magmaPathwaysResults.length === 0
                                        "
                                        class="p-4"
                                    >
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading MAGMA pathway
                                                results...</span
                                            >
                                        </div>
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>

                                    <!-- Pathway table -->
                                    <DataTable
                                        v-else-if="
                                            magmaPathwaysResults.length > 0
                                        "
                                        :first="magmaPathwaysFirst"
                                        :rows="magmaPathwaysRows"
                                        :sortField="magmaPathwaysSortField"
                                        :sortOrder="magmaPathwaysSortOrder"
                                        :value="magmaPathwaysResults"
                                        ref="magmaPathwaysDt"
                                        :lazy="true"
                                        :totalRecords="
                                            magmaPathwaysTotalRecords
                                        "
                                        :loading="magmaPathwaysLoading"
                                        paginator
                                        :rows-per-page-options="[10, 20, 50]"
                                        @page="onMagmaPathwaysPage"
                                        @sort="onMagmaPathwaysSort"
                                        :filters="magmaPathwaysFilters"
                                        @filter="onMagmaPathwaysFilter"
                                        stripedRows
                                        class="p-datatable-sm"
                                        filterDisplay="row"
                                        :showFilterOperator="false"
                                        :showFilterMatchModes="false"
                                        :showFilterMenu="false"
                                        :showClearButton="false"
                                    >
                                        <Column
                                            field="pathwayName"
                                            header="Pathway"
                                            sortable
                                            filterMatchMode="contains"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputText
                                                    v-model="
                                                        magmaPathwaysFilters[
                                                            'pathwayName'
                                                        ].value
                                                    "
                                                    placeholder="Search pathway"
                                                    class="p-column-filter w-full"
                                                    @keydown.enter="
                                                        onMagmaPathwaysFilter
                                                    "
                                                />
                                            </template>
                                        </Column>
                                        <Column
                                            field="pValue"
                                            header="P-Value"
                                            sortable
                                            filterMatchMode="lte"
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        magmaPathwaysFilters[
                                                            'pValue'
                                                        ].value
                                                    "
                                                    placeholder="≤ Value"
                                                    class="p-column-filter w-full"
                                                    mode="decimal"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="9"
                                                    @keydown.enter="
                                                        onMagmaPathwaysFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatPValue(
                                                        slotProps.data.pValue,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="numGenes"
                                            header="# Genes"
                                            sortable
                                        ></Column>
                                        <Column
                                            field="beta"
                                            header="Beta"
                                            sortable
                                        >
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data.beta,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="stdErr"
                                            header="SE"
                                            sortable
                                        >
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data.stdErr,
                                                    )
                                                }}
                                            </template>
                                        </Column>

                                        <template #empty>
                                            <div class="text-center p-4">
                                                No MAGMA pathway results found.
                                            </div>
                                        </template>
                                        <template #loading>
                                            <div class="p-4">
                                                <div
                                                    class="mb-2"
                                                    v-for="i in 5"
                                                    :key="i"
                                                >
                                                    <Skeleton height="3rem" />
                                                </div>
                                            </div>
                                        </template>
                                    </DataTable>

                                    <!-- No pathway results message -->
                                    <div
                                        v-else-if="!magmaPathwaysLoading"
                                        class="text-center p-4 text-gray-500"
                                    >
                                        No MAGMA pathway results available.
                                    </div>
                                </div>
                            </div>

                            <div class="mt-4 flex justify-end">
                                <Button
                                    label="View MAGMA Log"
                                    icon="pi pi-file-check"
                                    @click="
                                        $router.push(
                                            `/log/${jobId}?method=magma`,
                                        )
                                    "
                                    size="small"
                                    outlined
                                />
                            </div>
                        </TabPanel>

                        <TabPanel v-if="shouldShowPigeanTab" value="pigean">
                            <div v-if="pigeanWorkflowRunning" class="p-4">
                                <div
                                    class="mb-4 p-4 bg-blue-100 text-blue-700 rounded"
                                >
                                    <div
                                        class="flex items-center justify-between"
                                    >
                                        <div>
                                            <h3 class="font-semibold mb-1">
                                                PIGEAN Analysis Running
                                            </h3>
                                            <p class="text-sm">
                                                The PIGEAN workflow is currently
                                                processing. Results will be
                                                available once complete.
                                            </p>
                                            <p class="text-sm mt-1">
                                                Status:
                                                {{ pigeanWorkflowStatus }}
                                            </p>
                                        </div>
                                        <Button
                                            label="Refresh"
                                            @click="checkResultsAvailability"
                                            class="ml-2"
                                            size="small"
                                        />
                                    </div>
                                </div>
                                <div class="mb-2" v-for="i in 5" :key="i">
                                    <Skeleton height="3rem" />
                                </div>
                            </div>

                            <div v-else>
                                <!-- Gene Results Section -->
                                <div
                                    class="mb-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
                                >
                                    <div
                                        class="flex items-center justify-between mb-4"
                                    >
                                        <h3
                                            class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                                        >
                                            Gene Results
                                        </h3>
                                        <Tag
                                            v-if="pigeanGeneTotalRecords > 0"
                                            :value="`${pigeanGeneTotalRecords} genes`"
                                            severity="info"
                                        />
                                    </div>

                                    <!-- Gene Scatter Plot - uses filtered data -->
                                    <div
                                        v-if="pigeanGeneDataLoaded"
                                        class="mb-6"
                                    >
                                        <PigeanGeneScatterPlot
                                            :geneResults="
                                                filteredPigeanGeneData
                                            "
                                            :key="pigeanChartKey"
                                        />
                                    </div>
                                    <div
                                        v-else-if="pigeanGeneLoading"
                                        class="mb-6"
                                    >
                                        <h4 class="font-semibold text-lg mb-3">
                                            Gene Support Plot
                                        </h4>
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading scatter plot
                                                data...</span
                                            >
                                        </div>
                                        <Skeleton height="400px" />
                                    </div>

                                    <!-- Gene table loading skeleton -->
                                    <div
                                        v-if="
                                            pigeanGeneLoading &&
                                            pigeanGeneAllData.length === 0
                                        "
                                        class="p-4"
                                    >
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading PIGEAN gene
                                                results...</span
                                            >
                                        </div>
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>

                                    <!-- Gene table (client-side pagination) -->
                                    <DataTable
                                        v-else
                                        :value="paginatedPigeanGeneData"
                                        dataKey="gene"
                                        :first="pigeanGeneFirst"
                                        :rows="pigeanGeneRows"
                                        :sortField="pigeanGeneSortField"
                                        :sortOrder="pigeanGeneSortOrder"
                                        :totalRecords="pigeanGeneTotalRecords"
                                        paginator
                                        :rows-per-page-options="[10, 20, 50]"
                                        :filters="pigeanGeneFilters"
                                        @page="onPigeanGenePage"
                                        @sort="onPigeanGeneSort"
                                        :expandedRows="pigeanGeneExpandedRows"
                                        @update:expandedRows="
                                            onPigeanGeneExpandedRowsChange
                                        "
                                        stripedRows
                                        class="p-datatable-sm"
                                        filterDisplay="row"
                                        :showFilterOperator="false"
                                        :showFilterMatchModes="false"
                                        :showFilterMenu="false"
                                        :showClearButton="false"
                                    >
                                        <Column
                                            field="gene"
                                            header="Gene"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <AutoComplete
                                                    v-model="
                                                        pigeanGeneFilterInput
                                                    "
                                                    :suggestions="
                                                        pigeanGeneSuggestions
                                                    "
                                                    @complete="
                                                        onPigeanGeneComplete
                                                    "
                                                    @item-select="
                                                        onPigeanGeneSelect
                                                    "
                                                    @clear="onPigeanGeneClear"
                                                    placeholder="Search gene"
                                                    class="p-column-filter"
                                                    fluid
                                                    showClear
                                                />
                                            </template>
                                            <template #body="{ data }">
                                                <a
                                                    :href="`https://a2f.hugeamp.org/pigean/gene.html?gene=${data.gene}`"
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                                >
                                                    {{ data.gene }}
                                                </a>
                                            </template>
                                        </Column>

                                        <Column
                                            field="combined"
                                            header="Combined Score"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneFilters[
                                                            'combined'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="3"
                                                    showClear
                                                    @keydown.enter="
                                                        onPigeanGeneFilter
                                                    "
                                                    @update:modelValue="
                                                        onPigeanGeneFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data
                                                            .combined || 0,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="huge_score"
                                            header="HuGE Score"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneFilters[
                                                            'huge_score'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="3"
                                                    showClear
                                                    @keydown.enter="
                                                        onPigeanGeneFilter
                                                    "
                                                    @update:modelValue="
                                                        onPigeanGeneFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data
                                                            .huge_score || 0,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="log_bf"
                                            header="log10 BF"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneFilters[
                                                            'log_bf'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="3"
                                                    showClear
                                                    @keydown.enter="
                                                        onPigeanGeneFilter
                                                    "
                                                    @update:modelValue="
                                                        onPigeanGeneFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data.log_bf ||
                                                            0,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="prior"
                                            header="Prior"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneFilters[
                                                            'prior'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="6"
                                                    showClear
                                                    @keydown.enter="
                                                        onPigeanGeneFilter
                                                    "
                                                    @update:modelValue="
                                                        onPigeanGeneFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data.prior ||
                                                            0,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="n"
                                            header="# Gene Sets"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneFilters['n']
                                                            .value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="0"
                                                    :maxFractionDigits="0"
                                                    showClear
                                                    @keydown.enter="
                                                        onPigeanGeneFilter
                                                    "
                                                    @update:modelValue="
                                                        onPigeanGeneFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    slotProps.data.n !== null &&
                                                    slotProps.data.n !==
                                                        undefined
                                                        ? slotProps.data.n.toLocaleString()
                                                        : "—"
                                                }}
                                            </template>
                                        </Column>
                                        <Column header="Gene Sets">
                                            <template #body="{ data }">
                                                <span
                                                    class="inline-flex"
                                                    v-tooltip.left="
                                                        !data?.gene_sets?.length
                                                            ? 'No data available'
                                                            : null
                                                    "
                                                >
                                                    <Button
                                                        size="small"
                                                        outlined
                                                        :label="
                                                            isPigeanGeneRowExpanded(
                                                                data,
                                                            )
                                                                ? 'Hide'
                                                                : 'Show'
                                                        "
                                                        :disabled="
                                                            !data?.gene_sets
                                                                ?.length
                                                        "
                                                        @click="
                                                            togglePigeanGeneRow(
                                                                data,
                                                            )
                                                        "
                                                    />
                                                </span>
                                            </template>
                                        </Column>

                                        <template #expansion="slotProps">
                                            <div
                                                class="p-4 bg-gray-50 dark:bg-gray-800 rounded"
                                            >
                                                <h4 class="font-semibold mb-2">
                                                    Gene Sets for
                                                    {{ slotProps.data.gene }}
                                                </h4>

                                                <DataTable
                                                    v-if="
                                                        slotProps.data
                                                            ?.gene_sets?.length
                                                    "
                                                    :value="
                                                        slotProps.data.gene_sets
                                                    "
                                                    size="small"
                                                    class="p-datatable-sm"
                                                    paginator
                                                    :rows="5"
                                                    :rowsPerPageOptions="[
                                                        5, 10, 20,
                                                    ]"
                                                >
                                                    <Column
                                                        field="gene_set"
                                                        header="Gene Set"
                                                    >
                                                        <template
                                                            #body="{ data }"
                                                        >
                                                            <a
                                                                v-if="
                                                                    data?.gene_set
                                                                "
                                                                :href="`https://a2f.hugeamp.org/pigean/geneset.html?geneset=${encodeURIComponent(
                                                                    data.gene_set,
                                                                )}&genesetSize=small&traitGroup=all`"
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                                            >
                                                                {{
                                                                    data.gene_set
                                                                }}
                                                            </a>
                                                            <span v-else
                                                                >—</span
                                                            >
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="combined"
                                                        header="Combined Score"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .combined ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .combined,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="beta"
                                                        header="Beta (Joint)"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .beta ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .beta,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="beta_uncorrected"
                                                        header="Beta (Marginal)"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .beta_uncorrected ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .beta_uncorrected,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="prior"
                                                        header="Prior"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .prior ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .prior,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="log_bf"
                                                        header="log10 BF"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .log_bf ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .log_bf,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                </DataTable>

                                                <div
                                                    v-else
                                                    class="text-sm text-gray-500"
                                                >
                                                    No gene-set details
                                                    available for this gene.
                                                </div>
                                            </div>
                                        </template>

                                        <template #empty>
                                            <div class="text-center p-4">
                                                No PIGEAN gene results found.
                                            </div>
                                        </template>
                                    </DataTable>
                                </div>

                                <!-- Gene Set Results Section -->
                                <div
                                    class="mt-8 p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm"
                                >
                                    <div
                                        class="flex items-center justify-between mb-4"
                                    >
                                        <h3
                                            class="font-semibold text-xl text-gray-800 dark:text-gray-100"
                                        >
                                            Gene Set Results
                                        </h3>
                                        <Tag
                                            v-if="pigeanGeneSetTotalRecords > 0"
                                            :value="`${pigeanGeneSetTotalRecords} gene sets`"
                                            severity="info"
                                        />
                                    </div>

                                    <!-- Gene Set Scatter Plot -->
                                    <div
                                        v-if="pigeanGeneSetDataLoaded"
                                        class="mb-6"
                                    >
                                        <PigeanGeneSetScatterPlot
                                            :geneSetResults="
                                                pigeanGeneSetResults
                                            "
                                            :key="pigeanGeneSetChartKey"
                                        />
                                    </div>
                                    <div
                                        v-else-if="pigeanGeneSetLoading"
                                        class="mb-6"
                                    >
                                        <h4 class="font-semibold text-lg mb-3">
                                            Gene Set Plot
                                        </h4>
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading scatter plot
                                                data...</span
                                            >
                                        </div>
                                        <Skeleton height="400px" />
                                    </div>

                                    <!-- Gene set table loading skeleton -->
                                    <div
                                        v-if="
                                            pigeanGeneSetLoading &&
                                            pigeanGeneSetResults.length === 0
                                        "
                                        class="p-4"
                                    >
                                        <div
                                            class="flex items-center gap-2 text-sm text-gray-500 mb-3"
                                        >
                                            <i
                                                class="pi pi-spinner pi-spin text-primary"
                                            ></i>
                                            <span
                                                >Loading PIGEAN gene set
                                                results...</span
                                            >
                                        </div>
                                        <div
                                            class="mb-2"
                                            v-for="i in 5"
                                            :key="i"
                                        >
                                            <Skeleton height="3rem" />
                                        </div>
                                    </div>

                                    <!-- Gene set table -->
                                    <DataTable
                                        v-else
                                        :value="pigeanGeneSetResults"
                                        dataKey="gene_set"
                                        :first="pigeanGeneSetFirst"
                                        :rows="pigeanGeneSetRows"
                                        :sortField="pigeanGeneSetSortField"
                                        :sortOrder="pigeanGeneSetSortOrder"
                                        :totalRecords="
                                            pigeanGeneSetTotalRecords
                                        "
                                        :lazy="true"
                                        paginator
                                        :rows-per-page-options="[10, 20, 50]"
                                        :loading="pigeanGeneSetLoading"
                                        :filters="pigeanGeneSetFilters"
                                        @page="onPigeanGeneSetPage"
                                        @sort="onPigeanGeneSetSort"
                                        @filter="onPigeanGeneSetFilter"
                                        :expandedRows="
                                            pigeanGeneSetExpandedRows
                                        "
                                        @update:expandedRows="
                                            onPigeanGeneSetExpandedRowsChange
                                        "
                                        stripedRows
                                        class="p-datatable-sm"
                                        filterDisplay="row"
                                        :showFilterOperator="false"
                                        :showFilterMatchModes="false"
                                        :showFilterMenu="false"
                                        :showClearButton="false"
                                    >
                                        <Column
                                            field="gene_set"
                                            header="Gene Set"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <AutoComplete
                                                    v-model="
                                                        pigeanGeneSetFilterInput
                                                    "
                                                    :suggestions="
                                                        pigeanGeneSetSuggestions
                                                    "
                                                    @complete="
                                                        onPigeanGeneSetComplete
                                                    "
                                                    @item-select="
                                                        onPigeanGeneSetSelect
                                                    "
                                                    @clear="
                                                        onPigeanGeneSetClear
                                                    "
                                                    placeholder="Search gene set"
                                                    class="p-column-filter"
                                                    fluid
                                                    showClear
                                                />
                                            </template>
                                            <template #body="{ data }">
                                                <a
                                                    :href="`https://a2f.hugeamp.org/pigean/geneset.html?geneset=${encodeURIComponent(
                                                        data.gene_set || '',
                                                    )}&genesetSize=small&traitGroup=all`"
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                                >
                                                    {{ data.gene_set }}
                                                </a>
                                            </template>
                                        </Column>
                                        <Column
                                            field="beta_uncorrected"
                                            header="Beta (Marginal)"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneSetFilters[
                                                            'beta_uncorrected'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="3"
                                                    @keydown.enter="
                                                        onPigeanGeneSetFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data
                                                            .beta_uncorrected ||
                                                            0,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="beta"
                                            header="Beta (Joint)"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneSetFilters[
                                                            'beta'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="3"
                                                    :maxFractionDigits="3"
                                                    @keydown.enter="
                                                        onPigeanGeneSetFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    formatNumber(
                                                        slotProps.data.beta ||
                                                            0,
                                                    )
                                                }}
                                            </template>
                                        </Column>
                                        <Column
                                            field="n"
                                            header="# Genes"
                                            sortable
                                            :showFilterMenu="false"
                                        >
                                            <template #filter>
                                                <InputNumber
                                                    v-model="
                                                        pigeanGeneSetFilters[
                                                            'n'
                                                        ].value
                                                    "
                                                    placeholder="≥ Value"
                                                    class="p-column-filter w-full"
                                                    :minFractionDigits="0"
                                                    :maxFractionDigits="0"
                                                    @keydown.enter="
                                                        onPigeanGeneSetFilter
                                                    "
                                                />
                                            </template>
                                            <template #body="slotProps">
                                                {{
                                                    slotProps.data.n !== null &&
                                                    slotProps.data.n !==
                                                        undefined
                                                        ? slotProps.data.n.toLocaleString()
                                                        : "—"
                                                }}
                                            </template>
                                        </Column>
                                        <Column header="Genes">
                                            <template #body="{ data }">
                                                <span
                                                    class="inline-flex"
                                                    v-tooltip.left="
                                                        !data?.genes?.length
                                                            ? 'No data available'
                                                            : null
                                                    "
                                                >
                                                    <Button
                                                        size="small"
                                                        outlined
                                                        :label="
                                                            isPigeanGeneSetRowExpanded(
                                                                data.gene_set,
                                                            )
                                                                ? 'Hide'
                                                                : 'Show'
                                                        "
                                                        :disabled="
                                                            !data?.genes?.length
                                                        "
                                                        @click="
                                                            togglePigeanGeneSetRow(
                                                                data,
                                                            )
                                                        "
                                                    />
                                                </span>
                                            </template>
                                        </Column>

                                        <template #expansion="slotProps">
                                            <div
                                                class="p-4 bg-gray-50 dark:bg-gray-800 rounded"
                                            >
                                                <h4 class="font-semibold mb-2">
                                                    Genes in
                                                    {{
                                                        slotProps.data.gene_set
                                                    }}
                                                </h4>
                                                <DataTable
                                                    v-if="
                                                        slotProps.data?.genes
                                                            ?.length
                                                    "
                                                    :value="
                                                        slotProps.data.genes
                                                    "
                                                    size="small"
                                                    class="p-datatable-sm"
                                                    paginator
                                                    :rows="5"
                                                    :rowsPerPageOptions="[
                                                        5, 10, 20,
                                                    ]"
                                                >
                                                    <Column
                                                        field="gene"
                                                        header="Gene"
                                                    >
                                                        <template
                                                            #body="{ data }"
                                                        >
                                                            <a
                                                                v-if="
                                                                    data?.gene
                                                                "
                                                                :href="`https://a2f.hugeamp.org/pigean/gene.html?gene=${data.gene}`"
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                                                            >
                                                                {{ data.gene }}
                                                            </a>
                                                            <span v-else
                                                                >—</span
                                                            >
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="combined"
                                                        header="Combined Score"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .combined ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .combined,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="beta_uncorrected"
                                                        header="Beta (Marginal)"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .beta_uncorrected ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .beta_uncorrected,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="beta"
                                                        header="Beta (Joint)"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .beta ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .beta,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="prior"
                                                        header="Prior"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .prior ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .prior,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                    <Column
                                                        field="log_bf"
                                                        header="log10 BF"
                                                    >
                                                        <template #body="row">
                                                            {{
                                                                typeof row.data
                                                                    .log_bf ===
                                                                "number"
                                                                    ? formatNumber(
                                                                          row
                                                                              .data
                                                                              .log_bf,
                                                                      )
                                                                    : "—"
                                                            }}
                                                        </template>
                                                    </Column>
                                                </DataTable>
                                                <div
                                                    v-else
                                                    class="text-sm text-gray-500"
                                                >
                                                    No gene-level details
                                                    available for this gene set.
                                                </div>
                                            </div>
                                        </template>

                                        <template #empty>
                                            <div class="text-center p-4">
                                                No PIGEAN gene set results
                                                found.
                                            </div>
                                        </template>
                                    </DataTable>
                                </div>
                            </div>

                            <div class="mt-4 flex justify-end">
                                <Button
                                    label="View PIGEAN Log"
                                    icon="pi pi-file-check"
                                    @click="
                                        $router.push(
                                            `/log/${jobId}?method=pigean`,
                                        )
                                    "
                                    size="small"
                                    outlined
                                />
                            </div>
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from "vue";
import { useResultsStore } from "~/stores/ResultsStore.js";
const route = useRoute();
const router = useRouter();
import { storeToRefs } from "pinia";

const resultsStore = useResultsStore();

const dataset = ref(route.query.dataset);
const tab = ref(route.query.tab || "sldsc");
const filteredBiosamples = ref([]);
const filteredGenes = ref([]);

// Tab management
const activeTab = ref(route.query.tab || "sldsc");

// Workflow status tracking
const workflowStatus = ref({});
const hasWorkflowData = ref(false);

// SLDSC specific data
const sldscResults = ref([]);
const sldscTotalRecords = ref(0);
const sldscLoading = ref(false);
const sldscFirst = ref(0);
const sldscRows = ref(10);
const sldscSortField = ref("pValue");
const sldscSortOrder = ref(1);
const sldscDt = ref();
const hasSldscResults = ref(false);

// MAGMA specific data
const magmaResults = ref([]);
const magmaTotalRecords = ref(0);
const magmaLoading = ref(false);
const magmaFirst = ref(0);
const magmaRows = ref(10);
const magmaSortField = ref("pValue");
const magmaSortOrder = ref(1);
const magmaDt = ref();
const hasMagmaResults = ref(false);

// MAGMA Pathways specific data
const magmaPathwaysResults = ref([]);
const magmaPathwaysTotalRecords = ref(0);
const magmaPathwaysLoading = ref(false);
const magmaPathwaysFirst = ref(0);
const magmaPathwaysRows = ref(10);
const magmaPathwaysSortField = ref("pValue");
const magmaPathwaysSortOrder = ref(1);
const magmaPathwaysDt = ref();
const hasMagmaPathwaysResults = ref(false);

// PIGEAN specific data
const pigeanGeneAllData = ref([]); // All fetched data (top 1000)
const pigeanGeneLoading = ref(false);
const pigeanGeneFirst = ref(0);
const pigeanGeneRows = ref(10);
const pigeanGeneSortField = ref("combined");
const pigeanGeneSortOrder = ref(-1);
const pigeanGeneExpandedRows = ref({});

const pigeanGeneSetResults = ref([]);
const pigeanGeneSetTotalRecords = ref(0);
const pigeanGeneSetLoading = ref(false);
const pigeanGeneSetFirst = ref(0);
const pigeanGeneSetRows = ref(10);
const pigeanGeneSetSortField = ref("beta");
const pigeanGeneSetSortOrder = ref(-1);
const pigeanGeneSetSubRecords = ref({});
const pigeanGeneSetExpandedRows = ref({});

const hasPigeanGeneResults = ref(false);
const hasPigeanGeneSetResults = ref(false);

// Flags to track if data has been loaded (prevent repeated fetches)
const pigeanGeneDataLoaded = ref(false);
const pigeanGeneSetDataLoaded = ref(false);

// Job IDs for linking to logs
const sldscJobId = ref(null);
const magmaJobId = ref(null);
const magmaPathwaysJobId = ref(null);
const pigeanJobId = ref(null);

// Shared data from store
const {
    error,
    tissues: apiTissues,
    biosamples: apiBiosamples,
    annotations: apiAnnotations,
    genes: apiGenes,
} = storeToRefs(resultsStore);

// Computed properties for tab headers
const sldscTabHeader = computed(() => {
    return "SLDSC";
});

const magmaTabHeader = computed(() => {
    return "MAGMA";
});

const pigeanTabHeader = computed(() => {
    return "PIGEAN";
});

// Computed properties for tab visibility and workflow status
const shouldShowSldscTab = computed(() => {
    // Only show if workflow succeeded OR if we have data (fallback)
    const sldscStatus =
        workflowStatus.value.ldsc?.ldsc?.status ||
        workflowStatus.value.sldsc?.sldsc?.status;

    if (hasWorkflowData.value) {
        // If we have workflow data, only show if succeeded
        return sldscStatus === "SUCCEEDED" || hasSldscResults.value;
    } else {
        // Fallback: show if we have results data
        return hasSldscResults.value;
    }
});

const shouldShowMagmaTab = computed(() => {
    // Only show if workflow succeeded OR if we have data (fallback)
    const magmaStatus = workflowStatus.value.magma?.magma?.status;

    if (hasWorkflowData.value) {
        // If we have workflow data, only show if succeeded
        return magmaStatus === "SUCCEEDED" || hasMagmaResults.value;
    } else {
        // Fallback: show if we have results data
        return hasMagmaResults.value;
    }
});

const hasPigeanResults = computed(() => {
    return hasPigeanGeneResults.value || hasPigeanGeneSetResults.value;
});

const shouldShowPigeanTab = computed(() => {
    const pigeanStatus = workflowStatus.value.pigean?.pigean?.status;

    if (hasWorkflowData.value) {
        return pigeanStatus === "SUCCEEDED" || hasPigeanResults.value;
    }

    return hasPigeanResults.value;
});

// Client-side filtering for PIGEAN gene data
const filteredPigeanGeneData = computed(() => {
    let data = [...pigeanGeneAllData.value];

    // Apply filters
    const filters = pigeanGeneFilters.value;

    // Gene name filter (case-insensitive contains)
    if (filters.gene?.value) {
        const searchTerm = filters.gene.value.toLowerCase();
        data = data.filter((item) =>
            item.gene?.toLowerCase().includes(searchTerm),
        );
    }
    if (filters.combined?.value != null) {
        data = data.filter((item) => item.combined >= filters.combined.value);
    }
    if (filters.huge_score?.value != null) {
        data = data.filter(
            (item) => item.huge_score >= filters.huge_score.value,
        );
    }
    if (filters.log_bf?.value != null) {
        data = data.filter((item) => item.log_bf >= filters.log_bf.value);
    }
    if (filters.prior?.value != null) {
        data = data.filter((item) => item.prior >= filters.prior.value);
    }
    if (filters.n?.value != null) {
        data = data.filter((item) => item.n >= filters.n.value);
    }

    // Apply sorting
    if (pigeanGeneSortField.value) {
        const field = pigeanGeneSortField.value;
        const order = pigeanGeneSortOrder.value || 1;
        data.sort((a, b) => {
            const aVal = a[field] ?? 0;
            const bVal = b[field] ?? 0;
            if (aVal < bVal) return -1 * order;
            if (aVal > bVal) return 1 * order;
            return 0;
        });
    }

    return data;
});

// Total records after filtering (for pagination)
const pigeanGeneTotalRecords = computed(() => {
    return filteredPigeanGeneData.value.length;
});

// Key for forcing chart re-render when filters change
const pigeanChartKey = computed(() => {
    return `pigean-chart-${dataset.value}-${pigeanGeneTotalRecords.value}`;
});

// Key for forcing gene set chart re-render when data changes
const pigeanGeneSetChartKey = computed(() => {
    return `pigean-geneset-chart-${dataset.value}-${pigeanGeneSetTotalRecords.value}`;
});

// Client-side pagination for PIGEAN gene table
const paginatedPigeanGeneData = computed(() => {
    const start = pigeanGeneFirst.value;
    const end = start + pigeanGeneRows.value;
    return filteredPigeanGeneData.value.slice(start, end);
});

const sldscWorkflowStatus = computed(() => {
    return (
        workflowStatus.value.ldsc?.ldsc?.status ||
        workflowStatus.value.sldsc?.sldsc?.status ||
        null
    );
});

const magmaWorkflowStatus = computed(() => {
    return workflowStatus.value.magma?.magma?.status || null;
});

const pigeanWorkflowStatus = computed(() => {
    return workflowStatus.value.pigean?.pigean?.status || null;
});

const sldscWorkflowRunning = computed(() => {
    const status = sldscWorkflowStatus.value;
    return (
        status &&
        ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
            status.toUpperCase(),
        )
    );
});

const magmaWorkflowRunning = computed(() => {
    const status = magmaWorkflowStatus.value;
    return (
        status &&
        ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
            status.toUpperCase(),
        )
    );
});

const pigeanWorkflowRunning = computed(() => {
    const status = pigeanWorkflowStatus.value;
    return (
        status &&
        ["RUNNING", "RUNNABLE", "PENDING", "SUBMITTED"].includes(
            status.toUpperCase(),
        )
    );
});
const canDownloadCurrentTab = computed(() => {
    if (activeTab.value === "magma") {
        return hasMagmaResults.value;
    }
    if (activeTab.value === "pigean") {
        return hasPigeanResults.value;
    }
    return hasSldscResults.value;
});

// Computed property to find a job ID for viewing logs
const jobId = computed(() => {
    // Use the job ID from the API response based on active tab
    if (activeTab.value === "magma" && magmaJobId.value) {
        return magmaJobId.value;
    } else if (activeTab.value === "sldsc" && sldscJobId.value) {
        return sldscJobId.value;
    } else if (activeTab.value === "pigean" && pigeanJobId.value) {
        return pigeanJobId.value;
    }

    // Fallback to workflow status job ID
    if (workflowStatus.value) {
        const workflows = workflowStatus.value;

        if (activeTab.value === "magma" && workflows.magma?.magma?.job_id) {
            return workflows.magma.magma.job_id;
        } else if (activeTab.value === "sldsc") {
            // Check both sldsc and ldsc for SLDSC tab
            if (workflows.sldsc?.sldsc?.job_id) {
                return workflows.sldsc.sldsc.job_id;
            } else if (workflows.ldsc?.ldsc?.job_id) {
                return workflows.ldsc.ldsc.job_id;
            }
        } else if (
            activeTab.value === "pigean" &&
            workflows.pigean?.pigean?.job_id
        ) {
            return workflows.pigean.pigean.job_id;
        }
    }

    // Final fallback to dataset name
    return dataset.value;
});
const downloadButtonLabel = computed(() => {
    return `Download ${activeTab.value.toUpperCase()} Results`;
});

const formatNumber = (value) => {
    return new Intl.NumberFormat("en-US", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
    }).format(value);
};

const config = useRuntimeConfig();
const downloadUrl = computed(() => {
    let resultTypeParam = "ldsc";
    if (activeTab.value === "magma") {
        resultTypeParam = "magma";
    } else if (activeTab.value === "pigean") {
        resultTypeParam = "pigean";
    }
    return `${config.public.apiBaseUrl}/api/download/${dataset.value}?result_type=${resultTypeParam}`;
});

function openDownloadLink() {
    window.open(
        downloadUrl.value + `&token=${localStorage.getItem("authToken")}`,
        "_blank",
    );
}

const formatPValue = (value) => {
    if (value < 0.001) {
        return value.toExponential(2);
    }
    return value.toFixed(3);
};

const getStatusClass = (status) => {
    if (!status) return "bg-gray-200 text-gray-700";

    switch (status.toUpperCase()) {
        case "SUCCEEDED":
            return "bg-green-200 text-green-800";
        case "FAILED":
            return "bg-red-200 text-red-800";
        case "RUNNING":
            return "bg-yellow-200 text-yellow-800";
        case "PENDING":
            return "bg-blue-200 text-blue-800";
        case "SUBMITTED":
            return "bg-yellow-200 text-yellow-800";
        default:
            return "bg-gray-200 text-gray-700";
    }
};

// Define options for dropdowns
const annotationOptions = computed(() => {
    if (!apiAnnotations.value || apiAnnotations.value.length === 0) {
        return [
            { label: "All Annotations", value: null },
            { label: "Binding Sites", value: "binding_sites" },
            { label: "Accessible Chromatin", value: "accessible_chromatin" },
            { label: "Enhancer", value: "enhancer" },
            { label: "Promoter", value: "promoter" },
        ];
    }

    return [
        { label: "All Annotations", value: null },
        ...apiAnnotations.value.map((annotation) => ({
            label: annotation,
            value: annotation,
        })),
    ];
});

// Get tissues from API response
const tissueOptions = computed(() => {
    if (!apiTissues.value || apiTissues.value.length === 0) {
        if (!sldscResults.value?.length)
            return [{ label: "All Tissues", value: null }];

        // Fall back to generating from results if API didn't provide tissues
        const uniqueTissues = [
            ...new Set(sldscResults.value.map((item) => item.tissue)),
        ];
        return [
            { label: "All Tissues", value: null },
            ...uniqueTissues.map((tissue) => ({
                label: tissue,
                value: tissue,
            })),
        ];
    }

    return [
        { label: "All Tissues", value: null },
        ...apiTissues.value.map((tissue) => ({
            label: tissue,
            value: tissue,
        })),
    ];
});

// Search biosamples for autocomplete
const searchBiosamples = (event) => {
    const query = event.query.toLowerCase();

    // When the query is empty, show all biosamples
    if (query === "") {
        if (apiBiosamples.value && apiBiosamples.value.length > 0) {
            filteredBiosamples.value = apiBiosamples.value;
        } else if (sldscResults.value?.length) {
            // Fall back to generating from results if API didn't provide biosamples
            filteredBiosamples.value = [
                ...new Set(sldscResults.value.map((item) => item.biosample)),
            ];
        } else {
            filteredBiosamples.value = [];
        }
        return;
    }

    if (apiBiosamples.value && apiBiosamples.value.length > 0) {
        filteredBiosamples.value = apiBiosamples.value.filter((biosample) =>
            biosample.toLowerCase().includes(query),
        );
    } else if (sldscResults.value?.length) {
        // Fall back to filtering from results if API didn't provide biosamples
        const uniqueBiosamples = [
            ...new Set(sldscResults.value.map((item) => item.biosample)),
        ];
        filteredBiosamples.value = uniqueBiosamples.filter((biosample) =>
            biosample.toLowerCase().includes(query),
        );
    } else {
        filteredBiosamples.value = [];
    }
};

// biosample selection
const onBiosampleSelect = (event) => {
    biosampleFilterInput.value = event.value;
    filters.value.biosample.value = event.value;
    onSldscFilter();
};

// clearing the autocomplete
const onBiosampleClear = () => {
    biosampleFilterInput.value = null;
    filters.value.biosample.value = null;
    onSldscFilter();
};

// Search genes for autocomplete (MAGMA)
const searchGenes = (event) => {
    const query = event.query.toLowerCase();

    if (query === "") {
        if (apiGenes.value && apiGenes.value.length > 0) {
            filteredGenes.value = apiGenes.value;
        } else if (magmaResults.value?.length) {
            filteredGenes.value = [
                ...new Set(magmaResults.value.map((item) => item.gene)),
            ];
        } else {
            filteredGenes.value = [];
        }
        return;
    }

    if (apiGenes.value && apiGenes.value.length > 0) {
        filteredGenes.value = apiGenes.value.filter((gene) =>
            gene.toLowerCase().includes(query),
        );
    } else if (magmaResults.value?.length) {
        const uniqueGenes = [
            ...new Set(magmaResults.value.map((item) => item.gene)),
        ];
        filteredGenes.value = uniqueGenes.filter((gene) =>
            gene.toLowerCase().includes(query),
        );
    } else {
        filteredGenes.value = [];
    }
};

// Gene selection (MAGMA)
const onGeneSelect = (event) => {
    magmaGeneFilterInput.value = event.value;
    magmaFilters.value.gene.value = event.value;
    onMagmaFilter();
};

// Clearing the gene autocomplete
const onGeneClear = () => {
    magmaGeneFilterInput.value = null;
    magmaFilters.value.gene.value = null;
    onMagmaFilter();
};

const filters = ref({
    annotation: { value: null, matchMode: "equals" },
    tissue: { value: null, matchMode: "equals" },
    biosample: { value: null, matchMode: "equals" },
    enrichment: { value: null, matchMode: "gte" },
    pValue: { value: null, matchMode: "lte" },
});

const biosampleFilterInput = ref(null);

const magmaFilters = ref({
    gene: { value: null, matchMode: "equals" },
    pValue: { value: null, matchMode: "lte" },
});

const magmaGeneFilterInput = ref(null);

const magmaPathwaysFilters = ref({
    pathwayName: { value: null, matchMode: "contains" },
    pValue: { value: null, matchMode: "lte" },
});

const pigeanGeneFilters = ref({
    gene: { value: null, matchMode: "contains" },
    prior: { value: null, matchMode: "gte" },
    combined: { value: null, matchMode: "gte" },
    huge_score: { value: null, matchMode: "gte" },
    log_bf: { value: null, matchMode: "gte" },
    n: { value: null, matchMode: "gte" },
});

const pigeanGeneFilterInput = ref(null);

const pigeanGeneSetFilters = ref({
    gene_set: { value: null, matchMode: "contains" },
    beta_uncorrected: { value: null, matchMode: "gte" },
    beta: { value: null, matchMode: "gte" },
    n: { value: null, matchMode: "gte" },
});

const pigeanGeneSetFilterInput = ref(null);

const transformFilters = (filters) => {
    const transformedFilters = {};
    Object.entries(filters).forEach(([key, filter]) => {
        if (
            !filter ||
            filter.value === null ||
            filter.value === "" ||
            typeof filter.value === "undefined"
        ) {
            return;
        }

        const filterName = filter.paramKey || key;
        const filterKey = `filter_${filterName}`;
        const matchMode = filter.matchMode || "equals";
        const value = filter.value;

        switch (matchMode) {
            case "lte":
                transformedFilters[filterKey] = `<=${value}`;
                break;
            case "gte":
                transformedFilters[filterKey] = `>=${value}`;
                break;
            case "equals":
                transformedFilters[filterKey] = `eq:${value}`;
                break;
            case "contains":
                transformedFilters[filterKey] = `contains:${value}`;
                break;
            default:
                transformedFilters[filterKey] = value;
        }
    });
    return transformedFilters;
};

// Tab change handler
const onTabChange = (event) => {
    let newValue = null;
    if (typeof event === "string") {
        newValue = event;
    } else if (event && event.value) {
        newValue = event.value;
    }

    if (!newValue || newValue === activeTab.value) {
        return;
    }

    if (
        (newValue === "sldsc" && !shouldShowSldscTab.value) ||
        (newValue === "magma" && !shouldShowMagmaTab.value) ||
        (newValue === "pigean" && !shouldShowPigeanTab.value)
    ) {
        return;
    }

    activeTab.value = newValue;
    tab.value = newValue;
};

// SLDSC Results functions
const loadSldscResults = async () => {
    try {
        sldscLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: sldscFirst.value,
            rows: sldscRows.value,
            sort_field: sldscSortField.value,
            sort_order: sldscSortOrder.value,
        });

        // Add any filter parameters
        const transformedFilters = transformFilters(filters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            sldscResults.value = data.items;
            hasSldscResults.value = data.items.length > 0;
        }
        if (data.totalRecords) sldscTotalRecords.value = data.totalRecords;
        if (data.tissues) apiTissues.value = data.tissues;
        if (data.biosamples) apiBiosamples.value = data.biosamples;
        if (data.annotations) apiAnnotations.value = data.annotations;
        if (data.jobId) sldscJobId.value = data.jobId;
    } catch (err) {
        console.error("Failed to load SLDSC results:", err);
    } finally {
        sldscLoading.value = false;
    }
};

const onSldscPage = (event) => {
    sldscFirst.value = event.first;
    sldscRows.value = event.rows;
    loadSldscResults();
};

const onSldscSort = (event) => {
    sldscSortField.value = event.sortField;
    sldscSortOrder.value = event.sortOrder;
    loadSldscResults();
};

const onSldscFilter = () => {
    sldscFirst.value = 0;
    loadSldscResults();
};

// MAGMA Results functions
const loadMagmaResults = async () => {
    try {
        magmaLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: magmaFirst.value,
            rows: magmaRows.value,
            sort_field: magmaSortField.value,
            sort_order: magmaSortOrder.value,
        });

        // Add any filter parameters
        const transformedFilters = transformFilters(magmaFilters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/magma-results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            magmaResults.value = data.items;
            hasMagmaResults.value = data.items.length > 0;
        }
        if (data.totalRecords) magmaTotalRecords.value = data.totalRecords;
        if (data.genes) apiGenes.value = data.genes;
        if (data.jobId) magmaJobId.value = data.jobId;
    } catch (err) {
        console.error("Failed to load MAGMA results:", err);
    } finally {
        magmaLoading.value = false;
    }
};

const onMagmaPage = (event) => {
    magmaFirst.value = event.first;
    magmaRows.value = event.rows;
    loadMagmaResults();
};

const onMagmaSort = (event) => {
    magmaSortField.value = event.sortField;
    magmaSortOrder.value = event.sortOrder;
    loadMagmaResults();
};

const onMagmaFilter = () => {
    magmaFirst.value = 0;
    loadMagmaResults();
};

// MAGMA Pathways Results functions
const loadMagmaPathwaysResults = async () => {
    try {
        magmaPathwaysLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: magmaPathwaysFirst.value,
            rows: magmaPathwaysRows.value,
            sort_field: magmaPathwaysSortField.value,
            sort_order: magmaPathwaysSortOrder.value,
        });

        // Add any filter parameters
        const transformedFilters = transformFilters(magmaPathwaysFilters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/magma-pathways-results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        if (data.items) {
            magmaPathwaysResults.value = data.items;
            hasMagmaPathwaysResults.value = data.items.length > 0;
        }
        if (data.totalRecords)
            magmaPathwaysTotalRecords.value = data.totalRecords;
        if (data.jobId) magmaPathwaysJobId.value = data.jobId;
    } catch (err) {
        console.error("Failed to load MAGMA pathways results:", err);
        hasMagmaPathwaysResults.value = false;
    } finally {
        magmaPathwaysLoading.value = false;
    }
};

const onMagmaPathwaysPage = (event) => {
    magmaPathwaysFirst.value = event.first;
    magmaPathwaysRows.value = event.rows;
    loadMagmaPathwaysResults();
};

const onMagmaPathwaysSort = (event) => {
    magmaPathwaysSortField.value = event.sortField;
    magmaPathwaysSortOrder.value = event.sortOrder;
    loadMagmaPathwaysResults();
};

const onMagmaPathwaysFilter = () => {
    magmaPathwaysFirst.value = 0;
    loadMagmaPathwaysResults();
};

// PIGEAN Results functions

// Load top 1000 genes (used for both table and chart)
const loadPigeanGeneData = async () => {
    // Prevent multiple fetches
    if (pigeanGeneDataLoaded.value || pigeanGeneLoading.value) {
        return;
    }

    try {
        pigeanGeneLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: 0,
            rows: 1000, // Fetch top 1000 genes
            sort_field: "combined", // Default sort by combined score
            sort_order: -1, // Descending
        });

        const endpoint = `/api/pigean-gene-results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        pigeanGeneAllData.value = data.items || [];
        hasPigeanGeneResults.value = pigeanGeneAllData.value.length > 0;
        pigeanGeneDataLoaded.value = true;

        if (data.jobId) {
            pigeanJobId.value = data.jobId;
        }
    } catch (err) {
        console.error("Failed to load PIGEAN gene results:", err);
        pigeanGeneDataLoaded.value = false;
    } finally {
        pigeanGeneLoading.value = false;
    }
};

// Autocomplete suggestions for gene filter
const pigeanGeneSuggestions = ref([]);

const onPigeanGeneComplete = (event) => {
    const query = event.query.toLowerCase();
    // Get unique gene names from all data that match the query
    const allGenes = pigeanGeneAllData.value
        .map((item) => item.gene)
        .filter((gene) => gene?.toLowerCase().includes(query));
    // Return unique values, limited to first 20
    pigeanGeneSuggestions.value = [...new Set(allGenes)].slice(0, 20);
};

const onPigeanGeneSelect = (event) => {
    pigeanGeneFilters.value.gene.value = event.value;
    pigeanGeneFilterInput.value = event.value;
    onPigeanGeneFilter();
};

const onPigeanGeneClear = () => {
    pigeanGeneFilterInput.value = null;
    pigeanGeneFilters.value.gene.value = null;
    onPigeanGeneFilter();
};

// Autocomplete suggestions for gene set filter
const pigeanGeneSetSuggestions = ref([]);

const onPigeanGeneSetComplete = (event) => {
    const query = event.query.toLowerCase();
    // Get unique gene set names from results that match the query
    const allGeneSets = pigeanGeneSetResults.value
        .map((item) => item.gene_set)
        .filter((geneSet) => geneSet?.toLowerCase().includes(query));
    // Return unique values, limited to first 20
    pigeanGeneSetSuggestions.value = [...new Set(allGeneSets)].slice(0, 20);
};

const onPigeanGeneSetSelect = (event) => {
    pigeanGeneSetFilters.value.gene_set.value = event.value;
    pigeanGeneSetFilterInput.value = event.value;
    onPigeanGeneSetFilter();
};

const onPigeanGeneSetClear = () => {
    pigeanGeneSetFilterInput.value = null;
    pigeanGeneSetFilters.value.gene_set.value = null;
    onPigeanGeneSetFilter();
};

// Client-side pagination handler
const onPigeanGenePage = (event) => {
    pigeanGeneFirst.value = event.first;
    pigeanGeneRows.value = event.rows;
    // No API call needed - pagination is handled by computed property
};

// Client-side sorting handler
const onPigeanGeneSort = (event) => {
    pigeanGeneSortField.value = event.sortField;
    pigeanGeneSortOrder.value = event.sortOrder;
    pigeanGeneFirst.value = 0; // Reset to first page on sort
    // No API call needed - sorting is handled by computed property
};

// Client-side filtering handler
const onPigeanGeneFilter = () => {
    pigeanGeneFirst.value = 0; // Reset to first page on filter
    // No API call needed - filtering is handled by computed property
};

const loadPigeanGeneSetResults = async (forceReload = false) => {
    // Prevent multiple fetches unless forced
    if (
        (pigeanGeneSetDataLoaded.value || pigeanGeneSetLoading.value) &&
        !forceReload
    ) {
        return;
    }

    try {
        pigeanGeneSetLoading.value = true;
        resultsStore.init();

        const queryParams = new URLSearchParams({
            first: pigeanGeneSetFirst.value,
            rows: pigeanGeneSetRows.value,
            sort_field: pigeanGeneSetSortField.value,
            sort_order: pigeanGeneSetSortOrder.value,
        });

        const transformedFilters = transformFilters(pigeanGeneSetFilters.value);
        Object.entries(transformedFilters).forEach(([key, value]) => {
            queryParams.append(key, value);
        });

        const endpoint = `/api/pigean-gene-set-results/${dataset.value}?${queryParams.toString()}`;
        const { data } = await resultsStore.axios.get(endpoint);

        pigeanGeneSetResults.value = data.items || [];
        pigeanGeneSetSubRecords.value = data.subRecords || {};
        hasPigeanGeneSetResults.value = pigeanGeneSetResults.value.length > 0;
        pigeanGeneSetDataLoaded.value = true;
        if (typeof data.totalRecords === "number") {
            pigeanGeneSetTotalRecords.value = data.totalRecords;
        }
        if (data.jobId) {
            pigeanJobId.value = data.jobId;
        }
    } catch (err) {
        console.error("Failed to load PIGEAN gene set results:", err);
        pigeanGeneSetDataLoaded.value = false;
    } finally {
        pigeanGeneSetLoading.value = false;
    }
};

const onPigeanGeneSetPage = (event) => {
    pigeanGeneSetFirst.value = event.first;
    pigeanGeneSetRows.value = event.rows;
    loadPigeanGeneSetResults(true); // Force reload for pagination
};

const onPigeanGeneSetSort = (event) => {
    pigeanGeneSetSortField.value = event.sortField;
    pigeanGeneSetSortOrder.value = event.sortOrder;
    loadPigeanGeneSetResults(true); // Force reload for sorting
};

const onPigeanGeneSetFilter = () => {
    pigeanGeneSetFirst.value = 0;
    loadPigeanGeneSetResults(true); // Force reload for filtering
};

const onPigeanGeneExpandedRowsChange = (value) => {
    pigeanGeneExpandedRows.value = value;
};

const togglePigeanGeneRow = (rowData) => {
    const current = { ...pigeanGeneExpandedRows.value };
    const key = rowData?.gene;
    if (!key) {
        return;
    }

    if (current[key]) {
        delete current[key];
    } else {
        current[key] = rowData;
    }

    pigeanGeneExpandedRows.value = current;
};

const isPigeanGeneRowExpanded = (rowData) => {
    const key = rowData?.gene;
    if (!key) {
        return false;
    }
    return Boolean(pigeanGeneExpandedRows.value?.[key]);
};

const onPigeanGeneSetExpandedRowsChange = (value) => {
    pigeanGeneSetExpandedRows.value = value;
};

const togglePigeanGeneSetRow = (rowData) => {
    const current = { ...pigeanGeneSetExpandedRows.value };
    const key = rowData?.gene_set;
    if (!key) {
        return;
    }

    if (current[key]) {
        delete current[key];
    } else {
        current[key] = rowData;
    }

    pigeanGeneSetExpandedRows.value = current;
};

const isPigeanGeneSetRowExpanded = (geneSet) => {
    if (!geneSet) {
        return false;
    }
    return Boolean(pigeanGeneSetExpandedRows.value?.[geneSet]);
};

// Check both result types availability and set initial tab
const checkResultsAvailability = async () => {
    try {
        resultsStore.init();

        // Check workflow status to determine what results are available
        const workflowResponse = await resultsStore.axios.get(
            `/api/workflow-status/${dataset.value}`,
        );
        const workflows = workflowResponse.data;

        // Store workflow status for potential display to user
        workflowStatus.value = workflows;
        hasWorkflowData.value = Object.keys(workflows).length > 0;

        console.log("Workflow status for dataset:", dataset.value, workflows);

        // Check if LDSC/SLDSC workflows are available and completed successfully
        const sldscStatus =
            workflows.ldsc?.ldsc?.status || workflows.sldsc?.sldsc?.status;
        const hasSldscWorkflow = !!sldscStatus;
        const sldscSucceeded = sldscStatus === "SUCCEEDED";

        // Check if MAGMA workflows are available and completed successfully
        const magmaStatus = workflows.magma?.magma?.status;
        const hasMagmaWorkflow = !!magmaStatus;
        const magmaSucceeded = magmaStatus === "SUCCEEDED";

        const pigeanStatus = workflows.pigean?.pigean?.status;
        const hasPigeanWorkflow = !!pigeanStatus;
        const pigeanSucceeded = pigeanStatus === "SUCCEEDED";

        // Set results availability based on workflow status
        if (sldscSucceeded) {
            hasSldscResults.value = true;
        } else if (hasSldscWorkflow) {
            // Workflow exists but hasn't succeeded - don't show results
            hasSldscResults.value = false;
        } else {
            // No workflow info - fallback to checking for existing data
            try {
                const sldscResponse = await resultsStore.axios.get(
                    `/api/results/${dataset.value}?first=0&rows=1`,
                );
                hasSldscResults.value =
                    sldscResponse.data.items &&
                    sldscResponse.data.items.length > 0;
            } catch (e) {
                hasSldscResults.value = false;
            }
        }

        if (magmaSucceeded) {
            hasMagmaResults.value = true;
            hasMagmaPathwaysResults.value = true;
            console.log(
                "MAGMA workflow succeeded, marking results as available",
            );
        } else if (hasMagmaWorkflow) {
            // Workflow exists but hasn't succeeded - don't show results
            hasMagmaResults.value = false;
            hasMagmaPathwaysResults.value = false;
        } else {
            // No workflow info - fallback to checking for existing data
            try {
                console.log("Checking MAGMA data availability via API...");
                const magmaResponse = await resultsStore.axios.get(
                    `/api/magma-results/${dataset.value}?first=0&rows=1`,
                );
                hasMagmaResults.value =
                    magmaResponse.data.items &&
                    magmaResponse.data.items.length > 0;
                console.log(
                    "MAGMA API check result:",
                    hasMagmaResults.value,
                    magmaResponse.data,
                );

                // Also check for pathways
                try {
                    const magmaPathwaysResponse = await resultsStore.axios.get(
                        `/api/magma-pathways-results/${dataset.value}?first=0&rows=1`,
                    );
                    hasMagmaPathwaysResults.value =
                        magmaPathwaysResponse.data.items &&
                        magmaPathwaysResponse.data.items.length > 0;
                } catch (pathwaysErr) {
                    console.log("MAGMA pathways check failed:", pathwaysErr);
                    hasMagmaPathwaysResults.value = false;
                }
            } catch (e) {
                console.log("MAGMA API check failed:", e);
                hasMagmaResults.value = false;
                hasMagmaPathwaysResults.value = false;
            }
        }

        if (pigeanSucceeded) {
            hasPigeanGeneResults.value = true;
            hasPigeanGeneSetResults.value = true;
        } else if (hasPigeanWorkflow) {
            hasPigeanGeneResults.value = false;
            hasPigeanGeneSetResults.value = false;
        } else {
            try {
                const pigeanGeneResponse = await resultsStore.axios.get(
                    `/api/pigean-gene-results/${dataset.value}?first=0&rows=1`,
                );
                hasPigeanGeneResults.value =
                    pigeanGeneResponse.data.items &&
                    pigeanGeneResponse.data.items.length > 0;
            } catch (geneErr) {
                console.log("PIGEAN gene API check failed:", geneErr);
                hasPigeanGeneResults.value = false;
            }

            try {
                const pigeanGeneSetResponse = await resultsStore.axios.get(
                    `/api/pigean-gene-set-results/${dataset.value}?first=0&rows=1`,
                );
                hasPigeanGeneSetResults.value =
                    pigeanGeneSetResponse.data.items &&
                    pigeanGeneSetResponse.data.items.length > 0;
            } catch (geneSetErr) {
                console.log("PIGEAN gene-set API check failed:", geneSetErr);
                hasPigeanGeneSetResults.value = false;
            }
        }

        // Ensure we have a valid active tab
        // If current active tab shouldn't be shown, switch to the first available tab
        await nextTick(); // Wait for computed properties to update

        const currentTabValid =
            (activeTab.value === "sldsc" && shouldShowSldscTab.value) ||
            (activeTab.value === "magma" && shouldShowMagmaTab.value) ||
            (activeTab.value === "pigean" && shouldShowPigeanTab.value);

        if (!currentTabValid) {
            if (shouldShowSldscTab.value) {
                activeTab.value = "sldsc";
            } else if (shouldShowMagmaTab.value) {
                activeTab.value = "magma";
            } else if (shouldShowPigeanTab.value) {
                activeTab.value = "pigean";
            }
        }

        // Load data for successful workflows only
        if (sldscSucceeded && sldscResults.value.length === 0) {
            loadSldscResults();
        }

        if (magmaSucceeded && magmaResults.value.length === 0) {
            console.log("MAGMA results detected as available, loading data...");
            loadMagmaResults();
        }

        if (magmaSucceeded && magmaPathwaysResults.value.length === 0) {
            console.log(
                "MAGMA pathways results detected as available, loading data...",
            );
            loadMagmaPathwaysResults();
        }

        if (pigeanSucceeded && !pigeanGeneDataLoaded.value) {
            loadPigeanGeneData();
        }

        if (pigeanSucceeded && !pigeanGeneSetDataLoaded.value) {
            loadPigeanGeneSetResults();
        }
    } catch (err) {
        console.error("Failed to check results availability:", err);
        // Fallback to trying to load results directly
        try {
            const sldscResponse = await resultsStore.axios.get(
                `/api/results/${dataset.value}?first=0&rows=1`,
            );
            hasSldscResults.value =
                sldscResponse.data.items && sldscResponse.data.items.length > 0;
        } catch (e) {
            hasSldscResults.value = false;
        }

        try {
            const magmaResponse = await resultsStore.axios.get(
                `/api/magma-results/${dataset.value}?first=0&rows=1`,
            );
            hasMagmaResults.value =
                magmaResponse.data.items && magmaResponse.data.items.length > 0;
        } catch (e) {
            hasMagmaResults.value = false;
        }

        try {
            const magmaPathwaysResponse = await resultsStore.axios.get(
                `/api/magma-pathways-results/${dataset.value}?first=0&rows=1`,
            );
            hasMagmaPathwaysResults.value =
                magmaPathwaysResponse.data.items &&
                magmaPathwaysResponse.data.items.length > 0;
        } catch (e) {
            hasMagmaPathwaysResults.value = false;
        }

        try {
            const pigeanGeneResponse = await resultsStore.axios.get(
                `/api/pigean-gene-results/${dataset.value}?first=0&rows=1`,
            );
            hasPigeanGeneResults.value =
                pigeanGeneResponse.data.items &&
                pigeanGeneResponse.data.items.length > 0;
        } catch (e) {
            hasPigeanGeneResults.value = false;
        }

        try {
            const pigeanGeneSetResponse = await resultsStore.axios.get(
                `/api/pigean-gene-set-results/${dataset.value}?first=0&rows=1`,
            );
            hasPigeanGeneSetResults.value =
                pigeanGeneSetResponse.data.items &&
                pigeanGeneSetResponse.data.items.length > 0;
        } catch (e) {
            hasPigeanGeneSetResults.value = false;
        }
    }
};

// Watch for activeTab changes to ensure content is displayed
watch(activeTab, (newTab) => {
    if (newTab && route.query.tab !== newTab) {
        router.replace({
            query: { ...route.query, tab: newTab },
        });
    }

    if (
        newTab === "sldsc" &&
        hasSldscResults.value &&
        sldscResults.value.length === 0
    ) {
        loadSldscResults();
    } else if (
        newTab === "magma" &&
        hasMagmaResults.value &&
        magmaResults.value.length === 0
    ) {
        loadMagmaResults();
    }

    // Also load pathways if on magma tab
    if (
        newTab === "magma" &&
        hasMagmaPathwaysResults.value &&
        magmaPathwaysResults.value.length === 0
    ) {
        loadMagmaPathwaysResults();
    }

    if (
        newTab === "pigean" &&
        hasPigeanGeneResults.value &&
        !pigeanGeneDataLoaded.value
    ) {
        loadPigeanGeneData();
    }

    if (
        newTab === "pigean" &&
        hasPigeanGeneSetResults.value &&
        !pigeanGeneSetDataLoaded.value
    ) {
        loadPigeanGeneSetResults();
    }
});

// Watch for route query parameter changes
watch(
    () => route.query.tab,
    (newTab) => {
        if (newTab && ["sldsc", "magma", "pigean"].includes(newTab)) {
            activeTab.value = newTab;
            tab.value = newTab;
        }
    },
    { immediate: true },
);

// Watch for dataset changes to reset loaded flags
watch(
    () => route.query.dataset,
    (newDataset) => {
        if (newDataset && newDataset !== dataset.value) {
            dataset.value = newDataset;
            // Reset loaded flags so data will be fetched again
            pigeanGeneDataLoaded.value = false;
            pigeanGeneSetDataLoaded.value = false;
            // Clear existing data
            pigeanGeneAllData.value = [];
            pigeanGeneSetResults.value = [];
            // Reset pagination
            pigeanGeneFirst.value = 0;
            pigeanGeneSetFirst.value = 0;
            biosampleFilterInput.value = null;
            magmaGeneFilterInput.value = null;
            pigeanGeneFilterInput.value = null;
        }
    },
);

onMounted(async () => {
    // First check workflow availability to determine what tabs to show
    await checkResultsAvailability();

    // Then load data for the active tab if it has results available
    if (
        activeTab.value === "magma" &&
        hasMagmaResults.value &&
        magmaResults.value.length === 0
    ) {
        loadMagmaResults();
    } else if (
        activeTab.value === "sldsc" &&
        hasSldscResults.value &&
        sldscResults.value.length === 0
    ) {
        loadSldscResults();
    }

    // Also load pathways if on magma tab
    if (
        activeTab.value === "magma" &&
        hasMagmaPathwaysResults.value &&
        magmaPathwaysResults.value.length === 0
    ) {
        loadMagmaPathwaysResults();
    }

    if (
        activeTab.value === "pigean" &&
        hasPigeanGeneResults.value &&
        !pigeanGeneDataLoaded.value
    ) {
        loadPigeanGeneData();
    }

    if (
        activeTab.value === "pigean" &&
        hasPigeanGeneSetResults.value &&
        !pigeanGeneSetDataLoaded.value
    ) {
        loadPigeanGeneSetResults();
    }
});
</script>

<style scoped>
.results-container {
    padding: 1rem;
}

.error-message {
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Annotation dot colors */
.color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}

.color-dot.binding_sites {
    background-color: #2196f3;
}

.color-dot.accessible_chromatin {
    background-color: #4caf50;
}

.color-dot.enhancer {
    background-color: #ff9800;
}

.color-dot.promoter {
    background-color: #e91e63;
}

:deep(.p-column-header-content) {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

:deep(.p-column-filter) {
    width: 100%;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
}

:deep(.p-select-label) {
    text-overflow: ellipsis;
    font-size: 0.875rem;
}

:deep(.p-select-panel .p-select-items) {
    font-size: 0.875rem;
}

:deep(.p-column-header-content) {
    flex-direction: column;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
    padding: 0.5rem;
}

:deep(.p-datatable .p-datatable-thead > tr > th) {
    padding-bottom: 0.5rem;
}

:deep(.p-inputtext, .p-inputnumber) {
    font-size: 0.875rem;
}

:deep(.p-datatable-filter-row) {
    background-color: #f8f9fa;
}

:deep(.dark .p-autocomplete .p-autocomplete-clear-icon),
:deep(.dark .p-inputnumber .p-inputnumber-clear-icon) {
    color: #cbd5f5;
}

:deep(.p-autocomplete .p-autocomplete-clear-icon:hover),
:deep(.p-inputnumber .p-inputnumber-clear-icon:hover) {
    color: #111827;
}
</style>
