import { readdirSync } from 'node:fs'
import { expect, it } from 'vitest'
import { paths } from '../auth'
import { browserRoute, rootViews, routeManifest } from '../routeManifest'

it('inventories every root Vue view and requires an access/state declaration', () => {
  const files = readdirSync('src').filter(file => file.endsWith('.vue')).map(file => file.slice(0, -4)).sort()
  expect([...rootViews].sort()).toEqual(files)
  expect([...new Set(routeManifest.map(route => route.view))].sort()).toEqual(files)
  expect(new Set(routeManifest.map(route => route.path)).size).toBe(routeManifest.length)
  for (const route of routeManifest) {
    expect(route.states).toContain('ready')
    expect(route.states).toContain('error')
    expect(browserRoute(route.path)?.view).toBe(route.view)
    if (route.access === 'session') expect(route.states).toContain('loading')
  }
})

it('retains all auth states and product route precedence', () => {
  for (const path of paths) expect(browserRoute('/' + path)?.access).toBe('public')
  expect(browserRoute('/app/provisioning')?.view).toBe('Provisioning')
  expect(browserRoute('/admin/provisioning')?.view).toBe('Provisioning')
  expect(browserRoute('/app/mail/thread')?.view).toBe('Webmail')
  expect(browserRoute('/app/messages')?.view).toBe('Dashboard')
  expect(browserRoute('/app/api/dashboard')).toBeUndefined()
  expect(browserRoute('/auth/session')).toBeUndefined()
})
