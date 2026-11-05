<script setup lang="ts">
const props = defineProps<{
  modelValue: number
}>()
const emit = defineEmits<{
  'update:modelValue': [value: number]
}>()

function setTranspose(val: number) {
  emit('update:modelValue', Math.max(-11, Math.min(11, val)))
}
</script>

<template>
  <div class="transpose-control">
    <button @click="setTranspose(modelValue - 1)" class="tp-btn" title="Transpose down">-</button>
    <span class="tp-value">Transpose: {{ modelValue > 0 ? '+' : '' }}{{ modelValue }}</span>
    <button @click="setTranspose(modelValue + 1)" class="tp-btn" title="Transpose up">+</button>
    <button @click="setTranspose(0)" class="tp-btn tp-reset" title="Reset">Reset</button>
  </div>
</template>

<style scoped>
.transpose-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
}
.tp-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}
.tp-btn:hover {
  background: var(--hover);
  border-color: var(--accent);
}
.tp-value {
  font-size: 0.85rem;
  color: var(--text-muted);
  min-width: 100px;
  text-align: center;
}
.tp-reset {
  font-size: 0.8rem;
  color: var(--text-muted);
}
</style>
