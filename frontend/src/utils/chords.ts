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

export type ChordDiagramMode = 'none' | 'uncommon' | 'all'
