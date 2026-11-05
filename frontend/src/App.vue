<script setup lang="ts">
import { onMounted } from 'vue'
import NavBar from './components/NavBar.vue'
import { useTheme } from './composables/useTheme'
import { useSettingsStore } from './stores/settings'

const settingsStore = useSettingsStore()
useTheme()

onMounted(() => {
  settingsStore.fetchSettings()
})
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
