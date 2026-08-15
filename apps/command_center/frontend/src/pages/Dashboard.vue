<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-semibold">Dashboard</h1>

    <div v-if="summary.data" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">Active Sites</div>
        <div class="text-2xl font-semibold">{{ summary.data.site_by_status.Active || 0 }}</div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">Provisioning</div>
        <div class="text-2xl font-semibold">{{ summary.data.site_by_status.Provisioning || 0 }}</div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">Pending Approval</div>
        <div class="text-2xl font-semibold">{{ summary.data.pending_requests }}</div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="text-sm text-ink-gray-5">Failed Sites</div>
        <div class="text-2xl font-semibold text-ink-red-4">{{ summary.data.site_by_status.Failed || 0 }}</div>
      </div>
    </div>

    <div v-if="summary.data && summary.data.server_count" class="rounded-lg border p-4">
      <div class="mb-2 text-sm font-medium text-ink-gray-5">Fleet Load (avg across {{ summary.data.server_count }} servers)</div>
      <div class="flex gap-6 text-sm">
        <div>CPU: <span class="font-semibold">{{ summary.data.fleet_avg.cpu }}%</span></div>
        <div>RAM: <span class="font-semibold">{{ summary.data.fleet_avg.ram }}%</span></div>
        <div>Disk: <span class="font-semibold">{{ summary.data.fleet_avg.disk }}%</span></div>
      </div>
    </div>

    <div v-if="summary.data && summary.data.recent_failed_deploys.length" class="rounded-lg border p-4">
      <div class="mb-2 text-sm font-medium text-ink-gray-5">Recent Deployment Failures</div>
      <ul class="space-y-1 text-sm">
        <li v-for="log in summary.data.recent_failed_deploys" :key="log.name">
          {{ log.site || log.site_request }} — {{ log.step }} ({{ log.timestamp }})
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { createResource } from 'frappe-ui'

const summary = createResource({
  url: 'command_center.api.dashboard.get_summary',
  auto: true,
})
</script>
