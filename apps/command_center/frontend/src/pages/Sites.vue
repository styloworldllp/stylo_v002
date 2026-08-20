<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Sites</h1>
      <Button v-if="session.isSuperAdmin" variant="outline" @click="openImportDialog">
        Import Existing Site
      </Button>
    </div>
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b text-left text-ink-gray-5">
          <th class="py-2">Site</th>
          <th>Client</th>
          <th>Server</th>
          <th>Modules</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="site in sites.data"
          :key="site.name"
          class="cursor-pointer border-b hover:bg-surface-gray-1"
          @click="$router.push(`/command-center/sites/${site.name}`)"
        >
          <td class="py-2">{{ site.sitename }}</td>
          <td>{{ site.client_name }}</td>
          <td>{{ site.server }}</td>
          <td>{{ site.module_count }} installed</td>
          <td>
            <Badge
              :theme="statusTheme(site.status)"
              :class="site.status === 'Failed' ? 'cursor-pointer' : ''"
              @click.stop="site.status === 'Failed' && viewLog(site.name)"
            >
              {{ site.status }}
            </Badge>
          </td>
        </tr>
      </tbody>
    </table>

    <Dialog v-model="showImportDialog" :options="{ title: 'Import Existing Site' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl label="Server" type="select" v-model="importForm.server" :options="serverOptions" />
          <FormControl label="Site Name" v-model="importForm.sitename" placeholder="e.g. nhs.stylo.io" />
          <FormControl label="Client Name" v-model="importForm.client_name" />
          <p class="text-xs text-ink-gray-5">
            SSHes into the server, detects installed apps via `bench list-apps`, and creates a
            matching Site + Stylo License (Active status) reflecting what's actually there.
            Runs in the background — progress opens automatically once started.
          </p>
          <p v-if="importError" class="text-xs text-ink-red-4">{{ importError }}</p>
          <Button variant="solid" :loading="importing" @click="importSite">Import</Button>
        </div>
      </template>
    </Dialog>

    <DeployProgress
      v-model="showProgress"
      :title="progressTitle"
      :site="progressSitename"
      :since="progressSince"
      @update:model-value="(open) => !open && sites.reload()"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createListResource, createResource, call } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import DeployProgress from '@/components/DeployProgress.vue'

const session = sessionStore()

const sites = createResource({
  url: 'command_center.api.sites.list_sites',
  auto: true,
})

const servers = createListResource({
  doctype: 'Server',
  fields: ['name'],
  pageLength: 100,
  auto: session.isSuperAdmin,
})
const serverOptions = computed(() => (servers.data || []).map((s) => s.name))

const showImportDialog = ref(false)
const importForm = ref({ server: '', sitename: '', client_name: '' })
const importing = ref(false)
const importError = ref('')
const showProgress = ref(false)
const progressSitename = ref('')
const progressSince = ref(null)
const progressTitle = ref('Importing Site')

function openImportDialog() {
  importForm.value = { server: serverOptions.value[0] || '', sitename: '', client_name: '' }
  importError.value = ''
  showImportDialog.value = true
}

async function importSite() {
  if (!importForm.value.server || !importForm.value.sitename) return
  importing.value = true
  importError.value = ''
  try {
    progressSince.value = await call('command_center.api.deploy.get_server_time')
    progressTitle.value = 'Importing Site'
    await call('command_center.api.sites.request_import_site', { ...importForm.value })
    progressSitename.value = importForm.value.sitename
    showImportDialog.value = false
    showProgress.value = true
  } catch (e) {
    importError.value = e.messages?.join(', ') || e.message || 'Import failed to start'
  } finally {
    importing.value = false
  }
}

function viewLog(sitename) {
  progressTitle.value = 'Deploy Log'
  progressSitename.value = sitename
  progressSince.value = null
  showProgress.value = true
}

function statusTheme(status) {
  return { Active: 'green', Provisioning: 'blue', Suspended: 'orange', Failed: 'red' }[status] || 'gray'
}
</script>
