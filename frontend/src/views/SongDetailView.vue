<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import { useSettingsStore } from '../stores/settings'
import SongDisplay from '../components/SongDisplay.vue'
import ChordDiagram from '../components/ChordDiagram.vue'
import { analyzeSong } from '../api/songs'

const route = useRoute()
const router = useRouter()
const store = useSongStore()
const settingsStore = useSettingsStore()

const suggestedKey = ref<string | null>(null)
const keyConfidence = ref<number | null>(null)
const selectedChord = ref<string | null>(null)
const hasAudio = ref(false)
const recording = ref(false)
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

onMounted(async () => {
  await Promise.all([
    store.fetchSong(route.params.id as string),
    settingsStore.fetchSettings(),
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

async function removeSong() {
  if (confirm('Delete this song? All versions will be lost.')) {
    await store.deleteSong(route.params.id as string)
    router.push('/songs')
  }
}

function printSong() {
  window.open(`/api/export/song/${route.params.id}/pdf`, '_blank')
}

function printBrowser() {
  window.print()
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
      try {
        await fetch(`/api/songs/${route.params.id}/audio`, { method: 'POST', body: formData })
        hasAudio.value = true
      } catch (e) { console.error('Upload failed', e) }
    }
    mediaRecorder.start()
    recording.value = true
  } catch (e) { console.error('Recording failed', e) }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
    recording.value = false
  }
}

async function deleteAudio() {
  if (!confirm('Delete audio recording?')) return
  try {
    await fetch(`/api/songs/${route.params.id}/audio`, { method: 'DELETE' })
    hasAudio.value = false
  } catch {}
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
      <div class="detail-actions">
        <router-link :to="`/songs/${song.id}/edit`" class="btn-secondary">Edit</router-link>
        <button @click="printSong" class="btn-secondary">PDF</button>
        <button @click="printBrowser" class="btn-secondary">Print</button>
        <button @click="removeSong" class="btn-danger">Delete</button>
        <router-link to="/songs" class="btn-secondary">Back</router-link>
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
</style>
