<template>
  <div class="flex items-center gap-3">
    <input
      ref="fileInput"
      type="file"
      webkitdirectory
      directory
      class="falcon-b-folder-input"
      @change="onChange"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useFalconStore } from '~/stores/FalconStore';

const store = useFalconStore();
const fileInput = ref(null);

async function onChange(e) {
  await store.loadFolder(e.target.files);
}
</script>

<style scoped>
/* From PEGS styles.css:20-22 — original input appearance */
.falcon-b-folder-input {
  padding: 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  font-size: 0.9em;
}
</style>
