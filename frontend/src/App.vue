<script setup lang="ts">
import { ref, watch } from 'vue'
import NavBar from './components/NavBar.vue'
import AppNotice from './components/AppNotice.vue'
import { useTheme } from './composables/useTheme'
import { useSettingsStore } from './stores/settings'
import { useAuthStore } from './stores/auth'

const settingsStore = useSettingsStore()
const auth = useAuthStore()
const settingsError = ref('')
useTheme()

watch(
  () => auth.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      settingsError.value = ''
      settingsStore.fetchSettings().catch((e: unknown) => {
        settingsError.value =
          e instanceof Error ? e.message : 'Could not load settings'
      })
    }
  },
  { immediate: true },
)
</script>

<template>
  <NavBar />
  <main class="main-content">
    <AppNotice v-if="settingsError" class="settings-notice" type="error" :message="settingsError" />
    <router-view />
  </main>
</template>

<style scoped>
.main-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 1rem;
}
@media print {
  .settings-notice {
    display: none !important;
  }
}
</style>
