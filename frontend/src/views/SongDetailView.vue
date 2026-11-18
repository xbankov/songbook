<script setup lang="ts">
import { watch, computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import { useSettingsStore } from '../stores/settings'
import { useAutoScroll } from '../composables/useAutoScroll'
import SongDisplay from '../components/SongDisplay.vue'
import ChordDiagram from '../components/ChordDiagram.vue'
import AppNotice from '../components/AppNotice.vue'
import {
  analyzeSong,
  favoriteVersion,
  forkVersion,
  listVersions,
  restoreVersion,
  setYoutubeLink,
  unfavoriteVersion,
  type KeyChord,
  type SongAnalysis,
  type SongVersion,
} from '../api/songs'
import { apiDelete, apiUpload, downloadFile, openFile } from '../api/client'

const route = useRoute()
const router = useRouter()
const store = useSongStore()
const settingsStore = useSettingsStore()

const suggestedKey = ref<string | null>(null)
const keyConfidence = ref<number | null>(null)
const keyMethod = ref<string | null>(null)
const keyType = ref<'major' | 'minor' | null>(null)
const keyChordCount = ref(0)
const keyChords = ref<string[]>([])
const keyEvidence = ref<KeyChord[]>([])
const keyPanelOpen = ref(false)
const keyPanel = ref<HTMLElement | null>(null)
const keyToggle = ref<HTMLButtonElement | null>(null)
const applyingKey = ref(false)
const keyError = ref('')
const keyNotice = ref('')
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
const storedYoutubeUrl = computed(() => {
  const value = store.current?.metadata?.youtube_url
  return typeof value === 'string' ? value : ''
})
const youtubeId = computed(() => {
  const match = storedYoutubeUrl.value.match(/[?&]v=([A-Za-z0-9_-]{11})(?:&|$)/)
  return match ? match[1] : ''
})
// Rebuilt from the id, so the link can only ever point at youtube.com.
const youtubeUrl = computed(() =>
  youtubeId.value ? `https://www.youtube.com/watch?v=${youtubeId.value}` : '',
)
const showVideo = ref(false)
const editingYoutube = ref(false)
const youtubeInput = ref('')
const youtubeError = ref('')
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

// Performance mode (#140): the song page itself becomes the full-screen,
// large-text, highlighted-line view. The old /songs/:id/play route redirects
// here with ?performance=1.
const performance = ref(false)
const activeLine = ref(0)
const fontSize = ref(1.4)
const stage = ref<HTMLElement | null>(null)
const {
  autoScroll,
  speed: scrollSpeed,
  toggle: toggleScroll,
  stop: stopScroll,
  changeSpeed,
} = useAutoScroll(stage)
const reduceMotion =
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
let wakeLock: { release: () => Promise<void> } | null = null
let unmounted = false

let loadRequestId = 0

async function loadSong(id: string) {
  const request = ++loadRequestId
  // Never show the previous song's key evidence while the next one loads.
  setAnalysis(null)
  await Promise.all([
    store.fetchSong(id),
    settingsStore.fetchSettings().catch(() => {}),
  ])
  if (request !== loadRequestId) return
  versions.value = []
  showHistory.value = false
  showVideo.value = false
  editingYoutube.value = false
  youtubeError.value = ''
  keyNotice.value = ''
  keyPanelOpen.value = false
  activeLine.value = 0
  if (store.current?.id === id) {
    hasAudio.value = !!(store.current.metadata?.audio_file)
    if (performance.value) void requestPerformanceFullscreen()
    try {
      const analysis = await analyzeSong(id)
      if (request !== loadRequestId) return
      setAnalysis(analysis)
    } catch {}
  }
}

watch(
  () => route.params.id as string,
  (id) => {
    void loadSong(id)
  },
  { immediate: true },
)

const song = computed(() => store.current)

function setAnalysis(analysis: SongAnalysis | null) {
  suggestedKey.value = analysis?.suggested_key ?? null
  keyConfidence.value = analysis?.confidence ?? null
  keyMethod.value = analysis?.method ?? null
  keyType.value = analysis?.key_type ?? null
  keyChordCount.value = analysis?.chord_count ?? 0
  keyChords.value = analysis?.key_chords ?? []
  keyEvidence.value = analysis?.chords ?? []
}

const keyInKeyCount = computed(() =>
  keyEvidence.value
    .filter((chord) => chord.in_key)
    .reduce((total, chord) => total + chord.count, 0),
)

function closeKeyPanel() {
  if (!keyPanelOpen.value) return
  keyPanelOpen.value = false
  keyToggle.value?.focus()
}

function toggleKeyPanel() {
  if (!keyPanelOpen.value) keyError.value = ''
  keyPanelOpen.value = !keyPanelOpen.value
}

function onKeyPanelPointerDown(event: PointerEvent) {
  const target = event.target as Node
  if (keyPanel.value?.contains(target) || keyToggle.value?.contains(target)) return
  closeKeyPanel()
}

function onKeyPanelKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeKeyPanel()
}

