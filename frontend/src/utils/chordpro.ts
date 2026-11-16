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
