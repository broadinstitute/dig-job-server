<script setup>
import { ref } from 'vue';
import { useUserStore } from "~/stores/UserStore.js";
import {useToast} from "primevue/usetoast";
const userStore = useUserStore();
const router = useRouter();
const toast = useToast();
const datasets = ref([]);
const config = useRuntimeConfig();
const eventSources = ref({});

onMounted(async () => {
  datasets.value = await userStore.retrieveDatasets();
  datasets.value.forEach(data => {
    if (data.status?.includes('RUNNING')) {
      console.log(`Connecting to running job for dataset: ${data.dataset}`);
      listenForJobStatus(data.id, data);
    }
  });
});

onUnmounted(() => {
  Object.values(eventSources.value).forEach(es => es.close());
  eventSources.value = {};
});

const listenForJobStatus = (jobId, data) => {
  // Close existing connection for this job if it exists
  if (eventSources.value[jobId]) {
    eventSources.value[jobId].close();
  }

  const eventSource = new EventSource(`${config.public.apiBaseUrl}/api/job-status/${jobId}`);
  eventSources.value[jobId] = eventSource;

  eventSource.onmessage = async (event) => {
    if (!event.data) return; // Ignore keepalive messages

    const statusData = JSON.parse(event.data);
    console.log('Job status update:', statusData);

    // Update the status in the datasets table
    data.status = statusData.status;

    if (statusData.status.endsWith('SUCCEEDED')) {
      eventSource.close();
      delete eventSources.value[jobId];
      toast.add({severity: 'success', summary: 'Success', detail: `${statusData.method} completed successfully`});
    } else if (statusData.status.endsWith('FAILED')) {
      eventSource.close();
      delete eventSources.value[jobId];
      toast.add({severity: 'error', summary: 'Error', detail: `${statusData.method} failed`});
    }
  };

  eventSource.onerror = (error) => {
    console.error('EventSource failed:', error);
    eventSource?.close();
    delete eventSources.value[jobId];
  };
};

async function runSumstats(data) {
  const {job_id} = await userStore.startAnalysis(data.dataset, 'sumstats');
  data.status = "RUNNING sumstats";
  listenForJobStatus(job_id, data);
  toast.add({severity: 'success', summary: 'Success', detail: 'sumstats started successfully'});
}

async function runSldsc(data) {
  const {job_id} = await userStore.startAnalysis(data.dataset, 'sldsc');
  data.status = "RUNNING sldsc";
  listenForJobStatus(job_id, data);
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
