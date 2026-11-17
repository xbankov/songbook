<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'
import { useAutoScroll } from '../composables/useAutoScroll'
import { transposeChord } from '../utils/chords'

const settingsStore = useSettingsStore()

const props = defineProps<{
  chordpro: string
  title: string
  artist: string
  capo?: number
  songKey?: string | null
  suggestedKey?: string | null
  hideControls?: boolean
  hideSettingsControls?: boolean
  columnsOverride?: 1 | 2
  transposeOverride?: number
  displayModeOverride?: 'above' | 'inline'
  /** Play view (#41): index of the highlighted line across all sections. */
  activeLine?: number | null
}>()

const emit = defineEmits<{
  /** A line was clicked; the index counts lines across all sections. */
  (e: 'line-select', index: number): void
}>()

const songDisplay = ref<HTMLElement | null>(null)

const {
  autoScroll,
  speed: scrollSpeed,
  toggle: toggleAutoScroll,
  changeSpeed: setSpeed,
} = useAutoScroll()

const transpose = computed(
  () => settingsStore.transpose + (props.transposeOverride ?? 0),
)
const displayMode = computed(
  () => props.displayModeOverride ?? settingsStore.displayMode,
)
const doubleColumn = computed(() => {
  if (props.columnsOverride === 1) return false
  if (props.columnsOverride === 2) return true
  return settingsStore.doubleColumn
})

interface ChordSpan { type: 'chord'; chord: string; position: number }
interface TextSpan { type: 'text'; text: string; position: number }
type Span = ChordSpan | TextSpan

interface RenderedLine { spans: Span[] }
interface RenderedSection { label: string | null; title: string | null; lines: RenderedLine[] }

function parseChordPro(text: string, semitones: number) {
  const lines = text.split('\n')
  const sections: RenderedSection[] = []
  let currentSection: RenderedSection = { label: null, title: null, lines: [] }
  // Title, artist, capo and key come from the song's fields only (#37).
  const meta = { title: props.title, artist: props.artist, capo: props.capo ?? 0, key: props.songKey ?? null }

  for (const raw of lines) {
    const stripped = raw.trim()
    if (stripped.startsWith('{') && stripped.endsWith('}')) {
      const content = stripped.slice(1, -1)
      const colon = content.indexOf(':')
      const tag = colon >= 0 ? content.slice(0, colon).trim() : content
      const val = colon >= 0 ? content.slice(colon + 1).trim() : ''
      if (tag.startsWith('start_of_')) {
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
    let lyricPos = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(raw)) !== null) {
      if (m.index > lastIdx) {
        const text = raw.slice(lastIdx, m.index)
        spans.push({ type: 'text', text, position: lyricPos })
        lyricPos += text.length
      }
      spans.push({
        type: 'chord',
        chord: transposeChord(m[1], semitones),
        position: lyricPos,
      })
      lastIdx = re.lastIndex
    }
    if (lastIdx < raw.length) {
      spans.push({ type: 'text', text: raw.slice(lastIdx), position: lyricPos })
    }
    if (spans.length > 0) currentSection.lines.push({ spans })
  }
  if (currentSection.lines.length > 0) sections.push(currentSection)
  return { sections, ...meta }
}

const parsed = computed(() => parseChordPro(props.chordpro, transpose.value))

// First flat line index of each section, for activeLine / line-select.
const sectionOffsets = computed(() => {
  const offsets: number[] = []
  let total = 0
  for (const section of parsed.value.sections) {
    offsets.push(total)
    total += section.lines.length
  }
  return offsets
})

function lineIndex(sectionIndex: number, lineIndexInSection: number): number {
  return sectionOffsets.value[sectionIndex] + lineIndexInSection
}

