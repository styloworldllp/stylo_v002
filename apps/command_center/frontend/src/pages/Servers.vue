<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-semibold">Servers</h1>
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b text-left text-ink-gray-5">
          <th class="py-2">Server</th>
          <th>Hosting</th>
          <th>CPU</th>
          <th>RAM</th>
          <th>Disk</th>
          <th>Sites</th>
          <th>Freshness</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in recommendation.data?.candidates || []" :key="c.server" class="border-b">
          <td class="py-2">
            <div>{{ c.label || c.server }}</div>
            <div class="text-xs text-ink-gray-5">{{ findServer(c.server)?.host || '—' }}</div>
          </td>
          <td>{{ findServer(c.server)?.hosting_type || '—' }}</td>
          <td>{{ c.score !== null ? findServer(c.server)?.last_cpu_percent : '—' }}%</td>
          <td>{{ findServer(c.server)?.last_ram_percent ?? '—' }}%</td>
          <td>{{ findServer(c.server)?.last_disk_percent ?? '—' }}%</td>
          <td>{{ c.site_count }} / {{ c.max_sites }}</td>
          <td>
            <Badge :theme="c.stale ? 'orange' : 'green'">{{ c.stale ? 'Stale' : 'Live' }}</Badge>
          </td>
          <td>
            <Button variant="outline" size="sm" @click="openCommandDialog(c.server)">
              Run Command
            </Button>
          </td>
        </tr>
      </tbody>
    </table>

    <Dialog v-model="showCommandDialog" :options="{ title: `Run Command — ${commandServer}`, size: 'xl' }">
      <template #body-content>
        <div class="space-y-3">
          <p class="text-xs text-ink-gray-5">
            Runs directly over SSH on this server, no confirmation beyond this dialog.
            Every run is logged to Deploy Log.
          </p>
          <p v-if="sitesOnServer.length" class="text-xs text-ink-gray-5">
            Sites on this server: <span class="font-medium">{{ sitesOnServer.join(', ') }}</span>
            — a `bench --site` command only works for one of these.
          </p>
          <FormControl
            label="Command"
            v-model="commandText"
            placeholder="e.g. bench --site nhs.stylo.io list-apps"
            @keyup.enter="runCommand"
          />
          <Button variant="solid" :loading="running" @click="runCommand">Run</Button>
          <div v-if="commandOutput !== null">
            <div class="mb-1 text-xs font-medium text-ink-gray-5">
              Exit code: {{ commandExitCode }}
            </div>
            <pre class="max-h-80 overflow-auto rounded bg-surface-gray-2 p-3 text-xs">{{ commandOutput }}</pre>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { createResource, createListResource, call } from 'frappe-ui'

const recommendation = createResource({
  url: 'command_center.api.server.get_server_recommendation',
  auto: true,
})

const servers = createListResource({
  doctype: 'Server',
  fields: ['name', 'host', 'hosting_type', 'last_cpu_percent', 'last_ram_percent', 'last_disk_percent'],
  pageLength: 100,
  auto: true,
})

const allSites = createListResource({
  doctype: 'Site',
  fields: ['sitename', 'server'],
  pageLength: 200,
  auto: true,
})

function findServer(name) {
  return servers.data?.find((s) => s.name === name)
}

const showCommandDialog = ref(false)
const commandServer = ref('')
const commandText = ref('')
const commandOutput = ref(null)
const commandExitCode = ref(null)
const running = ref(false)
const sitesOnServer = ref([])

function openCommandDialog(server) {
  commandServer.value = server
  commandText.value = ''
  commandOutput.value = null
  commandExitCode.value = null
  sitesOnServer.value = (allSites.data || [])
    .filter((s) => s.server === server)
    .map((s) => s.sitename)
  showCommandDialog.value = true
}

async function runCommand() {
  if (!commandText.value.trim()) return
  running.value = true
  try {
    const result = await call('command_center.api.console.run_command', {
      server: commandServer.value,
      command: commandText.value,
    })
    commandExitCode.value = result.exit_code
    commandOutput.value = (result.stdout || '') + (result.stderr ? '\n--- stderr ---\n' + result.stderr : '')
  } finally {
    running.value = false
  }
}
</script>
