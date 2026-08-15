<template>
  <div v-if="site.doc" class="space-y-4">
    <h1 class="text-2xl font-semibold">{{ site.doc.sitename }}</h1>
    <div class="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
      <div><span class="text-ink-gray-5">Client:</span> {{ site.doc.client_name }}</div>
      <div><span class="text-ink-gray-5">Server:</span> {{ site.doc.server }}</div>
      <div><span class="text-ink-gray-5">Status:</span> {{ site.doc.status }}</div>
      <div><span class="text-ink-gray-5">License:</span> {{ site.doc.license || '—' }}</div>
    </div>
    <div>
      <div class="mb-2 flex items-center justify-between">
        <div class="text-sm font-medium text-ink-gray-5">Installed Modules</div>
        <Button v-if="session.isSuperAdmin" variant="outline" size="sm" @click="openInstallDialog">
          Install Module
        </Button>
      </div>
      <table class="w-full text-sm">
        <tbody>
          <tr v-for="m in site.doc.modules" :key="m.name" class="border-b">
            <td class="py-1">{{ m.module_key }}</td>
            <td class="py-1 text-ink-gray-5">{{ m.installed_on }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="showInstallDialog" :options="{ title: 'Install Module' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl
            label="Module"
            type="select"
            v-model="moduleToInstall"
            :options="availableModules"
          />
          <p class="text-xs text-ink-gray-5">
            Runs in the background over SSH — installs the app(s), runs post-install, and
            restarts the site's web service. Check the Dashboard for failures.
          </p>
          <Button variant="solid" @click="installModule">Start Install</Button>
        </div>
      </template>
    </Dialog>

    <DeployProgress
      v-model="showProgress"
      title="Installing Module"
      :site="props.siteName"
      :since="progressSince"
      @update:model-value="(open) => !open && site.reload()"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createDocumentResource, createResource, call } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import DeployProgress from '@/components/DeployProgress.vue'

const props = defineProps({ siteName: String })
const session = sessionStore()

const site = createDocumentResource({
  doctype: 'Site',
  name: props.siteName,
  auto: true,
})

const allModules = createResource({
  url: 'command_center.module_map.get_module_choices',
  auto: true,
})

const showInstallDialog = ref(false)
const moduleToInstall = ref('')
const showProgress = ref(false)
const progressSince = ref(null)

const availableModules = computed(() => {
  const installed = new Set((site.doc?.modules || []).map((m) => m.module_key))
  return (allModules.data || []).filter((m) => !installed.has(m))
})

function openInstallDialog() {
  moduleToInstall.value = availableModules.value[0] || ''
  showInstallDialog.value = true
}

async function installModule() {
  if (!moduleToInstall.value) return
  // Captured before enqueueing so get_deploy_progress can exclude this site's Deploy Log
  // history from any module installed before now.
  progressSince.value = await call('command_center.api.deploy.get_server_time')
  await call('command_center.api.deploy.request_add_module', {
    site: props.siteName,
    module_key: moduleToInstall.value,
  })
  showInstallDialog.value = false
  showProgress.value = true
}
</script>
