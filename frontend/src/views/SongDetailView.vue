<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import { useSettingsStore } from '../stores/settings'
import SongDisplay from '../components/SongDisplay.vue'
import ChordDiagram from '../components/ChordDiagram.vue'
import AppNotice from '../components/AppNotice.vue'
import {
  analyzeSong,
  favoriteVersion,
  forkVersion,
  listVersions,
  restoreVersion,
  unfavoriteVersion,
  type SongVersion,
} from '../api/songs'
import { apiDelete, apiUpload, downloadFile, openFile } from '../api/client'

const route = useRoute()
const router = useRouter()
const store = useSongStore()
const settingsStore = useSettingsStore()

const suggestedKey = ref<string | null>(null)
const keyConfidence = ref<number | null>(null)
const selectedChord = ref<string | null>(null)
const hasAudio = ref(false)
const recording = ref(false)
const pdfError = ref('')
const audioError = ref('')
const exportError = ref('')
const versions = ref<SongVersion[]>([])
const showHistory = ref(false)
const loadingVersions = ref(false)
const restoringVersion = ref<number | null>(null)
const historyError = ref('')
const historyNotice = ref('')
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

onMounted(async () => {
  await Promise.all([
    store.fetchSong(route.params.id as string),
    settingsStore.fetchSettings().catch(() => {}),
  ])
  if (store.current) {
    hasAudio.value = !!(store.current.metadata?.audio_file)
    try {
      const analysis = await analyzeSong(route.params.id as string)
      suggestedKey.value = analysis.suggested_key
      keyConfidence.value = analysis.confidence
    } catch {}
  }
})

const song = computed(() => store.current)

const successNotice = computed(() => {
  if (route.query.created) return 'Song created'
  if (route.query.imported) return 'Song imported'
  return ''
})

async function removeSong() {
  if (confirm('Delete this song? All versions will be lost.')) {
    await store.deleteSong(route.params.id as string)
    router.push('/songs')
  }
}

async function printSong() {
  pdfError.value = ''
  try {
    await openFile(`/api/export/song/${route.params.id}/pdf`)
  } catch (e: unknown) {
    pdfError.value = e instanceof Error ? e.message : 'Could not open PDF'
  }
}

function printBrowser() {
  router.push({
    name: 'SongPrint',
    params: { id: route.params.id },
  })
}

async function downloadChordPro() {
  if (!song.value) return
  exportError.value = ''
  try {
    await downloadFile(
      `/api/songs/${song.value.id}/export?format=chordpro`,
      `${song.value.title}.cho`,
    )
  } catch (e: unknown) {
    exportError.value = e instanceof Error ? e.message : 'Could not download ChordPro'
  }
}

async function toggleHistory() {
  showHistory.value = !showHistory.value
  if (!showHistory.value || versions.value.length) return
  loadingVersions.value = true
  historyError.value = ''
  try {
    versions.value = await listVersions(route.params.id as string)
  } catch (e: unknown) {
    historyError.value = e instanceof Error ? e.message : 'Could not load versions'
  } finally {
    loadingVersions.value = false
  }
}

function favoriteVersions(): number[] {
  const value = store.current?.metadata?.favorite_versions
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === 'number')
    : []
}

function isFavorite(version: number): boolean {
  return favoriteVersions().includes(version)
}

async function toggleFavorite(version: SongVersion) {
  historyError.value = ''
  historyNotice.value = ''
  try {
    const song = isFavorite(version.version)
      ? await unfavoriteVersion(route.params.id as string, version.version)
      : await favoriteVersion(route.params.id as string, version.version)
    store.current = song
  } catch (e: unknown) {
    historyError.value = e instanceof Error ? e.message : 'Could not update favourite'
  }
}

async function copyVersionLink(version: SongVersion) {
  const url = `${window.location.origin}/songs/${route.params.id}/print?version=${version.version}`
  try {
    await navigator.clipboard.writeText(url)
    historyError.value = ''
    historyNotice.value = `Link to v${version.version} copied`
  } catch {
    historyError.value = 'Could not copy the link'
  }
}

