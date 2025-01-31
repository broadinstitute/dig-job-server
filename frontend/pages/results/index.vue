<script setup>
import {useUserStore} from "~/stores/UserStore";
const userStore = useUserStore();
const route = useRoute();

const results = ref([]);

onMounted(async () => {
  results.value = await userStore.getResults(route.query.dataset);
});

</script>
<template>
  <div class="p-5">
    <DataTable :value="results" class="mb-3">
      <Column field="annotation" header="Annotation"></Column>
      <Column field="tissue" header="Tissue"></Column>
      <Column field="biosample" header="Biosample"></Column>
      <Column field="enrichment" header="Enrichment"></Column>
      <Column field="pValue" header="P-Value"></Column>
    </DataTable>
  </div>
</template>
