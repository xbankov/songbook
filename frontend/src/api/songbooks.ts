import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { SongResponse } from './songs'

export interface SongbookResponse {
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

export function updateSongbook(id: string, data: { name?: string; description?: string }): Promise<SongbookResponse> {
  return apiPut(`/api/songbooks/${id}`, data)
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
