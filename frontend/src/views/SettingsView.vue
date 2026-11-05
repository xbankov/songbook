<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useSettingsStore } from '../stores/settings'
import { apiGet, apiPost } from '../api/client'

const auth = useAuthStore()
const settingsStore = useSettingsStore()
const backups = ref<{ filename: string; size: number; created_at: string }[]>([])
const loadingBackups = ref(false)
const restoring = ref(false)
const backingUp = ref(false)
const message = ref('')
const saved = ref(false)

onMounted(async () => {
  await settingsStore.fetchSettings()
})

async function saveSettings() {
  saved.value = false
  if (!settingsStore.settings) return
  await settingsStore.updateSettings({
    font: settingsStore.settings.font,
    font_size: settingsStore.settings.font_size,
    double_column: settingsStore.settings.double_column,
    display_mode: settingsStore.settings.display_mode,
    transpose: settingsStore.settings.transpose,
  })
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

async function listBackups() {
  loadingBackups.value = true
  try {
    backups.value = await apiGet('/api/backup/list')
  } catch {
    backups.value = []
  } finally {
    loadingBackups.value = false
  }
}

async function createBackup() {
  backingUp.value = true
  message.value = ''
  try {
    const result = await apiPost<{ filename: string }>('/api/backup/create')
    message.value = `Backup created: ${result.filename}`
    await listBackups()
  } catch (e: unknown) {
    message.value = e instanceof Error ? e.message : 'Backup failed'
  } finally {
    backingUp.value = false
  }
}

async function downloadBackup(filename: string) {
  const token = localStorage.getItem('auth')
  const headers: Record<string, string> = {}
  if (token) {
    try { headers['Authorization'] = `Bearer ${JSON.parse(token).accessToken}` } catch {}
  }
  const resp = await fetch(`/api/backup/download/${encodeURIComponent(filename)}`, { headers })
  if (!resp.ok) return
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

async function restoreBackup(filename: string) {
  if (!confirm(`Restore from ${filename}? This will overwrite all data.`)) return
  restoring.value = true
  message.value = ''
  try {
    const result = await apiPost<{ message: string }>(`/api/backup/restore?filename=${encodeURIComponent(filename)}`)
    message.value = result.message
  } catch (e: unknown) {
    message.value = e instanceof Error ? e.message : 'Restore failed'
  } finally {
    restoring.value = false
  }
}
</script>

<template>
  <div class="settings-page">
    <h1>Settings</h1>

    <section class="section">
      <h2>Display Settings</h2>
      <div v-if="settingsStore.settings" class="display-settings">
        <div class="setting-row">
          <label>Font:</label>
          <select v-model="settingsStore.settings.font" class="input">
            <option value="DejaVu Sans Mono">DejaVu Sans Mono</option>
            <option value="DejaVu Sans">DejaVu Sans</option>
            <option value="DejaVu">DejaVu</option>
          </select>
        </div>
        <div class="setting-row">
          <label>Font Size:</label>
          <input v-model.number="settingsStore.settings.font_size" type="number" min="6" max="20" class="input-num" />
        </div>
        <div class="setting-row">
          <label>Display Mode:</label>
          <select v-model="settingsStore.settings.display_mode" class="input">
            <option value="above">Chords Above Lyrics</option>
            <option value="inline">Chords Inline</option>
          </select>
        </div>
        <div class="setting-row">
          <label>Double Column:</label>
          <input v-model="settingsStore.settings.double_column" type="checkbox" />
        </div>
        <div class="setting-row">
          <label>Transposition:</label>
          <div class="transpose-control">
            <button @click="settingsStore.settings.transpose = Math.max(-11, settingsStore.settings.transpose - 1)" class="ctrl-btn">&minus;</button>
            <span class="ctrl-label">{{ settingsStore.settings.transpose > 0 ? '+' : '' }}{{ settingsStore.settings.transpose }}</span>
            <button @click="settingsStore.settings.transpose = Math.min(11, settingsStore.settings.transpose + 1)" class="ctrl-btn">+</button>
            <button v-if="settingsStore.settings.transpose !== 0" @click="settingsStore.settings.transpose = 0" class="ctrl-btn ctrl-reset">Reset</button>
          </div>
        </div>
        <button @click="saveSettings" class="btn-primary">Save</button>
        <span v-if="saved" class="saved-msg">Saved!</span>
      </div>
    </section>

    <section class="section">
      <h2>Account</h2>
      <p>You are signed in.</p>
      <button @click="auth.logout()" class="btn-secondary">Sign Out</button>
    </section>

    <section class="section">
      <h2>Import</h2>
      <p>Paste a URL from <strong>Ultimate Guitar</strong> or <strong>supermusic.sk</strong> on the Songs page to import a song.</p>
    </section>

    <section class="section">
      <h2>Export</h2>
      <p>View any song or songbook and click <strong>Print PDF</strong> to generate a formatted PDF.</p>
    </section>

    <section class="section">
      <h2>Mobile App</h2>
      <p>Songbook is a <strong>PWA</strong> — open it in your browser and install to home screen for an app-like experience.</p>
      <p>For Android APK: run <code>npx cap build android</code> in the frontend directory.</p>
    </section>

    <section class="section">
      <h2>Backup & Restore</h2>
      <p>Automated daily backups are stored on the server. Manual backups can be created and restored below.</p>
      <div class="backup-actions">
        <button @click="createBackup" class="btn-secondary" :disabled="backingUp">
          {{ backingUp ? 'Creating...' : 'Create Backup' }}
        </button>
        <button @click="listBackups" class="btn-secondary">
          {{ loadingBackups ? 'Loading...' : 'List Backups' }}
        </button>
      </div>
      <div v-if="message" class="backup-msg">{{ message }}</div>
      <div v-if="backups.length" class="backup-list">
        <div v-for="b in backups" :key="b.filename" class="backup-item">
          <span class="backup-name">{{ b.filename }}</span>
          <span class="backup-size">({{ (b.size / 1024).toFixed(1) }} KB)</span>
          <div class="backup-actions-inline">
            <button @click="downloadBackup(b.filename)" class="btn-sm">Download</button>
            <button @click="restoreBackup(b.filename)" class="btn-sm btn-danger-sm" :disabled="restoring">Restore</button>
          </div>
        </div>
      </div>
    </section>

    <section class="section about">
      <h2>Songbook v2.0</h2>
      <p>Built with FastAPI, PostgreSQL, Vue 3. ChordPro format. Versioned songs. PDF export.</p>
      <p class="links">
        <a href="/api/docs" target="_blank">API Docs (Swagger)</a>
        <a href="/api/health" target="_blank">Health Check</a>
      </p>
    </section>
  </div>
</template>

<style scoped>
.settings-page { max-width: 700px; }
h1 { font-size: 1.4rem; margin-bottom: 1.5rem; }
.section { margin-bottom: 2rem; }
.section h2 { font-size: 1.1rem; margin-bottom: 0.5rem; padding-bottom: 0.25rem; border-bottom: 1px solid var(--border); }
.section p { margin: 0.5rem 0; color: var(--text); font-size: 0.9rem; }
code { background: var(--surface); padding: 0.1rem 0.3rem; border-radius: 3px; }
.display-settings { display: flex; flex-direction: column; gap: 0.75rem; }
.setting-row { display: flex; align-items: center; gap: 0.75rem; font-size: 0.9rem; }
.setting-row label { min-width: 120px; color: var(--text); }
.input { padding: 0.4rem 0.5rem; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-size: 0.85rem; }
.input-num { width: 60px; padding: 0.4rem 0.5rem; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; color: var(--text); font-size: 0.85rem; }
.transpose-control { display: flex; align-items: center; gap: 0.35rem; }
.ctrl-btn { background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 0.25rem 0.5rem; border-radius: 3px; cursor: pointer; font-size: 0.85rem; font-family: inherit; }
.ctrl-btn:hover { border-color: var(--accent); }
.ctrl-label { font-size: 0.85rem; color: var(--text-muted); min-width: 40px; text-align: center; }
.ctrl-reset { font-size: 0.75rem; color: var(--text-muted); }
.btn-primary { padding: 0.5rem 1rem; background: var(--accent); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; align-self: flex-start; }
.saved-msg { color: var(--accent); font-size: 0.85rem; }
.btn-secondary { padding: 0.4rem 0.8rem; background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 4px; cursor: pointer; }
.links { display: flex; gap: 1rem; }
.links a { color: var(--accent); text-decoration: none; font-size: 0.85rem; }
.backup-actions { display: flex; gap: 0.5rem; margin: 0.5rem 0; }
.backup-msg { margin: 0.5rem 0; padding: 0.5rem; background: var(--hover); border-radius: 4px; font-size: 0.85rem; }
.backup-list { display: flex; flex-direction: column; gap: 0.35rem; margin-top: 0.5rem; }
.backup-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; padding: 0.35rem 0; }
.backup-name { font-family: monospace; font-size: 0.8rem; }
.backup-size { color: var(--text-muted); font-size: 0.8rem; }
.backup-actions-inline { margin-left: auto; display: flex; gap: 0.35rem; }
.btn-sm { padding: 0.2rem 0.5rem; background: var(--surface); border: 1px solid var(--border); border-radius: 3px; cursor: pointer; font-size: 0.75rem; color: var(--text); text-decoration: none; }
.btn-danger-sm { color: var(--danger); border-color: var(--danger); }
</style>