async function fork(version: SongVersion) {
  if (!confirm(`Fork version ${version.version} into a new song?`)) return
  historyError.value = ''
  historyNotice.value = ''
  try {
    const song = await forkVersion(route.params.id as string, version.version)
    router.push(`/songs/${song.id}?created=1`)
  } catch (e: unknown) {
    historyError.value = e instanceof Error ? e.message : 'Fork failed'
  }
}
async function restore(version: SongVersion) {
  if (!confirm(`Restore version ${version.version}? This creates a new version.`)) return
  const songId = route.params.id as string
  restoringVersion.value = version.version
  historyError.value = ''

  let restored
  try {
    restored = await restoreVersion(songId, version.version)
  } catch (e: unknown) {
    historyError.value = e instanceof Error ? e.message : 'Restore failed'
    restoringVersion.value = null
    return
  }

  // Ignore a late response if the user navigated away or a newer edit won.
  const isCurrentSong = route.params.id === restored.id
  const isNewest = !store.current || restored.version >= store.current.version
  if (isCurrentSong && isNewest) {
    store.current = restored
    try {
      const analysis = await analyzeSong(songId)
      suggestedKey.value = analysis.suggested_key
      keyConfidence.value = analysis.confidence
    } catch {}
  }

  try {
    versions.value = isCurrentSong ? await listVersions(songId) : []
  } catch {
    // The restore itself succeeded; clear the cache so reopening retries.
    versions.value = []
    historyError.value = 'Restored, but could not refresh history'
  } finally {
    restoringVersion.value = null
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      const formData = new FormData()
      formData.append('file', blob, 'recording.webm')
      audioError.value = ''
      try {
        await apiUpload(`/api/songs/${route.params.id}/audio`, formData)
        hasAudio.value = true
      } catch (e: unknown) {
        audioError.value = e instanceof Error ? e.message : 'Upload failed'
      }
    }
    mediaRecorder.start()
    recording.value = true
  } catch (e: unknown) {
    audioError.value = e instanceof Error ? e.message : 'Recording failed'
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
    recording.value = false
  }
}

async function deleteAudio() {
  if (!confirm('Delete audio recording?')) return
  audioError.value = ''
  try {
    await apiDelete(`/api/songs/${route.params.id}/audio`)
    hasAudio.value = false
  } catch (e: unknown) {
    audioError.value = e instanceof Error ? e.message : 'Could not delete recording'
  }
}

const chords = computed(() => {
  if (!song.value) return []
  const set = new Set<string>()
  const re = /\[([^\]]+)\]/g
  let m: RegExpExecArray | null
  while ((m = re.exec(song.value.body)) !== null) {
    const c = m[1].trim()
    if (c && /^[A-G][#b]?(m|min|maj|dim|aug|sus|add|[0-9])*/i.test(c)) {
      set.add(c)
    }
  }
  return [...set].sort()
})
</script>

