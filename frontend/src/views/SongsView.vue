<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import { apiDownload, apiGet, apiPost, downloadFile, openFile } from '../api/client'
import { useDebounceFn } from '@vueuse/core'
import AppNotice from '../components/AppNotice.vue'

const router = useRouter()
const store = useSongStore()

const notice = ref<{ type: 'info' | 'success' | 'error'; message: string } | null>(null)

function showNotice(type: 'info' | 'success' | 'error', message: string) {
  // Do not let a later success hide an outstanding error from another action.
  if (type !== 'error' && notice.value?.type === 'error') return
  notice.value = { type, message }
}

const search = ref('')
const artist = ref('')
const difficulty = ref('')
const genre = ref('')
const letter = ref('')
const page = ref(1)
const pageSize = 25
const totalPages = computed(() => Math.max(1, Math.ceil(store.total / pageSize)))
const pageNumbers = computed(() => {
  const start = Math.max(1, page.value - 2)
  const end = Math.min(totalPages.value, start + 4)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})
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
const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')
const selected = ref<Set<string>>(new Set())
const selectedIds = computed(() => Array.from(selected.value))
const allSelected = computed(
  () =>
    store.songs.length > 0 &&
    store.songs.every((song) => selected.value.has(song.id)),
)

function toggleSelect(id: string) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function toggleAll() {
  const next = new Set(selected.value)
  if (allSelected.value) {
    store.songs.forEach((song) => next.delete(song.id))
  } else {
    store.songs.forEach((song) => next.add(song.id))
  }
  selected.value = next
}

function selectionQuery(): string {
  return selectedIds.value
    .map((id) => `ids=${encodeURIComponent(id)}`)
    .join('&')
}

interface SearchResult {
  title: string
  artist: string
  url: string
  source: string
  rating: number
}

function listParams() {
  return {
    search: search.value || undefined,
    artist: artist.value || undefined,
    difficulty: difficulty.value || undefined,
    genre: genre.value || undefined,
    letter: letter.value || undefined,
    sort: sortBy.value,
    order: sortOrder.value,
    limit: pageSize,
    offset: (page.value - 1) * pageSize,
  }
}

async function fetchPage() {
  await store.fetchSongs(listParams())
  if (page.value > totalPages.value) {
    page.value = totalPages.value
    await store.fetchSongs(listParams())
  }
}

onMounted(fetchPage)

const doSearch = useDebounceFn(async () => {
  page.value = 1
  await fetchPage()
}, 300)

function goToPage(target: number) {
  if (store.loading) return
  page.value = Math.min(Math.max(1, target), totalPages.value)
  void fetchPage()
}

function setLetter(value: string) {
  letter.value = letter.value === value ? '' : value
  void doSearch()
}

function clearFilters() {
  search.value = ''
  artist.value = ''
  difficulty.value = ''
  genre.value = ''
  letter.value = ''
  page.value = 1
  void fetchPage()
}

async function doImport() {
  if (!importUrl.value) return
  try {
    const song = await store.importSong(importUrl.value)
    router.push(`/songs/${song.id}?imported=1`)
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Import failed')
  }
}

async function removeSong(id: string) {
  if (!confirm('Delete this song?')) return
  try {
    await store.deleteSong(id)
    const next = new Set(selected.value)
    next.delete(id)
    selected.value = next
    showNotice('success', 'Song deleted')
    if (page.value > totalPages.value) page.value = totalPages.value
    await fetchPage()
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Delete failed')
  }
}

async function doBulkImport() {
  if (!bulkText.value.trim()) return
  bulkImporting.value = true
  try {
    const imported = await store.bulkImport(bulkText.value)
    bulkText.value = ''
    showBulkImport.value = false
    showNotice('success', `Imported ${imported.length} song${imported.length === 1 ? '' : 's'}`)
    page.value = 1
    await fetchPage()
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Bulk import failed')
  } finally {
    bulkImporting.value = false
  }
}

async function exportSelected() {
  if (!selectedIds.value.length) return
  try {
    await downloadFile(
      `/api/songs/export/selected?${selectionQuery()}`,
      'selected.cho',
    )
    showNotice('success', `Exported ${selectedIds.value.length} songs`)
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Export failed')
  }
}

async function printSelected() {
  if (!selectedIds.value.length) return
  try {
    await openFile(`/api/export/selected/pdf?${selectionQuery()}`)
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Could not open PDF')
  }
}

