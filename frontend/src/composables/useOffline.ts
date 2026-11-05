import { ref, watch } from 'vue'

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
        await fetch('/api/songs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(edit.data),
        })
      } else if (edit.type === 'update') {
        await fetch(`/api/songs/${edit.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(edit.data),
        })
      } else if (edit.type === 'delete') {
        await fetch(`/api/songs/${edit.id}`, { method: 'DELETE' })
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