watch(keyPanelOpen, (open) => {
  if (open) {
    document.addEventListener('pointerdown', onKeyPanelPointerDown)
    document.addEventListener('keydown', onKeyPanelKeydown)
  } else {
    document.removeEventListener('pointerdown', onKeyPanelPointerDown)
    document.removeEventListener('keydown', onKeyPanelKeydown)
  }
})

async function applySuggestedKey() {
  if (!suggestedKey.value || !song.value) return
  const key = suggestedKey.value
  if (!confirm(`Use ${key} as the song key? This creates a new version.`)) return
  applyingKey.value = true
  keyError.value = ''
  try {
    const updated = await store.updateSong(song.value.id, { key })
    keyNotice.value = `Song key set to ${updated.key ?? key} (version ${updated.version})`
    closeKeyPanel()
  } catch (e: unknown) {
    keyError.value = e instanceof Error ? e.message : 'Could not set the song key'
  } finally {
    applyingKey.value = false
  }
}

function setPerformanceQuery(on: boolean) {
  const query = { ...route.query }
  if (on) query.performance = '1'
  else delete query.performance
  void router.replace({ query })
}

async function requestPerformanceFullscreen() {
  await nextTick()
  const element = stage.value
  if (!element || document.fullscreenElement) return
  try {
    await element.requestFullscreen()
  } catch {
    // Not supported (e.g. iOS Safari): the fixed stage still fills the window.
  }
}

async function keepScreenOn() {
  try {
    const nav = navigator as Navigator & {
      wakeLock?: { request: (type: 'screen') => Promise<{ release: () => Promise<void> }> }
    }
    const sentinel = (await nav.wakeLock?.request('screen')) ?? null
    if (unmounted || !performance.value) {
      void sentinel?.release().catch(() => {})
      return
    }
    // Overlapping requests (mount + quick toggle): keep only the newest.
    const previous = wakeLock
    wakeLock = sentinel
    if (previous && previous !== sentinel) void previous.release().catch(() => {})
  } catch {
    wakeLock = null
  }
}

async function enterPerformance(updateQuery = true) {
  if (performance.value) return
  performance.value = true
  activeLine.value = 0
  if (updateQuery) setPerformanceQuery(true)
  void keepScreenOn()
  await requestPerformanceFullscreen()
}

async function exitPerformance(updateQuery = true) {
  if (!performance.value) return
  performance.value = false
  stopScroll()
  void wakeLock?.release().catch(() => {})
  wakeLock = null
  if (updateQuery) setPerformanceQuery(false)
  if (document.fullscreenElement) {
    try {
      await document.exitFullscreen()
    } catch {
      // The browser already left full screen.
    }
  }
}

function togglePerformance() {
  if (performance.value) void exitPerformance()
  else void enterPerformance()
}

function selectLine(index: number) {
  const total = stage.value?.querySelectorAll('[data-line]').length ?? 0
  if (total === 0) return
  activeLine.value = Math.max(0, Math.min(total - 1, index))
}

function step(delta: number) {
  selectLine(activeLine.value + delta)
}

function changeFont(delta: number) {
  fontSize.value = Math.round(Math.max(0.8, Math.min(3, fontSize.value + delta)) * 10) / 10
}

