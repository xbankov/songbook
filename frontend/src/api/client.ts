const API_BASE = ''  // proxied by vite / nginx

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  params?: Record<string, string | number | undefined>
}

function buildUrl(path: string, params?: Record<string, string | number | undefined>): string {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') url.searchParams.set(k, String(v))
    })
  }
  return url.toString()
}

function getToken(): string | null {
  try {
    const raw = localStorage.getItem('auth')
    if (raw) {
      const parsed = JSON.parse(raw)
      return parsed?.accessToken || null
    }
  } catch {}
  return null
}

function handleUnauthorized(requestToken: string | null): void {
  // A late 401 from an old request must not clear a newer token (e.g. the user
  // just logged in again). Only clear if the failed request used the current one.
  if (getToken() !== requestToken) return
  localStorage.removeItem('auth')
  if (window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

export async function apiDownload(path: string): Promise<Blob> {
  const requestToken = getToken()
  const headers: Record<string, string> = {}
  if (requestToken) {
    headers['Authorization'] = `Bearer ${requestToken}`
  }
  const response = await fetch(buildUrl(path), { headers })
  if (!response.ok) {
    if (response.status === 401) {
      handleUnauthorized(requestToken)
    }
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(err.detail || `Request failed: ${response.status}`)
  }
  return response.blob()
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, params } = options
  const requestToken = getToken()

  const fetchHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  }
  if (requestToken) {
    fetchHeaders['Authorization'] = `Bearer ${requestToken}`
  }

  const response = await fetch(buildUrl(path, params), {
    method,
    headers: fetchHeaders,
    body: body ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
  })

  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/api/auth/login')) {
      handleUnauthorized(requestToken)
    }
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(err.detail || `Request failed: ${response.status}`)
  }

  const text = await response.text()
  if (!text) return undefined as T
  return JSON.parse(text)
}

export function apiGet<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  return apiRequest<T>(path, { params })
}

export function apiPost<T>(path: string, body?: unknown, contentType?: string): Promise<T> {
  const headers: Record<string, string> = {}
  if (contentType) {
    headers['Content-Type'] = contentType
  }
  return apiRequest<T>(path, { method: 'POST', body, headers })
}

export function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, { method: 'PUT', body })
}

export function apiDelete<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: 'DELETE' })
}
