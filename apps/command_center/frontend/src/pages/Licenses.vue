<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-semibold">Licenses</h1>
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b text-left text-ink-gray-5">
          <th class="py-2">License</th>
          <th>Site</th>
          <th>Client</th>
          <th>Entitled Modules</th>
          <th>End Date</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="l in licenses.data" :key="l.name" class="border-b">
          <td class="py-2">{{ l.name }}</td>
          <td>{{ l.site }}</td>
          <td>{{ l.client_name }}</td>
          <td>{{ (l.modules || []).join(', ') || '—' }}</td>
          <td>{{ l.end_date || '—' }}</td>
          <td><Badge :theme="statusTheme(l.status)">{{ l.status }}</Badge></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const licenses = createResource({
  url: 'command_center.api.licenses.get_licenses',
  auto: true,
})

function statusTheme(status) {
  return {
    Demo: 'blue',
    Active: 'green',
    'Grace Period': 'orange',
    Suspended: 'gray',
    Expired: 'red',
    Terminated: 'red',
  }[status] || 'gray'
}
</script>