watch(activeLine, async (index) => {
  if (!performance.value) return
  await nextTick()
  const line = stage.value?.querySelector(`[data-line="${index}"]`)
  // Keep the current line mid-screen. Jump rather than animate while
  // autoscroll runs, so its frames do not fight the line scroll.
  line?.scrollIntoView?.({
    block: 'center',
    behavior: autoScroll.value || reduceMotion ? 'auto' : 'smooth',
  })
})

watch(
  () => route.query.performance,
  (value) => {
    const on = value === '1'
    if (on && !performance.value) void enterPerformance(false)
    else if (!on && performance.value) void exitPerformance(false)
  },
)

function onKey(event: KeyboardEvent) {
  if (!performance.value) return
  // Leave browser shortcuts (Alt+Left = back, Shift+Space, ...) alone.
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
  const target = event.target
  // Space/Enter on a focused toolbar button press that button.
  if (target instanceof HTMLButtonElement && (event.key === ' ' || event.key === 'Enter')) {
    return
  }
  if (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  ) {
    return
  }
  switch (event.key) {
    case 'ArrowDown':
    case 'ArrowRight':
    case 'PageDown':
    case ' ':
      event.preventDefault()
      step(1)
      break
    case 'ArrowUp':
    case 'ArrowLeft':
    case 'PageUp':
      event.preventDefault()
      step(-1)
      break
    case 'Home':
      event.preventDefault()
      selectLine(0)
      break
    case 'Escape':
      event.preventDefault()
      void exitPerformance()
      break
  }
}

function onFullscreenChange() {
  // Esc or the browser's own control left full screen: leave performance too.
  if (!document.fullscreenElement && performance.value) void exitPerformance()
}

function onVisibility() {
  // The browser drops the wake lock when the tab is hidden.
  if (document.visibilityState === 'visible' && performance.value) void keepScreenOn()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  document.addEventListener('visibilitychange', onVisibility)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  if (route.query.performance === '1') void enterPerformance(false)
})

onBeforeUnmount(() => {
  unmounted = true
  window.removeEventListener('keydown', onKey)
  document.removeEventListener('visibilitychange', onVisibility)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  document.removeEventListener('pointerdown', onKeyPanelPointerDown)
  document.removeEventListener('keydown', onKeyPanelKeydown)
  stopScroll()
  void wakeLock?.release().catch(() => {})
  if (document.fullscreenElement) void document.exitFullscreen().catch(() => {})
})

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
  if (!song.value || song.value.id !== route.params.id) return
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

function startYoutubeEdit() {
  youtubeInput.value = storedYoutubeUrl.value
  youtubeError.value = ''
  editingYoutube.value = true
}

