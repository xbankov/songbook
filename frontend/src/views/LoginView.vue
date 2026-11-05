<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    router.push('/songs')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Invalid credentials'
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Songbook</h1>
      <p class="subtitle">Sign in to access your songbook</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label>Username</label>
          <input v-model="username" type="text" required autofocus />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="password" type="password" required />
        </div>
        <div v-if="error" class="error">{{ error }}</div>
        <button type="submit" class="btn-primary">Sign In</button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  padding-top: 6rem;
}
.login-card {
  width: 100%;
  max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 2rem;
}
h1 {
  margin: 0 0 0.25rem;
  font-size: 1.5rem;
  text-align: center;
}
.subtitle {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
  margin: 0 0 1.5rem;
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
  padding: 0.6rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-size: 0.95rem;
  box-sizing: border-box;
}
.field input:focus {
  outline: none;
  border-color: var(--accent);
}
.error {
  color: #e74c3c;
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
}
.btn-primary {
  width: 100%;
  padding: 0.6rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 600;
}
.btn-primary:hover {
  opacity: 0.9;
}
</style>
