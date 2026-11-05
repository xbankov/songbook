import { defineStore } from 'pinia'
import * as settingsApi from '../api/settings'

interface SettingsState {
  settings: settingsApi.GlobalSettings | null
  loading: boolean
}

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    settings: null,
    loading: false,
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
      this.loading = true
      try {
        this.settings = await settingsApi.getSettings()
      } finally {
        this.loading = false
      }
    },
    async updateSettings(data: settingsApi.GlobalSettingsUpdate) {
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