<template>
  <div class="detail-page">
    <div v-if="store.loading" class="loading">Loading...</div>
    <div v-else-if="!song" class="error">Song not found</div>
    <template v-else>
      <AppNotice v-if="successNotice" type="success" :message="successNotice" />
      <AppNotice v-if="pdfError" type="error" :message="pdfError" />
      <AppNotice v-if="audioError" type="error" :message="audioError" />
      <AppNotice v-if="exportError" type="error" :message="exportError" />

      <div class="detail-actions">
        <router-link :to="`/songs/${song.id}/edit`" class="btn-secondary">Edit</router-link>
        <button @click="printSong" class="btn-secondary">PDF</button>
        <button @click="downloadChordPro" class="btn-secondary">ChordPro</button>
        <button @click="printBrowser" class="btn-secondary">Print</button>
        <button @click="toggleHistory" class="btn-secondary">
          {{ showHistory ? 'Hide History' : 'History' }}
        </button>
        <button @click="removeSong" class="btn-danger">Delete</button>
        <router-link to="/songs" class="btn-secondary">Back</router-link>
      </div>

      <AppNotice v-if="historyError" type="error" :message="historyError" />
      <AppNotice v-if="historyNotice" type="success" :message="historyNotice" />

      <div v-if="showHistory" class="history-panel">
        <h2>Version history</h2>
        <div v-if="loadingVersions" class="history-loading">Loading...</div>
        <div v-else class="history-list">
          <div v-for="v in versions" :key="v.id" class="history-row">
            <div class="history-info">
              <strong>v{{ v.version }}</strong>
              <span>by {{ v.author }}</span>
              <span>{{ new Date(v.created_at).toLocaleString() }}</span>
            </div>
            <div class="history-actions">
              <button
                class="btn-secondary"
                :title="isFavorite(v.version) ? 'Remove favourite' : 'Favourite'"
                @click="toggleFavorite(v)"
              >
                {{ isFavorite(v.version) ? '★' : '☆' }}
              </button>
              <button class="btn-secondary" @click="copyVersionLink(v)">Link</button>
              <button class="btn-secondary" @click="fork(v)">Fork</button>
              <button
                class="btn-secondary"
                :disabled="restoringVersion !== null"
                @click="restore(v)"
              >
                {{ restoringVersion === v.version ? 'Restoring...' : 'Restore' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="suggestedKey" class="key-suggestion">
        Suggested key: <strong>{{ suggestedKey }}</strong>
        <span v-if="keyConfidence !== null" class="confidence">({{ keyConfidence }}% confidence)</span>
      </div>

      <div class="audio-section">
        <button v-if="!recording && !hasAudio" @click="startRecording" class="btn-secondary">Record Audio</button>
        <button v-if="recording" @click="stopRecording" class="btn-danger">Stop Recording</button>
        <template v-if="hasAudio">
          <audio :src="`/api/songs/${route.params.id}/audio`" controls class="audio-player" preload="none"></audio>
          <button @click="deleteAudio" class="btn-danger-sm" title="Delete audio">×</button>
        </template>
      </div>

      <div v-if="chords.length" class="chord-diagrams">
        <ChordDiagram
          v-for="c in chords"
          :key="c"
          :chord="c"
          @click="selectedChord = selectedChord === c ? null : c"
          class="chord-item"
        />
      </div>

      <SongDisplay
        :chordpro="song.body"
        :title="song.title"
        :artist="song.artist"
        :capo="song.capo"
        :song-key="song.key"
        :suggested-key="suggestedKey"
      />

      <div class="version-info">
        <span>Version {{ song.version }}</span>
        <span>Updated {{ new Date(song.updated_at).toLocaleDateString() }}</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.history-panel {
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
}
.history-panel h2 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
}
.history-loading {
  color: var(--text-muted);
  font-size: 0.85rem;
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.history-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.35rem 0;
  border-top: 1px solid var(--border);
}
.history-info {
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
  font-size: 0.85rem;
}
.history-info span {
  color: var(--text-muted);
  font-size: 0.8rem;
}
.history-actions {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
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
.btn-secondary:hover {
  border-color: var(--accent);
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
.loading,
.error {
  text-align: center;
  padding: 2rem;
}
.version-info {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--text-muted);
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.key-suggestion {
  margin-bottom: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface);
  border: 1px solid var(--accent);
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--text);
}
.key-suggestion strong {
  color: var(--accent);
}
.confidence {
  color: var(--text-muted);
  font-size: 0.8rem;
}
.chord-diagrams {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
}
.chord-item {
  cursor: pointer;
}
.audio-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
}
.audio-player {
  flex: 1;
  max-width: 300px;
  height: 36px;
}
.btn-danger-sm {
  background: none;
  border: none;
  color: var(--danger);
  font-size: 1.2rem;
  cursor: pointer;
}

@media print {
  .version-info {
    display: none !important;
  }
}
</style>