async function saveYoutube(url: string | null) {
  youtubeError.value = ''
  const songId = route.params.id as string
  try {
    const updated = await setYoutubeLink(songId, url)
    // Ignore a late response after navigating to another song.
    if (route.params.id !== songId) return
    store.current = updated
    editingYoutube.value = false
    showVideo.value = false
  } catch (e: unknown) {
    if (route.params.id !== songId) return
    youtubeError.value = e instanceof Error ? e.message : 'Could not save the YouTube link'
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
      setAnalysis(analysis)
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
    <div
      v-else-if="performance"
      ref="stage"
      class="play-stage"
      :style="{ '--song-font-size': `${fontSize}rem` }"
    >
      <div class="play-toolbar" role="group" aria-label="Performance controls">
        <button class="play-btn" title="Exit performance mode" aria-label="Exit performance mode" @click="exitPerformance()">✕</button>
        <button class="play-btn" title="Previous line" aria-label="Previous line" @click="step(-1)">▲</button>
        <button class="play-btn" title="Next line" aria-label="Next line" @click="step(1)">▼</button>
        <span class="spacer" />
        <button class="play-btn" title="Smaller text" aria-label="Smaller text" @click="changeFont(-0.1)">A−</button>
        <button class="play-btn" title="Larger text" aria-label="Larger text" @click="changeFont(0.1)">A+</button>
        <button
          :class="['play-btn', { active: autoScroll }]"
          title="Auto-scroll"
          :aria-pressed="autoScroll"
          @click="toggleScroll"
        >
          {{ autoScroll ? 'Stop' : 'Scroll' }}
        </button>
        <template v-if="autoScroll">
          <button class="play-btn" title="Slower" aria-label="Slower" @click="changeSpeed(-0.1)">−</button>
          <span class="speed">{{ scrollSpeed.toFixed(1) }}</span>
          <button class="play-btn" title="Faster" aria-label="Faster" @click="changeSpeed(0.1)">+</button>
        </template>
      </div>

      <SongDisplay
        :chordpro="song.body"
        :title="song.title"
        :artist="song.artist"
        :capo="song.capo"
        :song-key="song.key"
        :suggested-key="suggestedKey"
        :columns-override="1"
        :active-line="activeLine"
        hide-controls
        class="play-song"
        @line-select="selectLine"
      />
    </div>
    <template v-else>
      <AppNotice v-if="successNotice" type="success" :message="successNotice" />
      <AppNotice v-if="pdfError" type="error" :message="pdfError" />
      <AppNotice v-if="audioError" type="error" :message="audioError" />
      <AppNotice v-if="exportError" type="error" :message="exportError" />

      <div class="detail-actions">
        <button @click="togglePerformance" class="btn-secondary" :aria-pressed="performance">Performance</button>
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
      <AppNotice v-if="keyNotice" type="success" :message="keyNotice" />

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
        <button
          ref="keyToggle"
          class="key-suggestion-toggle"
          :aria-expanded="keyPanelOpen"
          aria-controls="key-analysis"
          @click="toggleKeyPanel"
        >
          <span>Suggested key: <strong>{{ suggestedKey }}</strong></span>
          <span v-if="keyConfidence !== null" class="confidence">{{ keyConfidence }}% confidence</span>
          <span class="key-details">{{ keyPanelOpen ? 'Hide details' : 'Details' }}</span>
        </button>

        <div
          v-if="keyPanelOpen"
          id="key-analysis"
          ref="keyPanel"
          class="key-panel"
          role="dialog"
          aria-label="Suggested key details"
          tabindex="-1"
        >
          <h2>{{ suggestedKey }} · {{ keyType || 'key' }} · {{ keyConfidence }}% confidence</h2>
          <p class="key-method">
            Detected by {{ keyMethod || 'chord analysis' }}:
            {{ keyInKeyCount }} of {{ keyChordCount }} chord occurrences belong to this key.
          </p>
          <p v-if="keyChords.length" class="key-scale">
            Key chords: {{ keyChords.join(' · ') }}
          </p>
          <h3>Strongest chords</h3>
          <ul class="key-evidence">
            <li v-for="chord in keyEvidence.slice(0, 6)" :key="chord.name">
              <span class="key-chord-name">{{ chord.name }}</span>
              <span class="key-chord-count">×{{ chord.count }}</span>
              <span :class="['key-chord-tag', { outside: !chord.in_key }]">
                {{ chord.in_key ? 'in key' : 'outside' }}
              </span>
            </li>
          </ul>
          <AppNotice v-if="keyError" type="error" :message="keyError" />
          <div class="key-panel-actions">
            <button class="btn-primary" :disabled="applyingKey" @click="applySuggestedKey">
              {{ applyingKey ? 'Applying...' : 'Use as song key' }}
            </button>
            <button class="btn-secondary" @click="closeKeyPanel">Cancel</button>
          </div>
        </div>
      </div>

      <div class="audio-section">
        <button v-if="!recording && !hasAudio" @click="startRecording" class="btn-secondary">Record Audio</button>
        <button v-if="recording" @click="stopRecording" class="btn-danger">Stop Recording</button>
        <template v-if="hasAudio">
          <audio :src="`/api/songs/${route.params.id}/audio`" controls class="audio-player" preload="none"></audio>
          <button @click="deleteAudio" class="btn-danger-sm" title="Delete audio">×</button>
        </template>
      </div>

      <div class="youtube-section">
        <AppNotice v-if="youtubeError" type="error" :message="youtubeError" />
        <form v-if="editingYoutube" class="youtube-form" @submit.prevent="saveYoutube(youtubeInput.trim() || null)">
          <input
            v-model="youtubeInput"
            class="youtube-input"
            type="text"
            inputmode="url"
            placeholder="https://www.youtube.com/watch?v=…"
            aria-label="YouTube link"
          />
          <button type="submit" class="btn-secondary">Save</button>
          <button type="button" class="btn-secondary" @click="editingYoutube = false">Cancel</button>
        </form>
        <template v-else-if="youtubeId">
          <!-- Load the player only on request: no third-party request per view. -->
          <button class="btn-secondary" @click="showVideo = !showVideo">
            {{ showVideo ? 'Hide video' : 'Show video' }}
          </button>
          <a :href="youtubeUrl" target="_blank" rel="noopener noreferrer" class="youtube-link">Open on YouTube</a>
          <button class="btn-secondary" @click="startYoutubeEdit">Change</button>
          <button class="btn-danger-sm" title="Remove YouTube link" aria-label="Remove YouTube link" @click="saveYoutube(null)">×</button>
        </template>
        <button v-else class="btn-secondary" @click="startYoutubeEdit">Add YouTube link</button>
        <div v-if="showVideo && youtubeId" class="youtube-player">
          <iframe
            :src="`https://www.youtube-nocookie.com/embed/${youtubeId}`"
            title="YouTube video"
            allow="encrypted-media; picture-in-picture; fullscreen"
            referrerpolicy="strict-origin-when-cross-origin"
            loading="lazy"
          ></iframe>
        </div>
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
/* Performance mode covers the nav bar and page chrome without changing the
   app layout (the old play view's stage, now on the song page). */
.play-stage {
  position: fixed;
  inset: 0;
  z-index: 1000;
  overflow-y: auto;
  background: var(--bg);
  color: var(--text);
  padding: 0 1rem 50vh;
}
.play-toolbar {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
  padding: 0.5rem 0;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  margin-bottom: 1rem;
}
.spacer {
  flex: 1;
}
.play-btn {
  min-width: 2.4rem;
  min-height: 2.4rem;
  padding: 0.3rem 0.6rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 1rem;
  cursor: pointer;
}
.play-btn.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
}
.speed {
  min-width: 2rem;
  text-align: center;
  color: var(--text-muted);
}
.play-song {
  max-width: 1100px;
  margin: 0 auto;
  cursor: pointer;
}
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
.btn-primary {
  padding: 0.4rem 0.8rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  background: var(--surface);
  border: 1px solid var(--accent);
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--text);
  overflow: hidden;
}
.key-suggestion strong {
  color: var(--accent);
}
.key-suggestion-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: none;
  border: none;
  color: var(--text);
  font: inherit;
  font-size: 0.85rem;
  text-align: left;
  cursor: pointer;
}
.key-suggestion-toggle:hover {
  background: var(--hover);
}
.key-suggestion-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.key-details {
  margin-left: auto;
  color: var(--accent);
  white-space: nowrap;
}
.confidence {
  color: var(--text-muted);
  font-size: 0.8rem;
}
.key-panel {
  padding: 0.5rem 0.75rem 0.75rem;
  border-top: 1px solid var(--border);
}
.key-panel:focus {
  outline: none;
}
.key-panel h2 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
}
.key-panel h3 {
  margin: 0.75rem 0 0.35rem;
  font-size: 0.9rem;
}
.key-method,
.key-scale {
  margin: 0.25rem 0;
  color: var(--text-muted);
  font-size: 0.82rem;
}
.key-evidence {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.key-evidence li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
}
.key-chord-name {
  min-width: 3rem;
  font-weight: 600;
}
.key-chord-count {
  color: var(--text-muted);
}
.key-chord-tag {
  font-size: 0.7rem;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  background: var(--hover);
  color: var(--accent);
}
.key-chord-tag.outside {
  color: #e05252;
}
.key-panel-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
  flex-wrap: wrap;
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
.youtube-section {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.youtube-form {
  display: flex;
  flex: 1;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.youtube-input {
  flex: 1;
  min-width: 220px;
  padding: 0.4rem 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
}
.youtube-link {
  color: var(--accent);
  font-size: 0.85rem;
}
.youtube-player {
  flex-basis: 100%;
  max-width: 640px;
  aspect-ratio: 16 / 9;
}
.youtube-player iframe {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 4px;
}
@media print {
  .youtube-section {
    display: none !important;
  }
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
