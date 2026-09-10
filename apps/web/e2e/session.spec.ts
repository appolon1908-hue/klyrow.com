import { expect, test } from '@playwright/test'

const session = {
  authenticated: true, identity_id: 'browser-fixture', tenant_id: 'workspace-fixture',
  email: 'user@example.com', role: 'READ_ONLY', capabilities: ['mail.read'],
  csrf_token: 'browser-fixture-csrf', expires_at: '2099-01-01T00:00:00Z',
}
const dashboard = {
  metrics: { sent_24h: 0, messages_total: 0, quota: 10, delivered: 0, bounced: 0,
    delivery_rate: 0, contacts: 0, campaigns: 0, suppressions: 0, outbox_active: 0, outbox_failed: 0 },
  domains: [], senders: [{ id: 'sender-fixture', address: 'sender@example.com', role: 'sender' }],
  recent_messages: [], onboarding: null,
}

test('expired protected deep link survives sign-in initiation', async ({ page }) => {
  await page.route('**/auth/session', route => route.fulfill({ status: 401, json: { detail: 'session_expired' } }))
  await page.goto('/app/mail/thread?folder=SENT#latest')
  await expect(page).toHaveURL(/\/login\?return_to=/)
  expect(new URL(page.url()).searchParams.get('return_to')).toBe('/app/mail/thread?folder=SENT#latest')
  const initiation = page.waitForRequest(request => new URL(request.url()).pathname === '/auth/google')
  await page.getByRole('button', { name: 'Continue with Google' }).click()
  expect(new URL((await initiation).url()).searchParams.get('return_to')).toBe('/app/mail/thread?folder=SENT#latest')
})

test('send UI consumes canonical capability and preserves the mutation key on retry', async ({ page }) => {
  let canSend = false
  const keys: string[] = []
  await page.route('**/auth/session', route => route.fulfill({ json: { ...session, capabilities: canSend ? ['mail.send'] : ['mail.read'] } }))
  await page.route('**/app/api/dashboard', route => route.fulfill({ json: dashboard }))
  await page.route('**/app/api/team', route => route.fulfill({ json: [] }))
  await page.route('**/app/api/email/send', route => {
    keys.push(route.request().headers()['idempotency-key'])
    expect(route.request().headers()['x-klyrow-csrf']).toBe(session.csrf_token)
    return route.fulfill({ status: 503, json: { detail: 'delivery_unavailable' } })
  })
  await page.goto('/app')
  await page.getByRole('button', { name: 'send', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Send email', exact: true })).toBeDisabled()
  await expect(page.getByRole('status')).toContainText('does not allow sending')
  canSend = true
  await page.getByRole('button', { name: 'Refresh', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Send email', exact: true })).toBeEnabled()
  await page.getByLabel('To', { exact: true }).fill('recipient@example.com')
  await page.getByLabel('Subject', { exact: true }).fill('Browser fixture')
  await page.getByLabel('Message', { exact: true }).fill('No provider is contacted by this test.')
  await page.getByRole('button', { name: 'Send email', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('delivery_unavailable')
  await page.getByRole('button', { name: 'Send email', exact: true }).click()
  await expect.poll(() => keys.length).toBe(2)
  expect(keys[0]).toBeTruthy()
  expect(keys[1]).toBe(keys[0])
  await page.getByLabel('Subject', { exact: true }).fill('Changed intent')
  await page.getByRole('button', { name: 'Send email', exact: true }).click()
  await expect.poll(() => keys.length).toBe(3)
  expect(keys[2]).not.toBe(keys[0])
})

test('logout invalidates another tab through a backend-authorized reload', async ({ context, page }) => {
  let authenticated = true
  await context.route('**/auth/session', route => route.fulfill({ json: authenticated ? session : { authenticated: false } }))
  await context.route('**/app/api/dashboard', route => route.fulfill({ json: dashboard }))
  await context.route('**/app/api/team', route => route.fulfill({ json: [] }))
  await context.route('**/auth/logout', route => { authenticated = false; return route.fulfill({ json: { logged_out: true } }) })
  await page.goto('/app')
  const other = await context.newPage()
  await other.goto('/app?view=messages#recent')
  await expect(other.getByRole('heading', { name: 'Command center' })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page).toHaveURL(/\/logged-out$/)
  await expect(other).toHaveURL(/\/login\?return_to=/)
  expect(new URL(other.url()).searchParams.get('return_to')).toBe('/app?view=messages#recent')
  expect(await other.evaluate(() => ({ local: Object.keys(localStorage), session: Object.keys(sessionStorage) }))).toEqual({ local: [], session: [] })
})


test('an API session expiry retains the current workspace deep link', async ({ page }) => {
  await page.route('**/auth/session', route => route.fulfill({ json: session }))
  await page.route('**/app/api/dashboard', route => route.fulfill({ status: 401, json: { detail: 'session_expired' } }))
  await page.goto('/app?view=messages#recent')
  await expect(page).toHaveURL(/\/login\?return_to=/)
  expect(new URL(page.url()).searchParams.get('return_to')).toBe('/app?view=messages#recent')
})


for (const boundary of ['session', 'api']) test(`disabled principal at ${boundary} uses the account-disabled view`, async ({ page }) => {
  await page.route('**/auth/session', route => route.fulfill(boundary === 'session'
    ? { status: 401, json: { detail: 'principal_disabled' } }
    : { json: session }))
  await page.route('**/app/api/dashboard', route => route.fulfill({ status: 401, json: { detail: 'principal_disabled' } }))
  await page.goto('/app')
  await expect(page).toHaveURL(/\/account-disabled$/)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
})
