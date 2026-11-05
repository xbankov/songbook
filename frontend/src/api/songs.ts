import { apiGet, apiPost, apiPut, apiDelete } from './client'

export interface SongResponse {
  id: string
  title: string
  artist: string
  capo: number
  key: string | null
  body: string
  metadata: Record<string, unknown> & { audio_file?: string }
  version: number
  created_at: string
  updated_at: string
}

export interface SongCreate {
  title: string
  artist?: string
  capo?: number
  key?: string
  body?: string
}

export interface ListParams {
  search?: string
  artist?: string
  tag?: string
  sort?: string
  order?: string
  limit?: number
  offset?: number
}

export function listSongs(params?: ListParams): Promise<SongResponse[]> {
  return apiGet('/api/songs', params as Record<string, string | number | undefined>)
}

export function getSong(id: string): Promise<SongResponse> {
  return apiGet(`/api/songs/${id}`)
}

export function createSong(data: SongCreate): Promise<SongResponse> {
  return apiPost('/api/songs', data)
}

export function updateSong(id: string, data: Partial<SongCreate>): Promise<SongResponse> {
  return apiPut(`/api/songs/${id}`, data)
}

export function deleteSong(id: string): Promise<void> {
  return apiDelete(`/api/songs/${id}`)
}

export function importSong(url: string): Promise<SongResponse> {
  return apiPost(`/api/songs/import?url=${encodeURIComponent(url)}`)
}

export function transposeSong(id: string, interval: number): Promise<SongResponse> {
  return apiGet(`/api/songs/${id}/transpose?interval=${interval}`)
}

export function bulkImport(text: string): Promise<SongResponse[]> {
  return apiPost('/api/songs/import/bulk', text, 'text/plain')
}

export interface SongAnalysis {
  suggested_key: string | null
  confidence: number | null
}

export function analyzeSong(id: string): Promise<SongAnalysis> {
  return apiGet(`/api/songs/${id}/analyze`)
}
