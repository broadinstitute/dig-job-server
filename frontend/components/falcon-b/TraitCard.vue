<template>
  <div class="trait-card">
    <div class="trait-card-header" @click="expanded = !expanded">
      <span class="trait-name">{{ row.name }}</span>
      <span class="trait-chip clump">Clump {{ row.clumpId }}</span>
      <span v-if="row.isLead" class="trait-chip lead">⭐ Lead</span>
      <span v-if="row.isNovel === false" class="trait-chip known">Known</span>
      <span v-if="row.isNovel === true" class="trait-chip novel">Novel</span>
      <span class="trait-meta">
        Chr {{ row.chr }} · Prob {{ row.prob.toFixed(3) }} · NegP {{ row.negP.toFixed(2) }}
      </span>
      <span class="trait-toggle">{{ expanded ? '−' : '+' }}</span>
    </div>

    <div v-if="expanded" class="trait-card-body">
      <div v-if="row.traits?.length" class="trait-section">
        <h4>Associated traits</h4>
        <ul>
          <li v-for="(t, i) in row.traits" :key="i" class="trait-citation">
            <span class="mono">{{ t.Trait || t.trait || '—' }}</span>
            <span v-if="t.Citation || t.citation" class="muted">
              ({{ t.Citation || t.citation }})
            </span>
          </li>
        </ul>
      </div>
      <div v-if="row.clinicalTrials?.length" class="trait-section">
        <h4>Clinical trials</h4>
        <ul>
          <li v-for="(t, i) in row.clinicalTrials" :key="i" class="trial-row">
            <span class="mono">{{ t.drugId }}</span>
            · {{ t.indication }}
            <span class="trait-chip phase">Phase {{ t.phase }}</span>
          </li>
        </ul>
      </div>
      <div
        v-if="!row.traits?.length && !row.clinicalTrials?.length"
        class="muted"
      >
        No trait or trial data.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
defineProps({ row: { type: Object, required: true } });
const expanded = ref(false);
</script>

<style scoped>
.trait-card {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 10px 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  overflow-wrap: break-word;
  word-break: break-word;
  margin-bottom: 8px;
  color: #111827;
}
.trait-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex-wrap: wrap;
}
.trait-name {
  font-weight: 600;
  color: #111827;
}
.trait-chip {
  font-size: 0.75em;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  background: #f3f4f6;
  color: #374151;
}
.trait-chip.lead { background: #fef3c7; border-color: #fbbf24; color: #92400e; }
.trait-chip.known { background: #e5e7eb; border-color: #9ca3af; color: #4b5563; }
.trait-chip.novel { background: #d1fae5; border-color: #10b981; color: #047857; }
.trait-chip.clump { background: #dbeafe; border-color: #60a5fa; color: #1e40af; }
.trait-chip.phase { background: #ede9fe; border-color: #a78bfa; color: #5b21b6; }
.trait-meta {
  margin-left: auto;
  font-size: 0.8em;
  color: #6b7280;
}
.trait-toggle {
  width: 18px;
  text-align: center;
  color: #6b7280;
  font-weight: bold;
}
.trait-card-body {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}
.trait-section {
  margin-bottom: 10px;
}
.trait-section h4 {
  margin: 0 0 4px 0;
  font-size: 0.85em;
  font-weight: 600;
  color: #374151;
}
.trait-section ul {
  list-style: disc inside;
  font-size: 0.85em;
  margin: 0;
  padding: 0;
}
.trait-citation {
  margin-bottom: 4px;
  line-height: 1.4;
}
.mono { font-family: monospace; }
.muted { color: #6b7280; font-size: 0.85em; }
</style>
