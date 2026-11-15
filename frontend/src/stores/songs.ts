import { defineStore } from 'pinia'
import * as songsApi from '../api/songs'

interface SongState {
  songs: songsApi.SongResponse[]
  current: songsApi.SongResponse | null
  loading: boolean
  error: string | null
  _listRequestId: number
}

export const useSongStore = defineStore('songs', {
  state: (): SongState => ({
    songs: [],
    current: null,
    loading: false,
    error: null,
    _listRequestId: 0,
  }),
  actions: {
    async fetchSongs(params?: songsApi.ListParams) {
      const requestId = ++this._listRequestId
      this.loading = true
      this.error = null
      try {
        const songs = await songsApi.listSongs(params)
        if (requestId === this._listRequestId) {
          this.songs = songs
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
      if (this.current?.id === id) this.current = null
    },
    async importSong(url: string) {
      const song = await songsApi.importSong(url)
      this.songs.unshift(song)
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
      return songsApi.bulkImport(text)
    },
  },
})
