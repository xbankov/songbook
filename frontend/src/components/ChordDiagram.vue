<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  chord: string
}>()

const chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

const tones: Record<string, number> = {
  C: 0, 'C#': 1, Db: 1, D: 2, 'D#': 3, Eb: 3,
  E: 4, F: 5, 'F#': 6, Gb: 6, G: 7, 'G#': 8,
  Ab: 8, A: 9, 'A#': 10, Bb: 10, B: 11,
}

const strings = [4, 3, 2, 1, 0]
const frets = 5
const stringCount = 6

function getFret(rootNote: string, targetNote: string, inversion: number): number {
  const rootIdx = tones[rootNote]
  const targetIdx = tones[targetNote]
  if (rootIdx === undefined || targetIdx === undefined) return -1
  const interval = (targetIdx - rootIdx + 12) % 12
  return (interval + inversion * 12) % 12
}

interface FretPos {
  string: number
  fret: number
  finger?: number
}

const positions = computed<FretPos[]>(() => {
  const match = props.chord.match(/^([A-G][#b]?)(.*)$/)
  if (!match) return []
  const rootTone = match[1]
  const quality = match[2].toLowerCase()

  const intervals: number[] = [0]
  if (!quality || quality === '' || quality === 'maj') {
    intervals.push(4, 7)
  } else if (quality === 'm' || quality === 'mi' || quality === 'min' || quality === 'minor') {
    intervals.push(3, 7)
  } else if (quality === '7' || quality === 'dom7') {
    intervals.push(4, 7, 10)
  } else if (quality === 'maj7') {
    intervals.push(4, 7, 11)
  } else if (quality === 'm7' || quality === 'min7') {
    intervals.push(3, 7, 10)
  } else if (quality === 'dim') {
    intervals.push(3, 6)
  } else if (quality === 'aug') {
    intervals.push(4, 8)
  } else if (quality === 'sus4') {
    intervals.push(5, 7)
  } else if (quality === 'sus2') {
    intervals.push(2, 7)
  } else if (quality === 'dim7') {
    intervals.push(3, 6, 9)
  } else if (quality === 'm7b5') {
    intervals.push(3, 6, 10)
  }

  const rootIdx = tones[rootTone]
  if (rootIdx === undefined) return []

  const notes = intervals.map(i => chromatic[(rootIdx + i) % 12])
  const openStrings = ['E', 'A', 'D', 'G', 'B', 'E']

  const result: FretPos[] = []
  for (let s = 0; s < stringCount; s++) {
    const open = openStrings[s]
    const openIdx = tones[open]
    if (openIdx === undefined) continue
    let bestFret = -1
    for (const note of notes) {
      const noteIdx = tones[note]
      if (noteIdx === undefined) continue
      let f = (noteIdx - openIdx + 12) % 12
      if (f === 0) f = 12
      if (f <= frets) {
        if (bestFret === -1 || f < bestFret) bestFret = f
      }
    }
    if (bestFret > 0 && bestFret <= frets) {
      result.push({ string: s, fret: bestFret })
    } else if (bestFret === 0) {
      result.push({ string: s, fret: 0 })
    }
  }

  return result
})

const cellW = 28
const cellH = 28
const nutH = 10
const padding = { top: 20, left: 20, right: 20, bottom: 10 }
const svgW = cellW * (stringCount - 1) + padding.left + padding.right
const svgH = nutH + cellH * frets + padding.top + padding.bottom

function stringX(s: number): number {
  return padding.left + s * cellW
}

function fretY(f: number): number {
  return padding.top + nutH + (f - 1) * cellH
}
</script>

<template>
  <div v-if="positions.length" class="chord-diagram">
    <div class="chord-name">{{ chord }}</div>
    <svg :width="svgW" :height="svgH" viewBox="0 0 200 180" class="fretboard">
      <line
        v-for="s in stringCount"
        :key="'str' + s"
        :x1="stringX(s - 1)"
        :y1="padding.top"
        :x2="stringX(s - 1)"
        :y2="padding.top + nutH + frets * cellH"
        stroke="var(--text)"
        stroke-width="1.5"
      />
      <line
        v-for="f in frets + 1"
        :key="'fret' + f"
        :x1="padding.left"
        :y1="f === 1 ? padding.top : fretY(f - 1)"
        :x2="padding.left + (stringCount - 1) * cellW"
        :y2="f === 1 ? padding.top : fretY(f - 1)"
        :stroke="f === 1 ? 'var(--text)' : 'var(--border)'"
        :stroke-width="f === 1 ? 4 : 1.5"
      />
      <template v-for="(pos, i) in positions" :key="i">
        <template v-if="pos.fret > 0">
          <circle
            :cx="stringX(pos.string)"
            :cy="fretY(pos.fret) + cellH / 2"
            r="8"
            fill="var(--accent)"
            stroke="var(--accent)"
          />
          <text
            :x="stringX(pos.string)"
            :y="fretY(pos.fret) + cellH / 2 + 1"
            text-anchor="middle"
            dominant-baseline="central"
            fill="#000"
            font-size="9"
            font-weight="bold"
          >{{ pos.fret }}</text>
        </template>
        <template v-else>
          <text
            :x="stringX(pos.string)"
            :y="padding.top - 6"
            text-anchor="middle"
            dominant-baseline="central"
            fill="var(--text-muted)"
            font-size="10"
            font-weight="bold"
          >O</text>
        </template>
      </template>
    </svg>
  </div>
</template>

<style scoped>
.chord-diagram {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  margin: 0.25rem;
}
.chord-name {
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--accent);
  margin-bottom: 2px;
}
.fretboard {
  width: 100px;
  height: 100px;
}
</style>
