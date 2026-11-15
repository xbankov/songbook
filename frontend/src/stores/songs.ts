import { defineStore } from 'pinia'
import * as songsApi from '../api/songs'

interface SongState {
  songs: songsApi.SongResponse[]
  current: songsApi.SongResponse | null
  loading: boolean
  error: string | null
  total: number
  _listRequestId: number
}

export const useSongStore = defineStore('songs', {
  state: (): SongState => ({
    songs: [],
    current: null,
    loading: false,
    error: null,
    total: 0,
    _listRequestId: 0,
  }),
  actions: {
    async fetchSongs(params?: songsApi.ListParams) {
      const requestId = ++this._listRequestId
      this.loading = true
      this.error = null
      try {
        const response = await songsApi.listSongs(params)
        if (requestId === this._listRequestId) {
          this.songs = response.items
          this.total = response.total
        }
      } catch (e: unknown) {
        if (requestId === this._listRequestId) {
          this.error = e instanceof Error ? e.message : 'Failed to load songs'
        }
      } finally {
        if (requestId === this._listRequestId) {
          this.loading = false
        }
      }
    },
    async fetchSong(id: string) {
      this.loading = true
      this.error = null
      try {
        this.current = await songsApi.getSong(id)
      } catch (e: unknown) {
        this.error = e instanceof Error ? e.message : 'Failed to load song'
      } finally {
        this.loading = false
      }
    },
    async createSong(data: songsApi.SongCreate) {
      const song = await songsApi.createSong(data)
      this.songs.unshift(song)
      this.total += 1
      return song
    },
    async updateSong(id: string, data: Partial<songsApi.SongCreate>) {
      const song = await songsApi.updateSong(id, data)
      const idx = this.songs.findIndex((s) => s.id === id)
      if (idx >= 0) this.songs[idx] = song
      if (this.current?.id === id) this.current = song
      return song
    },
    async deleteSong(id: string) {
      await songsApi.deleteSong(id)
      this.songs = this.songs.filter((s) => s.id !== id)
      this.total = Math.max(0, this.total - 1)
      if (this.current?.id === id) this.current = null
    },
    async importSong(url: string) {
      const song = await songsApi.importSong(url)
      this.songs.unshift(song)
      this.total += 1
      return song
    },
    async transposeSong(id: string, interval: number) {
      const song = await songsApi.transposeSong(id, interval)
      const idx = this.songs.findIndex((s) => s.id === id)
      if (idx >= 0) this.songs[idx] = song
      if (this.current?.id === id) this.current = song
      return song
    },
    async bulkImport(text: string) {
      const songs = await songsApi.bulkImport(text)
      this.total += songs.length
      return songs
    },
  },
})
