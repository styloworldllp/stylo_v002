<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">{{ servers.length }} server(s) registered</p>
      <button @click="openAdd = true" class="btn-primary">+ Add Server</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Name</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Hostname</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Region</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Sites</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="servers.length === 0">
            <td colspan="6" class="text-center py-12 text-gray-400 text-sm">No servers added yet</td>
          </tr>
          <tr v-for="s in servers" :key="s.id" class="hover:bg-gray-50">
            <td class="px-5 py-3.5 font-medium text-gray-900">{{ s.name }}</td>
            <td class="px-5 py-3.5 text-gray-600 font-mono text-xs">{{ s.hostname }}:{{ s.ssh_port }}</td>
            <td class="px-5 py-3.5 text-gray-500">{{ s.region || '—' }}</td>
            <td class="px-5 py-3.5 text-gray-600">{{ s.site_count }} / {{ s.max_sites }}</td>
            <td class="px-5 py-3.5">
              <span
                class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                :class="s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
              >{{ s.is_active ? 'active' : 'inactive' }}</span>
            </td>
            <td class="px-5 py-3.5">
              <div class="flex items-center gap-2 justify-end">
                <button @click="checkHealth(s)" class="text-xs text-brand-600 hover:underline">Health</button>
                <button @click="startEdit(s)" class="text-xs text-gray-500 hover:text-gray-700">Edit</button>
                <button @click="deleteServer(s)" class="text-xs text-red-500 hover:text-red-700">Remove</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Health result -->
    <div v-if="healthResult" class="bg-gray-900 rounded-xl p-4">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs text-gray-400 font-mono">{{ healthResult.server }} — health check</span>
        <button @click="healthResult = null" class="text-gray-500 hover:text-gray-300 text-sm">×</button>
      </div>
      <p class="text-xs font-medium mb-1" :class="healthResult.status === 'ok' ? 'text-green-400' : 'text-red-400'">
        {{ healthResult.status === 'ok' ? '✓ Connected' : '✗ ' + healthResult.detail }}
      </p>
      <pre v-if="healthResult.containers?.length" class="text-green-300 text-xs font-mono">{{ healthResult.containers.join('\n') }}</pre>
    </div>

    <!-- Add/Edit Modal -->
    <Modal v-model="openAdd" :title="editing ? 'Edit Server' : 'Add Server'">
      <form @submit.prevent="saveServer" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div class="col-span-2">
            <label class="form-label">Name <span class="text-red-500">*</span></label>
            <input v-model="form.name" required class="form-input" placeholder="EU-West-1" />
          </div>
          <div class="col-span-2">
            <label class="form-label">Hostname / IP <span class="text-red-500">*</span></label>
            <input v-model="form.hostname" required class="form-input" placeholder="192.168.1.10" />
          </div>
          <div>
            <label class="form-label">SSH Port</label>
            <input v-model.number="form.ssh_port" type="number" class="form-input" placeholder="22" />
          </div>
          <div>
            <label class="form-label">SSH User</label>
            <input v-model="form.ssh_user" class="form-input" placeholder="root" />
          </div>
          <div class="col-span-2">
            <label class="form-label">Region</label>
            <input v-model="form.region" class="form-input" placeholder="us-east-1" />
          </div>
          <div>
            <label class="form-label">Max Sites</label>
            <input v-model.number="form.max_sites" type="number" class="form-input" placeholder="20" />
          </div>
        </div>
        <div>
          <label class="form-label">SSH Private Key (PEM) <span class="text-red-500">*</span></label>
          <textarea
            v-model="form.ssh_private_key"
            :required="!editing"
            rows="6"
            class="form-input font-mono text-xs"
            placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;..."
          />
          <p v-if="editing" class="text-xs text-gray-400 mt-1">Leave blank to keep existing key</p>
        </div>
        <p v-if="formError" class="text-red-500 text-sm">{{ formError }}</p>
        <div class="flex justify-end gap-2 pt-1">
          <button type="button" @click="openAdd = false" class="btn-ghost">Cancel</button>
          <button type="submit" :disabled="saving" class="btn-primary">{{ saving ? 'Saving…' : 'Save' }}</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
/**
 * Servers.vue — managed server list with add / edit / delete / health check.
 *
 * Table columns: name, hostname:port, region, site_count/max_sites, status, actions
 *
 * Add/Edit modal:
 *   Shared form with all Server fields.  When editing, the SSH private key
 *   field is optional (leave blank to keep the existing key in the DB).
 *
 * Health check:
 *   Calls GET /api/servers/{id}/health which SSHes in and runs `docker ps`.
 *   Result is rendered in a dark terminal-style panel below the table.
 *   Returns {"status":"error"} (not HTTP 500) so the UI shows a friendly message.
 *
 * Delete guard:
 *   Backend rejects deletion if the server has any active/suspended sites.
 *   The UI shows the backend error in an alert().
 */
import { onMounted, ref } from 'vue'
import api from '../api'
import Modal from '../components/Modal.vue'

const servers = ref([])
const openAdd = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const healthResult = ref(null)

const blankForm = () => ({
  name: '', hostname: '', ssh_port: 22, ssh_user: 'root',
  ssh_private_key: '', region: '', max_sites: 20,
})
const form = ref(blankForm())

async function load() {
  const { data } = await api.get('/api/servers')
  servers.value = data
}

onMounted(load)

function startEdit(s) {
  editing.value = s
  form.value = { ...s, ssh_private_key: '' }
  openAdd.value = true
}

async function saveServer() {
  saving.value = true
  formError.value = ''
  try {
    const payload = { ...form.value }
    if (editing.value && !payload.ssh_private_key) delete payload.ssh_private_key
    if (editing.value) {
      await api.put(`/api/servers/${editing.value.id}`, payload)
    } else {
      await api.post('/api/servers', payload)
    }
    openAdd.value = false
    editing.value = null
    form.value = blankForm()
    await load()
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Save failed'
  } finally {
    saving.value = false
  }
}

async function deleteServer(s) {
  if (!confirm(`Remove server "${s.name}"?`)) return
  try {
    await api.delete(`/api/servers/${s.id}`)
    await load()
  } catch (e) {
    alert(e.response?.data?.detail || 'Cannot remove server')
  }
}

async function checkHealth(s) {
  healthResult.value = null
  try {
    const { data } = await api.get(`/api/servers/${s.id}/health`)
    healthResult.value = { ...data, server: s.name }
  } catch (e) {
    healthResult.value = { status: 'error', detail: e.response?.data?.detail || 'Request failed', server: s.name }
  }
}
</script>

<style>
.form-label { @apply block text-sm font-medium text-gray-700 mb-1; }
.form-input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent; }
.btn-primary { @apply bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60; }
.btn-ghost { @apply border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium px-4 py-2 rounded-lg transition-colors; }
</style>
