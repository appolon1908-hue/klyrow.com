<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { appApi, getSession } from './api'

interface PlatformMetrics {
  tenants: number
  users: number
  messages: number
  outbox_active: number
  outbox_failed: number
  verified_domains: number
  webhooks: number
  usage_events: number
}

const metrics = ref<PlatformMetrics | null>(null)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const session = await getSession()
    if (!session.authenticated) {
      location.assign('/login?return_to=/admin')
      return
    }
    metrics.value = await appApi<PlatformMetrics>('/app/api/admin/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'admin_dashboard_unavailable'
  } finally {
    loading.value = false
  }
}

async function logout() {
  const result = await appApi<{ end_session_url?: string }>('/auth/logout', { method: 'POST' })
  location.assign(result.end_session_url || '/logged-out')
}

onMounted(load)
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <a class="brand" href="/admin"><span>K</span><b>Klyrow</b><small>ADMIN</small></a>
      <nav aria-label="Platform administration">
        <a class="active" href="/admin">Overview</a>
        <a href="/app">Customer workspace</a>
      </nav>
      <button class="sign-out" @click="logout">Sign out</button>
    </aside>
    <main class="admin-main">
      <header>
        <div>
          <p class="eyebrow">PLATFORM OPERATIONS</p>
          <h1>Administration</h1>
          <p class="sub">A read-first view of Klyrow tenant, delivery and integration health.</p>
        </div>
        <button class="refresh" @click="load">Refresh</button>
      </header>

      <section v-if="loading" class="panel" role="status">Loading platform metrics…</section>
      <section v-else-if="error" class="panel error" role="alert">
        <strong>Administrative access unavailable</strong>
        <p>{{ error }}</p>
        <a href="/app">Return to workspace</a>
      </section>
      <template v-else-if="metrics">
        <section class="metrics">
          <article><span>Tenants</span><strong>{{ metrics.tenants.toLocaleString() }}</strong><small>Provisioned workspaces</small></article>
          <article><span>Users</span><strong>{{ metrics.users.toLocaleString() }}</strong><small>Application identities</small></article>
          <article><span>Messages</span><strong>{{ metrics.messages.toLocaleString() }}</strong><small>Recorded email intents</small></article>
          <article><span>Verified domains</span><strong>{{ metrics.verified_domains.toLocaleString() }}</strong><small>Approved sending domains</small></article>
        </section>

        <section class="grid">
          <article class="panel">
            <p class="eyebrow">DELIVERY QUEUE</p>
            <h2>Outbox health</h2>
            <div class="row"><span>Active / retrying</span><strong>{{ metrics.outbox_active }}</strong></div>
            <div class="row"><span>Failed</span><strong :class="{ danger: metrics.outbox_failed > 0 }">{{ metrics.outbox_failed }}</strong></div>
            <p class="note">Queue state is read from the same durable outbox used by the email delivery engine.</p>
          </article>
          <article class="panel">
            <p class="eyebrow">INTEGRATIONS</p>
            <h2>Event surfaces</h2>
            <div class="row"><span>Webhook endpoints</span><strong>{{ metrics.webhooks }}</strong></div>
            <div class="row"><span>Usage events</span><strong>{{ metrics.usage_events }}</strong></div>
            <p class="note">Platform administration remains separate from tenant-scoped customer operations.</p>
          </article>
        </section>

        <section class="panel boundary">
          <div>
            <p class="eyebrow">SECURITY BOUNDARY</p>
            <h2>Platform role required</h2>
            <p>This route is backed by the server-side browser session and fails closed unless the mapped Klyrow user has the <code>platform_admin</code> role.</p>
          </div>
          <a href="/app">Open customer dashboard →</a>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.admin-shell{min-height:100vh;background:#080808;color:#f7f8fa;font-family:Inter,"Helvetica Neue","Segoe UI",Roboto,Arial,sans-serif}.admin-sidebar{position:fixed;inset:0 auto 0 0;width:250px;background:#050505;border-right:1px solid #292b30;padding:26px 18px;display:flex;flex-direction:column}.brand{display:flex;align-items:center;gap:9px;color:#f7f8fa;text-decoration:none;padding:0 8px 30px}.brand span{display:grid;place-items:center;width:32px;height:32px;background:#ffd700;color:#080808;border-radius:4px;font-weight:900}.brand b{font-size:20px}.brand small{font-size:9px;letter-spacing:.14em;color:#ffd700;margin-left:auto}.admin-sidebar nav{display:grid;gap:4px}.admin-sidebar nav a{padding:12px 14px;border-radius:4px;color:#979aa2;text-decoration:none;font-weight:650}.admin-sidebar nav a:hover,.admin-sidebar nav a.active{background:#121212;color:#ffd700}.sign-out{margin-top:auto;border:0;border-top:1px solid #292b30;background:transparent;color:#979aa2;text-align:left;padding:18px 10px;cursor:pointer}.admin-main{margin-left:250px;padding:38px clamp(22px,4vw,64px) 70px}.admin-main header{display:flex;justify-content:space-between;align-items:center;margin-bottom:34px}.eyebrow{font-size:11px;letter-spacing:.14em;color:#ffd700;font-weight:800;margin:0}.admin-main h1{font-size:clamp(34px,4vw,52px);letter-spacing:-.05em;margin:6px 0 9px}.sub,.note{color:#979aa2}.refresh{min-height:44px;border:1px solid #292b30;background:#0d0d0d;color:#c9cbd1;border-radius:4px;padding:0 16px;cursor:pointer}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:18px}.metrics article,.panel{border:1px solid #292b30;background:#0d0d0d;border-radius:6px;padding:22px}.metrics span{color:#979aa2;font-size:13px}.metrics strong{display:block;font-size:32px;margin:12px 0 5px;letter-spacing:-.04em}.metrics small{color:#c9cbd1}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}.panel h2{font-size:23px;margin:6px 0 20px}.row{display:flex;justify-content:space-between;gap:20px;padding:14px 0;border-bottom:1px solid #222;color:#c9cbd1}.row strong{color:#f7f8fa}.row strong.danger{color:#ff9292}.note{line-height:1.6;font-size:13px;margin:18px 0 0}.boundary{display:flex;justify-content:space-between;gap:30px;align-items:center}.boundary p{color:#c9cbd1;max-width:780px;line-height:1.6}.boundary code{color:#ffd700}.boundary a,.panel.error a{color:#ffd700;text-decoration:none;font-weight:750}.panel.error{border-color:#6d2a2a}.panel.error p{color:#ffaaaa}:focus-visible{outline:2px solid #ffd700;outline-offset:2px}@media(max-width:900px){.metrics{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}@media(max-width:700px){.admin-sidebar{position:static;width:auto;flex-direction:row;align-items:center;border-right:0;border-bottom:1px solid #292b30;padding:12px}.brand{padding:0 16px 0 0}.admin-sidebar nav{display:flex}.sign-out{display:none}.admin-main{margin-left:0;padding:26px 16px 50px}.admin-main header{align-items:flex-start}.metrics{grid-template-columns:1fr 1fr}.boundary{align-items:flex-start;flex-direction:column}}@media(max-width:450px){.metrics{grid-template-columns:1fr}.admin-sidebar nav a:nth-child(2){display:none}}
</style>
