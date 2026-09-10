<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Team</h1>
      <Button variant="solid" @click="openAddDialog">Add Team Member</Button>
    </div>

    <table class="w-full text-sm">
      <thead>
        <tr class="border-b text-left text-ink-gray-5">
          <th class="py-2">Name</th>
          <th>Email</th>
          <th>Role</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in team.data" :key="u.email" class="border-b">
          <td class="py-2">{{ u.full_name }}</td>
          <td>{{ u.email }}</td>
          <td class="w-56">
            <FormControl
              type="select"
              :model-value="primaryRole(u)"
              :options="ROLE_OPTIONS"
              @update:model-value="(role) => changeRole(u, role)"
            />
          </td>
          <td><Badge :theme="u.enabled ? 'green' : 'gray'">{{ u.enabled ? 'Active' : 'Disabled' }}</Badge></td>
          <td class="space-x-2 text-right">
            <Button size="sm" @click="resetPassword(u)">Reset Password</Button>
            <Button size="sm" variant="outline" @click="toggleStatus(u)">
              {{ u.enabled ? 'Disable' : 'Enable' }}
            </Button>
          </td>
        </tr>
      </tbody>
    </table>

    <Dialog v-model="showPasswordDialog" :options="{ title: 'Password Reset' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-6">
          New password for <strong>{{ resetTarget?.email }}</strong> — copy it now, it will
          not be shown again:
        </p>
        <div class="mt-3 flex items-center gap-2">
          <code class="flex-1 rounded bg-surface-gray-2 px-3 py-2 font-mono text-sm">{{ newPassword }}</code>
          <Button size="sm" @click="copyPassword">Copy</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showAddDialog" :options="{ title: 'Add Team Member' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl label="Full Name" v-model="newMember.full_name" />
          <FormControl label="Email" v-model="newMember.email" />
          <FormControl
            label="Role"
            type="select"
            v-model="newMember.role"
            :options="[
              'Command Center Super Admin',
              'Command Center Admin',
              'Command Center Support Staff',
            ]"
          />
          <p class="text-xs text-ink-gray-5">
            Super Admin: founding team, approves sites/licenses. Admin: creates sites for
            clients. Support Staff: read-only ticket rollup, works tickets in Helpdesk.
          </p>
          <Button variant="solid" @click="addMember">Send Invite</Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { createResource, call } from 'frappe-ui'

const ROLE_OPTIONS = [
  'Command Center Super Admin',
  'Command Center Admin',
  'Command Center Support Staff',
]

const team = createResource({
  url: 'command_center.api.users.list_team',
  auto: true,
})

const showAddDialog = ref(false)
const newMember = ref({ full_name: '', email: '', role: 'Command Center Admin' })

function openAddDialog() {
  newMember.value = { full_name: '', email: '', role: 'Command Center Admin' }
  showAddDialog.value = true
}

async function addMember() {
  if (!newMember.value.email || !newMember.value.full_name) return
  await call('command_center.api.users.add_team_member', { ...newMember.value })
  showAddDialog.value = false
  team.reload()
}

// A team member can technically hold more than one Command Center role (e.g. Administrator
// itself does); the select shows/edits the highest-privilege one they currently have.
function primaryRole(u) {
  return ROLE_OPTIONS.find((r) => u.roles.includes(r)) || ROLE_OPTIONS[1]
}

async function changeRole(u, role) {
  if (role === primaryRole(u)) return
  await call('command_center.api.users.update_team_member_role', { email: u.email, role })
  team.reload()
}

async function toggleStatus(u) {
  await call('command_center.api.users.set_team_member_status', {
    email: u.email,
    enabled: u.enabled ? 0 : 1,
  })
  team.reload()
}

const showPasswordDialog = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')

async function resetPassword(u) {
  const r = await call('command_center.api.users.reset_team_member_password', { email: u.email })
  resetTarget.value = u
  newPassword.value = r.new_password
  showPasswordDialog.value = true
}

function copyPassword() {
  navigator.clipboard?.writeText(newPassword.value)
}
</script>
