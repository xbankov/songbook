import { ref, watch } from 'vue'
import { apiDelete, apiRequest } from '../api/client'

interface PendingEdit {
  id: string
  type: 'create' | 'update' | 'delete'
  data: unknown
  timestamp: number
}

const isOnline = ref(navigator.onLine)
const pendingEdits = ref<PendingEdit[]>([])

function loadPending() {
  try {
    const raw = localStorage.getItem('pending_edits')
    if (raw) pendingEdits.value = JSON.parse(raw)
  } catch {}
}

function savePending() {
  localStorage.setItem('pending_edits', JSON.stringify(pendingEdits.value))
}

loadPending()

window.addEventListener('online', () => { isOnline.value = true; syncPending() })
window.addEventListener('offline', () => { isOnline.value = false })

function addPendingEdit(edit: PendingEdit) {
  pendingEdits.value.push(edit)
  savePending()
}

function removePendingEdit(id: string) {
  pendingEdits.value = pendingEdits.value.filter(e => e.id !== id)
  savePending()
}

async function syncPending() {
  if (!navigator.onLine) return
  for (const edit of [...pendingEdits.value]) {
    try {
      if (edit.type === 'create') {
        await apiRequest('/api/songs', { method: 'POST', body: edit.data })
      } else if (edit.type === 'update') {
        await apiRequest(`/api/songs/${edit.id}`, { method: 'PUT', body: edit.data })
      } else if (edit.type === 'delete') {
        await apiDelete(`/api/songs/${edit.id}`)
      }
      removePendingEdit(edit.id)
    } catch {
      continue
    }
  }
}

export function useOffline() {
  return {
    isOnline,
    pendingEdits,
    addPendingEdit,
    removePendingEdit,
    syncPending,
  }
}
