<template>
  <div v-show="visible" class="falcon-inspector">
    <div class="falcon-inspector-header">
      <h4>🔍 Selection Details</h4>
      <button class="falcon-inspector-close" @click="visible = false">&times;</button>
    </div>
    <div class="falcon-inspector-body">
      <div class="falcon-inspector-content" v-html="html" />
      <button class="falcon-inspector-copy" @click="copy">
        📋 {{ copyLabel }}
      </button>
    </div>
  </div>
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

<style scoped>
/* From PEGS index.html:214-226 */
.falcon-inspector {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 320px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  z-index: 9999;
  overflow: hidden;
  color: #111827;
}
.falcon-inspector-header {
  padding: 12px 15px;
  background: #f3f4f6;
  border-bottom: 1px solid #d1d5db;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.falcon-inspector-header h4 {
  margin: 0;
  color: #111827;
  font-size: 1em;
}
.falcon-inspector-close {
  background: none;
  border: none;
  font-size: 1.2em;
  color: #6b7280;
  cursor: pointer;
}
.falcon-inspector-body {
  padding: 15px;
}
.falcon-inspector-content {
  font-family: monospace;
  font-size: 0.95em;
  line-height: 1.6;
  color: #374151;
  margin-bottom: 15px;
  user-select: text;
}
.falcon-inspector-copy {
  width: 100%;
  padding: 8px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  color: #374151;
  transition: background 0.2s;
}
.falcon-inspector-copy:hover {
  background: #f3f4f6;
}
</style>
