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
          <th>Roles</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="u in team.data" :key="u.email" class="border-b">
          <td class="py-2">{{ u.full_name }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.roles.join(', ') }}</td>
          <td><Badge :theme="u.enabled ? 'green' : 'gray'">{{ u.enabled ? 'Active' : 'Disabled' }}</Badge></td>
        </tr>
      </tbody>
    </table>

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
</script>
