<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import { apiGet, apiPost } from '../api/client'
import { useDebounceFn } from '@vueuse/core'

const router = useRouter()
const store = useSongStore()

const search = ref('')
const artist = ref('')
const sortBy = ref('updated_at')
const sortOrder = ref('desc')
const importUrl = ref('')
const showImport = ref(false)
const showBulkImport = ref(false)
const bulkText = ref('')
const bulkImporting = ref(false)
const showSearchImport = ref(false)
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const searching = ref(false)

interface SearchResult {
  title: string
  artist: string
  url: string
  source: string
  rating: number
}

onMounted(() => store.fetchSongs())

const doSearch = useDebounceFn(async () => {
  await store.fetchSongs({
    search: search.value || undefined,
    artist: artist.value || undefined,
    sort: sortBy.value,
    order: sortOrder.value,
  })
}, 300)

async function doImport() {
  if (!importUrl.value) return
  try {
    const song = await store.importSong(importUrl.value)
    router.push(`/songs/${song.id}`)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : 'Import failed')
  }
}

async function removeSong(id: string) {
  if (confirm('Delete this song?')) {
    await store.deleteSong(id)
  }
}

async function doBulkImport() {
  if (!bulkText.value.trim()) return
  bulkImporting.value = true
  try {
    await store.bulkImport(bulkText.value)
    bulkText.value = ''
    showBulkImport.value = false
    await store.fetchSongs()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : 'Bulk import failed')
  } finally {
    bulkImporting.value = false
  }
}

async function bulkExport(format: string) {
  const token = localStorage.getItem('auth')
  const headers: Record<string, string> = {}
  if (token) {
    try { headers['Authorization'] = `Bearer ${JSON.parse(token).accessToken}` } catch {}
  }
  const resp = await fetch(`/api/songs/export/bulk?format=${format}`, { headers })
  if (!resp.ok) return
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `songs.${format}`; a.click()
  URL.revokeObjectURL(url)
}

async function doSearchImport() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const data = await apiGet<{ results: SearchResult[] }>('/api/search', { q: searchQuery.value })
    searchResults.value = data.results
  } catch {
    searchResults.value = []
  } finally {
    searching.value = false
  }
}

async function importSearchResult(url: string) {
  try {
    const songData = await apiPost<{ title: string; artist: string; body: string }>(`/api/search/import?url=${encodeURIComponent(url)}`)
    const song = await store.createSong({
      title: songData.title,
      artist: songData.artist,
      body: songData.body,
    })
    router.push(`/songs/${song.id}`)
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : 'Import failed')
  }
}
</script>

<template>
  <div class="songs-page">
    <div class="toolbar">
      <input v-model="search" placeholder="Search songs..." @input="doSearch" class="search-input" />
      <input v-model="artist" placeholder="Filter by artist..." @input="doSearch" class="search-input" />
      <button @click="showImport = !showImport" class="btn-secondary">Import URL</button>
      <button @click="showSearchImport = !showSearchImport" class="btn-secondary">Search</button>
      <button @click="showBulkImport = !showBulkImport" class="btn-secondary">Bulk</button>
      <button @click="bulkExport('chordpro')" class="btn-secondary" title="Export all as ChordPro">Export</button>
    </div>

    <div v-if="showImport" class="import-bar">
      <input v-model="importUrl" placeholder="Ultimate Guitar or supermusic.sk URL..." class="search-input" />
      <button @click="doImport" class="btn-primary">Import Song</button>
    </div>

    <div v-if="showSearchImport" class="search-import">
      <div class="search-bar">
        <input v-model="searchQuery" placeholder="Search for songs to import..." class="search-input" @keyup.enter="doSearchImport" />
        <button @click="doSearchImport" class="btn-primary" :disabled="searching">{{ searching ? 'Searching...' : 'Search' }}</button>
      </div>
      <div v-if="searchResults.length" class="search-results">
        <div v-for="r in searchResults" :key="r.url" class="search-result">
          <div class="result-info">
            <strong>{{ r.title }}</strong> — {{ r.artist }}
            <span class="badge">{{ r.source }}</span>
          </div>
          <button @click="importSearchResult(r.url)" class="btn-sm">Import</button>
        </div>
      </div>
    </div>

    <div v-if="showBulkImport" class="bulk-import">
      <textarea v-model="bulkText" class="bulk-textarea" placeholder="Paste multiple ChordPro songs separated by ---" rows="8"></textarea>
      <button @click="doBulkImport" class="btn-primary" :disabled="bulkImporting">
        {{ bulkImporting ? 'Importing...' : 'Bulk Import' }}
      </button>
    </div>

    <div v-if="store.loading" class="loading">Loading...</div>
    <div v-else-if="store.error" class="error">{{ store.error }}</div>
    <div v-else-if="store.songs.length === 0" class="empty">
      No songs yet. Add one or import from Ultimate Guitar!
    </div>

    <div v-else class="song-list">
      <div v-for="song in store.songs" :key="song.id" class="song-card" @click="router.push(`/songs/${song.id}`)">
        <div class="song-card-info">
          <h3>{{ song.title }}</h3>
          <p>{{ song.artist }}</p>
        </div>
        <div class="song-card-meta">
          <span class="badge">v{{ song.version }}</span>
          <button @click.stop="removeSong(song.id)" class="btn-danger-sm" title="Delete">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.search-input {
  flex: 1;
  min-width: 150px;
  padding: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 0.9rem;
}
.search-input:focus {
  outline: none;
  border-color: var(--accent);
}
.import-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.btn-primary {
  padding: 0.5rem 1rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-secondary {
  padding: 0.5rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 4px;
  cursor: pointer;
}
.btn-secondary:hover {
  border-color: var(--accent);
}
.bulk-import {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.bulk-textarea {
  width: 100%;
  padding: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-family: monospace;
  font-size: 0.85rem;
  resize: vertical;
}
.search-import {
  margin-bottom: 1rem;
}
.search-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.search-results {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
}
.search-result {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.85rem;
}
.search-result:last-child {
  border-bottom: none;
}
.result-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.badge {
  font-size: 0.7rem;
  padding: 0.15rem 0.35rem;
  background: var(--hover);
  border-radius: 3px;
  color: var(--accent);
}
.btn-sm {
  padding: 0.25rem 0.5rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8rem;
}
.btn-danger-sm {
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 0.25rem;
}
.loading,
.empty,
.error {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}
.error {
  color: #e74c3c;
}
.song-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.song-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.song-card:hover {
  border-color: var(--accent);
}
.song-card-info h3 {
  margin: 0;
  font-size: 1rem;
}
.song-card-info p {
  margin: 0.2rem 0 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.song-card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.badge {
  font-size: 0.75rem;
  padding: 0.15rem 0.4rem;
  background: var(--hover);
  border-radius: 3px;
  color: var(--text-muted);
}
</style>
