<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { appApi, getSession, idempotencyKey, type BrowserSession } from './api'

type MetricKey = 'sent_24h'|'messages_total'|'quota'|'delivered'|'bounced'|'delivery_rate'|'contacts'|'campaigns'|'suppressions'|'outbox_active'|'outbox_failed'
interface DashboardData {
  metrics: Record<MetricKey, number>
  domains: Array<{ id: string; domain: string; verified: boolean }>
  senders: Array<{ id: string; address: string; role: string }>
  recent_messages: Array<{ id: string; recipient: string; sender: string; subject: string; status: string; created_at: string }>
  onboarding: { step: number; use_case?: string; checklist: Record<string, boolean>; completed: boolean } | null
}
interface TeamMember { user_id: string; email: string | null; role: string; created_at: string }

const session = ref<BrowserSession>({ authenticated: false })
const dashboard = ref<DashboardData | null>(null)
const team = ref<TeamMember[]>([])
const loading = ref(true), error = ref(''), sendStatus = ref(''), sending = ref(false)
const recipient = ref(''), sender = ref(''), subject = ref(''), text = ref('')
const active = ref<'overview'|'messages'|'domains'|'team'|'send'>('overview')
const usage = computed(() => dashboard.value ? Math.min(100, Math.round((dashboard.value.metrics.sent_24h / Math.max(1, dashboard.value.metrics.quota)) * 100)) : 0)

async function load() {
  loading.value = true; error.value = ''
  try {
    session.value = await getSession()
    if (!session.value.authenticated) { location.assign('/login?return_to=/app'); return }
    dashboard.value = await appApi<DashboardData>('/app/api/dashboard')
    team.value = await appApi<TeamMember[]>('/app/api/team')
    sender.value = dashboard.value.senders[0]?.address || ''
  } catch (err) { error.value = err instanceof Error ? err.message : 'dashboard_unavailable' }
  finally { loading.value = false }
}
async function sendEmail() {
  sending.value = true; sendStatus.value = ''
  try {
    const result = await appApi<{ id: string; status: string }>('/app/api/email/send', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey('dashboard-send') },
      body: JSON.stringify({ to: recipient.value, sender: sender.value, subject: subject.value, text: text.value, html: `<p>${text.value.replace(/[&<>]/g, value => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[value] || value))}</p>`, stream: 'transactional' }),
    })
    sendStatus.value = `Accepted as ${result.id}`
    recipient.value = ''; subject.value = ''; text.value = ''
    await load()
  } catch (err) { sendStatus.value = err instanceof Error ? err.message : 'send_failed' }
  finally { sending.value = false }
}
async function logout() {
  const current = await getSession()
  const result = await appApi<{ end_session_url?: string }>('/auth/logout', { method: 'POST' })
  if (current.authenticated && result.end_session_url) location.assign(result.end_session_url)
  else location.assign('/logged-out')
}
onMounted(load)
</script>

