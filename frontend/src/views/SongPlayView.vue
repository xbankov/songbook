<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getSong, type SongResponse } from '../api/songs'
import { useSettingsStore } from '../stores/settings'
import { useAutoScroll } from '../composables/useAutoScroll'
import SongDisplay from '../components/SongDisplay.vue'

// Play/sing view (#41): full screen, large text, a highlighted current line
// that follows taps, arrow keys, Space, and page-turner pedals (PageUp/Down).

const route = useRoute()
const router = useRouter()
const settingsStore = useSettingsStore()

const song = ref<SongResponse | null>(null)
const loading = ref(true)
const error = ref('')
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
// Keep line jumps instant while autoscroll runs, and honour reduced motion.
const reduceMotion =
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
let wakeLock: { release: () => Promise<void> } | null = null
let unmounted = false

async function load(id: string) {
  loading.value = true
  error.value = ''
  try {
    const [loaded] = await Promise.all([
      getSong(id),
      settingsStore.fetchSettings().catch(() => {}),
    ])
    song.value = loaded
    activeLine.value = 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Could not load song'
  } finally {
    loading.value = false
  }
}

function selectLine(index: number) {
  const total = stage.value?.querySelectorAll('[data-line]').length ?? 0
  if (total === 0) return
  activeLine.value = Math.max(0, Math.min(total - 1, index))
}

function step(delta: number) {
  selectLine(activeLine.value + delta)
}

watch(activeLine, async (index) => {
  await nextTick()
  const line = stage.value?.querySelector(`[data-line="${index}"]`)
  // Keep the current line mid-screen so the next lines stay visible. Jump
  // instead of animating while autoscroll runs: its frames would cancel a
  // smooth scroll and leave the line off-screen.
  line?.scrollIntoView?.({
    block: 'center',
    behavior: autoScroll.value || reduceMotion ? 'auto' : 'smooth',
  })
})

function changeFont(delta: number) {
  fontSize.value = Math.round(Math.max(0.8, Math.min(3, fontSize.value + delta)) * 10) / 10
}

async function toggleFullscreen() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen()
    else await stage.value?.requestFullscreen()
  } catch {
    // Not supported (e.g. iOS Safari): the view already fills the window.
  }
}

function exit() {
  const target = `/songs/${route.params.id}`
  // Came from the song page: go back, so history has no duplicate entry.
  // Otherwise (opened directly) replace, so Back does not reopen play mode.
  if (router.options.history.state.back === target) router.back()
  else router.replace(target)
}

function onKey(event: KeyboardEvent) {
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
      if (!document.fullscreenElement) exit()
      break
  }
}

async function keepScreenOn() {
  try {
    const nav = navigator as Navigator & {
      wakeLock?: { request: (type: 'screen') => Promise<{ release: () => Promise<void> }> }
    }
    const sentinel = (await nav.wakeLock?.request('screen')) ?? null
    if (unmounted) {
      // The view closed while the request was pending.
      void sentinel?.release().catch(() => {})
      return
    }
    // Overlapping requests (mount + quick tab switch): keep only the newest.
    const previous = wakeLock
    wakeLock = sentinel
    if (previous && previous !== sentinel) void previous.release().catch(() => {})
  } catch {
    wakeLock = null
  }
}

function onVisibility() {
  // The browser drops the wake lock when the tab is hidden.
  if (document.visibilityState === 'visible') void keepScreenOn()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  document.addEventListener('visibilitychange', onVisibility)
  void keepScreenOn()
})

onBeforeUnmount(() => {
  unmounted = true
  window.removeEventListener('keydown', onKey)
  document.removeEventListener('visibilitychange', onVisibility)
  stopScroll()
  void wakeLock?.release().catch(() => {})
})

watch(() => route.params.id as string, (id) => void load(id), { immediate: true })
</script>

<template>
  <div ref="stage" class="play-stage" :style="{ '--song-font-size': `${fontSize}rem` }">
    <div class="play-toolbar" role="group" aria-label="Play controls">
      <button class="play-btn" title="Exit play mode" aria-label="Exit play mode" @click="exit">✕</button>
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
      <button class="play-btn" title="Full screen" aria-label="Full screen" @click="toggleFullscreen">⛶</button>
    </div>

    <div v-if="loading" class="play-message">Loading...</div>
    <div v-else-if="error" class="play-message" role="alert">{{ error }}</div>
    <SongDisplay
      v-else-if="song"
      class="play-song"
      :chordpro="song.body"
      :title="song.title"
      :artist="song.artist"
      :capo="song.capo"
      :song-key="song.key"
      :columns-override="1"
      :active-line="activeLine"
      hide-controls
      @line-select="selectLine"
    />
  </div>
</template>

<style scoped>
/* Covers the nav bar and page chrome without changing the app layout. */
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
.play-message {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
.play-song {
  max-width: 1100px;
  margin: 0 auto;
  cursor: pointer;
}
</style>
