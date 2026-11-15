<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSongStore } from '../stores/songs'
import { useSettingsStore } from '../stores/settings'
import SongDisplay from '../components/SongDisplay.vue'

const route = useRoute()
const store = useSongStore()
const settingsStore = useSettingsStore()

const columns = ref<1 | 2>(route.query.columns === '2' ? 2 : 1)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    await Promise.all([
      store.fetchSong(route.params.id as string),
      settingsStore.fetchSettings().catch(() => {}),
    ])
    if (!store.current) error.value = 'Song not found'
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not load song'
  } finally {
    loading.value = false
  }
})

const song = computed(() => store.current)

function printPage() {
  window.print()
}
</script>

<template>
  <div class="print-page">
    <div class="print-toolbar">
      <span class="toolbar-label">Columns:</span>
      <button :class="{ active: columns === 1 }" @click="columns = 1">1</button>
      <button :class="{ active: columns === 2 }" @click="columns = 2">2</button>
      <button class="print-btn" @click="printPage">Print</button>
      <router-link :to="`/songs/${route.params.id}`">Back</router-link>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error || !song" class="error">{{ error || 'Song not found' }}</div>
    <SongDisplay
      v-else
      :chordpro="song.body"
      :title="song.title"
      :artist="song.artist"
      :capo="song.capo"
      :song-key="song.key"
      hide-controls
      :columns-override="columns === 2"
    />
  </div>
</template>

<style scoped>
.print-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
}
.print-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}
.toolbar-label {
  color: var(--text-muted);
  font-size: 0.85rem;
}
.print-toolbar button,
.print-toolbar a {
  padding: 0.35rem 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  text-decoration: none;
  font-size: 0.85rem;
  cursor: pointer;
}
.print-toolbar button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
}
.print-btn {
  margin-left: auto;
}
.loading,
.error {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
@media print {
  .print-page {
    max-width: none;
    margin: 0;
    padding: 0;
  }
  .print-toolbar {
    display: none !important;
  }
}
</style>
