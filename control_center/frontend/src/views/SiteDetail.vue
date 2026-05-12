<template>
  <div v-if="site" class="space-y-6">
    <!-- Header -->
    <div class="bg-white rounded-xl border border-gray-200 p-5">
      <div class="flex items-start justify-between">
        <div>
          <div class="flex items-center gap-3">
            <h1 class="text-xl font-bold text-gray-900">{{ site.domain }}</h1>
            <StatusBadge :status="site.status" />
          </div>
          <p class="text-sm text-gray-400 mt-1">
            Site #{{ site.id }} · Server {{ site.server_id }} · Image: {{ site.docker_image_tag }}
          </p>
          <p v-if="site.notes" class="text-sm text-gray-500 mt-2 italic">{{ site.notes }}</p>
        </div>
        <!-- Deploy actions -->
        <div class="flex flex-wrap gap-2">
          <button @click="deploy('provision')" :disabled="deploying" class="btn-primary text-xs">Provision</button>
          <button @click="deploy('update')" :disabled="deploying" class="btn-primary text-xs">Deploy Update</button>
          <button @click="deploy('suspend')" :disabled="deploying" class="btn-ghost text-xs">Suspend</button>
          <button @click="deploy('resume')" :disabled="deploying" class="btn-ghost text-xs">Resume</button>
          <button @click="deploy('terminate')" :disabled="deploying" class="text-xs border border-red-300 text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors">Terminate</button>
        </div>
      </div>

      <!-- API key -->
      <div class="mt-4 flex items-center gap-2">
        <code class="text-xs bg-gray-100 px-3 py-1.5 rounded font-mono select-all">{{ showKey ? site.site_api_key : '••••••••••••••••••••••••••••••••' }}</code>
        <button @click="showKey = !showKey" class="text-xs text-gray-400 hover:text-gray-600">{{ showKey ? 'Hide' : 'Show' }} API key</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 border-b border-gray-200">
      <button
        v-for="tab in ['Licenses', 'Deploy History']"
        :key="tab"
        @click="activeTab = tab"
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px"
        :class="activeTab === tab ? 'border-brand-500 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700'"
      >{{ tab }}</button>
    </div>

    <!-- Licenses tab -->
    <div v-if="activeTab === 'Licenses'" class="space-y-3">
      <div class="flex justify-end">
        <button @click="openIssue = true" class="btn-primary">+ Issue License</button>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">User Email</th>
              <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Expires</th>
              <th class="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-if="site.licenses.length === 0">
              <td colspan="4" class="text-center py-8 text-gray-400 text-sm">No licenses issued</td>
            </tr>
            <tr v-for="lic in site.licenses" :key="lic.id" class="hover:bg-gray-50">
              <td class="px-5 py-3.5 font-medium text-gray-800">{{ lic.user_email }}</td>
              <td class="px-5 py-3.5"><StatusBadge :status="lic.status" /></td>
              <td class="px-5 py-3.5 text-sm" :class="isExpiringSoon(lic.expires_at) ? 'text-orange-600 font-medium' : 'text-gray-500'">
                {{ formatDate(lic.expires_at) }}
              </td>
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-2 justify-end">
                  <button
                    v-if="lic.status === 'active'"
                    @click="revokeLicense(lic)"
                    class="text-xs text-red-500 hover:text-red-700"
                  >Revoke</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Deploy History tab -->
    <div v-if="activeTab === 'Deploy History'" class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Action</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Image Tag</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Started</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Duration</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="site.recent_logs.length === 0">
            <td colspan="6" class="text-center py-8 text-gray-400 text-sm">No deployments yet</td>
          </tr>
          <tr v-for="log in site.recent_logs" :key="log.id" class="hover:bg-gray-50">
            <td class="px-5 py-3.5 font-medium capitalize text-gray-800">{{ log.action }}</td>
            <td class="px-5 py-3.5"><StatusBadge :status="log.status" /></td>
            <td class="px-5 py-3.5 text-gray-500 text-xs font-mono">{{ log.image_tag }}</td>
            <td class="px-5 py-3.5 text-gray-500 text-xs">{{ formatDate(log.started_at) }}</td>
            <td class="px-5 py-3.5 text-gray-400 text-xs">{{ duration(log.started_at, log.finished_at) }}</td>
            <td class="px-5 py-3.5">
              <button @click="viewLog(log)" class="text-xs text-brand-600 hover:underline">Logs</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Issue license modal -->
    <Modal v-model="openIssue" title="Issue License">
      <form @submit.prevent="issueLicense" class="space-y-4">
        <div>
          <label class="form-label">User Email <span class="text-red-500">*</span></label>
          <input v-model="licForm.user_email" type="email" required class="form-input" placeholder="user@client.com" />
        </div>
        <div>
          <label class="form-label">Expires At <span class="text-red-500">*</span></label>
          <input v-model="licForm.expires_at" type="date" required class="form-input" />
        </div>
        <p v-if="licError" class="text-red-500 text-sm">{{ licError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" @click="openIssue = false" class="btn-ghost">Cancel</button>
          <button type="submit" :disabled="licSaving" class="btn-primary">{{ licSaving ? 'Issuing…' : 'Issue' }}</button>
        </div>
      </form>
    </Modal>

    <!-- Deploy log viewer -->
    <DeployLogModal v-model="showLogModal" :log-id="selectedLogId" :action="selectedAction" />
  </div>
  <div v-else class="flex items-center justify-center h-48 text-gray-400 text-sm">
    Loading…
  </div>
</template>

<script setup>
/**
 * SiteDetail.vue — full detail page for a single site deployment.
 *
 * Header section:
 *   Domain, status badge, image tag, notes, 5 deploy action buttons,
 *   and a toggleable API key display (the key the bench uses for sync).
 *
 * Tabs:
 *   Licenses      — table of all user licenses for this site with
 *                   inline revoke button and "Issue License" modal
 *   Deploy History — last 20 deploy log entries with action/status/duration
 *                   and a "Logs" button that opens DeployLogModal
 *
 * Deploy flow:
 *   deploy(action) → POST /api/deploy/{action}/{site_id}
 *   → immediately opens DeployLogModal with the returned log_id
 *   → modal polls every 3s until status changes from "running"
 *   → load() is called again to refresh site status after dispatch
 *
 * Issue license:
 *   openIssue modal collects user_email + expires_at, POSTs to /api/licenses,
 *   then refreshes the page via load().
 */
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'
import DeployLogModal from '../components/DeployLogModal.vue'
import Modal from '../components/Modal.vue'
import StatusBadge from '../components/StatusBadge.vue'

const route = useRoute()
const site = ref(null)
const activeTab = ref('Licenses')
const showKey = ref(false)
const deploying = ref(false)
const openIssue = ref(false)
const licSaving = ref(false)
const licError = ref('')
const licForm = ref({ user_email: '', expires_at: '' })
const showLogModal = ref(false)
const selectedLogId = ref(null)
const selectedAction = ref('')

async function load() {
  const { data } = await api.get(`/api/sites/${route.params.id}`)
  site.value = data
}
onMounted(load)

async function deploy(action) {
  if (!confirm(`Run "${action}" on ${site.value.domain}?`)) return
  deploying.value = true
  try {
    const { data } = await api.post(`/api/deploy/${action}/${site.value.id}`)
    selectedLogId.value = data.log_id
    selectedAction.value = action
    showLogModal.value = true
    await load()
  } catch (e) {
    alert(e.response?.data?.detail || 'Deploy failed')
  } finally {
    deploying.value = false
  }
}

async function revokeLicense(lic) {
  if (!confirm(`Revoke license for ${lic.user_email}?`)) return
  await api.put(`/api/licenses/${lic.id}/revoke`)
  await load()
}

async function issueLicense() {
  licSaving.value = true
  licError.value = ''
  try {
    await api.post('/api/licenses', {
      site_id: site.value.id,
      user_email: licForm.value.user_email,
      expires_at: licForm.value.expires_at,
    })
    openIssue.value = false
    licForm.value = { user_email: '', expires_at: '' }
    await load()
  } catch (e) {
    licError.value = e.response?.data?.detail || 'Failed'
  } finally {
    licSaving.value = false
  }
}

function viewLog(log) {
  selectedLogId.value = log.id
  selectedAction.value = log.action
  showLogModal.value = true
}

function formatDate(d) {
  return new Date(d).toLocaleDateString()
}

function isExpiringSoon(expires_at) {
  return (new Date(expires_at) - Date.now()) < 7 * 86400000
}

function duration(start, end) {
  if (!end) return '—'
  const s = Math.round((new Date(end) - new Date(start)) / 1000)
  if (s < 60) return `${s}s`
  return `${Math.round(s / 60)}m`
}
</script>

<style>
.form-label { @apply block text-sm font-medium text-gray-700 mb-1; }
.form-input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent; }
.btn-primary { @apply bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60; }
.btn-ghost { @apply border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium px-4 py-2 rounded-lg transition-colors; }
</style>
