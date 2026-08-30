export type AuthActionResult = {
  status?: string
  redirect_to?: string | null
  valid?: boolean
}

export class AuthActionError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code = 'authentication_action_failed') {
    super(code)
    this.name = 'AuthActionError'
    this.status = status
    this.code = code
  }
}

export async function requestAuthAction(
  path: string,
  payload: Record<string, unknown> = {},
): Promise<AuthActionResult> {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  const body = await response.json().catch(() => ({})) as AuthActionResult & { detail?: string }
  if (!response.ok) throw new AuthActionError(response.status, String(body.detail || 'authentication_action_failed'))
  return body
}

export function safeAuthRedirect(value: string): string {
  const target = new URL(value, location.origin)
  if (target.origin !== location.origin && target.origin !== 'https://auth.codestra.co') {
    throw new AuthActionError(502, 'unsafe_authentication_redirect')
  }
  return target.origin === location.origin
    ? `${target.pathname}${target.search}${target.hash}`
    : target.toString()
}
