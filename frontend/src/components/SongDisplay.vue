<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useSettingsStore } from '../stores/settings'
import { useAutoScroll } from '../composables/useAutoScroll'
import { getChordShape } from '../api/chords'
import { transposeChord } from '../utils/chords'
import ChordDiagram from './ChordDiagram.vue'

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

// One chord popover for the whole display (#142): only one can be open.
const activeChord = ref<string | null>(null)
const activeFrets = ref<number[] | undefined>(undefined)
const chordLoading = ref(false)
const chordError = ref('')
const chordPopover = ref<HTMLElement | null>(null)
const chordTrigger = ref<HTMLElement | null>(null)
const popoverStyle = ref<Record<string, string>>({})
let chordRequest = 0

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

function chordSpans(spans: Span[]): ChordSpan[] {
  return spans.filter((span): span is ChordSpan => span.type === 'chord')
}

const chordVariants = computed(() => {
  const chord = activeChord.value
  if (!chord) return []
  const match = chord.match(/^([A-G][#b]?)/)
  if (!match) return [chord]
  const root = match[1]
  const bass = root === 'G' ? 'C' : 'G'
  return [...new Set([
    chord,
    root,
    `${root}m`,
    `${root}7`,
    `${root}maj7`,
    `${root}m7`,
    `${root}sus4`,
    `${root}/${bass}`,
  ])]
})

async function loadChordShape(chord: string) {
  const request = ++chordRequest
  activeFrets.value = undefined
  chordError.value = ''
  chordLoading.value = true
  try {
    const shape = await getChordShape(chord)
    if (request === chordRequest && activeChord.value === chord) {
      activeFrets.value = shape.frets
    }
  } catch {
    if (request === chordRequest && activeChord.value === chord) {
      chordError.value = 'Showing a local shape'
    }
  } finally {
    if (request === chordRequest) chordLoading.value = false
  }
}

function closeChord(restoreFocus = true) {
  activeChord.value = null
  activeFrets.value = undefined
  chordLoading.value = false
  chordError.value = ''
  chordRequest += 1
  document.removeEventListener('pointerdown', onChordPointerDown)
  document.removeEventListener('keydown', onChordKeydown, true)
  const trigger = chordTrigger.value
  chordTrigger.value = null
  if (restoreFocus) trigger?.focus()
}

function onChordPointerDown(event: PointerEvent) {
  const target = event.target as Element
  if (chordPopover.value?.contains(target) || chordTrigger.value?.contains(target)) return
  // Another chord replaces the current popover; let its click handler do it.
  if (target.closest?.('.chord-btn')) return
  closeChord()
}

function onChordKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    // Capture phase: close the reference before performance mode exits.
    event.stopPropagation()
    closeChord()
  }
}

function openChord(chord: string, event: MouseEvent) {
  const trigger = event.currentTarget
  if (!(trigger instanceof HTMLElement)) return
  if (activeChord.value === chord && chordPopover.value) {
    closeChord()
    return
  }
  activeChord.value = chord
  chordTrigger.value = trigger
  const width = 300
  const rect = trigger.getBoundingClientRect()
  popoverStyle.value = {
    top: `${Math.max(8, Math.min(rect.bottom + 6, window.innerHeight - 330))}px`,
    left: `${Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))}px`,
  }
  document.removeEventListener('pointerdown', onChordPointerDown)
  document.addEventListener('pointerdown', onChordPointerDown)
  document.removeEventListener('keydown', onChordKeydown, true)
  document.addEventListener('keydown', onChordKeydown, true)
  void loadChordShape(chord)
}

function chooseVariant(chord: string) {
  activeChord.value = chord
  void loadChordShape(chord)
}

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onChordPointerDown)
  document.removeEventListener('keydown', onChordKeydown, true)
})
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
        <span v-if="suggestedKey && suggestedKey !== parsed.key" class="suggested-key">Suggested: {{ suggestedKey }}</span>
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
            <div class="chord-row">
              <span class="chord-text" aria-hidden="true">{{ chordRow(line.spans) }}</span>
              <button
                v-for="(chord, ci) in chordSpans(line.spans)"
                :key="`${chord.chord}-${chord.position}-${ci}`"
                type="button"
                class="chord-btn chord-above-btn"
                :style="{ left: `${chord.position}ch`, width: `${chord.chord.length}ch` }"
                :aria-label="chord.chord"
                aria-haspopup="dialog"
                :aria-expanded="activeChord === chord.chord"
                @click.stop="openChord(chord.chord, $event)"
              />
            </div>
            <div class="lyric-row"><span>{{ lyricRow(line.spans) }}</span></div>
          </div>
          <div
            v-else
            :class="lineClasses('line-inline', si, li)"
            :data-line="lineIndex(si, li)"
            @click="emit('line-select', lineIndex(si, li))"
          >
            <template v-for="(span, pi) in line.spans" :key="pi">
              <button
                v-if="span.type === 'chord'"
                type="button"
                class="chord-btn chord-inline"
                :aria-label="span.chord"
                aria-haspopup="dialog"
                :aria-expanded="activeChord === span.chord"
                @click.stop="openChord(span.chord, $event)"
              >
                [{{ span.chord }}]
              </button>
              <span v-else>{{ span.text }}</span>
            </template>
          </div>
        </template>
      </div>
    </div>

    <div
      v-if="activeChord"
      ref="chordPopover"
      class="chord-popover"
      role="dialog"
      aria-label="Chord reference"
      :style="popoverStyle"
    >
      <div class="chord-popover-header">
        <strong>{{ activeChord }}</strong>
        <button
          type="button"
          class="chord-popover-close"
          aria-label="Close chord reference"
          @click="closeChord()"
        >
          ×
        </button>
      </div>
      <ChordDiagram :chord="activeChord" :frets="activeFrets" />
      <div class="chord-variants">
        <button
          v-for="variant in chordVariants"
          :key="variant"
          type="button"
          :class="['chord-variant', { active: variant === activeChord }]"
          @click="chooseVariant(variant)"
        >
          {{ variant }}
        </button>
      </div>
      <p v-if="chordLoading" class="chord-note">Loading shape...</p>
      <p v-else-if="chordError" class="chord-note">{{ chordError }}</p>
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
.chord-row { position: relative; white-space: pre; overflow: visible; min-height: 1.2em; }
.chord-text { font-weight: 700; color: var(--accent); }
.lyric-row { white-space: pre; overflow: visible; color: var(--text); margin-top: -0.05rem; }

