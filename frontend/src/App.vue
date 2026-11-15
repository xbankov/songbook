<script setup lang="ts">
import { watch } from 'vue'
import NavBar from './components/NavBar.vue'
import { useTheme } from './composables/useTheme'
import { useSettingsStore } from './stores/settings'
import { useAuthStore } from './stores/auth'

const settingsStore = useSettingsStore()
const auth = useAuthStore()
useTheme()

watch(
  () => auth.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      settingsStore.fetchSettings().catch(() => {})
    }
  },
  { immediate: true },
)
</script>

<template>
  <NavBar />
  <main class="main-content">
    <router-view />
  </main>
</template>

<style scoped>
.main-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
}
</style>
