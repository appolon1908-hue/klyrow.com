export interface BrowserSession {
  authenticated: boolean
  session_id?: string
  identity_id?: string
  user_id?: string
  email?: string | null
  tenant_id?: string
  role?: string
  expires_at?: string
  csrf_token?: string
  workspaces?: Array<{ tenant_id: string; role: string }>
}

let csrfToken = ''

export async function getSession(): Promise<BrowserSession> {
  const response = await fetch('/auth/session', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error('session_unavailable')
  const body = await response.json() as BrowserSession
  csrfToken = body.csrf_token || ''
  return body
}

export async function appApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    if (!csrfToken) await getSession()
    headers.set('X-Klyrow-CSRF', csrfToken)
  }
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' })
  if (response.status === 401) {
    location.assign('/login?return_to=' + encodeURIComponent(location.pathname))
    throw new Error('authentication_required')
  }
  if (!response.ok) {
    let detail = `request_failed_${response.status}`
    try { detail = String((await response.json() as { detail?: string }).detail || detail) } catch { /* response may be empty */ }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}

export function idempotencyKey(prefix = 'web') {
  return `${prefix}:${crypto.randomUUID()}`
}
