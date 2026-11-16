// Title, artist, capo and key live in the song's own fields (#37). These
// ChordPro tags are only added back when a song is exported, so the editor
// strips them from the body. Mirrors split_chordpro_metadata in the backend.

export type MetadataTag = 'title' | 'artist' | 'capo' | 'key'

const METADATA_LINE = /^\s*\{\s*(title|artist|capo|key)\s*:(.*)\}\s*$/i

export function splitChordProMetadata(body: string): {
  body: string
  values: Partial<Record<MetadataTag, string>>
} {
  const values: Partial<Record<MetadataTag, string>> = {}
  const kept: string[] = []
  for (const line of body.replace(/\r/g, '').split('\n')) {
    const match = METADATA_LINE.exec(line)
    if (match) {
      const tag = match[1].toLowerCase() as MetadataTag
      if (!(tag in values)) values[tag] = match[2].trim()
    } else {
      kept.push(line)
    }
  }
  while (kept.length && !kept[0].trim()) kept.shift()
  return { body: kept.join('\n'), values }
}

export interface SongMetadata {
  title: string
  artist: string
  capo: number
  key: string
}

// Mirrors is_unset_field in the backend: blank values and the "Unknown"
// placeholder are unset; capo 0 means "no capo", so only a missing capo is.
function isUnset(tag: MetadataTag, value: string | number | null | undefined): boolean {
  if (value === null || value === undefined) return true
  if (tag === 'capo') return false
  const text = String(value).trim()
  return !text || ((tag === 'title' || tag === 'artist') && text === 'Unknown')
}

// The song's fields win; an old body tag only fills a field that is unset.
// Mirrors resolve_song_metadata in the backend (#37).
export function resolveMetadata(
  body: string,
  fields: {
    title?: string | null
    artist?: string | null
    capo?: number | null
    key?: string | null
  },
): { body: string; meta: SongMetadata } {
  const { body: clean, values } = splitChordProMetadata(body)
  const pick = (tag: 'title' | 'artist' | 'key'): string => {
    const value = fields[tag]
    if (!isUnset(tag, value)) return String(value)
    return values[tag] || (value ?? '')
  }
  let capo = fields.capo
  if (isUnset('capo', capo)) {
    const parsed = parseInt(values.capo ?? '')
    capo = isNaN(parsed) ? 0 : parsed
  }
  return {
    body: clean,
    meta: { title: pick('title'), artist: pick('artist'), capo: capo ?? 0, key: pick('key') },
  }
}
