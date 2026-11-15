import { defineStore } from 'pinia'
import { nextTick } from 'vue'
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
    async logout() {
      this.accessToken = null
      // The persisted-state plugin writes {"accessToken":null}; remove the key
      // after that write so no auth state is left behind.
      await nextTick()
      localStorage.removeItem('auth')
    },
  },
  persist: true,
})
