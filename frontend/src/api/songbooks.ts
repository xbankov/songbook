import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { SongResponse } from './songs'
import type { ChordDiagramMode } from '../utils/chords'

export interface SongbookMetadata {
  author: string | null
  date: string | null
  genre: string | null
  difficulty: string | null
  chord_diagrams: ChordDiagramMode
}

export interface SongbookResponse extends SongbookMetadata {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface SongbookEntryResponse {
  id: string
  song_id: string
  songbook_id: string
  sort_order: number
  transpose: number
  double_column: number
  song: SongResponse | null
}

export interface SongbookDetailResponse extends SongbookResponse {
  entries: SongbookEntryResponse[]
}

export interface SongbookCreate {
  name: string
  description?: string
}

export function listSongbooks(): Promise<SongbookResponse[]> {
  return apiGet('/api/songbooks')
}

export function getSongbook(id: string): Promise<SongbookDetailResponse> {
  return apiGet(`/api/songbooks/${id}`)
}

export function createSongbook(data: SongbookCreate): Promise<SongbookResponse> {
  return apiPost('/api/songbooks', data)
}

export type SongbookUpdate = Partial<SongbookMetadata> & { name?: string; description?: string }

export function updateSongbook(id: string, data: SongbookUpdate): Promise<SongbookResponse> {
  return apiPut(`/api/songbooks/${id}`, data)
}

export interface ChordShape {
  name: string
  /** Fret per string, low E first; 0 = open, -1 = muted. */
  frets: number[]
}

/** The songbook's chord chart, computed by the server exactly as in the PDF. */
export function getSongbookChords(id: string): Promise<ChordShape[]> {
  return apiGet(`/api/songbooks/${id}/chords`)
}

export function deleteSongbook(id: string): Promise<void> {
  return apiDelete(`/api/songbooks/${id}`)
}

export function addSongToSongbook(songbookId: string, songId: string): Promise<SongbookEntryResponse> {
  return apiPost(`/api/songbooks/${songbookId}/songs?song_id=${songId}`)
}

export function updateSongbookEntry(songbookId: string, entryId: string, data: { sort_order?: number; transpose?: number; double_column?: number }): Promise<SongbookEntryResponse> {
  return apiPut(`/api/songbooks/${songbookId}/songs/${entryId}`, data)
}

export function reorderSongbook(songbookId: string, entryIds: string[]): Promise<SongbookDetailResponse> {
  return apiPut(`/api/songbooks/${songbookId}/order`, { entry_ids: entryIds })
}

export function removeSongFromSongbook(songbookId: string, entryId: string): Promise<void> {
  return apiDelete(`/api/songbooks/${songbookId}/songs/${entryId}`)
}
