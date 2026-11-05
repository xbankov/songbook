<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSongbookStore } from '../stores/songbooks'

const router = useRouter()
const store = useSongbookStore()

const showNew = ref(false)
const newName = ref('')
const newDesc = ref('')

onMounted(() => store.fetchSongbooks())

async function create() {
  if (!newName.value) return
  const sb = await store.createSongbook({ name: newName.value, description: newDesc.value })
  newName.value = ''
  newDesc.value = ''
  showNew.value = false
  router.push(`/songbooks/${sb.id}`)
}
</script>

<template>
  <div class="songbooks-page">
    <div class="header">
      <h1>Songbooks</h1>
      <button @click="showNew = !showNew" class="btn-secondary">New Songbook</button>
    </div>

    <div v-if="showNew" class="new-form">
      <input v-model="newName" placeholder="Songbook name" class="input" />
      <input v-model="newDesc" placeholder="Description (optional)" class="input" />
      <button @click="create" class="btn-primary">Create</button>
    </div>

    <div v-if="store.loading" class="loading">Loading...</div>
    <div v-else-if="store.songbooks.length === 0" class="empty">No songbooks yet.</div>

    <div v-else class="songbook-list">
      <div
        v-for="sb in store.songbooks"
        :key="sb.id"
        class="songbook-card"
        @click="router.push(`/songbooks/${sb.id}`)"
      >
        <h3>{{ sb.name }}</h3>
        <p v-if="sb.description">{{ sb.description }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.header h1 {
  margin: 0;
  font-size: 1.4rem;
}
.btn-secondary {
  padding: 0.4rem 0.8rem;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary {
  padding: 0.4rem 1rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.new-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.input {
  flex: 1;
  min-width: 150px;
  padding: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
}
.input:focus {
  outline: none;
  border-color: var(--accent);
}
.songbook-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.songbook-card {
  padding: 0.75rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
}
.songbook-card:hover {
  border-color: var(--accent);
}
.songbook-card h3 {
  margin: 0;
  font-size: 1rem;
}
.songbook-card p {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}
.loading,
.empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}
</style>
