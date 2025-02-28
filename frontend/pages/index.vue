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

async function runSumstats(data) {
  await userStore.startAnalysis(data.dataset, 'sumstats');
  data.status = "RUNNING sumstats";
  toast.add({severity: 'success', summary: 'Success', detail: 'sumstats started successfully'});
}

async function runSldsc(data) {
  await userStore.startAnalysis(data.dataset, 'sldsc');
  data.status = "RUNNING sldsc";
  toast.add({severity: 'success', summary: 'Success', detail: 'SLDSC started successfully'});
}

async function handleDelete(dataSet) {
  await userStore.deleteDataset(dataSet);
  datasets.value = datasets.value.filter((dataset) => dataset.dataset !== dataSet);
  toast.add({severity: 'success', summary: 'Success', detail: 'Dataset deleted successfully'});
}

</script>
<template>
  <div class="p-5">
    <DataTable :value="datasets" class="mb-3">
      <Column field="dataset" header="Dataset Name"></Column>
      <Column header="Status">
          <template #body="{ data }">
            <template v-if="data.status && (data.status.endsWith('SUCCEEDED') || data.status.endsWith('FAILED'))">
              <router-link :to="`/log/${data.id}`">{{ data.status }}</router-link>
            </template>
            <template v-else>
              {{ data.status }}
            </template>
        </template>
      </Column>
      <Column header="Analysis">
        <template #body="{ data }">
          <span>
            <Button v-if="!data.status" @click.prevent="runSumstats(data)" label="Run Sum Stats"></Button>
            <Button v-if="data.status === 'sumstats SUCCEEDED'" @click.prevent="runSldsc(data)" label="Run SLDSC"></Button>
            <Button v-if="data.status === 'sldsc SUCCEEDED'" @click="router.push(`/results?dataset=${data.dataset}`)" label="Results"></Button>
          </span>
        </template>
      </Column>
      <Column header="" :style="{ width: '8rem' }" >
        <template #body="{ data }">
          <Button
              icon="pi pi-trash"
              size="small"
              @click="handleDelete(data.dataset)"
              v-tooltip.top="'Delete Dataset'"
          />
        </template>
      </Column>
    </DataTable>
   <Button @click="router.push('/upload')" icon="pi pi-upload" label="Upload Dataset"></Button>
    <Toast position="top-center" />
  </div>
</template>
