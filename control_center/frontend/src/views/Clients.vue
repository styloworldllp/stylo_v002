<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">{{ clients.length }} client(s)</p>
      <button @click="openAdd = true" class="btn-primary">+ Add Client</button>
    </div>

    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Name</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Email</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Company</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Phone</th>
            <th class="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Created</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="clients.length === 0">
            <td colspan="6" class="text-center py-12 text-gray-400 text-sm">No clients yet</td>
          </tr>
          <tr v-for="c in clients" :key="c.id" class="hover:bg-gray-50">
            <td class="px-5 py-3.5 font-medium text-gray-900">{{ c.name }}</td>
            <td class="px-5 py-3.5 text-gray-600">{{ c.email }}</td>
            <td class="px-5 py-3.5 text-gray-500">{{ c.company || '—' }}</td>
            <td class="px-5 py-3.5 text-gray-500">{{ c.phone || '—' }}</td>
            <td class="px-5 py-3.5 text-gray-400 text-xs">{{ formatDate(c.created_at) }}</td>
            <td class="px-5 py-3.5">
              <div class="flex items-center gap-2 justify-end">
                <button @click="startEdit(c)" class="text-xs text-gray-500 hover:text-gray-700">Edit</button>
                <button @click="deleteClient(c)" class="text-xs text-red-500 hover:text-red-700">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="openAdd" :title="editing ? 'Edit Client' : 'Add Client'">
      <form @submit.prevent="saveClient" class="space-y-4">
        <div>
          <label class="form-label">Name <span class="text-red-500">*</span></label>
          <input v-model="form.name" required class="form-input" placeholder="Acme Corp" />
        </div>
        <div>
          <label class="form-label">Email <span class="text-red-500">*</span></label>
          <input v-model="form.email" type="email" required class="form-input" placeholder="billing@acme.com" />
        </div>
        <div>
          <label class="form-label">Company</label>
          <input v-model="form.company" class="form-input" placeholder="Acme Corporation" />
        </div>
        <div>
          <label class="form-label">Phone</label>
          <input v-model="form.phone" class="form-input" placeholder="+1 555 000 0000" />
        </div>
        <p v-if="formError" class="text-red-500 text-sm">{{ formError }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" @click="openAdd = false" class="btn-ghost">Cancel</button>
          <button type="submit" :disabled="saving" class="btn-primary">{{ saving ? 'Saving…' : 'Save' }}</button>
        </div>
      </form>
    </Modal>
  </div>
</template>

<script setup>
/**
 * Clients.vue — billing contact / organisation management.
 *
 * Simple CRUD table for Client records.
 * Add/Edit modal: name (required), email (required, unique), company, phone.
 *
 * Note: deleting a client does not cascade-delete their sites in the current
 * implementation — ensure sites are terminated first.
 */
import { onMounted, ref } from 'vue'
import api from '../api'
import Modal from '../components/Modal.vue'

const clients = ref([])
const openAdd = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const form = ref({ name: '', email: '', company: '', phone: '' })

async function load() {
  const { data } = await api.get('/api/clients')
  clients.value = data
}
onMounted(load)

function startEdit(c) {
  editing.value = c
  form.value = { name: c.name, email: c.email, company: c.company, phone: c.phone }
  openAdd.value = true
}

async function saveClient() {
  saving.value = true
  formError.value = ''
  try {
    if (editing.value) {
      await api.put(`/api/clients/${editing.value.id}`, form.value)
    } else {
      await api.post('/api/clients', form.value)
    }
    openAdd.value = false
    editing.value = null
    form.value = { name: '', email: '', company: '', phone: '' }
    await load()
  } catch (e) {
    formError.value = e.response?.data?.detail || 'Save failed'
  } finally {
    saving.value = false
  }
}

async function deleteClient(c) {
  if (!confirm(`Delete client "${c.name}"?`)) return
  try {
    await api.delete(`/api/clients/${c.id}`)
    await load()
  } catch (e) {
    alert(e.response?.data?.detail || 'Cannot delete')
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