function lineClasses(base: string, si: number, li: number) {
  return [base, { 'active-line': props.activeLine === lineIndex(si, li) }]
}

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
    <div v-if="!hideControls" class="song-controls">
      <div v-if="!hideSettingsControls" class="transpose-control">
        <button @click="settingsStore.setTranspose(Math.max(-11, transpose - 1))" class="ctrl-btn" title="Transpose down">&minus;</button>
        <span class="ctrl-label">Transpose: {{ transpose > 0 ? '+' : '' }}{{ transpose }}</span>
        <button @click="settingsStore.setTranspose(Math.min(11, transpose + 1))" class="ctrl-btn" title="Transpose up">+</button>
        <button v-if="transpose !== 0" @click="settingsStore.setTranspose(0)" class="ctrl-btn ctrl-reset" title="Reset">Reset</button>
      </div>
      <div v-if="!hideSettingsControls" class="mode-toggle">
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
        <button v-if="autoScroll" @click="setSpeed(-0.1)" class="ctrl-btn ctrl-sm" title="Slower" aria-label="Slower">−</button>
        <span v-if="autoScroll" class="ctrl-label">{{ scrollSpeed.toFixed(1) }}</span>
        <button v-if="autoScroll" @click="setSpeed(0.1)" class="ctrl-btn ctrl-sm" title="Faster" aria-label="Faster">+</button>
      </div>
    </div>

    <div class="song-header">
      <h1 class="song-title">{{ parsed.title }}</h1>
      <h2 class="song-artist">{{ parsed.artist }}</h2>
      <div v-if="parsed.capo || parsed.key || suggestedKey" class="song-meta">
        <span v-if="parsed.capo">Capo: {{ parsed.capo }}</span>
        <span v-if="parsed.key">Key: {{ transposeChord(parsed.key, transpose) }}</span>
        <span v-if="suggestedKey" class="suggested-key">Suggested: {{ suggestedKey }}</span>
      </div>
    </div>

    <div class="song-body" :class="['mode-' + displayMode, { 'double-column': doubleColumn }]">
      <div v-for="(section, si) in parsed.sections" :key="si" :class="['section', { long: section.lines.length > 10 }]">
        <div v-if="section.label" class="section-label">
          {{ section.title || section.label.charAt(0).toUpperCase() + section.label.slice(1) }}
        </div>
        <template v-for="(line, li) in section.lines" :key="li">
          <div
            v-if="displayMode === 'above'"
            :class="lineClasses('line-above', si, li)"
            :data-line="lineIndex(si, li)"
            @click="emit('line-select', lineIndex(si, li))"
          >
            <div class="chord-row"><span class="chord-text">{{ chordRow(line.spans) }}</span></div>
            <div class="lyric-row"><span>{{ lyricRow(line.spans) }}</span></div>
          </div>
          <div
            v-else
            :class="lineClasses('line-inline', si, li)"
            :data-line="lineIndex(si, li)"
            @click="emit('line-select', lineIndex(si, li))"
          >
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
.mode-above { font-family: 'Courier New', 'Consolas', 'Liberation Mono', monospace; font-size: var(--song-font-size, 1rem); }
.double-column.mode-above { column-count: 2; column-gap: 2rem; }
.double-column.mode-inline { column-count: 2; column-gap: 2rem; }
.line-above { margin-bottom: 0.15rem; }
.chord-row { white-space: pre; overflow: visible; min-height: 1.2em; }
.chord-text { font-weight: 700; color: var(--accent); }
.lyric-row { white-space: pre; overflow: visible; color: var(--text); margin-top: -0.05rem; }

/* Inline mode */
.mode-inline { font-family: 'Courier New', 'Consolas', 'Liberation Mono', monospace; font-size: var(--song-font-size, 1rem); line-height: 1.6; }
.active-line { background: color-mix(in srgb, var(--accent) 22%, transparent); border-radius: 3px; box-shadow: -0.4rem 0 0 var(--accent); }
.line-inline { white-space: pre-wrap; word-break: break-word; }
.chord-inline { font-weight: 700; color: var(--accent); }

@media print {
  .song-display { padding-bottom: 0 !important; }
  .song-controls { display: none !important; }
  .mode-above { font-size: 9pt !important; }
  .mode-inline { font-size: 9pt !important; }
  .chord-text, .chord-inline { color: #2c5282 !important; }
  .song-title { font-size: 14pt !important; }
  .song-artist { font-size: 11pt !important; }
  .section-label {
    font-size: 10pt !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid #e0d0b0;
    padding-bottom: 1pt;
    margin: 8pt 0 3pt 0;
  }
  .double-column.mode-above,
  .double-column.mode-inline {
    column-count: 2;
    column-gap: 10mm;
  }
  .section-label { break-after: avoid; }
  .section { break-inside: avoid; }
  .section.long { break-inside: auto; }
  .line-above,
  .line-inline { break-inside: avoid; }
  .song-title,
  .song-artist,
  .song-meta,
  .lyric-row { color: #000 !important; }
  .chord-row,
  .lyric-row {
    white-space: pre-wrap !important;
    overflow-wrap: anywhere;
    max-width: 100%;
  }
}
</style>
