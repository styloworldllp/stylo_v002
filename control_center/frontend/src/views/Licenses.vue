<template>
  <div class="space-y-4">
    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3">
      <input v-model="search" class="form-input w-56" placeholder="Search email…" />
      <select v-model="filterSite" class="form-input w-48">
        <option value="">All sites</option>
        <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.domain }}</option>
      </select>
      <select v-model="filterStatus" class="form-input w-36">
        <option value="">All statuses</option>
        <option>active</option>
        <option>revoked</option>
        <option>expired</option>
      </select>
      <div class="ml-auto">
        <button @click="openIssue = true" class="btn-primary">+ Issue License</button>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">User Email</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Site</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Issued</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Expires</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="filtered.length === 0">
            <td colspan="6" class="text-center py-12 text-gray-400 text-sm">No licenses found</td>
          </tr>
          <tr v-for="lic in filtered" :key="lic.id" class="hover:bg-gray-50">
            <td class="px-5 py-3.5 font-medium text-gray-900">{{ lic.user_email }}</td>
            <td class="px-5 py-3.5 text-gray-500 text-xs">{{ siteDomain(lic.site_id) }}</td>
            <td class="px-5 py-3.5"><StatusBadge :status="lic.status" /></td>
            <td class="px-5 py-3.5 text-gray-400 text-xs">{{ formatDate(lic.issued_at) }}</td>
            <td class="px-5 py-3.5 text-sm" :class="expClass(lic)">{{ formatDate(lic.expires_at) }}</td>
            <td class="px-5 py-3.5">
              <div class="flex items-center gap-3 justify-end">
                <button
                  v-if="lic.status === 'active'"
                  @click="startRenew(lic)"
                  class="text-xs text-brand-600 hover:underline"
                >Renew</button>
                <button
                  v-if="lic.status === 'active'"
                  @click="revoke(lic)"
                  class="text-xs text-red-500 hover:text-red-700"
                >Revoke</button>
                <button
                  v-if="lic.status !== 'active'"
                  @click="deleteLicense(lic)"
                  class="text-xs text-gray-400 hover:text-gray-600"
                >Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Issue modal -->
    <Modal v-model="openIssue" title="Issue License">
      <form @submit.prevent="issueLicense" class="space-y-4">
        <div>
          <label class="form-label">Site <span class="text-red-500">*</span></label>
          <select v-model.number="issueForm.site_id" required class="form-input">
            <option value="">Select site…</option>
            <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.domain }}</option>
          </select>
        </div>
        <div>
          <label class="form-label">User Email <span class="text-red-500">*</span></label>
          <input v-model="issueForm.user_email" type="email" required class="form-input" placeholder="user@example.com" />
        </div>
        <div>
          <label class="form-label">Expires At <span class="text-red-500">*</span></label>
          <input v-model="issueForm.expires_at" type="date" required class="form-input" />
        </div>
        <p v-if="issueError" class="text-red-500 text-sm">{{ issueError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" @click="openIssue = false" class="btn-ghost">Cancel</button>
          <button type="submit" :disabled="issueSaving" class="btn-primary">{{ issueSaving ? 'Issuing…' : 'Issue' }}</button>
        </div>
      </form>
    </Modal>

    <!-- Renew modal -->
    <Modal v-model="openRenew" title="Renew License">
      <form @submit.prevent="renewLicense" class="space-y-4">
        <p class="text-sm text-gray-600">Renewing license for <strong>{{ renewTarget?.user_email }}</strong></p>
        <div>
          <label class="form-label">New Expiry Date <span class="text-red-500">*</span></label>
          <input v-model="renewDate" type="date" required class="form-input" />
        </div>
        <div class="flex justify-end gap-2">
          <button type="button" @click="openRenew = false" class="btn-ghost">Cancel</button>
          <button type="submit" :disabled="renewSaving" class="btn-primary">{{ renewSaving ? 'Renewing…' : 'Renew' }}</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
/**
 * Licenses.vue — global license management across all sites.
 *
 * Filters (client-side computed):
 *   search       — substring match on user_email
 *   filterSite   — show only licenses for a specific site
 *   filterStatus — active | revoked | expired
 *
 * Expiry color coding in the table:
 *   < 1 day left  → red + bold
 *   < 7 days left → orange + bold
 *   Otherwise     → normal gray
 *
 * Actions:
 *   Issue   — modal: site + email + expiry date → POST /api/licenses
 *             duplicate guard: backend rejects if active license already exists
 *   Revoke  — PUT /api/licenses/{id}/revoke (only shown for active licenses)
 *   Renew   — modal: new expiry date → PUT /api/licenses/{id}/renew
 *             also resets alert_sent_7d / alert_sent_1d flags
 *   Delete  — DELETE /api/licenses/{id} (only shown for non-active licenses)
 */
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import Modal from '../components/Modal.vue'
import StatusBadge from '../components/StatusBadge.vue'

const licenses = ref([])
const sites = ref([])
const search = ref('')
const filterSite = ref('')
const filterStatus = ref('')
const openIssue = ref(false)
const issueSaving = ref(false)
const issueError = ref('')
const issueForm = ref({ site_id: '', user_email: '', expires_at: '' })
const openRenew = ref(false)
const renewSaving = ref(false)
const renewTarget = ref(null)
const renewDate = ref('')

async function load() {
  const [l, s] = await Promise.all([api.get('/api/licenses'), api.get('/api/sites')])
  licenses.value = l.data
  sites.value = s.data
}
onMounted(load)

const filtered = computed(() => {
  return licenses.value.filter((l) => {
    return (
      (!search.value || l.user_email.includes(search.value)) &&
      (!filterSite.value || l.site_id === filterSite.value) &&
      (!filterStatus.value || l.status === filterStatus.value)
    )
  })
})

function siteDomain(id) {
  return sites.value.find((s) => s.id === id)?.domain || `#${id}`
}

function formatDate(d) {
  return new Date(d).toLocaleDateString()
}

function expClass(lic) {
  if (lic.status !== 'active') return 'text-gray-400'
  const diff = new Date(lic.expires_at) - Date.now()
  if (diff < 86400000) return 'text-red-600 font-medium'
  if (diff < 7 * 86400000) return 'text-orange-500 font-medium'
  return 'text-gray-500'
}

async function issueLicense() {
  issueSaving.value = true
  issueError.value = ''
  try {
    await api.post('/api/licenses', issueForm.value)
    openIssue.value = false
    issueForm.value = { site_id: '', user_email: '', expires_at: '' }
    await load()
  } catch (e) {
    issueError.value = e.response?.data?.detail || 'Failed'
  } finally {
    issueSaving.value = false
  }
}

async function revoke(lic) {
  if (!confirm(`Revoke license for ${lic.user_email}?`)) return
  await api.put(`/api/licenses/${lic.id}/revoke`)
  await load()
}

function startRenew(lic) {
  renewTarget.value = lic
  renewDate.value = ''
  openRenew.value = true
}

async function renewLicense() {
  renewSaving.value = true
  try {
    await api.put(`/api/licenses/${renewTarget.value.id}/renew`, { expires_at: renewDate.value })
    openRenew.value = false
    await load()
  } finally {
    renewSaving.value = false
  }
}

async function deleteLicense(lic) {
  if (!confirm(`Delete license record for ${lic.user_email}?`)) return
  await api.delete(`/api/licenses/${lic.id}`)
  await load()
}
</script>

<style>
.form-label { @apply block text-sm font-medium text-gray-700 mb-1; }
.form-input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent; }
.btn-primary { @apply bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60; }
.btn-ghost { @apply border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium px-4 py-2 rounded-lg transition-colors; }
</style>
