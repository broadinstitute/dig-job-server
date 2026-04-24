<template>
  <div class="flex items-center gap-3">
    <Button
      icon="pi pi-folder-open"
      label="Choose Folder"
      severity="secondary"
      outlined
      @click="triggerFileDialog"
    />
    <span
      v-if="selectedFileCount > 0"
      class="text-xs text-gray-500 dark:text-gray-400"
    >
      {{ selectedFileCount }} file(s) selected
    </span>
    <input
      ref="fileInput"
      type="file"
      webkitdirectory
      directory
      class="hidden"
      @change="onChange"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();
const fileInput = ref(null);
const selectedFileCount = ref(0);

function triggerFileDialog() {
  fileInput.value?.click();
}

async function onChange(e) {
  selectedFileCount.value = e.target.files?.length || 0;
  await store.loadFolder(e.target.files);
}
</script>
