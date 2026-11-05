import { defineStore } from 'pinia'
import { apiPost } from '../api/client'

interface AuthState {
  accessToken: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },
  actions: {
    async login(username: string, password: string) {
      const result = await apiPost<{ access_token: string; token_type: string }>('/api/auth/login', { username, password })
      this.accessToken = result.access_token
    },
    logout() {
      this.accessToken = null
    },
  },
  persist: true,
})
