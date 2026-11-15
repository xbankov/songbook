<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getSong, getVersion, type SongResponse, type SongVersion } from '../api/songs'
import { useSettingsStore } from '../stores/settings'
import SongDisplay from '../components/SongDisplay.vue'

const route = useRoute()
const settingsStore = useSettingsStore()

const song = ref<SongResponse | SongVersion | null>(null)
const loading = ref(true)
const error = ref('')
const columns = ref<1 | 2>(route.query.columns === '2' ? 2 : 1)
const hasExplicitColumns =
  route.query.columns === '1' || route.query.columns === '2'
let requestId = 0

async function load(id: string) {
  const currentRequest = ++requestId
  loading.value = true
  error.value = ''
  song.value = null
  const version = route.query.version ? Number(route.query.version) : null
  try {
    const [loaded] = await Promise.all([
      version ? getVersion(id, version) : getSong(id),
      settingsStore.fetchSettings().catch(() => {}),
    ])
    if (currentRequest !== requestId) return
    song.value = loaded
    if (!hasExplicitColumns) {
      columns.value = settingsStore.doubleColumn ? 2 : 1
    }
  } catch (e: unknown) {
    if (currentRequest !== requestId) return
    error.value = e instanceof Error ? e.message : 'Could not load song'
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

watch(
  () => [route.params.id as string, route.query.version] as const,
  ([id]) => {
    void load(id)
  },
  { immediate: true },
)

const canPrint = computed(() => !loading.value && !error.value && !!song.value)

function printPage() {
  if (canPrint.value) window.print()
}
</script>

<template>
  <div class="print-page">
    <div class="print-toolbar">
      <span class="toolbar-label">Columns:</span>
      <button :class="{ active: columns === 1 }" @click="columns = 1">1</button>
      <button :class="{ active: columns === 2 }" @click="columns = 2">2</button>
      <button class="print-btn" :disabled="!canPrint" @click="printPage">Print</button>
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
      :columns-override="columns"
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
.print-toolbar button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
