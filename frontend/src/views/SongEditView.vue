<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import ChordProEditor from '../components/ChordProEditor.vue'
import SongDisplay from '../components/SongDisplay.vue'

const route = useRoute()
const router = useRouter()
const store = useSongStore()

const isEdit = !!route.params.id
const title = ref('')
const artist = ref('')
const capo = ref(0)
const key = ref('')
const body = ref('')
const saving = ref(false)

onMounted(async () => {
  if (isEdit) {
    await store.fetchSong(route.params.id as string)
    if (store.current) {
      title.value = store.current.title
      artist.value = store.current.artist
      capo.value = store.current.capo
      key.value = store.current.key || ''
      body.value = store.current.body
    }
  }
})

async function save() {
  saving.value = true
  try {
    if (isEdit) {
      await store.updateSong(route.params.id as string, {
        title: title.value,
        artist: artist.value,
        capo: capo.value,
        key: key.value || undefined,
        body: body.value,
      })
    } else {
      const song = await store.createSong({
        title: title.value,
        artist: artist.value,
        capo: capo.value,
        key: key.value || undefined,
        body: body.value,
      })
      router.replace(`/songs/${song.id}/edit`)
    }
  } finally {
    saving.value = false
  }
}

async function transpose(interval: number) {
  if (!isEdit) return
  const song = await store.transposeSong(route.params.id as string, interval)
  body.value = song.body
}
</script>

<template>
  <div class="edit-page">
    <h1>{{ isEdit ? 'Edit Song' : 'New Song' }}</h1>

    <form @submit.prevent="save" class="edit-form">
      <div class="form-row">
        <div class="field">
          <label>Title</label>
          <input v-model="title" type="text" required />
        </div>
        <div class="field">
          <label>Artist</label>
          <input v-model="artist" type="text" required />
        </div>
      </div>
      <div class="form-row">
        <div class="field">
          <label>Capo (fret)</label>
          <input v-model.number="capo" type="number" min="0" max="11" />
        </div>
        <div class="field">
          <label>Key</label>
          <input v-model="key" placeholder="e.g. G, Am" />
        </div>
        <div v-if="isEdit" class="field">
          <label>Transpose</label>
          <div class="transpose-actions">
            <button type="button" @click="transpose(-1)" class="btn-sm">-1</button>
            <button type="button" @click="transpose(1)" class="btn-sm">+1</button>
          </div>
        </div>
      </div>

      <div class="field">
        <label>ChordPro Body</label>
        <ChordProEditor v-model="body" />
      </div>

      <div class="form-actions">
        <button type="submit" class="btn-primary" :disabled="saving">
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
        <router-link v-if="isEdit" :to="`/songs/${route.params.id}`" class="btn-secondary">
          Cancel
        </router-link>
        <router-link v-else to="/songs" class="btn-secondary">Cancel</router-link>
      </div>
    </form>

    <div v-if="body" class="preview">
      <h2>Preview</h2>
      <SongDisplay :chordpro="body" :title="title || 'Preview'" :artist="artist || 'Artist'" :capo="capo || 0" :song-key="key || null" />
    </div>
  </div>
</template>

<style scoped>
.edit-form {
  max-width: 800px;
}
.form-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}
.form-row .field {
  flex: 1;
}
.field {
  margin-bottom: 1rem;
}
.field label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
  color: var(--text-muted);
}
.field input {
  width: 100%;
  padding: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 0.95rem;
}
.field input:focus {
  outline: none;
  border-color: var(--accent);
}
.field input[type="number"] {
  max-width: 80px;
}
.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}
.btn-primary {
  padding: 0.5rem 1.5rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.6;
}
.btn-secondary {
  padding: 0.5rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  font-size: 0.9rem;
}
.btn-sm {
  padding: 0.3rem 0.6rem;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 3px;
  cursor: pointer;
}
.btn-sm:hover {
  border-color: var(--accent);
}
.transpose-actions {
  display: flex;
  gap: 0.25rem;
}
.preview {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.preview h2 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
}
</style>
