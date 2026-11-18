import { apiGet } from './client'

export interface ChordShapeResponse {
  name: string
  /** Fret per string, low E first; 0 open, -1 muted. */
  frets: number[]
}

/** The server's open-position shape for the chord popover (#142). */
export function getChordShape(chord: string): Promise<ChordShapeResponse> {
  return apiGet('/api/chords', { chord })
}
