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
  capabilities?: string[]
  workspaces?: Array<{ tenant_id: string; role: string }>
}

// Consumer projection of the reviewed Orbit v2 contract, not package adoption.
// Source: SDK-repository@a194b5154a5b313c8fc4b9150abd17a4cc6612ae
// orbit/contracts/auth-session.openapi.yaml
export interface OrbitSession {
  authenticated: true
  expiresAt: string
  user: { id: string; displayName: string; email?: string }
  tenant: { id: string }
  roles: string[]
  capabilities: string[]
}

export function toOrbitSession(session: BrowserSession): OrbitSession | null {
  const expiry = Date.parse(session.expires_at || '')
  if (!session.authenticated || !session.identity_id || !session.tenant_id ||
      !Number.isFinite(expiry) || expiry <= Date.now()) return null
  return {
    authenticated: true,
    expiresAt: new Date(expiry).toISOString(),
    user: {
      id: session.identity_id,
      displayName: session.email || 'Klyrow user',
      ...(session.email ? { email: session.email } : {}),
    },
    tenant: { id: session.tenant_id },
    roles: session.role ? [session.role] : [],
    capabilities: [...new Set(session.capabilities || [])],
  }
}

export function hasCapability(session: BrowserSession, capability: string): boolean {
  const projection = toOrbitSession(session)
  return !!projection && (projection.capabilities.includes('*') || projection.capabilities.includes(capability))
}

export function hasInvalidPathCharacters(value: string): boolean {
  return [...value].some(character => character === String.fromCharCode(92) || character.charCodeAt(0) < 32)
}

export function safeReturnPath(value: string | null, fallback = '/app'): string {
  if (!value || value.length > 2048 || !value.startsWith('/') ||
      value.startsWith('//') || hasInvalidPathCharacters(value)) return fallback
  const target = new URL(value, location.origin)
  const path = target.pathname
  if (target.origin !== location.origin ||
      !(path === '/app' || path.startsWith('/app/') || path === '/admin' ||
        path.startsWith('/admin/') || path === '/onboarding') ||
      path === '/app/api' || path.startsWith('/app/api/')) return fallback
  return target.pathname + target.search + target.hash
}

export function loginLocation(): string {
  return '/login?return_to=' + encodeURIComponent(safeReturnPath(location.pathname + location.search + location.hash))
}
