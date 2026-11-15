import { defineStore } from 'pinia'
import * as settingsApi from '../api/settings'

interface SettingsState {
  settings: settingsApi.GlobalSettings | null
  loading: boolean
  _fetchPromise: Promise<void> | null
  _fetchId: number
}

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    settings: null,
    loading: false,
    _fetchPromise: null,
    _fetchId: 0,
  }),
  getters: {
    transpose: (state) => state.settings?.transpose ?? 0,
    doubleColumn: (state) => state.settings?.double_column ?? false,
    font: (state) => state.settings?.font ?? 'DejaVu Sans Mono',
    fontSize: (state) => state.settings?.font_size ?? 9,
    displayMode: (state) => state.settings?.display_mode ?? 'above',
  },
  actions: {
    async fetchSettings() {
      if (this._fetchPromise) return this._fetchPromise
      const requestId = ++this._fetchId
      this.loading = true
      this._fetchPromise = (async () => {
        try {
          const settings = await settingsApi.getSettings()
          // Ignore a response that started before a settings update.
          if (requestId === this._fetchId) {
            this.settings = settings
          }
        } finally {
          this.loading = false
          this._fetchPromise = null
        }
      })()
      return this._fetchPromise
    },
    async updateSettings(data: settingsApi.GlobalSettingsUpdate) {
      // Invalidate any in-flight fetch so it cannot overwrite this update.
      this._fetchId += 1
      this.settings = await settingsApi.updateSettings(data)
      return this.settings
    },
    async setTranspose(val: number) {
      await this.updateSettings({ transpose: val })
    },
    async setDoubleColumn(val: boolean) {
      await this.updateSettings({ double_column: val })
    },
    async setFont(val: string) {
      await this.updateSettings({ font: val })
    },
    async setFontSize(val: number) {
      await this.updateSettings({ font_size: val })
    },
    async setDisplayMode(val: string) {
      await this.updateSettings({ display_mode: val })
    },
  },
})
