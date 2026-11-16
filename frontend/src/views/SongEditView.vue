<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSongStore } from '../stores/songs'
import ChordProEditor from '../components/ChordProEditor.vue'
import SongDisplay from '../components/SongDisplay.vue'
import AppNotice from '../components/AppNotice.vue'
import { splitChordProMetadata } from '../utils/chordpro'

const route = useRoute()
const router = useRouter()
const store = useSongStore()

const isEdit = !!route.params.id
const title = ref('')
const artist = ref('')
const capo = ref(0)
const key = ref('')
const body = ref('')
const difficulty = ref('')
const genre = ref('')
const saving = ref(false)
const error = ref('')
const saved = ref(false)
let savedTimer: ReturnType<typeof setTimeout> | null = null

function tagValue(tags: string[], prefix: string): string {
  return tags.find((tag) => tag.startsWith(prefix))?.slice(prefix.length) || ''
}

function buildTags(): string[] {
  // A new song must not inherit tags from a previously viewed song.
  const current = isEdit ? store.current?.tags || [] : []
  const otherTags = current.filter(
    (tag) => !tag.startsWith('difficulty:') && !tag.startsWith('genre:'),
  )
  const extraDifficulties = current
    .filter((tag) => tag.startsWith('difficulty:'))
    .slice(1)
  const extraGenres = current.filter((tag) => tag.startsWith('genre:')).slice(1)
  const tags = [...otherTags, ...extraDifficulties, ...extraGenres]
  if (difficulty.value) tags.push(`difficulty:${difficulty.value}`)
  if (genre.value.trim()) tags.push(`genre:${genre.value.trim().toLowerCase()}`)
  return tags
}

onBeforeUnmount(() => {
  if (savedTimer) clearTimeout(savedTimer)
})

onMounted(async () => {
  if (isEdit) {
    await store.fetchSong(route.params.id as string)
    if (store.current) {
      // Older songs may still carry {title}/{artist}/{capo}/{key} in the body.
      // Keep them out of the editor; they only fill fields that are empty.
      const { body: cleanBody, values } = splitChordProMetadata(store.current.body)
      const parsedCapo = parseInt(values.capo ?? '')
      title.value = store.current.title || values.title || ''
      artist.value = store.current.artist || values.artist || ''
      capo.value = store.current.capo || (isNaN(parsedCapo) ? 0 : parsedCapo)
      key.value = store.current.key || values.key || ''
      body.value = cleanBody
      const tags = store.current.tags || []
      difficulty.value = tagValue(tags, 'difficulty:')
      genre.value = tagValue(tags, 'genre:')
    }
  }
})

async function save() {
  saving.value = true
  error.value = ''
  saved.value = false
  try {
    if (isEdit) {
      await store.updateSong(route.params.id as string, {
        title: title.value,
        artist: artist.value,
        capo: capo.value,
        key: key.value || undefined,
        body: body.value,
        tags: buildTags(),
      })
      saved.value = true
      if (savedTimer) clearTimeout(savedTimer)
      savedTimer = setTimeout(() => {
        saved.value = false
        savedTimer = null
      }, 2000)
    } else {
      const song = await store.createSong({
        title: title.value,
        artist: artist.value,
        capo: capo.value,
        key: key.value || undefined,
        body: body.value,
        tags: buildTags(),
      })
      router.replace(`/songs/${song.id}?created=1`)
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    saving.value = false
  }
}

async function transpose(interval: number) {
  if (!isEdit) return
  error.value = ''
  try {
    const song = await store.transposeSong(route.params.id as string, interval)
    body.value = song.body
    key.value = song.key || ''
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Transpose failed'
  }
}
</script>

<template>
  <div class="edit-page">
    <h1>{{ isEdit ? 'Edit Song' : 'New Song' }}</h1>

    <AppNotice v-if="error" type="error" :message="error" />
    <AppNotice v-if="saved" type="success" message="Saved" />

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

      <div class="form-row">
        <div class="field">
          <label>Difficulty</label>
          <select v-model="difficulty">
            <option value="">Not set</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        <div class="field">
          <label>Genre</label>
          <input v-model="genre" type="text" placeholder="e.g. bluegrass" maxlength="128" />
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
      <SongDisplay :chordpro="body" :title="title" :artist="artist" :capo="capo || 0" :song-key="key || null" />
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
.field input,
.field select {
  width: 100%;
  padding: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 0.95rem;
}
.field input:focus,
.field select:focus {
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
