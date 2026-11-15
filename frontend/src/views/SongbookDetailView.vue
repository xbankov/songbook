<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongbookStore } from '../stores/songbooks'
import { useSongStore } from '../stores/songs'
import { useSettingsStore } from '../stores/settings'
import SongDisplay from '../components/SongDisplay.vue'
import AppNotice from '../components/AppNotice.vue'
import { openFile } from '../api/client'
import type { SongbookEntryResponse } from '../api/songbooks'

const route = useRoute()
const router = useRouter()
const store = useSongbookStore()
const songStore = useSongStore()
const settingsStore = useSettingsStore()

const addSongId = ref('')
const expandedEntry = ref<string | null>(null)
const error = ref('')
const editing = ref(false)
const editName = ref('')
const editDesc = ref('')
const pendingEntries = ref<Record<string, boolean>>({})

onMounted(async () => {
  try {
    await Promise.all([
      store.fetchSongbook(route.params.id as string),
      songStore.fetchSongs(),
      settingsStore.fetchSettings(),
    ])
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load songbook'
  }
})

const songbook = computed(() => store.current)

async function addSong() {
  if (!addSongId.value) return
  error.value = ''
  try {
    await store.addSong(route.params.id as string, addSongId.value)
    addSongId.value = ''
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not add song'
  }
}

async function removeEntry(entryId: string) {
  error.value = ''
  try {
    await store.removeSong(route.params.id as string, entryId)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not remove song'
  }
}

function toggleExpand(entryId: string) {
  expandedEntry.value = expandedEntry.value === entryId ? null : entryId
}

function startEdit() {
  if (!songbook.value) return
  editName.value = songbook.value.name
  editDesc.value = songbook.value.description || ''
  editing.value = true
}

async function saveEdit() {
  if (!songbook.value || !editName.value.trim()) return
  error.value = ''
  const data: { name?: string; description?: string } = {}
  if (editName.value.trim() !== songbook.value.name) {
    data.name = editName.value.trim()
  }
  if (editDesc.value !== (songbook.value.description || '')) {
    data.description = editDesc.value
  }
  try {
    if (Object.keys(data).length) {
      await store.updateSongbook(route.params.id as string, data)
    }
    editing.value = false
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not update songbook'
  }
}

async function deleteBook() {
  if (!confirm(`Delete "${songbook.value?.name}"? This does not delete the songs.`)) return
  error.value = ''
  try {
    await store.deleteSongbook(route.params.id as string)
    router.push('/songbooks')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not delete songbook'
  }
}

async function moveEntry(entry: SongbookEntryResponse, direction: number) {
  if (!songbook.value || pendingEntries.value[entry.id]) return
  const entries = [...songbook.value.entries].sort((a, b) => a.sort_order - b.sort_order)
  const index = entries.findIndex((item) => item.id === entry.id)
  const target = index + direction
  if (index < 0 || target < 0 || target >= entries.length) return
  const ids = entries.map((item) => item.id)
  ;[ids[index], ids[target]] = [ids[target], ids[index]]
  error.value = ''
  pendingEntries.value[entry.id] = true
  try {
    await store.reorderEntries(route.params.id as string, ids)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not reorder'
  } finally {
    pendingEntries.value[entry.id] = false
  }
}

async function changeTranspose(entry: SongbookEntryResponse, delta: number) {
  if (pendingEntries.value[entry.id]) return
  const current = songbook.value?.entries.find((item) => item.id === entry.id) || entry
  error.value = ''
  pendingEntries.value[entry.id] = true
  try {
    await store.updateEntry(route.params.id as string, entry.id, {
      transpose: Math.max(-11, Math.min(11, current.transpose + delta)),
    })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not transpose'
  } finally {
    pendingEntries.value[entry.id] = false
  }
}

async function toggleEntryColumns(entry: SongbookEntryResponse) {
  if (pendingEntries.value[entry.id]) return
  const current = songbook.value?.entries.find((item) => item.id === entry.id) || entry
  error.value = ''
  pendingEntries.value[entry.id] = true
  try {
    await store.updateEntry(route.params.id as string, entry.id, {
      double_column: current.double_column ? 0 : 1,
    })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not change columns'
  } finally {
    pendingEntries.value[entry.id] = false
  }
}

async function printSongbook() {
  error.value = ''
  try {
    await openFile(`/api/export/songbook/${route.params.id}/pdf`)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not open PDF'
  }
}
</script>

