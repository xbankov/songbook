<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()

const props = defineProps<{
  chordpro: string
  title: string
  artist: string
  capo?: number
  songKey?: string | null
  suggestedKey?: string | null
}>()

const songDisplay = ref<HTMLElement | null>(null)

const autoScroll = ref(false)
const scrollSpeed = ref(1)
let scrollInterval: ReturnType<typeof setInterval> | null = null

const transpose = computed(() => settingsStore.transpose)
const displayMode = computed(() => settingsStore.displayMode)
const doubleColumn = computed(() => settingsStore.doubleColumn)

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollInterval = setInterval(() => {
      window.scrollBy(0, scrollSpeed.value)
    }, 100)
  } else if (scrollInterval) {
    clearInterval(scrollInterval)
    scrollInterval = null
  }
}

function setSpeed(s: number) {
  scrollSpeed.value = s
  if (autoScroll.value) {
    if (scrollInterval) clearInterval(scrollInterval)
    scrollInterval = setInterval(() => {
      window.scrollBy(0, scrollSpeed.value)
    }, 100)
  }
}

const chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

function transposeChord(chord: string, semitones: number): string {
  if (semitones === 0) return chord
  const match = chord.match(/^([A-G][#b]?)(.*)$/)
  if (!match) return chord
  let idx = chromatic.indexOf(match[1])
  if (idx === -1) return chord
  idx = (idx + semitones + 12) % 12
  return chromatic[idx] + (match[2] || '')
}

interface ChordSpan { type: 'chord'; chord: string; position: number }
interface TextSpan { type: 'text'; text: string; position: number }
type Span = ChordSpan | TextSpan

interface RenderedLine { spans: Span[] }
interface RenderedSection { label: string | null; title: string | null; lines: RenderedLine[] }

function parseChordPro(text: string, semitones: number) {
  const lines = text.split('\n')
  const sections: RenderedSection[] = []
  let currentSection: RenderedSection = { label: null, title: null, lines: [] }
  let meta = { title: props.title, artist: props.artist, capo: props.capo ?? 0, key: props.songKey ?? null as string | null }

  for (const raw of lines) {
    const stripped = raw.trim()
    if (stripped.startsWith('{') && stripped.endsWith('}')) {
      const content = stripped.slice(1, -1)
      const colon = content.indexOf(':')
      const tag = colon >= 0 ? content.slice(0, colon).trim() : content
      const val = colon >= 0 ? content.slice(colon + 1).trim() : ''
      if (tag === 'title') meta.title = val
      else if (tag === 'artist') meta.artist = val
      else if (tag === 'capo') { const n = parseInt(val); if (!isNaN(n)) meta.capo = n }
      else if (tag === 'key') meta.key = val
      else if (tag.startsWith('start_of_')) {
        if (currentSection.lines.length > 0) sections.push(currentSection)
        currentSection = { label: tag.slice(9), title: val || null, lines: [] }
      } else if (tag.startsWith('end_of_')) {
        if (currentSection.lines.length > 0) sections.push(currentSection)
        currentSection = { label: null, title: null, lines: [] }
      }
      continue
    }
    if (stripped === '') {
      if (currentSection.lines.length > 0) { sections.push(currentSection); currentSection = { label: null, title: null, lines: [] } }
      continue
    }
    const spans: Span[] = []
    const re = /\[([^\]]+)\]/g
    let lastIdx = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(raw)) !== null) {
      if (m.index > lastIdx) spans.push({ type: 'text', text: raw.slice(lastIdx, m.index), position: lastIdx })
      spans.push({ type: 'chord', chord: transposeChord(m[1], semitones), position: m.index })
      lastIdx = re.lastIndex
    }
    if (lastIdx < raw.length) spans.push({ type: 'text', text: raw.slice(lastIdx), position: lastIdx })
    if (spans.length > 0) currentSection.lines.push({ spans })
  }
  if (currentSection.lines.length > 0) sections.push(currentSection)
  return { sections, ...meta }
}

const parsed = computed(() => parseChordPro(props.chordpro, transpose.value))

function chordRow(spans: Span[]): string {
  const chars: string[] = []
  for (const span of spans) {
    if (span.type === 'chord') {
      while (chars.length < span.position) chars.push('\xa0')
      for (let i = 0; i < span.chord.length; i++) chars.push(span.chord[i])
    }
  }
  return chars.join('') || '\xa0'
}

function lyricRow(spans: Span[]): string {
  return spans.map(s => s.type === 'text' ? s.text : '').join('')
}
</script>

