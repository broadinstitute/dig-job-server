<script setup>
import { ref } from 'vue';
import { useUserStore } from "~/stores/UserStore";
const userStore = useUserStore();
const router = useRouter();

const datasets = ref([]);

onMounted(async () => {
  datasets.value = await userStore.retrieveDatasets();
});

</script>
<template>
  <div class="p-5">
    <DataTable :value="datasets" class="mb-3">
      <Column field="dataset" header="Dataset Name"></Column>
    </DataTable>
   <Button @click="router.push('/upload')" icon="pi pi-upload" label="Upload Dataset"></Button>
  </div>
</template>
