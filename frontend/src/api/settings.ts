import { apiGet, apiPut } from './client'

export interface GlobalSettings {
  id: string
  transpose: number
  double_column: boolean
  font: string
  font_size: number
  display_mode: string
}

export interface GlobalSettingsUpdate {
  transpose?: number
  double_column?: boolean
  font?: string
  font_size?: number
  display_mode?: string
}

export function getSettings(): Promise<GlobalSettings> {
  return apiGet('/api/settings')
}

export function updateSettings(data: GlobalSettingsUpdate): Promise<GlobalSettings> {
  return apiPut('/api/settings', data)
}
