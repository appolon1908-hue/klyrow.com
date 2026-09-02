import { createApp } from 'vue'
import AuthApp from './App.vue'
import Dashboard from './Dashboard.vue'
import Onboarding from './Onboarding.vue'
import AdminDashboard from './AdminDashboard.vue'
import Provisioning from './Provisioning.vue'
import Webmail from './Webmail.vue'
import './styles.css'

const path = location.pathname
const Root = path === '/app/provisioning' || path === '/admin/provisioning'
  ? Provisioning
  : path === '/app/mail' || path.startsWith('/app/mail/')
    ? Webmail
  : path === '/admin' || path.startsWith('/admin/')
    ? AdminDashboard
    : path === '/onboarding'
      ? Onboarding
      : path === '/app' || path.startsWith('/app/')
        ? Dashboard
        : AuthApp

createApp(Root).mount('#app')

// Invitation URLs carry the one-time capability in the query string. Hydrate
// the already-rendered Vue v-model through its native input event so recipients
// can validate the link directly without manually copying the token.
if (path === '/invite') {
  const token = new URLSearchParams(location.search).get('token') || ''
  const input = document.querySelector<HTMLInputElement>('#invite')
  if (token && input) {
    input.value = token
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }
}