<template>
  <AppNotice v-if="error" type="error" :message="error" />

  <div v-if="store.loading" class="loading">Loading...</div>
  <div v-else-if="!songbook" class="error">Songbook not found</div>
  <template v-else>
    <div class="header">
      <div>
        <h1>{{ songbook.name }}</h1>
        <p v-if="songbook.description" class="desc">{{ songbook.description }}</p>
      </div>
      <div class="actions">
        <button @click="printSongbook" class="btn-secondary">Print PDF</button>
        <button @click="startEdit" class="btn-secondary">Edit</button>
        <button @click="deleteBook" class="btn-danger">Delete</button>
        <router-link to="/songbooks" class="btn-secondary">Back</router-link>
      </div>
    </div>

    <div v-if="editing" class="edit-book">
      <input v-model="editName" class="input" placeholder="Songbook name" />
      <input v-model="editDesc" class="input" placeholder="Description" />
      <button @click="saveEdit" class="btn-primary">Save</button>
      <button @click="editing = false" class="btn-secondary">Cancel</button>
    </div>

    <div class="add-song">
      <select v-model="addSongId" class="input">
        <option value="" disabled>Select a song...</option>
        <option v-for="s in songStore.songs" :key="s.id" :value="s.id">
          {{ s.title }} — {{ s.artist }}
        </option>
      </select>
      <button @click="addSong" class="btn-primary">Add</button>
    </div>

    <div v-if="songbook.entries.length === 0" class="empty">No songs in this songbook. Add some!</div>

    <div v-else class="entries">
      <div v-for="entry in songbook.entries" :key="entry.id" class="entry">
        <div class="entry-main" @click="toggleExpand(entry.id)">
          <div class="entry-info">
            <span class="entry-order">{{ entry.sort_order + 1 }}.</span>
            <router-link :to="`/songs/${entry.song_id}`" class="entry-title" @click.stop>
              {{ entry.song?.title || 'Unknown' }}
            </router-link>
            <span class="entry-artist">{{ entry.song?.artist }}</span>
          </div>
          <div class="entry-controls" @click.stop>
            <button
              :disabled="pendingEntries[entry.id]"
              @click="moveEntry(entry, -1)"
              title="Move up"
            >
              ↑
            </button>
            <button
              :disabled="pendingEntries[entry.id]"
              @click="moveEntry(entry, 1)"
              title="Move down"
            >
              ↓
            </button>
            <button
              :disabled="pendingEntries[entry.id]"
              @click="changeTranspose(entry, -1)"
              title="Transpose down"
            >
              −
            </button>
            <span class="entry-transpose">{{ entry.transpose > 0 ? '+' : '' }}{{ entry.transpose }}</span>
            <button
              :disabled="pendingEntries[entry.id]"
              @click="changeTranspose(entry, 1)"
              title="Transpose up"
            >
              +
            </button>
            <button
              :class="['entry-columns', { active: entry.double_column }]"
              :disabled="pendingEntries[entry.id]"
              @click="toggleEntryColumns(entry)"
              title="Toggle 2 columns"
            >
              2-col
            </button>
          </div>
          <button @click.stop="removeEntry(entry.id)" class="btn-remove">×</button>
        </div>
        <div v-if="expandedEntry === entry.id" class="entry-detail">
          <SongDisplay
            v-if="entry.song"
            :chordpro="entry.song.body"
            :title="entry.song.title"
            :artist="entry.song.artist"
            :capo="entry.song.capo"
            :song-key="entry.song.key"
            :transpose-override="entry.transpose"
            :columns-override="entry.double_column ? 2 : 1"
            hide-settings-controls
          />
        </div>
      </div>
    </div>
  </template>
</template>

<style scoped>
.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.header h1 {
  margin: 0;
  font-size: 1.4rem;
}
.desc {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}
.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.edit-book {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.btn-danger {
  padding: 0.4rem 0.8rem;
  background: transparent;
  border: 1px solid #e74c3c;
  color: #e74c3c;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-danger:hover {
  background: #e74c3c;
  color: #fff;
}
.btn-secondary {
  padding: 0.4rem 0.8rem;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  font-size: 0.85rem;
}
.btn-primary {
  padding: 0.4rem 1rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.add-song {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  align-items: center;
  flex-wrap: wrap;
}
.input {
  flex: 1;
  min-width: 150px;
  padding: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
}
.entries {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.entry {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
}
.entry-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
}
.entry-main:hover {
  border-color: var(--accent);
}
.entry-controls {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  margin-left: auto;
  margin-right: 0.5rem;
}
.entry-controls button {
  min-width: 1.5rem;
  padding: 0.15rem 0.3rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--text-muted);
  font-size: 0.75rem;
  cursor: pointer;
}
.entry-controls button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
}
.entry-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.entry-transpose {
  min-width: 1.6rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.75rem;
}
.entry-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.entry-order {
  color: var(--text-muted);
  font-size: 0.85rem;
  min-width: 2rem;
}
.entry-title {
  font-weight: 600;
  text-decoration: none;
  color: var(--text);
}
.entry-title:hover {
  color: var(--accent);
}
.entry-artist {
  color: var(--text-muted);
  font-size: 0.85rem;
}
.btn-remove {
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 1.2rem;
  cursor: pointer;
}
.entry-detail {
  padding: 0.75rem;
  border-top: 1px solid var(--border);
}
.loading,
.error,
.empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}
</style>
