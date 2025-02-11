<script setup>
import { ref } from 'vue';
import { useUserStore } from "~/stores/UserStore.js";
import {useToast} from "primevue/usetoast";
const userStore = useUserStore();
const router = useRouter();
const toast = useToast();
const datasets = ref([]);

onMounted(async () => {
  datasets.value = await userStore.retrieveDatasets();
});

async function runSumstats(dataset) {
  await userStore.startAnalysis(dataset, 'sumstats');
  toast.add({severity: 'success', summary: 'Success', detail: 'sumstats started successfully'});
  console.log('Running sumstats for dataset:', dataset);
}

async function runSldsc(dataset) {
  await userStore.startAnalysis(dataset, 'sldsc');
  toast.add({severity: 'success', summary: 'Success', detail: 'SLDSC started successfully'});
  console.log('Running sldsc for dataset:', dataset);
}

</script>
<template>
  <div class="p-5">
    <DataTable :value="datasets" class="mb-3">
      <Column field="dataset" header="Dataset Name"></Column>
      <Column header="Analyses">
        <template #body="{ data }">
          <span>
            <Button @click.prevent="runSumstats(data.dataset)" label="Run Sum Stats"></Button> |
            <Button @click.prevent="runSldsc(data.dataset)" label="Run SLDSC"></Button> |
            <Button @click="router.push(`/results?dataset=${data.dataset}`)" label="Results"></Button>
          </span>
        </template>
      </Column>
    </DataTable>
   <Button @click="router.push('/upload')" icon="pi pi-upload" label="Upload Dataset"></Button>
    <Toast position="top-center" />
  </div>
</template>