async function bulkExport(format: string) {
  try {
    const blob = await apiDownload(`/api/songs/export/bulk?format=${format}`)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `songs.${format}`; a.click()
    URL.revokeObjectURL(url)
    showNotice('success', `Exported ${format}`)
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Export failed')
  }
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
    router.push(`/songs/${song.id}?imported=1`)
  } catch (e: unknown) {
    showNotice('error', e instanceof Error ? e.message : 'Import failed')
  }
}
</script>

<template>
  <div class="songs-page">
    <div class="toolbar">
      <input v-model="search" placeholder="Search songs..." @input="doSearch" class="search-input" />
      <input v-model="artist" placeholder="Filter by artist..." @input="doSearch" class="search-input" />
      <select v-model="difficulty" @change="doSearch" class="search-input filter-select">
        <option value="">All difficulties</option>
        <option value="easy">Easy</option>
        <option value="medium">Medium</option>
        <option value="hard">Hard</option>
      </select>
      <input v-model="genre" placeholder="Genre" @input="doSearch" class="search-input" />
      <button
        v-if="search || artist || difficulty || genre || letter"
        @click="clearFilters"
        class="btn-secondary"
      >
        Clear
      </button>
      <label class="select-all">
        <input type="checkbox" :checked="allSelected" @change="toggleAll" />
        Select all
      </label>
      <button
        :disabled="!selectedIds.length"
        @click="printSelected"
        class="btn-secondary"
      >
        Print selected ({{ selectedIds.length }})
      </button>
      <button
        :disabled="!selectedIds.length"
        @click="exportSelected"
        class="btn-secondary"
      >
        Export selected
      </button>
      <button @click="showImport = !showImport" class="btn-secondary">Import URL</button>
      <button @click="showSearchImport = !showSearchImport" class="btn-secondary">Search</button>
      <button @click="showBulkImport = !showBulkImport" class="btn-secondary">Bulk</button>
      <button @click="bulkExport('chordpro')" class="btn-secondary" title="Export all as ChordPro">Export</button>
    </div>

    <div class="alphabet">
      <button
        v-for="l in alphabet"
        :key="l"
        :class="{ active: letter === l }"
        @click="setLetter(l)"
      >
        {{ l }}
      </button>
      <button :class="{ active: letter === '#' }" @click="setLetter('#')">#</button>
    </div>

    <AppNotice v-if="notice" :type="notice.type" :message="notice.message" />

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
          <div v-if="song.tags?.length" class="song-tags">
            <span
              v-for="tag in song.tags.filter((t) => t.startsWith('difficulty:') || t.startsWith('genre:'))"
              :key="tag"
              class="tag"
            >
              {{ tag.replace(':', ': ') }}
            </span>
          </div>
        </div>
        <div class="song-card-meta">
          <input
            type="checkbox"
            class="song-select"
            :checked="selected.has(song.id)"
            @click.stop="toggleSelect(song.id)"
            title="Select song"
          />
          <span class="badge">v{{ song.version }}</span>
          <button @click.stop="removeSong(song.id)" class="btn-danger-sm" title="Delete">×</button>
        </div>
      </div>
    </div>

    <div v-if="store.total" class="pagination">
      <template v-if="store.total > pageSize">
        <button :disabled="store.loading || page === 1" @click="goToPage(page - 1)">Previous</button>
        <button
          v-for="p in pageNumbers"
          :key="p"
          :disabled="store.loading"
          :class="{ active: p === page }"
          @click="goToPage(p)"
        >
          {{ p }}
        </button>
        <button :disabled="store.loading || page === totalPages" @click="goToPage(page + 1)">Next</button>
      </template>
      <span class="page-info">{{ store.total }} songs</span>
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
.filter-select {
  flex: 0 0 auto;
  min-width: 140px;
}
.select-all {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}
.toolbar button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.song-select {
  cursor: pointer;
}
.alphabet {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
  margin-bottom: 1rem;
}
.alphabet button {
  min-width: 1.6rem;
  padding: 0.2rem 0.35rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--text-muted);
  font-size: 0.75rem;
  cursor: pointer;
}
.alphabet button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
}
.song-tags {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}
.tag {
  font-size: 0.7rem;
  color: var(--text-muted);
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
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
.pagination {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}
.pagination button {
  min-width: 2rem;
  padding: 0.3rem 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 0.8rem;
  cursor: pointer;
}
.pagination button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
}
.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  margin-left: 0.5rem;
  color: var(--text-muted);
  font-size: 0.8rem;
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
