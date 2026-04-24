<template>
  <Dialog
    v-model:visible="visible"
    header="Selection Details"
    :modal="false"
    :dismissable-mask="true"
    :style="{ width: '380px' }"
    position="bottomright"
    class="!z-50"
  >
    <div
      class="font-mono text-sm leading-6 text-gray-800 dark:text-gray-200 mb-3 select-text"
      v-html="html"
    />
    <Button
      icon="pi pi-copy"
      :label="copyLabel"
      severity="secondary"
      outlined
      size="small"
      class="w-full"
      @click="copy"
    />
  </Dialog>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const html = ref('');
const copyLabel = ref('Copy to Clipboard');

function show(rawHtml) {
  html.value = rawHtml || 'No data available for this point.';
  visible.value = true;
}

async function copy() {
  const tmp = document.createElement('div');
  tmp.innerHTML = html.value;
  try {
    await navigator.clipboard.writeText(tmp.innerText);
    copyLabel.value = 'Copied!';
    setTimeout(() => (copyLabel.value = 'Copy to Clipboard'), 1500);
  } catch (err) {
    console.error('clipboard write failed', err);
  }
}

defineExpose({ show });
</script>
