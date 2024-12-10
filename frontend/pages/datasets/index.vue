<script setup>
import { ref } from 'vue';
import { useUserStore } from "~/stores/UserStore";
const userStore = useUserStore();
const router = useRouter();

const datasets = ref([]);

onMounted(async () => {
  datasets.value = await userStore.retrieveDatasets();
});

async function runSumstats(dataset) {
  await userStore.startAnalysis(dataset, 'sumstats');
  console.log('Running sumstats for dataset:', dataset);
}

async function runSldsc(dataset) {
  await userStore.startAnalysis(dataset, 'sldsc');
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
            <a href="#" @click.prevent="runSumstats(data.dataset)">Run Sum Stats</a> |
            <a href="#" @click.prevent="runSldsc(data.dataset)">Run SLDSC</a>
          </span>
        </template>
      </Column>
    </DataTable>
   <Button @click="router.push('/upload')" icon="pi pi-upload" label="Upload Dataset"></Button>
  </div>
</template>
