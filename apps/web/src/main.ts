import { createApp } from 'vue'
import AuthApp from './App.vue'
import Dashboard from './Dashboard.vue'
import Onboarding from './Onboarding.vue'
import AdminDashboard from './AdminDashboard.vue'
import Provisioning from './Provisioning.vue'
import './styles.css'

const path = location.pathname
const Root = path === '/app/provisioning' || path === '/admin/provisioning'
  ? Provisioning
  : path === '/admin' || path.startsWith('/admin/')
    ? AdminDashboard
    : path === '/onboarding'
      ? Onboarding
      : path === '/app' || path.startsWith('/app/')
        ? Dashboard
        : AuthApp
createApp(Root).mount('#app')
