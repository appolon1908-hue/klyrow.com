import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthActionError, requestAuthAction, safeAuthRedirect } from '../authActions'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('same-origin authentication actions', () => {
  it('posts JSON and returns a reviewed redirect only after success', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ status: 'accepted', redirect_to: '/reset-sent' }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const result = await requestAuthAction('/auth/actions/recover', { email: 'user@example.com' })
    expect(result.redirect_to).toBe('/reset-sent')
    expect(fetchMock).toHaveBeenCalledWith('/auth/actions/recover', expect.objectContaining({
      method: 'POST',
      credentials: 'same-origin',
      body: JSON.stringify({ email: 'user@example.com' }),
    }))
  })

  it('does not convert backend failure into a success view', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'authentication_unavailable' }),
    }))
    await expect(requestAuthAction('/auth/actions/recover', { email: 'user@example.com' }))
      .rejects.toMatchObject({ status: 503, code: 'authentication_unavailable' })
  })

  it('allows only same-origin or canonical Codestra Identity redirects', () => {
    expect(safeAuthRedirect('/signup')).toBe('/signup')
    expect(safeAuthRedirect('https://auth.codestra.co/realms/codestra/protocol/openid-connect/auth'))
      .toContain('https://auth.codestra.co/')
    expect(() => safeAuthRedirect('https://evil.example/steal')).toThrow(AuthActionError)
  })
})
