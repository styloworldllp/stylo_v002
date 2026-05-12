<template>
  <div class="space-y-6">
    <!-- Stat cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="stat in stats" :key="stat.label" class="bg-white rounded-xl border border-gray-200 p-5">
        <p class="text-xs text-gray-500 uppercase tracking-wide font-medium">{{ stat.label }}</p>
        <p class="text-3xl font-bold text-gray-900 mt-1">{{ stat.value }}</p>
        <p v-if="stat.sub" class="text-xs mt-1" :class="stat.subClass || 'text-gray-400'">{{ stat.sub }}</p>
      </div>
    </div>

    <!-- Bottom grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Expiring soon -->
      <div class="bg-white rounded-xl border border-gray-200">
        <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 class="font-semibold text-gray-900 text-sm">Expiring Licenses (next 7 days)</h2>
          <RouterLink to="/licenses" class="text-xs text-brand-600 hover:underline">View all</RouterLink>
        </div>
        <div v-if="expiring.length === 0" class="px-5 py-8 text-center text-sm text-gray-400">
          No licenses expiring soon ✓
        </div>
        <ul v-else class="divide-y divide-gray-50">
          <li v-for="lic in expiring" :key="lic.id" class="flex items-center justify-between px-5 py-3">
            <div>
              <p class="text-sm font-medium text-gray-800">{{ lic.user_email }}</p>
              <p class="text-xs text-gray-400">{{ lic.site_domain || `Site #${lic.site_id}` }}</p>
            </div>
            <span class="text-xs text-orange-600 font-medium">{{ daysLeft(lic.expires_at) }}d left</span>
          </li>
        </ul>
      </div>

      <!-- Recent deploys -->
      <div class="bg-white rounded-xl border border-gray-200">
        <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 class="font-semibold text-gray-900 text-sm">Recent Deployments</h2>
          <RouterLink to="/sites" class="text-xs text-brand-600 hover:underline">All sites</RouterLink>
        </div>
        <div v-if="recentLogs.length === 0" class="px-5 py-8 text-center text-sm text-gray-400">
          No deployments yet
        </div>
        <ul v-else class="divide-y divide-gray-50">
          <li v-for="log in recentLogs" :key="log.id" class="flex items-center justify-between px-5 py-3">
            <div>
              <p class="text-sm font-medium text-gray-800">{{ log.site_domain || `Site #${log.site_id}` }}</p>
              <p class="text-xs text-gray-400 capitalize">{{ log.action }} · {{ formatDate(log.started_at) }}</p>
            </div>
            <StatusBadge :status="log.status" />
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Dashboard.vue — overview page loaded first after login.
 *
 * Sections:
 *   Top row — 4 stat cards (servers, active sites, active licenses, expiring in 7d)
 *   Bottom left  — licenses expiring in the next 7 days (max 8 shown)
 *   Bottom right — recent deploy logs collected from the last 5 sites (max 8)
 *
 * Data loading:
 *   onMounted fires 3 parallel requests (servers, sites, licenses).
 *   Recent logs require a second pass: one request per site (up to 5 sites).
 *   All loaded data is reactive via ref() and renders automatically.
 */
import { onMounted, ref } from 'vue'
import api from '../api'
import StatusBadge from '../components/StatusBadge.vue'

const stats = ref([
  { label: 'Servers', value: '—' },
  { label: 'Active Sites', value: '—' },
  { label: 'Active Licenses', value: '—' },
  { label: 'Expiring (7d)', value: '—', subClass: 'text-orange-500' },
])
const expiring = ref([])
const recentLogs = ref([])

onMounted(async () => {
  try {
    const [serversRes, sitesRes, licensesRes] = await Promise.all([
      api.get('/api/servers'),
      api.get('/api/sites'),
      api.get('/api/licenses'),
    ])

    const servers = serversRes.data
    const sites = sitesRes.data
    const licenses = licensesRes.data

    const activeSites = sites.filter((s) => s.status === 'active').length
    const activeLicenses = licenses.filter((l) => l.status === 'active').length

    const now = Date.now()
    const sevenDays = 7 * 24 * 60 * 60 * 1000
    const soonExpiring = licenses.filter((l) => {
      if (l.status !== 'active') return false
      const exp = new Date(l.expires_at).getTime()
      return exp > now && exp - now < sevenDays
    })

    stats.value = [
      { label: 'Servers', value: servers.length },
      { label: 'Active Sites', value: activeSites },
      { label: 'Active Licenses', value: activeLicenses },
      { label: 'Expiring (7d)', value: soonExpiring.length, subClass: soonExpiring.length > 0 ? 'text-orange-500' : 'text-gray-400' },
    ]
    expiring.value = soonExpiring.slice(0, 8)

    // Collect recent logs from all sites
    const allLogs = []
    for (const site of sites.slice(0, 5)) {
      try {
        const { data: logs } = await api.get(`/api/sites/${site.id}/logs`, { params: { limit: 3 } })
        logs.forEach((l) => allLogs.push({ ...l, site_domain: site.domain }))
      } catch {}
    }
    recentLogs.value = allLogs.sort((a, b) => new Date(b.started_at) - new Date(a.started_at)).slice(0, 8)
  } catch {}
})

function daysLeft(expires_at) {
  return Math.ceil((new Date(expires_at) - Date.now()) / 86400000)
}

function formatDate(d) {
  return new Date(d).toLocaleDateString()
}
</script>
