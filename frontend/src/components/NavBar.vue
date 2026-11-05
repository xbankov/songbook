<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import { useTheme } from '../composables/useTheme'
import { useOffline } from '../composables/useOffline'

const auth = useAuthStore()
const { theme, toggle } = useTheme()
const { isOnline, pendingEdits } = useOffline()
</script>

<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <router-link to="/songs" class="navbar-brand">Songbook</router-link>
      <div class="navbar-status">
        <span v-if="!isOnline" class="offline-badge" title="You are offline. Changes will sync when online.">Offline</span>
        <span v-if="pendingEdits.length" class="pending-badge" :title="`${pendingEdits.length} pending changes`">{{ pendingEdits.length }}</span>
      </div>
      <div class="navbar-links">
        <template v-if="auth.isAuthenticated">
          <router-link to="/songs" class="nav-link">Songs</router-link>
          <router-link to="/songbooks" class="nav-link">Songbooks</router-link>
          <router-link to="/songs/new" class="nav-link">Add Song</router-link>
          <router-link to="/settings" class="nav-link">Settings</router-link>
          <button @click="toggle" class="nav-btn theme-btn" :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'">
            {{ theme === 'dark' ? '☀' : '☾' }}
          </button>
          <button @click="auth.logout()" class="nav-btn">Logout</button>
        </template>
        <template v-else>
          <router-link to="/login" class="nav-link">Sign In</router-link>
        </template>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 1rem;
}
.navbar-inner {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  height: 48px;
  gap: 1rem;
}
.navbar-brand {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--accent);
  text-decoration: none;
}
.navbar-links {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-left: auto;
}
.nav-link {
  color: var(--text);
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}
.nav-link:hover,
.nav-link.router-link-active {
  background: var(--hover);
  color: var(--accent);
}
.nav-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}
.nav-btn:hover {
  background: var(--hover);
}
.theme-btn {
  font-size: 1rem;
  line-height: 1;
  padding: 0.25rem 0.5rem;
}
.navbar-status {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.offline-badge {
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  background: rgba(231, 76, 60, 0.2);
  color: #e74c3c;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pending-badge {
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  background: var(--accent);
  color: #000;
  border-radius: 50%;
  min-width: 1.2rem;
  text-align: center;
  font-weight: 700;
}
</style>
