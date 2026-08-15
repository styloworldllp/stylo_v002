<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-semibold">Support</h1>
    <p class="text-sm text-ink-gray-5">
      Rollup of Helpdesk tickets by site. Click a ticket to work it in Helpdesk.
    </p>
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b text-left text-ink-gray-5">
          <th class="py-2">Ticket</th>
          <th>Site</th>
          <th>Subject</th>
          <th>Status</th>
          <th>Priority</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tickets.data" :key="t.name" class="border-b">
          <td class="py-2">
            <a class="text-ink-blue-3 underline" :href="`/helpdesk/tickets/${t.name}`" target="_blank">
              {{ t.name }}
            </a>
          </td>
          <td>{{ t.site || '—' }}</td>
          <td>{{ t.subject }}</td>
          <td>{{ t.status }}</td>
          <td>{{ t.priority }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const tickets = createResource({
  url: 'command_center.api.tickets.get_tickets_by_site',
  auto: true,
})
</script>
