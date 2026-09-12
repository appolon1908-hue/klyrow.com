import { paths } from './auth'

export const rootViews = ['App', 'Dashboard', 'AdminDashboard', 'Onboarding', 'Provisioning', 'Webmail'] as const
export type RootView = typeof rootViews[number]

export interface BrowserRoute {
  path: string
  descendants?: boolean
  view: RootView
  access: 'public' | 'session'
  states: readonly string[]
}

// Ordered before the general product prefixes. These are current root views,
// not a claim that every intended product page has been implemented.
export const routeManifest: readonly BrowserRoute[] = [
  { path: '/app/provisioning', view: 'Provisioning', access: 'session', states: ['loading', 'error', 'empty', 'ready'] },
  { path: '/admin/provisioning', view: 'Provisioning', access: 'session', states: ['loading', 'error', 'empty', 'ready'] },
  { path: '/app/mail', descendants: true, view: 'Webmail', access: 'session', states: ['loading', 'error', 'empty', 'ready'] },
  { path: '/admin', descendants: true, view: 'AdminDashboard', access: 'session', states: ['loading', 'error', 'ready'] },
  { path: '/onboarding', view: 'Onboarding', access: 'session', states: ['loading', 'error', 'ready'] },
  { path: '/app', descendants: true, view: 'Dashboard', access: 'session', states: ['loading', 'error', 'ready'] },
  { path: '/', view: 'App', access: 'public', states: ['ready', 'validation', 'error'] },
  ...paths.map(path => ({ path: '/' + path, view: 'App' as const, access: 'public' as const, states: ['ready', 'validation', 'error'] })),
]

export function browserRoute(path: string): BrowserRoute | undefined {
  // API requests belong to Nginx/BFF, never to a product shell.
  if (path === '/app/api' || path.startsWith('/app/api/') ||
      path === '/auth' || path.startsWith('/auth/')) return undefined
  return routeManifest.find(route => path === route.path || (route.descendants && path.startsWith(route.path + '/')))
}
