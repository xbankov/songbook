<script setup lang="ts">
defineProps<{
  type?: 'info' | 'success' | 'error'
  message: string
}>()
</script>

<template>
  <div class="notice" :class="type || 'info'" role="status">
    {{ message }}
  </div>
</template>

<style scoped>
.notice {
  margin: 0.75rem 0;
  padding: 0.6rem 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 0.9rem;
}
.notice.success {
  border-color: #2e7d32;
  color: #2e7d32;
}
.notice.error {
  border-color: var(--danger);
  color: var(--danger);
}
.notice.info {
  border-color: var(--accent);
  color: var(--text);
}
</style>
