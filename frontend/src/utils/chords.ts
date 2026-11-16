const chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

export function transposeChord(chord: string, semitones: number): string {
  if (semitones === 0) return chord
  const match = chord.match(/^([A-G][#b]?)(.*)$/)
  if (!match) return chord
  let idx = chromatic.indexOf(match[1])
  if (idx === -1) return chord
  idx = (idx + semitones + 12) % 12
  return chromatic[idx] + (match[2] || '')
}

/** Distinct chord names in a ChordPro body, in order of appearance. */
export function extractChords(body: string): string[] {
  const found = new Set<string>()
  const re = /\[([^\]]+)\]/g
  let m: RegExpExecArray | null
  while ((m = re.exec(body)) !== null) {
    const chord = m[1].trim()
    if (chord && /^[A-G][#b]?(m|min|maj|dim|aug|sus|add|[0-9])*/i.test(chord)) {
      found.add(chord)
    }
  }
  return [...found]
}

/** Plain major/minor triads without a bass note: hidden by `uncommon`. */
export function isBasicChord(chord: string): boolean {
  return /^[A-G][#b]?(m|mi|min|minor|maj|major)?$/.test(chord)
}

export type ChordDiagramMode = 'none' | 'uncommon' | 'all'

/** Sorted distinct chords to chart for the given songs and mode (#89). */
export function chordChart(
  songs: { body: string; transpose: number }[],
  mode: ChordDiagramMode,
): string[] {
  if (mode === 'none') return []
  const chart = new Set<string>()
  for (const song of songs) {
    for (const chord of extractChords(song.body)) {
      const played = transposeChord(chord, song.transpose)
      if (mode === 'uncommon' && isBasicChord(played)) continue
      chart.add(played)
    }
  }
  return [...chart].sort()
}
