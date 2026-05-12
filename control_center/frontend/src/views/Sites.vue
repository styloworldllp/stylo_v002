<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <div class="flex-1">
        <input v-model="search" class="form-input max-w-xs" placeholder="Search domain…" />
      </div>
      <select v-model="filterStatus" class="form-input w-40">
        <option value="">All statuses</option>
        <option>provisioning</option>
        <option>active</option>
        <option>suspended</option>
        <option>terminated</option>
      </select>
      <button @click="openAdd = true" class="btn-primary">+ New Site</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Domain</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Server</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Licenses</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Last Deploy</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="filtered.length === 0">
            <td colspan="6" class="text-center py-12 text-gray-400 text-sm">No sites found</td>
          </tr>
          <tr v-for="s in filtered" :key="s.id" class="hover:bg-gray-50">
            <td class="px-5 py-3.5">
              <RouterLink :to="`/sites/${s.id}`" class="font-medium text-brand-600 hover:underline">
                {{ s.domain }}
              </RouterLink>
            </td>
            <td class="px-5 py-3.5"><StatusBadge :status="s.status" /></td>
            <td class="px-5 py-3.5 text-gray-500 text-xs">{{ serverName(s.server_id) }}</td>
            <td class="px-5 py-3.5 text-gray-600">{{ s.active_license_count }}</td>
            <td class="px-5 py-3.5 text-gray-400 text-xs">
              {{ s.last_deployed_at ? formatDate(s.last_deployed_at) : 'Never' }}
            </td>
            <td class="px-5 py-3.5">
              <RouterLink :to="`/sites/${s.id}`" class="text-xs text-brand-600 hover:underline">Detail →</RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- New Site Modal -->
    <Modal v-model="openAdd" title="New Site">
      <form @submit.prevent="createSite" class="space-y-4">
        <div>
          <label class="form-label">Domain <span class="text-red-500">*</span></label>
          <input v-model="form.domain" required class="form-input" placeholder="client.styloworld.io" />
        </div>
        <div>
          <label class="form-label">Client <span class="text-red-500">*</span></label>
          <select v-model.number="form.client_id" required class="form-input">
            <option value="">Select client…</option>
            <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="form-label">Server <span class="text-red-500">*</span></label>
          <select v-model.number="form.server_id" required class="form-input">
            <option value="">Select server…</option>
            <option v-for="sv in servers" :key="sv.id" :value="sv.id">{{ sv.name }} ({{ sv.region }})</option>
          </select>
        </div>
        <div>
          <label class="form-label">Docker Image Tag</label>
          <input v-model="form.docker_image_tag" class="form-input" placeholder="latest" />
        </div>
        <div>
          <label class="form-label">Notes</label>
          <textarea v-model="form.notes" rows="2" class="form-input" />
        </div>
        <p v-if="formError" class="text-red-500 text-sm">{{ formError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" @click="openAdd = false" class="btn-ghost">Cancel</button>
          <button type="submit" :disabled="saving" class="btn-primary">{{ saving ? 'Creating…' : 'Create Site' }}</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
/**
 * Sites.vue — all site records with search and status filtering.
 *
 * Table columns: domain (link to SiteDetail), status badge, server name,
 *                active license count, last deploy date, detail arrow
 *
 * Filters (client-side computed):
 *   search       — substring match on domain
 *   filterStatus — exact match on site.status
 *
 * Create Site modal:
 *   Requires domain, client_id, server_id.  Docker image tag defaults to
 *   "latest".  Creates a DB record only — provisioning is done separately
 *   from the SiteDetail page via the deploy action buttons.
 */
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import Modal from '../components/Modal.vue'
import StatusBadge from '../components/StatusBadge.vue'

const sites = ref([])
const servers = ref([])
const clients = ref([])
const search = ref('')
const filterStatus = ref('')
const openAdd = ref(false)
const saving = ref(false)
const formError = ref('')
const form = ref({ domain: '', client_id: '', server_id: '', docker_image_tag: 'latest', notes: '' })

async function load() {
  const [s, sv, cl] = await Promise.all([
    api.get('/api/sites'),
    api.get('/api/servers'),
    api.get('/api/clients'),
  ])
  sites.value = s.data
  servers.value = sv.data
  clients.value = cl.data
}
onMounted(load)

const filtered = computed(() => {
  return sites.value.filter((s) => {
    const matchSearch = !search.value || s.domain.includes(search.value)
    const matchStatus = !filterStatus.value || s.status === filterStatus.value
    return matchSearch && matchStatus
  })
})

function serverName(id) {
  return servers.value.find((s) => s.id === id)?.name || `#${id}`
}

async function createSite() {
  saving.value = true
  formError.value = ''
  try {
    await api.post('/api/sites', form.value)
    openAdd.value = false
    form.value = { domain: '', client_id: '', server_id: '', docker_image_tag: 'latest', notes: '' }
    await load()
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Create failed'
  } finally {
    saving.value = false
  }
}

function formatDate(d) {
  return new Date(d).toLocaleDateString()
}
</script>

<style>
.form-label { @apply block text-sm font-medium text-gray-700 mb-1; }
.form-input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent; }
.btn-primary { @apply bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60; }
.btn-ghost { @apply border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium px-4 py-2 rounded-lg transition-colors; }
</style>
