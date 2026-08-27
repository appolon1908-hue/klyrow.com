import { createApp } from 'vue'
import AuthApp from './App.vue'
import Dashboard from './Dashboard.vue'
import Onboarding from './Onboarding.vue'
import './styles.css'

const path = location.pathname
const Root = path === '/onboarding' ? Onboarding : path === '/app' || path.startsWith('/app/') ? Dashboard : AuthApp
createApp(Root).mount('#app')