<template>
  <div ref="songDisplay" class="song-display">
    <div class="song-controls">
      <div class="transpose-control">
        <button @click="settingsStore.setTranspose(Math.max(-11, transpose - 1))" class="ctrl-btn" title="Transpose down">&minus;</button>
        <span class="ctrl-label">Transpose: {{ transpose > 0 ? '+' : '' }}{{ transpose }}</span>
        <button @click="settingsStore.setTranspose(Math.min(11, transpose + 1))" class="ctrl-btn" title="Transpose up">+</button>
        <button v-if="transpose !== 0" @click="settingsStore.setTranspose(0)" class="ctrl-btn ctrl-reset" title="Reset">Reset</button>
      </div>
      <div class="mode-toggle">
        <button :class="['ctrl-btn', { active: displayMode === 'above' }]" @click="settingsStore.setDisplayMode('above')" title="Chords above lyrics">Above</button>
        <button :class="['ctrl-btn', { active: displayMode === 'inline' }]" @click="settingsStore.setDisplayMode('inline')" title="Chords inline with text">Inline</button>
        <button :class="['ctrl-btn', { active: doubleColumn }]" @click="settingsStore.setDoubleColumn(!doubleColumn)" title="Toggle double column">
          2-col
        </button>
      </div>
      <div class="autoscroll-controls">
        <button :class="['ctrl-btn', { active: autoScroll }]" @click="toggleAutoScroll" title="Auto-scroll">
          {{ autoScroll ? 'Stop' : 'Scroll' }}
        </button>
        <button v-if="autoScroll" @click="setSpeed(scrollSpeed - 0.5)" class="ctrl-btn ctrl-sm" title="Slower">−</button>
        <span v-if="autoScroll" class="ctrl-label">{{ scrollSpeed.toFixed(1) }}</span>
        <button v-if="autoScroll" @click="setSpeed(scrollSpeed + 0.5)" class="ctrl-btn ctrl-sm" title="Faster">+</button>
      </div>
    </div>

    <div class="song-header">
      <h1 class="song-title">{{ parsed.title }}</h1>
      <h2 class="song-artist">{{ parsed.artist }}</h2>
      <div v-if="parsed.capo || parsed.key || suggestedKey" class="song-meta">
        <span v-if="parsed.capo">Capo: {{ parsed.capo }}</span>
        <span v-if="parsed.key">Key: {{ parsed.key }}</span>
        <span v-if="suggestedKey" class="suggested-key">Suggested: {{ suggestedKey }}</span>
      </div>
    </div>

    <div class="song-body" :class="['mode-' + displayMode, { 'double-column': doubleColumn }]">
      <div v-for="(section, si) in parsed.sections" :key="si" class="section">
        <div v-if="section.label && section.label !== 'verse'" class="section-label">
          {{ section.title || section.label.charAt(0).toUpperCase() + section.label.slice(1) }}
        </div>
        <template v-for="(line, li) in section.lines" :key="li">
          <div v-if="displayMode === 'above'" class="line-above">
            <div class="chord-row"><span class="chord-text">{{ chordRow(line.spans) }}</span></div>
            <div class="lyric-row"><span>{{ lyricRow(line.spans) }}</span></div>
          </div>
          <div v-else class="line-inline">
            <span v-for="(span, pi) in line.spans" :key="pi" :class="span.type === 'chord' ? 'chord-inline' : ''">
              {{ span.type === 'chord' ? '[' + span.chord + ']' : span.text }}
            </span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.song-display { padding-bottom: 2rem; }

.song-controls {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;
  gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}
.transpose-control, .mode-toggle { display: flex; align-items: center; gap: 0.35rem; }
.ctrl-btn {
  background: var(--surface); border: 1px solid var(--border); color: var(--text);
  padding: 0.3rem 0.65rem; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-family: inherit;
}
.ctrl-btn:hover { border-color: var(--accent); }
.ctrl-btn.active { background: var(--accent); color: #000; border-color: var(--accent); }
.ctrl-label { font-size: 0.85rem; color: var(--text-muted); min-width: 90px; text-align: center; }
.ctrl-reset { font-size: 0.75rem; color: var(--text-muted); }
.ctrl-sm { font-size: 0.75rem; padding: 0.2rem 0.4rem; }
.autoscroll-controls { display: flex; align-items: center; gap: 0.25rem; }

.song-header { margin-bottom: 1.25rem; }
.song-title { font-size: 1.5rem; margin: 0; }
.song-artist { font-size: 1.1rem; color: var(--text-muted); margin: 0.25rem 0; font-weight: normal; }
.song-meta { font-size: 0.85rem; color: var(--text-muted); display: flex; gap: 1rem; flex-wrap: wrap; }
.suggested-key { color: var(--accent); font-style: italic; }

.section { margin-bottom: 1rem; }
.section-label {
  font-weight: 700; color: var(--accent); font-size: 0.85rem;
  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem;
}

/* Above mode */
.mode-above { font-family: 'Courier New', 'Consolas', 'Liberation Mono', monospace; font-size: 1rem; }
.double-column.mode-above { column-count: 2; column-gap: 2rem; }
.double-column.mode-inline { column-count: 2; column-gap: 2rem; }
.line-above { margin-bottom: 0.15rem; }
.chord-row { white-space: pre; overflow: visible; min-height: 1.2em; }
.chord-text { font-weight: 700; color: var(--accent); }
.lyric-row { white-space: pre; overflow: visible; color: var(--text); margin-top: -0.05rem; }

/* Inline mode */
.mode-inline { font-family: 'Courier New', 'Consolas', 'Liberation Mono', monospace; font-size: 1rem; line-height: 1.6; }
.line-inline { white-space: pre-wrap; word-break: break-word; }
.chord-inline { font-weight: 700; color: var(--accent); }

@media print {
  .song-controls { display: none !important; }
  .mode-above { font-size: 9pt !important; }
  .mode-inline { font-size: 9pt !important; }
  .chord-text, .chord-inline { color: #2c5282 !important; }
  .song-title { font-size: 14pt !important; }
  .song-artist { font-size: 11pt !important; }
  .section-label { font-size: 10pt !important; }
}
</style>