<template>
  <div class="product-shell">
    <aside class="product-sidebar">
      <a class="product-brand" href="/app"><span>K</span>Klyrow</a>
      <nav aria-label="Dashboard navigation">
        <a class="mail-link" href="/app/mail">Mail</a>
        <button v-for="item in ['overview','messages','domains','team','send']" :key="item" :class="{active:active===item}" @click="active=item as typeof active">{{ item }}</button>
      </nav>
      <div class="sidebar-foot"><span>{{ session.email }}</span><button @click="logout">Sign out</button></div>
    </aside>
    <main class="product-main">
      <header class="product-header"><div><p class="eyebrow">EMAIL OPERATIONS</p><h1>{{ active === 'overview' ? 'Command center' : active }}</h1></div><div class="header-actions"><a href="/onboarding">Setup</a><button class="refresh" @click="load">Refresh</button></div></header>
      <div v-if="loading" class="state-card" role="status">Loading your workspace…</div>
      <div v-else-if="error" class="state-card error" role="alert">{{ error }} <button @click="load">Try again</button></div>
      <template v-else-if="dashboard">
        <section v-if="active==='overview'" class="dashboard-stack">
          <div v-if="dashboard.onboarding && !dashboard.onboarding.completed" class="setup-banner"><div><strong>Finish workspace setup</strong><p>Complete domain, sender and team setup before increasing delivery.</p></div><a href="/onboarding">Continue setup →</a></div>
          <div class="metric-grid">
            <article><span>Sent · 24h</span><strong>{{ dashboard.metrics.sent_24h.toLocaleString() }}</strong><small>{{ usage }}% of daily quota</small></article>
            <article><span>Delivery rate</span><strong>{{ (dashboard.metrics.delivery_rate*100).toFixed(1) }}%</strong><small>{{ dashboard.metrics.delivered }} delivered</small></article>
            <article><span>Verified domains</span><strong>{{ dashboard.domains.filter(d=>d.verified).length }}/{{ dashboard.domains.length }}</strong><small>DNS sending identities</small></article>
            <article><span>Active outbox</span><strong>{{ dashboard.metrics.outbox_active }}</strong><small>{{ dashboard.metrics.outbox_failed }} failed</small></article>
          </div>
          <div class="two-column">
            <section class="panel"><div class="panel-title"><div><p class="eyebrow">TRAFFIC</p><h2>Recent messages</h2></div><button @click="active='messages'">View all</button></div><div class="table-wrap"><table><thead><tr><th>Recipient</th><th>Subject</th><th>Status</th><th>Time</th></tr></thead><tbody><tr v-for="message in dashboard.recent_messages" :key="message.id"><td>{{ message.recipient }}</td><td>{{ message.subject }}</td><td><span class="status" :data-status="message.status">{{ message.status }}</span></td><td>{{ new Date(message.created_at).toLocaleString() }}</td></tr><tr v-if="!dashboard.recent_messages.length"><td colspan="4">No messages yet.</td></tr></tbody></table></div></section>
            <section class="panel health"><p class="eyebrow">SENDING HEALTH</p><h2>Workspace readiness</h2><div class="health-row"><span>Allowed senders</span><strong>{{ dashboard.senders.length }}</strong></div><div class="health-row"><span>Contacts</span><strong>{{ dashboard.metrics.contacts }}</strong></div><div class="health-row"><span>Campaigns</span><strong>{{ dashboard.metrics.campaigns }}</strong></div><div class="health-row"><span>Suppressions</span><strong>{{ dashboard.metrics.suppressions }}</strong></div><button class="primary" @click="active='send'">Send transactional email</button></section>
          </div>
        </section>
        <section v-else-if="active==='messages'" class="panel"><div class="panel-title"><div><p class="eyebrow">MESSAGE LOG</p><h2>Recent email</h2></div></div><div class="table-wrap"><table><thead><tr><th>Recipient</th><th>Sender</th><th>Subject</th><th>Status</th><th>Created</th></tr></thead><tbody><tr v-for="message in dashboard.recent_messages" :key="message.id"><td>{{ message.recipient }}</td><td>{{ message.sender }}</td><td>{{ message.subject }}</td><td><span class="status">{{ message.status }}</span></td><td>{{ new Date(message.created_at).toLocaleString() }}</td></tr></tbody></table></div></section>
        <section v-else-if="active==='domains'" class="panel"><p class="eyebrow">DELIVERABILITY</p><h2>Sending domains</h2><div class="domain-list"><article v-for="domain in dashboard.domains" :key="domain.id"><div><strong>{{ domain.domain }}</strong><small>DKIM/SPF verification identity</small></div><span class="status" :data-status="domain.verified?'verified':'pending'">{{ domain.verified ? 'Verified' : 'Needs verification' }}</span></article><p v-if="!dashboard.domains.length" class="empty">No domains configured. Add a domain through the API or setup flow.</p></div></section>
        <section v-else-if="active==='team'" class="panel"><p class="eyebrow">ACCESS</p><h2>Workspace team</h2><div class="team-list"><article v-for="member in team" :key="member.user_id"><div><strong>{{ member.email || member.user_id }}</strong><small>Joined {{ new Date(member.created_at).toLocaleDateString() }}</small></div><span>{{ member.role }}</span></article></div></section>
        <section v-else class="panel compose"><p class="eyebrow">TRANSACTIONAL</p><h2>Send a message</h2><p class="muted">This uses the same backend policy engine, verified-domain checks, sender authorization, idempotency and outbox as the public API.</p><form @submit.prevent="sendEmail"><label>From<select v-model="sender" required><option v-for="item in dashboard.senders" :key="item.id" :value="item.address">{{ item.address }}</option></select></label><label>To<input v-model="recipient" type="email" required autocomplete="off"></label><label>Subject<input v-model="subject" required maxlength="200"></label><label>Message<textarea v-model="text" required rows="8"></textarea></label><button class="primary" :disabled="sending || !dashboard.senders.length">{{ sending ? 'Sending…' : 'Send email' }}</button><p v-if="sendStatus" role="status" class="send-status">{{ sendStatus }}</p></form></section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.product-shell{min-height:100vh;background:#080808;color:#f7f8fa;font-family:Inter,"Helvetica Neue","Segoe UI",Roboto,Arial,sans-serif}.product-sidebar{position:fixed;inset:0 auto 0 0;width:248px;padding:26px 18px;border-right:1px solid #292b30;background:#050505;display:flex;flex-direction:column;z-index:20}.product-brand{display:flex;align-items:center;gap:10px;color:#f7f8fa;text-decoration:none;font-weight:800;font-size:20px;letter-spacing:-.03em;padding:0 10px 30px}.product-brand span{display:grid;place-items:center;width:32px;height:32px;background:#ffd700;color:#080808;border-radius:4px}.product-sidebar nav{display:grid;gap:4px}.product-sidebar nav button,.product-sidebar nav .mail-link,.sidebar-foot button{border:0;background:transparent;color:#979aa2;text-align:left;padding:12px 14px;border-radius:4px;text-transform:capitalize;cursor:pointer;font-weight:650;text-decoration:none}.product-sidebar nav button:hover,.product-sidebar nav button.active,.product-sidebar nav .mail-link:hover{background:#121212;color:#ffd700}.sidebar-foot{margin-top:auto;padding:18px 10px 0;border-top:1px solid #292b30;display:grid;gap:8px;color:#c9cbd1;font-size:13px;overflow:hidden}.sidebar-foot button{padding:8px 0}.product-main{margin-left:248px;min-height:100vh;padding:34px clamp(22px,4vw,64px) 70px}.product-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:34px}.product-header h1{font-size:clamp(30px,4vw,48px);margin:5px 0 0;letter-spacing:-.045em}.eyebrow{font-size:11px;letter-spacing:.14em;color:#ffd700;font-weight:800;margin:0;text-transform:uppercase}.header-actions{display:flex;gap:10px;align-items:center}.header-actions a,.refresh{min-height:42px;padding:0 15px;border:1px solid #292b30;border-radius:4px;background:#0c0c0c;color:#c9cbd1;text-decoration:none;display:inline-flex;align-items:center;cursor:pointer}.dashboard-stack{display:grid;gap:22px}.setup-banner{border:1px solid #493f00;background:#151300;padding:20px 22px;border-radius:6px;display:flex;justify-content:space-between;gap:20px;align-items:center}.setup-banner p{color:#c9cbd1;margin:5px 0 0}.setup-banner a{color:#ffd700;text-decoration:none;font-weight:750}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.metric-grid article,.panel,.state-card{border:1px solid #292b30;background:#0d0d0d;border-radius:6px;padding:22px}.metric-grid span{color:#979aa2;font-size:13px}.metric-grid strong{display:block;font-size:32px;margin:12px 0 5px;letter-spacing:-.04em}.metric-grid small{color:#c9cbd1}.two-column{display:grid;grid-template-columns:minmax(0,2fr) minmax(280px,1fr);gap:16px}.panel-title{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-bottom:18px}.panel h2{font-size:23px;margin:5px 0 18px}.panel-title h2{margin-bottom:0}.panel-title button{background:transparent;border:0;color:#ffd700;cursor:pointer}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;color:#979aa2;font-weight:650;padding:11px 10px;border-bottom:1px solid #292b30}td{padding:13px 10px;border-bottom:1px solid #1e1e1e;color:#c9cbd1}.status{display:inline-flex;padding:4px 7px;border:1px solid #343434;border-radius:3px;color:#c9cbd1;font-size:11px;text-transform:uppercase;letter-spacing:.05em}.status[data-status="delivered"],.status[data-status="verified"]{border-color:#245f3e;color:#76dfa5}.status[data-status="failed"],.status[data-status="bounced"]{border-color:#6d2a2a;color:#ff9292}.health{display:grid;align-content:start}.health-row{display:flex;justify-content:space-between;padding:13px 0;border-bottom:1px solid #222;color:#c9cbd1}.health-row strong{color:#f7f8fa}.primary{min-height:48px;border:1px solid #ffd700;background:#ffd700;color:#080808;border-radius:4px;padding:0 18px;font-weight:800;cursor:pointer;margin-top:20px}.primary:disabled{opacity:.45;cursor:not-allowed}.domain-list,.team-list{display:grid}.domain-list article,.team-list article{display:flex;justify-content:space-between;gap:20px;align-items:center;padding:17px 0;border-bottom:1px solid #222}.domain-list small,.team-list small{display:block;color:#979aa2;margin-top:4px}.team-list>article>span{color:#ffd700;font-size:12px}.compose{max-width:780px}.muted,.empty{color:#979aa2}.compose form{display:grid;gap:16px;margin-top:22px}.compose label{display:grid;gap:7px;color:#c9cbd1;font-size:13px;font-weight:650}.compose input,.compose select,.compose textarea{width:100%;box-sizing:border-box;border:1px solid #34363b;background:#080808;color:#f7f8fa;border-radius:4px;padding:12px;font:inherit;outline:none}.compose input:focus,.compose select:focus,.compose textarea:focus{border-color:#ffd700;box-shadow:0 0 0 2px rgba(255,215,0,.15)}.send-status{color:#c9cbd1}.state-card.error{border-color:#6d2a2a}.state-card button{margin-left:10px}.product-shell :focus-visible{outline:2px solid #ffd700;outline-offset:2px}@media(max-width:980px){.metric-grid{grid-template-columns:repeat(2,1fr)}.two-column{grid-template-columns:1fr}}@media(max-width:720px){.product-sidebar{position:static;width:auto;inset:auto;flex-direction:row;align-items:center;padding:12px 14px;border-right:0;border-bottom:1px solid #292b30;overflow:auto}.product-brand{padding:0 10px 0 0}.product-sidebar nav{display:flex}.product-sidebar nav button,.product-sidebar nav .mail-link{white-space:nowrap}.sidebar-foot{display:none}.product-main{margin-left:0;padding:24px 16px 50px}.product-header{align-items:flex-start}.header-actions a{display:none}.metric-grid{grid-template-columns:1fr 1fr}}@media(max-width:460px){.metric-grid{grid-template-columns:1fr}.product-sidebar nav button:nth-child(2),.product-sidebar nav button:nth-child(4){display:none}.setup-banner{align-items:flex-start;flex-direction:column}}
</style>
