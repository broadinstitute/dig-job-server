<template>
  <DataTable
    :value="records"
    dataKey="id"
    :rows="20"
    :rowsPerPageOptions="[10, 20, 50, 100]"
    paginator
    sortField="pValue"
    :sortOrder="1"
    stripedRows
    class="p-datatable-sm"
  >
    <Column field="chromosome" header="Chr" sortable />
    <Column field="position" header="Position" sortable />
    <Column header="Variant">
      <template #body="{ data }">{{ data.reference }}/{{ data.alt }}</template>
    </Column>
    <Column field="dbSNP" header="rsID" sortable />
    <Column field="pValue" header="P-Value" sortable>
      <template #body="{ data }">{{ formatP(data.pValue) }}</template>
    </Column>
    <Column field="beta" header="Beta" sortable>
      <template #body="{ data }">{{ data.beta != null ? Number(data.beta).toFixed(4) : "—" }}</template>
    </Column>
    <template #empty>
      <div class="text-center p-4">No variants in this region.</div>
    </template>
  </DataTable>
</template>

<script setup>
defineProps({
  records: { type: Array, default: () => [] },
});

function formatP(v) {
  const n = Number(v);
  if (!(n >= 0)) return "—";
  return n < 0.001 ? n.toExponential(2) : n.toFixed(4);
}
</script>
