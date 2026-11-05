<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongbookStore } from '../stores/songbooks'
import { useSongStore } from '../stores/songs'
import { useSettingsStore } from '../stores/settings'
import SongDisplay from '../components/SongDisplay.vue'

const route = useRoute()
const router = useRouter()
const store = useSongbookStore()
const songStore = useSongStore()
const settingsStore = useSettingsStore()

const addSongId = ref('')
const expandedEntry = ref<string | null>(null)

onMounted(async () => {
  await Promise.all([
    store.fetchSongbook(route.params.id as string),
    songStore.fetchSongs(),
    settingsStore.fetchSettings(),
  ])
})

const songbook = computed(() => store.current)

async function addSong() {
  if (!addSongId.value) return
  await store.addSong(route.params.id as string, addSongId.value)
  addSongId.value = ''
}

async function removeEntry(entryId: string) {
  await store.removeSong(route.params.id as string, entryId)
}

function toggleExpand(entryId: string) {
  expandedEntry.value = expandedEntry.value === entryId ? null : entryId
}

function printSongbook() {
  const params = new URLSearchParams()
  window.open(`/api/export/songbook/${route.params.id}/pdf?${params}`, '_blank')
}
</script>

<template>
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
        <router-link to="/songbooks" class="btn-secondary">Back</router-link>
      </div>
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
