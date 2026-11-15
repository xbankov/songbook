import { apiDelete, apiGet, apiGetWithHeaders, apiPost, apiPut } from './client'

export interface SongResponse {
  id: string
  title: string
  artist: string
  capo: number
  key: string | null
  body: string
  metadata: Record<string, unknown> & { audio_file?: string }
  tags: string[]
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
  tags?: string[]
}

export interface ListParams {
  search?: string
  artist?: string
  tag?: string
  difficulty?: string
  genre?: string
  letter?: string
  sort?: string
  order?: string
  limit?: number
  offset?: number
}

export interface SongListResponse {
  items: SongResponse[]
  total: number
}

export async function listSongs(params?: ListParams): Promise<SongListResponse> {
  const { data, headers } = await apiGetWithHeaders<SongResponse[]>(
    '/api/songs',
    params as Record<string, string | number | undefined>,
  )
  const total = Number(headers.get('X-Total-Count') ?? data.length)
  return { items: data, total }
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

export interface SongVersion {
  id: string
  song_id: string
  version: number
  title: string
  artist: string
  capo: number
  key: string | null
  body: string
  author: string
  created_at: string
}

export function listVersions(id: string): Promise<SongVersion[]> {
  return apiGet(`/api/songs/${id}/versions`)
}

export function getVersion(id: string, version: number): Promise<SongVersion> {
  return apiGet(`/api/songs/${id}/versions/${version}`)
}

export function restoreVersion(id: string, version: number): Promise<SongResponse> {
  return apiPost(`/api/songs/${id}/versions/${version}/restore`)
}

export function favoriteVersion(id: string, version: number): Promise<SongResponse> {
  return apiPost(`/api/songs/${id}/versions/${version}/favorite`)
}

export function unfavoriteVersion(id: string, version: number): Promise<SongResponse> {
  return apiDelete(`/api/songs/${id}/versions/${version}/favorite`)
}

export function forkVersion(id: string, version: number): Promise<SongResponse> {
  return apiPost(`/api/songs/${id}/versions/${version}/fork`)
}

export function analyzeSong(id: string): Promise<SongAnalysis> {
  return apiGet(`/api/songs/${id}/analyze`)
}
