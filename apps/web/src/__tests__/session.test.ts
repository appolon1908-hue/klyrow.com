import { afterEach, describe, expect, it, vi } from 'vitest'
import { hasCapability, loginLocation, safeReturnPath, toOrbitSession, type BrowserSession } from '../session'

afterEach(() => vi.restoreAllMocks())
const session: BrowserSession = {
  authenticated: true, identity_id: 'identity-one', tenant_id: 'tenant-one',
  role: 'DEVELOPER', email: 'user@example.com', expires_at: '2099-01-01T00:00:00+00:00',
  csrf_token: 'unit-csrf', session_id: 'unit-session', capabilities: ['mail.send', 'mail.read', 'mail.read'],
}

describe('Orbit session consumer projection', () => {
  it('maps only safe identity, tenant, expiry, role and canonical capabilities', () => {
    expect(toOrbitSession(session)).toEqual({
      authenticated: true, expiresAt: '2099-01-01T00:00:00.000Z',
      user: { id: 'identity-one', displayName: 'user@example.com', email: 'user@example.com' },
      tenant: { id: 'tenant-one' }, roles: ['DEVELOPER'], capabilities: ['mail.send', 'mail.read'],
    })
  })
  it('does not infer grants from a role or incomplete/expired identity', () => {
    expect(hasCapability({ ...session, role: 'OWNER', capabilities: [] }, 'mail.send')).toBe(false)
    expect(hasCapability({ ...session, capabilities: ['*'] }, 'mail.send')).toBe(true)
    for (const patch of [{ authenticated: false }, { identity_id: '' }, { tenant_id: '' }, { expires_at: '2000-01-01T00:00:00Z' }, { expires_at: '' }]) {
      expect(toOrbitSession({ ...session, ...patch })).toBeNull()
      expect(hasCapability({ ...session, ...patch }, 'mail.send')).toBe(false)
    }
  })
})

describe('protected return destinations', () => {
  it('retains path, query and fragment across sign-in', () => {
    history.replaceState({}, '', '/app/mail/thread?folder=SENT#latest')
    expect(safeReturnPath('/app/mail/thread?folder=SENT#latest')).toBe('/app/mail/thread?folder=SENT#latest')
    expect(new URL(loginLocation(), location.origin).searchParams.get('return_to')).toBe('/app/mail/thread?folder=SENT#latest')
  })
  it('falls back for external, API, authentication or missing destinations', () => {
    for (const path of ['https://example.com', '/auth/logout', '/app/api/dashboard', '/unknown', null]) expect(safeReturnPath(path)).toBe('/app')
    expect(safeReturnPath(null, '/onboarding')).toBe('/onboarding')
  })
})
