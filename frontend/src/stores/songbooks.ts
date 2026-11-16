import { defineStore } from 'pinia'
import * as songbooksApi from '../api/songbooks'

interface SongbookState {
  songbooks: songbooksApi.SongbookResponse[]
  current: songbooksApi.SongbookDetailResponse | null
  loading: boolean
}

export const useSongbookStore = defineStore('songbooks', {
  state: (): SongbookState => ({
    songbooks: [],
    current: null,
    loading: false,
  }),
  actions: {
    async fetchSongbooks() {
      this.loading = true
      try {
        this.songbooks = await songbooksApi.listSongbooks()
      } finally {
        this.loading = false
      }
    },
    async fetchSongbook(id: string) {
      this.loading = true
      try {
        this.current = await songbooksApi.getSongbook(id)
      } finally {
        this.loading = false
      }
    },
    async createSongbook(data: songbooksApi.SongbookCreate) {
      const sb = await songbooksApi.createSongbook(data)
      this.songbooks.push(sb)
      return sb
    },
    async updateSongbook(id: string, data: songbooksApi.SongbookUpdate) {
      const sb = await songbooksApi.updateSongbook(id, data)
      const idx = this.songbooks.findIndex((item) => item.id === id)
      if (idx >= 0) this.songbooks[idx] = sb
      if (this.current?.id === id) {
        this.current = { ...this.current, ...sb }
      }
      return sb
    },
    async deleteSongbook(id: string) {
      await songbooksApi.deleteSongbook(id)
      this.songbooks = this.songbooks.filter((item) => item.id !== id)
      if (this.current?.id === id) this.current = null
    },
    async addSong(songbookId: string, songId: string) {
      const entry = await songbooksApi.addSongToSongbook(songbookId, songId)
      if (this.current?.id === songbookId) {
        this.current.entries.push(entry)
      }
      return entry
    },
    async removeSong(songbookId: string, entryId: string) {
      await songbooksApi.removeSongFromSongbook(songbookId, entryId)
      if (this.current?.id === songbookId) {
        this.current.entries = this.current.entries.filter((e) => e.id !== entryId)
      }
    },
    async updateEntry(songbookId: string, entryId: string, data: { sort_order?: number; transpose?: number; double_column?: number }) {
      const entry = await songbooksApi.updateSongbookEntry(songbookId, entryId, data)
      if (this.current?.id === songbookId) {
        const idx = this.current.entries.findIndex((e) => e.id === entryId)
        if (idx >= 0) this.current.entries[idx] = entry
      }
      return entry
    },
    async reorderEntries(songbookId: string, entryIds: string[]) {
      const book = await songbooksApi.reorderSongbook(songbookId, entryIds)
      if (this.current?.id === songbookId) {
        this.current = book
      }
      return book
    },
  },
})