/* Clickable chords and their reference popover (#142). */
.chord-btn {
  font: inherit;
  color: inherit;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}
.chord-above-btn {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: 3px;
}
.chord-above-btn:hover,
.chord-above-btn:focus-visible {
  background: color-mix(in srgb, var(--accent) 22%, transparent);
  outline: 1px solid var(--accent);
}
.chord-inline:hover,
.chord-inline:focus-visible {
  background: color-mix(in srgb, var(--accent) 22%, transparent);
  outline: none;
  text-decoration: underline;
}
.chord-popover {
  position: fixed;
  z-index: 1200;
  width: 300px;
  max-height: calc(100vh - 16px);
  overflow-y: auto;
  padding: 0.75rem;
  background: var(--surface);
  border: 1px solid var(--accent);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 35%);
}
.chord-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.chord-popover-header strong {
  color: var(--accent);
  font-size: 1.05rem;
}
.chord-popover-close {
  background: none;
  border: 0;
  color: var(--text-muted);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
}
.chord-variants {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.5rem;
}
.chord-variant {
  padding: 0.2rem 0.45rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  color: var(--text-muted);
  font-size: 0.78rem;
  cursor: pointer;
}
.chord-variant.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
}
.chord-note {
  margin: 0.4rem 0 0;
  color: var(--text-muted);
  font-size: 0.75rem;
}

/* Inline mode */
.mode-inline { font-family: 'Courier New', 'Consolas', 'Liberation Mono', monospace; font-size: var(--song-font-size, 1rem); line-height: 1.6; }
.active-line { background: color-mix(in srgb, var(--accent) 22%, transparent); border-radius: 3px; box-shadow: -0.4rem 0 0 var(--accent); }
.line-inline { white-space: pre-wrap; word-break: break-word; }
.chord-inline { font-weight: 700; color: var(--accent); }

@media print {
  .song-display { padding-bottom: 0 !important; }
  .song-controls { display: none !important; }
  .chord-popover { display: none !important; }
  .mode-above { font-size: 9pt !important; }
  .mode-inline { font-size: 9pt !important; }
  .chord-text, .chord-inline, .chord-btn { color: #2c5282 !important; }
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
